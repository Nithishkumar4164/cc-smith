# Round 1: On-device-first, privacy-first architecture

**Position.** The phone keeps the user's money data (ledger, holdings, caps, milestones, preferences) and runs the deterministic engine. The backend is a **user-agnostic card intelligence service**. It builds the Card Profile knowledge base and publishes **signed, versioned rule bundles** plus a launch/change feed. Every user downloads the same bundles. By default no PII leaves the device.

**Doc conflict.** `README.md` and `ideation.md` → "Decisions so far" say *Flutter, iOS + Android*. Commit `0766484` said *Android-only, sideloaded*. Commit `dc84212` then moved to iOS + Android for the public product. **My assumption:** Flutter, with Android as the primary target (capture, QR, UPI hand-off). iOS is a reduced client that supports manual entry and statement upload (`ideation.md` → "The app is the only surface"). The hackathon demo is Android only. This proposal also overturns one stated decision: "the app is a thin client" (`ideation.md`, same section). I defend that reversal below.

---

## 1. Orchestration topology and LLM steps

```
┌──────────────── PHONE (Flutter; Android-first) ─────────────────┐
│ Capture: NotificationListener (Kotlin channel) · QR · manual · CSV│
│   → parser_pack (signed templates) → Ledger (SQLCipher/Drift)     │
│ smith_engine (pure Dart): score · route · caps · milestones ·     │
│   portfolio optimise · backtest · replan diff · launch match      │
│ WorkManager jobs → local notifications                            │
│ Chat: capsule builder + client-side tool executor                 │
└──────▲ signed bundles + feeds (CDN, identical for all) ──────┬────┘
       │ FCM topic ping "bundle:v412" (no user id)            │ opt-in only:
┌──────┴──────── CARD INTELLIGENCE (Python, stateless re users)┴────┐
│ serp_gateway → fetcher → extract* → diff → HRQ → bundle publisher │
│ news/launch sweeps* · merchant_classify* · chat_relay (no storage)│
│ Postgres: card_versions, evidence, review_queue, merchant_pack,   │
│ serp_cache, credit_ledger, launch_feed      (NO user tables)      │
└───────────────────────────────────────────────────────────────────┘
 * = bounded LLM step
```

The backbone is a set of workflows, not autonomous agents. This follows `architecture.md` §1.7 and Option B: deterministic first, with one conversational agent. The difference from Option B is **where the engine runs and where the tools execute**.

| LLM step | Where | Model tier (per `models.md` §4) |
|---|---|---|
| `extract_profile` (T&C/MITC/AI Mode → schema with `source_ref`) | server, batch | Opus 5.5 Batch (Sonnet 5.5 if the 10-card gold set passes) |
| `triage_news` / `dedupe_launch` | server | Haiku 4.5 (model ID in config: retirement "not before 2026-10-15") → local `qwen3:8b` fallback |
| `classify_merchant` (name + Maps types → category) | server, on a merchant name only | Haiku 4.5 / `qwen3:8b` |
| `review_assist`, `eval_judge` | server, offline | Opus 5.5 |
| `chat` (Card Finder Q&A, "why?", Eligibility narrative) | server relay; **tools run on the phone** | Sonnet 5.5, low effort |
| `parse_unknown_alert` | phone, P2 | on-device small model (Gemini Nano via ML Kit GenAI / Gemma; **availability unverified**), else ask the user |

**Client-side tools.** The chat agent's tools (`simulate_rewards`, `optimize_portfolio`, `cap_status`, `renewal_review`, see `architecture.md` §7) are declared to Claude by the relay. Each `tool_use` block is forwarded to the app, which runs it locally and returns a `tool_result`. Claude sees only aggregated results. The relay keeps no conversation store. **Change my mind if** tool round trips over mobile networks push chat latency past ~6 s at p95.

## 2. Flows and P0 features → components

| Flow | Features | Components (phone ▸ server) |
|---|---|---|
| **Card Profile** | A1–A4 (P0), A5–A8, H1 (P0) | ▸ `bundle_sync`, signature check, provenance UI · server: gateway, fetcher, extractor, HRQ, `bundle_publisher`, public changelog |
| **Card Finder** | B1, B2, B5, B6, B7 (P0), B3, B4 | ▸ `smith_engine.optimize_portfolio` (1–3 cards), `reality_check` (effective rate after caps, rounding and minimums), hard-category table · no server call |
| **Checkout Advisor** | D1 typed (P0), D1 scan, D2, D3, D5, D6, D8 | ▸ `pay_pick` (<50 ms), UPI QR parse (`pa`, `pn`, `mc`), `upi://pay` hand-off, local `merchant_map` · server: `merchant_pack` (shared merchant→category seed) |
| **Coach: Eligibility Path** | C1, C2, C5 | ▸ rule evaluation against `eligibility` bundle fields, enquiry log, LTF proof vault (local files) · server: eligibility routes from AI Mode + community sources, reviewed in HRQ |
| **Coach: Cap Watch** | E2, E3, E4, F4 | ▸ cycle-correct counters from the ledger, threshold nudges, replan diff when the bundle changes |
| **Coach: Renewal Review** | F2, B3, F3 | ▸ T-45-day WorkManager job → keep/convert/close simulation on the real ledger |
| **Launch Radar** | F6, A7, G2 | server: sweeps → profile → HRQ → `launch_feed` entry · ▸ match on device: marginal gain ≥ ₹2,000 and >15% of fee (`architecture.md` §4.4) → local notification |

Remaining P0 features: **E1 manual** goes to the ledger as estimated entries (`ideation.md` → "Shape of the system" #4). **H3** gets an on-device consent screen, a "data on this phone" viewer and a published data map. **B7** becomes structural: bundles carry no payout fields, and the payout disclosure ships as a separate `affiliate.json` that the engine never imports. An open-source engine on the user's device makes that independence checkable (pain point #16, `features.md`).

## 3. App ↔ backend split, offline behaviour

**On the phone:**
- Notification capture on Android. This uses `NotificationListenerService`, not `READ_SMS`, which Play restricts to default SMS handlers (`ideation.md` → "Data capture under platform rules").
- QR scan, UPI hand-off, the ledger, all scoring and every Coach job.

**On the server:** card knowledge, SerpApi, extraction, review, merchant classification, and the chat relay.

**Offline:** Checkout Advisor, Card Finder, Cap Watch and Renewal Review all work with no network, using the last verified bundle. Offline is where pay-time actually happens (basements, kirana stores). The UI shows "bundle as of 2026-10-05". If the bundle is more than 14 days old, the app shows a staleness banner. Chat and Launch Radar need the network.

D1's 1-second budget is met by construction, with no network hop (compare the Redis precompute in `architecture.md` §4.3).

## 4. Data model and provenance

**Server (Postgres), all user-agnostic:**

| Table | Key fields |
|---|---|
| `card_field_versions` | `card_id, field_path, value, source_url, source_type, evidence_id, as_of, effective_from, pending_change, version, approved_by` |
| `evidence` | `sha256, url, fetched_at, raw_blob_ref, serp_search_id` (the local copy is canonical; the Search Archive expires at 31 days, `platform_offerings.md` §4.2) |
| `review_queue` | per `architecture.md` §2.1 |
| `merchant_pack` | `merchant_key (VPA pattern / normalised name), category, mcc_family_guess, source, confidence` |
| `launch_feed` | `card_id, first_seen, sources[], profile_version` |
| `serp_cache`, `credit_ledger` | per `architecture.md` §2.2 |

**Bundle** (`cards-v412.json.zst` + Ed25519 signature; the public key is pinned in the app):
- All cards, so the server never learns which cards a user holds. The size is roughly 1–3 MB for 300 cards (estimate).
- A rule DSL covering MCC rates, caps with their reset basis, rounding, channel and minimums (A2).
- `parser_pack` with per-bank alert templates.
- `merchant_pack`.
- A `schema_version`.
- Deltas keyed on version.

A field with no source stays null, and the engine reports "can't assess" (A1).

**Phone (Drift over SQLCipher; key in Android Keystore):**
- `ledger(txn_id, ts, amount, card_product_id, last4?, merchant_raw, merchant_key, category, channel, source: estimate|notif|statement|manual, superseded_by)`
- `holdings` (statement day, renewal month, LTF proof refs)
- `prefs` (hard constraints and valuations)
- `counters` (derived; rebuilt from the ledger)
- `merchant_map_personal` (the user's own MCC observations; this is the "personal merchant map" from `ideation.md`)
- `vault` (C5/F7 screenshots)

Card numbers are never stored (`ideation.md` → "Compliance and trust").

## 5. Data acquisition

Everything goes through `serp_gateway`, using the design in `platform_offerings.md` §4: a local cache before SerpApi's 1-hour cache, a budget guard from the free Account API, an allow-list, restrictor presets and async weekly sweeps. **No query ever contains user data** (`serpapi-compatibility.md` → H3).

| Flow | Engines |
|---|---|
| Card Profile | `google` with `site:`/`filetype:pdf` and `search_index mode=deep` for URL discovery; `google_ai_mode` (JSON + restrictor) for cited summaries; **own fetcher** (httpx + trafilatura/pypdf) for T&C, because SerpApi cannot fetch pages (`platform_offerings.md` §0) |
| Launch Radar | `google_news`/`google_news_light` weekly; `google_ads_transparency_center` (region 2356) per issuer, the "Strong" pick in `engines_for_flows.md` §3; `google_play` new-app diff; `youtube_channel` → free RSS |
| Cap Watch (rule changes) | `google_light` `site:technofino.in` / `site:reddit.com/r/CreditCardsIndia`; `bing_news` as a second source; these are signals only and trigger re-extraction |
| Eligibility Path | `google_ai_mode` (continuable) for FD-backed and card-to-card routes |
| Merchant pack | `google_maps` (0.72 s), only for merchant names absent from the pack, batched |

**Hackathon budget (250 free + 50/h, no in-event top-ups, `hackathon_credits_rules.md` Q1):** profiles for 20 cards ≈ 60, launch/news ≈ 30, merchants ≈ 25, eligibility ≈ 15, reserve ≈ 40, dev ≈ 80. Replay fixtures are used for CI.

**Non-SerpApi sources:**
- Issuer pages and PDFs (own fetcher)
- Reddit via the Arctic Shift archive and TechnoFino via snippets (`serpapi-compatibility.md` → Gaps)
- Official Google Places as the D2 primary (that note's recommendation)
- User-submitted corrections (A8)
- Later, Account Aggregator, which needs a regulated FIU partner and is deferred

## 6. LLM strategy and cost

The LLM never computes money (`ideation.md` → "Core thesis"). Server LLM cost is the same as `models.md` §5 (~$55–65/month at 100 users) minus the explainer. "Why this card?" is **templated from engine `reason_codes`** on the device, so it costs nothing and works offline. Chat capsules are small (≈2–4k tokens, aggregated), so cost per turn drops.

**What leaves the phone for chat (opt-in, previewable):**
- Category-level monthly spends, rounded to ₹500
- Held card product IDs
- Preference answers

**What never leaves:** merchant names, transactions, last-4 digits, names, phone numbers.

Anthropic has **no India region** (`inference_geo` is global or US only; `models.md` §1), so minimising what is sent is the only lever. Fable 5.x is excluded because it requires 30-day retention.

## 7. Scheduling, review, notifications

**Server.** Hackathon: APScheduler + SQLite. Product: Postgres + DBOS, which gives durable Python steps with no separate cluster (`frameworks.md` §"Local-first"). Jobs: `weekly_launch_scout`, `nightly_profile_refresh` (expired fields only), `daily_news_scan`, `publish_bundle`. Idempotency keys are on (card, field, new value).

**HRQ.** Every changed field waits for a human: an admin page shows old vs new, the evidence and the source. On approval the field joins the **next signed bundle**. Nothing reaches users without review (`architecture.md` §2.3).

**Device fan-out:**
1. On publish, FCM sends a **topic** message `bundles` (one message, no per-user targeting).
2. WorkManager syncs, re-runs the replan diff (F4) and launch match.
3. The app raises a **local** notification only if the user's routing changed or a launch beats their stack.

**Local jobs:** due dates (F1), T-45 renewal, cycle resets, milestone "₹X to go".

**iOS:** silent push is throttled, so iOS refreshes on `BGAppRefreshTask` and on app open. Alerts there can lag.

## 8. Security, privacy, compliance

| Concern (source) | Design response |
|---|---|
| **DPDP Act** (`ideation.md` → "Compliance and trust"; H3) | We remain the Data Fiduciary for what the app processes, but the server holds no personal data by default, so there is no user database to breach, export or delete. Consent notice at onboarding (itemised: notifications, chat capsule, crash logs), withdrawal per toggle, deletion = on-device wipe plus revoking any backup. Age gate (18+, avoiding verifiable parental consent). DPDP Rules 2025 phased timelines and the consent-manager role: **verify with counsel**. |
| **Play SMS policy** | No `READ_SMS`. Notification-listener access with prominent in-app disclosure before the system prompt. Parsing happens on the device, so the Data Safety form can say transaction data is "not collected" (Play defines collection as transmission off-device). The Play **Financial features declaration** still applies. The listener faces review risk; see Risks. |
| **RBI / localisation** | The RBI 2018 payment-data storage circular binds payment system operators. cc-smith moves no money (`ideation.md` → "Companion app"), so it is likely out of scope. Even so, with no server-side financial data there is nothing to localise, and the posture survives a stricter reading. A future AA integration would need a regulated FIU partner. |
| **Trust** (`reddit-…pain-points.md` 11c, `technofino-…pain-points.md` 11c: distrust of CRED-style aggregators) | "Your transactions never leave your phone" is a claim users can verify (network inspector, open-source engine). This differentiates from CRED/SaveSage (`ideation.md` → "Competition"). |
| Bundle integrity | Ed25519 signing with the key in cloud KMS; the app rejects unsigned bundles and downgrades; HTTPS + certificate pinning on the relay |
| Chat relay | Rate limits per anonymous install token (Play Integrity attestation), no storage, PII regex scrubber as a second guard |
| Merchant lookups | Opt-in, name + city only, batched daily, unauthenticated, to avoid linking lookups to a user |

## 9. Evals, testing, observability

- **One engine, one test suite.** `smith_engine` is pure Dart. Golden cases come from issuer T&Cs: cap boundaries, ₹67 rounding (`reddit-…` 1d), "once per cycle" rules, refund reversals. Property tests cover cap monotonicity. The same suite **gates every bundle publish**: CI runs `dart test` against the candidate bundle.
- **Parser packs.** A corpus of redacted alert texts from the team's own phones, with precision/recall per bank. A failing template blocks publish.
- **Server LLM nodes.** Use the per-node evals in `architecture.md` §4.7: extraction gold set (20–30 cards), merchant accuracy (~200 merchants), news triage precision/recall, chat judge plus the "every ₹ figure appears in tool output" check.
- **Observability.**
  - Server: OpenTelemetry + Langfuse, the credit dashboard, HRQ age.
  - Device: opt-in, PII-scrubbed crash and performance telemetry (Sentry) tagged with `engine_version` and `bundle_version`.
  - A **"Report wrong answer"** button sends a redacted repro (rule IDs, amounts bucketed) with explicit consent.
- **Analytics.** Only coarse opt-in feature counters. There is no funnel at the level of user spend.

## 10. Delivery plan

**Stack:**
- App: Flutter 3.x, Drift + SQLCipher, `mobile_scanner`, `workmanager`, `flutter_local_notifications`, Kotlin platform channel for the listener.
- Engine: `smith_engine` (pure Dart package).
- Backend: Python 3.12 FastAPI, Postgres (SQLite in the MVP), `serpapi` SDK, Anthropic SDK, an HTMX admin page.
- Infra: Cloudflare R2/CDN for bundles, FCM.

**Hackathon MVP (Oct 6 → submit by Oct 10, 23:59 IST):**

| Day | Deliverable |
|---|---|
| Oct 6–7 | Rule DSL + `smith_engine` + golden tests. 15–20 hand-verified cards (the team's own) as bundle v1 with provenance. App: onboarding preferences, holdings, manual spends (P0: A1–A4, B1, B2, B5–B7, E1, H1) |
| Oct 8 | Typed Checkout Advisor + QR → `upi://pay` hand-off (verify with real QRs, `ideation.md` → "Companion app"). Backend: gateway + cache + ledger, AI Mode extraction → HRQ page → signed publish → app sync |
| Oct 9 | Notification capture for 2 banks. Cap Watch + Renewal Review on a fake clock. Launch Radar sweep → feed → on-device match. Chat relay with 3 client-side tools |
| Oct 10 | Fixture-based evals, privacy screen, README (SerpApi usage), <3-minute local demo video, **submit (drafts aren't auto-submitted)** |

Cut order if behind: chat, then notification capture, then Ads Transparency.

**3-month product:**
- **M1:** 100–150 cards, delta bundles, KMS signing, parser packs for the top 10 issuers, on-device statement parsing (password-protected PDFs; library choice open), encrypted backup (user-key-wrapped, Drive appData).
- **M2:** closed beta with enthusiasts (`ideation.md` → "Open decisions" #3), A6/A7/A8 pipeline, Eligibility Path, Play policy pre-review, public changelog.
- **M3:** iOS parity (manual, statements), on-device small-model trial for unknown alerts, external privacy audit, published data map, opt-in aggregated community signals (H2) with k-anonymity thresholds.

## 11. Top risks

1. **Play review of notification-listener use** in a finance app could reject or delay the app. Mitigation: ship without capture, add it behind a separate consent, pre-submit questions to Play.
2. **Engine-on-device update lag.** Old app versions run old engine semantics. Mitigation: bundle `min_engine_version`; refuse to score with an "update app" prompt.
3. **Data loss on device change** destroys months of ledger that cap and milestone tracking depend on. Mitigation: E2E backup by M1.
4. **Parser drift** when banks change alert formats silently. Mitigation: hot-fix parser packs through bundles plus a "didn't catch this?" prompt.
5. **Wrong rules ship to every device at once.** Mitigation: HRQ, golden gate, staged rollout by bundle channel.

## Weakest points of my own proposal

- **I reverse a recorded decision** ("backend… app is a thin client"). Debuggability suffers: I cannot query a failing user's state, and support depends on users volunteering repros.
- **Product analytics and the data moat are weaker.** There is no server ledger for backtests across users, crowd MCC maps (D2) or rejection intelligence (C3). Those need opt-in aggregation that will have low uptake.
- **Engine portability.** Dart rules out Python reuse on the server. The future web recommender (`ideation.md` → "Web recommender") would need a Dart-compiled JS/WASM build or a second engine, and the duplication I avoided comes back.
- **The 4-day timeline is tight.** A Kotlin listener and a signing pipeline add more surface than a thin client would.
- **iOS is second-class.** It has no capture and alerts lag.
- **Chat cannot answer transaction-level questions** ("why did Zomato earn nothing?") without sending transaction data. That is either a consent escalation per question or a weaker answer.
- **I would change my mind if** Play rejects listener use for this category, if beta users mostly want multi-device or web access, or if an AA partnership makes server-side ledgers both compliant and expected.
