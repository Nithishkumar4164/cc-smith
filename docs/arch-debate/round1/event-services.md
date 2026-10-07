# Round 1: Event-driven services + MCP tool layer

Position: cc-smith is a set of bounded services (Card Knowledge, Rewards, Ledger, Signals, Notify), plus a SerpApi Gateway. They share state changes over an event bus. Every capability is exposed once, as typed functions, and published over an MCP server, so the in-app agent, Claude Desktop (ops) and n8n all use the same tools. Card knowledge is written only by jobs, and only through the review queue.

**The single-developer rule.** At the hackathon and in the first months, the "services" run as **one repo, one Postgres, one container image and several entrypoints**: `api`, `worker`, `mcp`, `admin`. Each service is a Python package with its own Postgres schema. `import-linter` contracts stop one package from importing another's internals. Reads between services are in-process function calls. **State changes travel only as events.** The bus is a table: a transactional outbox, workers claiming rows with `FOR UPDATE SKIP LOCKED`, and `LISTEN/NOTIFY` to wake them. Moving to Redis Streams or NATS later only changes the transport.

**Doc conflict.** The README and `ideation.md` → "Decisions so far" say the client is Flutter on iOS and Android. Commit `0766484` says "Android app the sole surface", but commit `dc84212` came after it and restored iOS. I assume Flutter on both platforms, Android-first. Scan, UPI hand-off and notification capture are Android-only (`ideation.md` → "The app is the only surface"). The hackathon demo is Android.

---

## 1. Orchestration topology and LLM steps

```
 Flutter app ──HTTPS──> api (FastAPI BFF) ──fn calls──> service packages
   │  local Checkout pack                    │                       │
   │                                         │ outbox rows           │
   v                                         v                       │
 FCM <── notify.worker <── events (Postgres outbox + LISTEN/NOTIFY) <┘
                               │ consumers (worker entrypoint, SKIP LOCKED)
  ┌────────────┬───────────────┼───────────────┬──────────────┐
  knowledge    rewards         ledger          signals        notify
  ingest→diff  projections     txns, caps      news/ads/forum  dedupe, quiet hrs
  →review_q    decision tables                 launch cands
       │                                             │
       └──────────── serp_gateway (only SerpApi key; cache, budget) ┘
 mcp entrypoint (FastMCP): the same tool functions, scoped per caller
   ├─ in-app chat agent (Sonnet 5.5), user scope
   ├─ Claude Desktop / Claude Code, ops scope (read + propose, never publish)
   └─ n8n, ops scope (triggers jobs through tools, never calls SerpApi directly)
 admin entrypoint: review queue UI, the only place where knowledge is published
```

| LLM step | Owner | Model |
|---|---|---|
| Chat agent (≈10 consolidated tools) | agent | Sonnet 5.5, low effort, cached system prompt and tool definitions |
| T&C / MITC extraction into the schema, with `{url, quote}` per field | knowledge.ingest | Sonnet 5.5 via Batch. Opus 5.5 re-extracts high-severity diffs |
| Review pre-annotation ("second opinion") | knowledge.review | Opus 5.5, rare |
| News, ad and forum triage → `{card_id, event_type, confidence, quote}` | signals | Haiku 4.5, with local `qwen3:8b` as fallback |
| Launch dedupe (only for ambiguous pairs) | signals | Haiku 4.5 |
| Merchant classification on a cache miss | ledger.merchant | local `qwen3:8b`. Merchant strings are user data (`models.md` §4) |
| Narrative for Coach and replan output (numbers injected, never generated) | notify / agent | Sonnet 5.5 low, or Haiku |

There is no supervisor and no multi-agent setup (`architecture.md` §1.2–1.3 and §6: a single agent with tools, workflows for batch work). Reward maths never goes through an LLM (`ideation.md` → "Core thesis").

- **Benefits.** Failures stay isolated: a broken launch scan cannot break payment advice. Each tool is written once and serves every caller. Batch flows are code, not LLM-chosen steps.
- **Costs.** Events make end-to-end flows harder to see than one graph (`architecture.md` §5.3). The design needs correlation IDs and tracing from day 1. It also has more concepts than Option B (about 3.5 days versus 3 for the hackathon, `architecture.md` §6).
- **I would change my mind if** the bus at the hackathon carries fewer than about 5 event types with one consumer each. In that case, plain function calls in Option B are honestly simpler.

## 2. Per-flow and P0 feature mapping

| Flow / feature | Components | Trigger |
|---|---|---|
| **Card Profile** (A1–A4, H1) | knowledge: `discover → fetch → extract → diff → review_item → publish`. Emits `card.version_published` | cron weekly, `signals.change_suspected`, A8 corrections |
| **Card Finder** (B1, B2, B5, B6, B7) | rewards.`recommend_portfolio`, `assess_card`, `effective_rate` (caps, minimums, rounding), and hard categories return "nothing earns" plus the lowest surcharge | API / agent tool |
| **Checkout Advisor** (D1 typed and scan, D8) | on-device pack lookup; the server `/pay` uses the same tables. Emits `payment.intent` and later `txn.recorded` | user |
| **Coach: Eligibility Path** (C1, P1) | rewards.eligibility rules → `plan_steps`, LLM narrative | user; `user.profile_changed` re-checks |
| **Coach: Cap Watch** (E2) | ledger.`cap_counter` projection on `txn.recorded` → 70/90/100% thresholds → notify; monthly rule re-check via knowledge | event + cron |
| **Coach: Renewal Review** (F2) | daily `renewal_due(T-45)` → rewards.`simulate(keep/convert/close)` → notify | cron + `card.version_published` |
| **Launch Radar** (A7, F6) | signals sweep → `launch.candidate` → knowledge builds the profile → review → on publish, rewards.`score_all_users` → notify above the threshold | weekly cron |
| **Replan** (F4) | `card.version_published` → rewards recomputes the playbook per holder → diff → notify a recap first | event |
| E1 manual entry (P0) | ledger.txn with `source=manual_estimate`; real entries supersede it | API |
| H3 privacy (P0) | consent service, purpose-tagged events, crypto-shredding (§8) | — |

B7 ranking independence is enforced by structure, not by convention. Affiliate payouts live in a `commerce` schema. The rewards Postgres role has **no grant** on that schema, so "the engine never sees payouts" (`ideation.md` → "Monetisation") is enforced by the database.

Replan, Cap Watch and Launch Radar are the same pattern (an event triggers a recompute, a diff and a notification), so event fan-out fits (`ideation.md` → "Replan flow"). The cost is ordering bugs: projections must be idempotent and versioned.

## 3. App and backend split, offline behaviour

**On the phone (Flutter, plus Kotlin for platform channels):**
- **Checkout pack.** A signed JSON per user, holding the decision table `(category, channel, amount_band) → ranked cards with cap_left`, held-card channel and UPI rules, the top 2,000 merchant mappings, and the pack's `as_of`. The phone does the lookup and simple arithmetic in under 50 ms with no network. That meets D1's "about a second" (`features.md` D1; `architecture.md` §4.3). The full engine stays in Python. Golden fixtures (JSON) run against both the Dart lookup and the Python engine in CI to catch drift.
- **QR scan.** `mobile_scanner` decodes the UPI QR (`pa`, `pn`, `mc`), picks the card, then fires the `upi://pay` intent (D8). The app also registers as a `upi://` handler.
- **Notification capture (Android).** A `NotificationListenerService` reads bank alert notifications. Parsing happens **on the device** with per-bank regex packs shipped in the pack. Only `{amount, last4, merchant_text, ts}` is uploaded. The raw text never leaves the phone (H3 "local-first capture"; `ideation.md` → "Data capture under platform rules").
- **Offline.** Advice still works from the cached pack, labelled "as of HH:MM". Captured transactions queue in `drift` (SQLite) and sync with idempotency keys. Chat and Finder need a network connection.

**On the backend:** knowledge, rewards, ledger of record, signals, notify, agent, MCP. iOS gets manual entry and statement upload only.

- **Costs.** Two code paths for advice. A stale pack after a devaluation gives wrong advice until it syncs, so `card.version_published` sends a silent FCM push that invalidates the pack.
- **I would change my mind if** measured `/pay` latency from Indian 4G is reliably under 400 ms. Server-only would then remove the Dart duplication.

## 4. Data model, storage and provenance

One Postgres 16 instance, with a schema per service. Money is stored as integer paise.

```
knowledge.card(id slug, bank, variant, network)
knowledge.field_value(card_id, path, value jsonb, evidence_id, as_of, effective_from,
        effective_to, status[published|pending|superseded], version)   -- A1: no evidence_id ⇒ excluded
knowledge.evidence(id, url, sha256, fetched_at, serp_search_id, blob_key, quote)
knowledge.review_item(id, card_id, path, old, new, evidence_ids[], severity, origin
        [ingest|correction|signal], extractor_model, status, reviewer, decided_at)
knowledge.changelog(card_id, version, diff jsonb, published_at)        -- public changelog
ledger.txn(id, user_id, holding_id, amount_paise, merchant_key, mcc, channel, ts,
        source[manual_estimate|statement|notification|email|aa], superseded_by, idem_key)
ledger.cap_counter(user_id, holding_id, bucket, cycle_start, spent, earned)  -- projection
ledger.merchant(key, place_id, category, mcc_guess, source, confidence)
ledger.user_merchant_override(user_id, key, category)
users.profile / preferences(hard_constraints, valuations) / holding(card_id, last4,
        statement_day, renewal_month) / consent(purpose, granted_at, revoked_at)
rewards.decision_table(user_id, pack_version, payload jsonb)           -- projection
signals.item(source[news|ads|forum|yt], url, iso_date, card_ids[], event_type, triage)
notify.notification(user_id, type, dedupe_key, sent_at, suppressed_reason)
ops.outbox(id, topic, key, payload, purpose, created_at, claimed_at, done_at, attempts)
ops.serp_cache / ops.credit_ledger                                       -- architecture.md §2.1
```

Pending changes are applied before scoring when `effective_from` is in the future (A1). Every value the app shows carries `as_of` and a source link (H1).

## 5. Data acquisition

The `serp_gateway` is the only holder of the SerpApi key (`platform_offerings.md` §4). It canonicalises queries and uses a durable cache. Budget guard: 45 searches an hour, with a per-purpose monthly envelope. Weekly sweeps use `async=true` plus polling of the Search Archive.

| Flow | Engines |
|---|---|
| Card Profile | `google` (`site:` / `filetype:pdf` for MITC discovery), `google_ai_mode` (JSON, restrictor, continuable) as a cited second opinion; **own fetcher** (httpx, trafilatura, pypdf) for the actual T&C (`serpapi-compatibility.md` → "Gaps") |
| Launch Radar | `google_news_light` (`so=1`), `google_ads_transparency_center` region 2356 (`engines_for_flows.md` §3), `search_index` |
| Cap Watch / devaluation signals | `google_news_light`, `google_light` with `site:technofino.in` / reddit snippets |
| Checkout merchant seed | `google_maps` → `type_ids`, async on a cache miss only, cached per place indefinitely. Official Places API in the product (`serpapi-compatibility.md` → "Recommendation") |
| Finder (P2) | `google_flights` / `google_hotels` for ₹ per point |

Hackathon budget: 250 searches a month, 50 an hour, no top-ups (`hackathon_credits_rules.md` Q1). Recorded fixtures give zero-credit dev and evals. The live split is Profile 120, Radar 40, Cap Watch 30, merchants 25, reserve 35. Sources outside SerpApi: issuer pages and PDFs, the Reddit archive API, statement PDFs, and later Account Aggregator.

## 6. LLM strategy and cost

- Direct Anthropic SDK, no framework (`architecture.md` §1.1).
- Structured outputs plus Pydantic validation, with one retry before the item goes to review as `extraction_failed`.
- Model IDs are kept in config. Haiku 4.5 is "not before 2026-10-15" for retirement (`models.md` §1).
- No forced `tool_choice` and no temperature on Sonnet or Opus 5.5.
- Send no names, card numbers or last4 to the LLM. Anthropic has no India region.

Estimated cost: about $55–65 a month at 100 users (`models.md` §5), and $20–50 for the hackathon.

## 7. Scheduling, durable execution, review and notifications

- **Hackathon:** APScheduler in `worker` writes outbox rows. Consumers are idempotent on `(topic, key)`. Retries back off, and an item moves to a DLQ after 5 attempts.
- **Product:** **DBOS** (Postgres-backed durable workflows, `frameworks.md` "Durable execution"), which adds no infrastructure, unlike Temporal.
- **Review queue.** Code does the diff. Unchanged fields only bump `as_of`. Changed values become a `review_item` with a severity (`architecture.md` §2.3). The published value keeps serving, marked `pending_change`. Approval in `admin` writes the version and the outbox event in one transaction.
- **Notify.** Dedupe keys (one per threshold per cycle), quiet hours, frequency caps, opt-outs, FCM delivery. The launch threshold is above ₹2,000 a year and above 15% of the fee.

## 8. Security, privacy and compliance

- **DPDP Act.** Consent is recorded per purpose. Every event carries a `purpose` tag, and consumers declare which purposes they may consume. Deletion has two parts. First, a `user.erased` event, and every service must implement a handler; CI fails if one is missing. Second, crypto-shredding of a per-user data key, which covers backups and the outbox history.
- **Card data.** No card numbers: product and last4 only (`ideation.md` → "Compliance and trust"). This keeps the system out of PCI scope.
- **Encryption.** At rest. Host in AWS ap-south-1.
- **MCP auth.**
  - User scope: an OAuth or JWT bearer token, and the server injects `user_id`; the model never supplies it.
  - Ops scope: a separate key, with read and `propose_correction` only.
  - **Nothing in MCP can publish card knowledge.**
- **Play policy.**
  - No `READ_SMS`. The NotificationListener is used with a prominent disclosure.
  - Data safety form.
  - The financial-features declaration.
- **RBI.** cc-smith moves no money (`ideation.md` → "Companion app"). Disclaimers on every recommendation, and affiliate disclosure (B7).
- **SerpApi.** No user data is sent to SerpApi (H3; `serpapi-compatibility.md`).

## 9. Evals, testing and observability

- **Engine.** Property and golden tests for cap boundaries, rounding, UPI rules and cycle resets.
- **Extraction.** Field precision and recall on 20–30 gold cards, plus hallucinated-field rate.
- **Triage and merchants.** Precision and recall on labelled sets (about 200 merchants).
- **Agent.** About 50 prompts mapped to expected tool sequences. A judge checks that every ₹ figure appears in the tool output (`architecture.md` §4.7, §5.3).
- **Bus.** Contract tests per event schema (Pydantic, versioned), plus a replay test: rebuild every projection from the outbox and compare.
- **Observability.** OpenTelemetry with a `correlation_id` carried through event payloads, and Langfuse for LLM spans. Dashboards: outbox lag, DLQ depth, review-queue age, credits used against budget, pack staleness.

## 10. Delivery plan

**Hackathon (Oct 7–10; submit by 20:00 IST Oct 10 because drafts are never judged):**
- **Oct 7.** Repo, schemas, outbox and worker loop (about 150 lines). Rewards engine with golden tests. 15 hand-verified cards with evidence. `/pay`.
- **Oct 8.** Gateway with cache, ledger and fixtures. Ingestion through to the review queue, plus the admin review page. Signals news and ads sweep, giving a Launch Radar candidate.
- **Oct 9.** Flutter: onboarding, Finder with line-item breakdown, Checkout (typed, QR scan, UPI hand-off). FastMCP server and the chat screen. Claude Desktop ops demo ("simulate this devaluation on all holders").
- **Oct 10.** Cap Watch and Renewal Review on a fake clock. Evals on fixtures. README, video under 3 minutes, submit.
- **Cut first if behind:** notification capture, Eligibility Path, n8n.

**3 months:**
- **Month 1.** Auth, DBOS, DPDP consent and erasure, 60 cards, reviewer roles.
- **Month 2.** Statement upload (E1), notification capture, Cap Watch live, public changelog, closed beta with TechnoFino and Reddit users (`ideation.md` → "Roadmap" steps 2–3).
- **Month 3.** Replan, Launch Radar scoring, Renewal Review, Play release, cost tuning.

**Stack:** Python 3.12, FastAPI, Pydantic, psycopg3, Postgres 16, FastMCP, Anthropic SDK, APScheduler → DBOS, Langfuse, Flutter (drift, mobile_scanner, FCM), Kotlin listener.

## 11. Top risks

1. **Wrong card facts.** Mitigated by the review queue, the gold set and `as_of` labels.
2. **Plumbing eats the hackathon.** Mitigated by the table-based bus and a hard 150-line budget for it.
3. **UPI deep links restricted by the payment apps.** Test on real QRs on day 3 (`ideation.md`).
4. **The 250-credit ceiling.** Mitigated by fixtures.
5. **Pack drift between Dart and Python.** Mitigated by shared fixtures.
6. **Play rejection over the notification listener.**

## Weakest points of my own proposal

- For a 4-day solo build, the "services" are mostly **naming and folder discipline**. The real benefits (independent deploys, team ownership, isolation under load) only show up later. Option B would ship the same demo with fewer concepts.
- **Eventual consistency is a real cost** for money advice. Between `txn.recorded` and the `cap_counter` update, the advice can be one transaction stale. Async event fan-out also makes DPDP erasure harder to prove than a single delete would be.
- **MCP adds an attack and maintenance surface**, mainly scoping and auth for the HTTP transport. Its value to end users is indirect: ops convenience and a demo "wow".
- **The on-device pack duplicates the engine logic in Dart.** Golden tests reduce that risk but don't remove it.
- **The table-based bus has a ceiling.** `LISTEN/NOTIFY` plus polling is fine for thousands of users, but not for a national launch. That migration is deferred, not avoided.
