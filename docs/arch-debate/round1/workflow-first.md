# Round 1 — Workflow-first architecture for cc-smith

Position: every flow is a deterministic workflow (code paths) with LLM calls only in bounded, schema-checked steps. One conversational agent sits in front with about ten consolidated tools. Checkout Advisor is code only. All search goes through one SerpApi gateway. A durable scheduler runs batch flows, and a human review queue (HRQ) gates every write to card facts.

**Doc conflict, and the assumption I make.** Commit `0766484` says "Android app (Flutter), sole surface". Commit `dc84212`, made three minutes later, and the current `README.md` / `ideation.md` → "Decisions so far" say "Flutter app, iOS + Android". I treat the later commit as the decision: one Flutter codebase, **Android-first**. Android gets scan, UPI hand-off and notification capture. iOS gets manual entry and statement upload (`ideation.md` → "The app is the only surface"). The hackathon ships an Android build only.

---

## 1. Orchestration topology

```
 Flutter app ──HTTPS──► FastAPI ─┬─► /pay  (Checkout Advisor: pure code, no LLM, p95 < 300 ms)
  (on-device: QR parse,          ├─► /chat (Coach Agent: Sonnet 5.5, ~10 tools) ──► workflows below
   notif parse, pay pack)        └─► /screens/* (rankings, trackers: call workflows directly)

 Workflows (plain Python step functions; checkpoint per step; idempotent)
   WF-Finder   WF-Eligibility   WF-CapWatch   WF-Renewal   WF-LaunchRadar   WF-ProfileRefresh   WF-Replan
        │              │              │             │              │                │
        └──────────────┴──── reward_engine (pure Python library) ──┴── card_kb ── review_queue
                                                                       ▲
 Scheduler (APScheduler → DBOS) ── events table ───────────────────────┘     serp_gateway ──► SerpApi
                                                                             fetcher ──► issuer pages / MITC PDFs
```

**LLM steps, and the only places they run:**

| Step | Used in | Kind | Model tier |
|---|---|---|---|
| `coach_agent` | chat screen | tool-calling loop, max 6 turns | Sonnet 5.5, effort low |
| `extract_terms` | ProfileRefresh, LaunchRadar | page text → strict JSON, with `{url, quote}` per field | Sonnet 5.5 via Batch; Opus 5.5 for gold set and disputed diffs |
| `triage_news` | CapWatch, LaunchRadar, Replan | item → `{card_ids, event_type, confidence, quote}` | Haiku 4.5 (model ID kept in config) |
| `classify_merchant` | async after /pay miss | name + Maps `types` → category enum | rules first, then local Ollama `qwen3:8b` or Haiku |
| `dedupe_launch` | LaunchRadar | ambiguous pairs only, after fuzzy match in code | Haiku 4.5 |
| `explain` | Finder, Renewal, Eligibility | engine output → prose; numbers injected, never generated | Sonnet 5.5 low (Haiku if evals pass) |
| `review_assist` | HRQ | second opinion on a diff | Opus 5.5, offline |

There are no free-roaming agents. **Why:** `research_notes/cc-smith orchestrator/architecture.md` §1.1 and §1.3 (Anthropic and OpenAI both say to start from workflows or a single agent), §1.2 ("many dependencies" is a multi-agent anti-pattern; flows share user and portfolio state), §4 (Option B) and §6 (B plus C's front agent). `ideation.md` → "Core thesis": the LLM is "never the source of card facts or the calculator".

**Benefits:** money maths is reproducible. The eval surface is per node. SerpApi spend is decided by code, not by a model. A hallucinated rate, the failure users already report (`reddit…pain-points.md` §12b, "wrong by 3x"), has no code path to reach a user.

**Costs:** an intent the tools don't cover gets a weak answer. Every new flow is engineering work, not a prompt edit.

**Would change my mind:** tool-selection evals under 90% at ~10 tools, or chat logs showing many multi-flow questions the tools can't compose.

## 2. Per-flow design and P0 feature map

| Flow | Trigger | Steps (* = LLM) | Notes |
|---|---|---|---|
| **Card Profile** (ProfileRefresh) | weekly per stale card; `news.change` event | discover URL (gateway) → fetch → `extract_terms`* → code validation (Pydantic ranges) → diff vs current → unchanged fields: bump `checked_at`; changed fields: HRQ → on approve, `profile.changed` | A field with no source stays empty (A1) |
| **Card Finder** | screen / chat | load profile + prefs → hard-constraint filter → per-category top-K prune → enumerate 1–3 card portfolios with optimal routing → marginal gain vs held stack → B5 effective-rate pass → `explain`* | ~150 cards: pruning keeps it under 100 ms |
| **Checkout Advisor** | /pay or on-device pay pack | merchant key → cache/rules/QR MCC → channel rules → offers → score held cards → template reply | Zero LLM. Unknown merchant → default card, `confidence=low`, enqueue `classify_merchant` |
| **Eligibility Path** | chat / screen | rule check per criterion → failed criteria → route table (FD-backed, card-to-card, relationship, wait N months) → dated steps → `explain`* | Routes come from the KB, sourced like any other field |
| **Cap Watch** | `payment.recorded`; monthly; news | counters by cycle (statement / calendar / odd quarter) → 70/90/100% thresholds → nudge with dedupe key; monthly cap-rule recheck → HRQ | Re-routing on approval goes through WF-Replan |
| **Renewal Review** | daily scan, T-45 days | simulate keep / convert-to-LTF / close (shift spend to the rest of the stack) on the 12-month ledger → waiver progress → `explain`* → notify | Convert is preferred over close (F2) |
| **Launch Radar** | weekly (Mon 06:00 IST) | News sweep (gateway, async) → `triage_news`* → dedupe (code, then `dedupe_launch`*) → ProfileRefresh for the new card → **HRQ before scoring** → `score_all_users` (vectorised) → notify if gain ≥ ₹2,000/yr and ≥ 15% of fee | Most SerpApi-heavy flow |

**P0 features** (`features.md` → "v1 scope"):

| Feature | Component |
|---|---|
| A1 versioned profiles, provenance | `card_kb` (field-level versions) + ProfileRefresh + HRQ |
| A2 earn rules (MCC, caps, rounding, channel) | `card_kb.earn_rules` schema + `reward_engine.rules` |
| A3 perks typed | `card_kb.perks` + `reward_engine.valuation` (user's own valuations) |
| A4 fees and waivers | `card_kb.fees` + `reward_engine.fees` |
| B1 portfolio recommendation | WF-Finder |
| B2 "Should I get X?" | WF-Finder in single-card mode (`assess_card` tool), pending devaluations applied |
| B5 reality check | `reward_engine.effective_rate()` on the user's spend pattern |
| B6 hard categories | `reward_engine` explicit "earns ₹0 here" result + surcharge table |
| B7 ranking independence | `affiliate_payouts` table in a separate schema the engine role **cannot read** (DB grants) |
| D1 which card now (typed) | Checkout Advisor |
| E1 manual ledger | `ledger` with `kind=estimated` rows |
| H1 provenance | every API fact returns `{value, source_url, as_of}`; UI renders it |
| H3 privacy | §8 |

The named Coach flows and Launch Radar are P1/P2 in `features.md`, but the hackathon needs them for "meaningful SerpApi usage" (`hackathon_credits_rules.md` Q4). The MVP therefore ships thin versions of them (§10).

## 3. App ↔ backend split

| On the phone (Flutter / Android) | On the backend |
|---|---|
| UPI QR decode (`upi://pay?pa=&pn=&mc=`): VPA, payee name, MCC when present | `reward_engine`, all workflows, `card_kb`, HRQ |
| `NotificationListenerService` + per-bank regex templates → `{amount, merchant, last4, ts}`. Raw text never leaves the device | Statement PDF parsing (P1): redact first, then parse |
| **Pay pack**: signed per-user snapshot (category × channel ranked cards, `cap_left`, held cards' marginal-rate tables, top 500 merchant keys, active offers), refreshed on every `score_table` rebuild | Pay-pack builder; `/pay` as the online path |
| UPI hand-off by Android intent with payee prefilled; register as a `upi://` handler | Merchant classification, notifications (FCM) |

**Offline:** Checkout Advisor answers from the pay pack, and its age shows ("caps as of 2 h ago"). Captured transactions queue locally and sync later. Chat, Finder and the trackers need a network.

**Why:** the ~1 s budget (`features.md` D1) and "never block on SerpApi" (`architecture.md` §4.3). Shops often have poor signal, and "local-first capture where possible" is in H3.

**Cost:** a Dart scorer duplicates part of the Python engine. I limit it to table lookup plus one cap-bounded multiply, and run shared golden vectors in both CI suites. The hackathon uses server `/pay` only.

**Would change my mind:** if `/pay` p95 over mobile networks stays under 400 ms in a field test, drop the pay pack until offline use matters.

## 4. Data model and storage

Postgres 16 (SQLite for the hackathon). Per-user tables use row-level security.

| Table | Key columns |
|---|---|
| `cards` | `card_id` slug, bank, variant, network, status |
| `card_fields` | `card_id, path` (e.g. `earn_rules.dining.cap`), `value jsonb, version, source_url, source_type (issuer_page/mitc_pdf/ai_mode/news/manual), evidence_id, effective_from, checked_at, status (live/pending/superseded)` |
| `evidence` | `sha256, url, fetched_at, bytes_ref, serp_search_id, quote` |
| `review_queue` | `card_id, path, old, new, evidence[], severity, extractor_model, status, reviewer, decided_at` |
| `card_changelog` | public view over superseded versions |
| `users`, `prefs`, `holdings` | prefs = hard constraints + valuations; holdings = `card_id, last4, statement_day, renewal_month, ltf_proof_ref` |
| `ledger` | `user_id, card_id, merchant_key, mcc, category, amount_inr, channel, ts, kind (estimated/manual/notification/statement), idempotency_key` |
| `cap_counters` | derived from the ledger; rebuildable |
| `merchant_map` | `merchant_key → category, mcc_guess, source (qr/rules/maps/llm/user/statement), confidence`; global vs per-user override |
| `score_table` | per user: `(category, channel) → ranked cards` |
| `serp_cache`, `credit_ledger`, `events`, `run_state`, `notification_outbox` | infrastructure |

Provenance is per field, not per card. A card can be half-assessed, and missing fields show "can't assess yet" (A1). **Why:** `ideation.md` → "Card knowledge base"; `architecture.md` §2.1. **Cost:** field-path rows are awkward to query; a materialised `card_profile_current` view serves the engine.

## 5. Data acquisition

The `serp_gateway` is the only holder of the key. It has an engine allow-list, India defaults (`gl=in, hl=en, google_domain=google.co.in`), a canonical-param cache key, fixed `json_restrictor` presets, a per-flow budget, an Account API guard (stop at 45 per hour), a replay mode for tests, and `search_metadata.id` persisted as evidence (`platform_offerings.md` §4.1–4.3).

| Flow | Engines | Cache TTL |
|---|---|---|
| Card Profile | `google` with `site:`/`filetype:pdf` for MITC URL discovery; `google_ai_mode` as **cross-check only** | URL 30 d |
| Cap Watch / Replan | `google_news_light` per bank `"devaluation" when:7d`; `google_light site:technofino.in` | 24 h |
| Launch Radar | `google_news` (`so=1`) generic + per issuer; optional `google_ads_transparency_center` | 7 d |
| Merchant classify | `google_maps` (product: official Google Places API first, per `serpapi-compatibility.md` → Recommendation) | 180 d |
| Card Finder / Checkout / Renewal | **none live** | — |

**Non-SerpApi sources:** our own fetcher (httpx + trafilatura; pdfplumber for MITC), Reddit archive API for community signals, user statements and corrections (A8), and the UPI QR `mc` field.

Free-tier envelope of 250 (hackathon): profile discovery 110, Launch Radar 40, Cap Watch news 25, Maps 30, demo reserve 45. Product: Developer plan ($75 / 5k).

A deliberate choice: **AI Mode is never the sole source of a published number.** It is itself an LLM summary (`architecture.md` §4.11), and only issuer pages and MITC documents carry the trust users lack (pain point 16). Here I diverge from `serpapi_tool_surface.md` §1, which makes AI Mode the primary extractor. **Cost:** fetching issuer sites is brittle (JS-heavy pages, bot walls).

## 6. LLM strategy and cost

- Direct Anthropic SDK with structured outputs (`output_config.format`) and `tool_choice: auto` + `strict`. Forced `tool_choice` returns 400 on Sonnet/Opus 5.5, and temperature can't be set (`models.md` §1).
- Every extraction field carries `{url, quote}`, because native citations can't be combined with JSON output. Code then checks that the quote appears in the fetched text.
- Explanations go through a guard: every ₹ figure and % in the prose must exist in the engine output, otherwise fall back to the template.
- Cost at ~1k active users: chat ~$75–120/month, extraction (Batch) ~$3, triage ~$5, `/pay` $0 (`architecture.md` §4.9). Hackathon spend $20–50.
- **Would change my mind:** if Haiku-class models pass the extraction gold set, run extraction on Haiku. If Haiku 4.5 retires (not before 2026-10-15, `models.md`), swap to the next small tier through config.

## 7. Scheduling, review and notifications

- **Hackathon:** APScheduler with a SQLite job store, plus a `run_state` table.
- **Product:** **DBOS Transact**: durable workflows on the same Postgres, cron schedules, steps that resume after a crash, and `recv()` to wait days for an HRQ decision with no extra server. Temporal is the upgrade path if fan-out passes ~100k users (`frameworks.md` → "Durable execution").
- **Jobs:** `launch_radar` (weekly), `profile_refresh` (nightly, stale fields only, within budget), `news_scan` (daily), `renewal_scan` (daily), `cycle_reset` (daily per statement day), `offers_rebuild` (nightly), `paypack_build` (on event).
- **HRQ:** an admin page (FastAPI + HTMX) showing old vs new, the evidence quote with a link, and approve / edit / reject. Severity routing: rate, cap or fee changes are high severity with a 24 h SLA. The current value keeps serving, flagged "under review". Approval emits `profile.changed`, which triggers WF-Replan for holders: re-route first, recommend a card last (`ideation.md` → "Replan flow").
- **Notifications:** FCM through a `notification_outbox` with a dedupe key, quiet hours (22:00–08:00 IST) and a weekly frequency cap. Launch Radar sends a notification only above the gain threshold.

## 8. Security, privacy and compliance

| Item | Design |
|---|---|
| Card numbers | Never stored. Card product + last four digits only (`ideation.md` → "Compliance and trust"). Regex strips 12–19 digit runs from every inbound payload |
| DPDP Act 2023 | Purpose-specific consent screens per input (manual, notification, statement); consent log; one-tap export and delete that cascades to the ledger and derived tables; published data map (H3). Cross-border transfer: Claude has no India region (`models.md` §1), so LLMs receive no PII: no names, VPAs or raw notifications; merchant keys only. Verify the s.16 transfer rules before launch |
| Play policy | No `READ_SMS`. `NotificationListenerService` with prominent disclosure and an in-app toggle (`ideation.md` → "Data capture under platform rules"). Gmail capture deferred because it needs a restricted-scope CASA assessment |
| RBI | We move no money and don't become a TPAP (`ideation.md` → "Companion app"). UPI hand-off only. Before taking affiliate or referral payouts, check whether issuer agent rules apply |
| Advice framing | Disclaimers; "as of" dates; payouts disclosed (B7); the engine can't read payouts (DB grant). Consumer-protection and ASCI disclosure rules on affiliate links: verify |
| Infra | India-region hosting (AWS ap-south-1); KMS encryption at rest; per-user RLS; agent rate limits; SerpApi key server-side only and never in git (a hackathon disqualification rule) |

## 9. Evals, testing and observability

- **Engine:** golden worked examples from issuer T&Cs; Hypothesis property tests (cap boundaries, ₹0 rounding floors, odd quarters, UPI exclusions); Python↔Dart parity vectors.
- **LLM nodes on replay fixtures (0 credits):**
  - `extract_terms`: 25-card gold set, field precision/recall, hallucinated-field rate, quote-present rate.
  - `classify_merchant`: 200 Indian merchants.
  - `triage_news`: 100 labelled items.
  - `explain`: number guard plus a rubric LLM judge.
  - Agent: 50 prompts → expected tool sequence.
- **End to end:** fake clock (T-45, cycle reset, cap hit) and fake SerpApi. k6 on `/pay` (p95 < 300 ms).
- **Observability:** OTel + self-hosted Langfuse; dashboards for credits by flow, cache hit rate, HRQ age, extraction failures and notification opt-outs.
- **Alerts:** credits at 80%, high-severity HRQ item older than 24 h, `/pay` p95 over 500 ms.

## 10. Delivery plan

**Hackathon** (Oct 7–10; submit by Oct 10 18:00 IST, ahead of the 23:59 deadline). Stack: Python 3.12, FastAPI, Pydantic v2, SQLite, APScheduler, Anthropic SDK, `serpapi`, httpx/trafilatura/pdfplumber, Flutter Android.

| Day | Deliverable |
|---|---|
| Oct 7 | Schema; `reward_engine` with tests; 20 hand-verified cards; `/pay`; gateway with cache and replay; record fixtures |
| Oct 8 | ProfileRefresh (discover → fetch → extract → diff → HRQ page); WF-Finder with breakdowns; Flutter onboarding + rankings screens |
| Oct 9 | Launch Radar end to end; Cap Watch on manual ledger; Renewal on fake clock; Coach Agent with 8 tools; QR scan → `/pay` → UPI intent |
| Oct 10 | Evals on fixtures, README, demo video (< 3 min, incognito check), submit |

**3-month product:**

- **M1:** Postgres + RLS, DBOS, auth, 100 cards, reviewer roles, statement upload, closed beta (`ideation.md` roadmap step 2).
- **M2:** notification capture, pay pack, trackers (E2), Replan, public changelog, user corrections.
- **M3:** Eligibility Path in full, Places API, offers index, CI evals, DPDP review, load hardening, Play listing.

## 11. Top risks

1. KB correctness and reviewer throughput: 150 cards × monthly churn depends on humans.
2. Fetching issuer pages: bot walls and JS rendering.
3. Merchant → MCC error: a Google place type is not the acquirer's MCC (`serpapi-compatibility.md` D2).
4. UPI deep-link restrictions in major apps (`ideation.md`, "to verify").
5. Play review of notification access.
6. SerpApi credits during the hackathon (250, with nothing extra before judging).
7. Affiliate revenue weakening trust.

## Weakest points of my own proposal

- **Conversational ceiling.** Open questions such as "compare Atlas vs Infinia for my Europe trip" need tools to compose in ways the workflows never anticipated. A front agent with ~10 consolidated tools may answer them rigidly or not at all.
- **Rigidity tax.** Each new flow, and each bank quirk, is code plus tests. An agentic design adapts with a prompt change. The KB schema (A2's rounding, odd quarters and own-app-only rates) will churn, and every churn touches engine, schema, extractor prompt and HRQ UI.
- **Human review is the bottleneck.** I deliberately route every changed value through humans, so freshness depends on headcount. A missed devaluation is a correctness bug that I chose to accept.
- **Two scorers.** The pay pack duplicates engine logic in Dart, and parity tests reduce the risk without removing it.
- **Demo "wow".** Judges may prefer a visibly agentic story (`architecture.md` §6 rates Option B's demo appeal "Medium"). Launch Radar is the one place to show it.
- **Fetcher-first sourcing** covers fewer cards in four days than AI Mode-first would.
