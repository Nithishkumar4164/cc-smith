# Round 1 — Position: Supervisor + specialist agents over a deterministic spine

Author: architect "multi-agent". Date: 2026-10-06.

**Claim.** cc-smith should be organised as a **supervisor (Concierge) that calls specialist agents as tools**. Each specialist has its own small toolset, its own prompt and its own structured memory. Research-heavy work (Launch Radar, Card Profile verification) fans out to parallel sub-agents. All money maths stays in the deterministic engine, which every agent reaches as a tool. This is not the "6 chatty agents" straw man in `architecture.md` §3. Three things I concede up front:
- **Checkout Advisor uses no LLM.** It runs on the phone.
- **Scheduled flows are not started by sending messages to the supervisor.** Durable workflows call the specialists directly.
- **No agent can write card facts.** Agents can only queue proposed changes for review.

**Conflicts in the source docs, and what I assume.**
- `README.md` and `ideation.md` → "Decisions so far" say the app is Flutter for iOS and Android. Commit `0766484` says "Android app the sole surface". I assume **one Flutter codebase, with Android as the only shipped target for the hackathon and beta**. iOS gets a reduced version later (manual entry and statement upload only), as `ideation.md` → "The app is the only surface" already says.
- `architecture.md` §5 mentions "web / WhatsApp" chat. That is dropped, because the app is the sole surface.
- `architecture.md` numbers the flows 1, 2, 3a, 3b, 3c and 4. In the named flows: 1 = Card Finder, 2 = Checkout Advisor, 3a/3b/3c = Eligibility Path / Cap Watch / Renewal Review, 4 = Launch Radar.

---

## 1. Orchestration topology

```
 Flutter app (Android)                         Backend (FastAPI + Pydantic AI + Temporal)
 ┌──────────────────────┐   chat / actions   ┌───────────────────────────────────────────┐
 │ Checkout Advisor     │──────────────────▶ │ CONCIERGE (supervisor)  Sonnet 5.5 low     │
 │ (on-device engine,   │                    │  agents-as-tools, never handoffs           │
 │  no LLM, offline)    │◀── score-table ─── └──┬──────┬──────┬──────┬──────┬──────┬─────┘
 │ QR decode, notif     │      sync             │      │      │      │      │      │
 │ capture, UPI handoff │              CardScout Elig  CapWatch Renewal Explainer Profile
 └──────────────────────┘              (Finder)  Path                     (guarded) Curator
                                          │       │      │       │          │       │
  Temporal schedules ─────────────────────┼───────┼──────┼───────┼──────────┤  fan-out
  (call specialists directly) ──▶ LaunchScout lead ─▶ N source workers (Haiku)│  verifiers
                                          ▼       ▼      ▼       ▼          ▼       ▼
                ┌──────────────────────────────────────────────────────────────────────┐
                │ TOOLS: reward_engine (pure Python) · card_kb (read) · queue_review  │
                │ ledger · merchant_map · serp_gateway · fetcher · notify             │
                └──────────────────────────────────────────────────────────────────────┘
```

| Agent | Job | Tools (each agent has 6 or fewer) | Model |
|---|---|---|---|
| Concierge | Works out intent, manages the conversation, combines specialist results into one reply | the specialists, `get_user_context`, `update_user_context` | Sonnet 5.5, effort low |
| CardScout | Card Finder: B1, B2, B5, B6, B3 | `list_candidate_cards`, `optimize_portfolio`, `simulate_rewards`, `get_card_profile`, `pending_changes` | Sonnet 5.5 |
| EligibilityPath | C1, C2, B4 | `check_eligibility`, `plan_prerequisites`, `enquiry_log`, `community_routes` (cached) | Opus 5.5, effort medium (`models.md` §4) |
| CapWatch | E2, F4 replan recap | `cap_status`, `replan_diff`, `notify` | Haiku 4.5 |
| RenewalReview | F2, F3 | `renewal_review`, `simulate_rewards`, `closure_checklist` | Sonnet 5.5 |
| ProfileCurator (lead) | A1–A4, A6 | `serp_gateway`, `fetch_page`, `extract_card_terms`, `queue_review` | Opus 5.5 in Batch for extraction, Sonnet 5.5 as lead |
| ↳ Verifiers ×3 | Independent cross-checks: issuer PDF, AI Mode, DDG/Brave | one source tool each | Haiku 4.5 |
| LaunchScout (lead) | F6, A7 | worker fan-out, `dedupe_launch`, `score_all_users` | Sonnet 5.5 |
| ↳ Source workers | One per source family (§5) | one engine each | Haiku 4.5 / local qwen3:8b |
| Explainer | Turns engine output into prose. A guard checks every ₹ figure against the engine output | none (pure function of its input) | Sonnet 5.5 low |
| MerchantClassifier | Classifies unknown merchants, asynchronously | rules, Maps lookup | local qwen3:8b (`models.md` §4) |

**Why this shape.**
- **The tool count will outgrow one agent.** `features.md` lists about 50 features across sections A–H. By the P1 milestone a single agent would carry 25 to 35 tools, and several of them overlap: `simulate_rewards`, `renewal_review`, `replan_diff` and `optimize_portfolio` all "compute value". That is the split trigger in the OpenAI guide: "similarity or overlap", not raw tool count (`architecture.md` §1.3).
- **Specialists are tools of the supervisor, not handoffs.** The Concierge keeps the whole conversation, and each specialist gets a typed brief and returns typed JSON. This answers Cognition's "share context" objection (`architecture.md` §1.5): no agent makes decisions the others can't see.

**I would change my mind if** a single-agent prototype with 20 or more tools matches the multi-agent version on router and trajectory evals (§9).

## 2. Per-flow design and feature map

| Flow / P0 feature | Component | LLM in path? |
|---|---|---|
| **Card Profile**: A1 versioned profiles, A2 earn rules, A3 perks, A4 fees | ProfileCurator → verifiers → `review_queue` → `card_kb` | Offline only |
| H1 provenance | `card_profile_field.source_url/as_of/evidence_id`, shown in the UI on every figure | No |
| **Card Finder**: B1 portfolio, B2 "should I get X", B5 reality check, B6 hard categories | CardScout → `optimize_portfolio` (1–3 card combinations, marginal gain against the cards already held) → Explainer | Yes (chat), but the maths is code |
| B7 ranking independence | Engine process has no database grant on the `affiliate` schema. Payout shown by the app, not by an agent | No |
| **Checkout Advisor**: D1 typed (P0), scan (P1) | On-device lookup over the synced `score_table` plus local cap counters. "Why?" calls the Explainer asynchronously | **No** |
| E1 manual ledger | App form → `ledger_txn(source=estimated)` | No |
| H3 privacy | §8 | — |
| **Eligibility Path** (C1, P1) | EligibilityPath: the rules decide pass or fail, and the agent writes the plan | Yes |
| **Cap Watch** (E2, P1) | Event `txn.recorded` → code thresholds → CapWatch writes the nudge | Wording only |
| **Renewal Review** (F2, P1) | Temporal daily scan at T−45 days → RenewalReview | Yes |
| **Launch Radar** (F6, P2, but the hackathon centrepiece) | Weekly LaunchScout fan-out → dedupe → ProfileCurator → review → `score_all_users` → notify above a threshold | Yes, offline |

The cross-flow case is where the supervisor earns its cost. Take "Should I renew Regalia Gold, and if not, what replaces it and can I get it?". That touches Renewal Review, Card Finder and Eligibility Path. The Concierge calls RenewalReview first, then CardScout, then EligibilityPath, and returns one answer. A workflow with a fixed intent router (`architecture.md` §4.11, "Graph rigidity") cannot do this without a hand-written composite graph for each combination of flows.

## 3. App ↔ backend split, offline

**On the phone (Flutter, Android):**
- **QR decode.** The UPI QR `pn`/`mc` fields carry merchant name and MCC where present (`ideation.md` → "Payment-time advice"). Small-merchant QRs often lack them, so this needs testing.
- **Checkout Advisor engine.** A Dart lookup over `score_table[category × channel × amount_band] → ranked cards`, adjusted with local `cap_left`. Target p95 under 50 ms with no network.
- **NotificationListener capture** (P1), with a prominent disclosure. `READ_SMS` is restricted (`ideation.md` → "Data capture").
- **UPI deep-link hand-off** (P1).
- **Encrypted local ledger queue** (SQLCipher).

**On the server:** all agents, the engine, the knowledge base, the SerpApi gateway and the schedules.

**Offline behaviour.**
- Checkout Advisor answers from the last synced table and shows "rates as of <date>".
- Captured transactions queue locally and sync later.
- Chat, Card Finder and Launch Radar need the network.

**Cost of this choice.** The canonical engine is Python and the phone only does lookup and subtraction. If the synced table is stale (a cap changed since the last sync), the phone can give a wrong answer. Mitigations: sync on app open and on `profile.changed` through an FCM data message, and show a staleness badge after 24 h.

## 4. Data model and provenance

| Table | Key fields |
|---|---|
| `card` / `card_version` | `card_id` (slug), variant, network, `version`, `published_at` |
| `card_profile_field` | `card_id, field_path, value_json, source_url, evidence_id, as_of, effective_from, effective_to, status (live/pending/rejected), version`. Pending devaluations are stored with a future `effective_from` (A1) |
| `evidence` | `kind` (serp/page/pdf/user_report), SerpApi `search_metadata.id`, URL, sha256, raw blob, `fetched_at`. A local copy is kept because the Search Archive expires after 31 days (`platform_offerings.md` §3) |
| `review_item` | proposed field change, verifier votes, severity, reviewer, decision |
| `user`, `preference` | hard constraints plus valuations (`ideation.md` → "Preference profile") |
| `holding` | `card_id`, optional last 4 digits, statement day, renewal month. **Never the full card number** |
| `ledger_txn` | `source` (estimated/manual/statement/notification), merchant_id, MCC, amount, channel, card_id, `expected_reward`, `actual_reward` |
| `merchant_map` | global row plus per-user override: category, MCC guess, source, confidence |
| `cap_counter`, `score_table` | derived from the ledger, recomputable |
| `agent_memory` | **namespaced per specialist and structured**, with no vector store. Examples: LaunchScout `seen_items`, ProfileCurator `source_reliability`, EligibilityPath `plan_state` per user |
| `affiliate` (separate schema) | payouts. The engine role cannot read it |

## 5. Data acquisition

All SerpApi traffic goes through one `serp_gateway`, which holds the only key. It provides: a durable cache, an Account-API budget guard, a 45-per-hour ceiling, fixed `json_restrictor` presets, and evidence persistence (`platform_offerings.md` §4).

| Flow | Engines | Monthly share of the 250 free searches |
|---|---|---|
| Card Profile | `google` (`site:`/`filetype:pdf`) and `search_index` to discover issuer URLs; `google_ai_mode` (continuable) as one verifier; DDG `search_assist` / `brave_ai_mode` as tiebreakers | 120 |
| Launch Radar | `google_ads_transparency_center` (region 2356), `google_news_light`, `bing_news`, `google_play` diff, `google_autocomplete` diff, `youtube_channel` (resolve once, then poll the free RSS) (`engines_for_flows.md` §3) | 40 |
| Cap Watch / replan | `google_news` with `when:7d`, `google_light` with `site:technofino.in` | 30 |
| Eligibility Path | `google_light` with `site:` community routes, cached | 20 |
| Merchant map | `google_maps`, used only after a cache miss and a rules miss | 20 |
| Reserve | — | 20 |

**Other sources (not SerpApi):**
- Our own fetcher (httpx + trafilatura + pdfplumber, with Playwright for JS-rendered pages) for T&C and MITC documents. SerpApi only finds pages; it does not fetch them (`serpapi-compatibility.md` → "Gaps").
- The Arctic Shift Reddit archive.
- The Google Places API, preferred for D2 (merchant → MCC map).
- User statements and user corrections (A8).

## 6. LLM strategy and cost

- **Typed boundaries.** Every specialist returns strict JSON. Tool use is `auto` + `strict`, because forced `tool_choice` returns a 400 on the 5.5 models. Temperature can't be set on Opus/Sonnet 5.5 (`models.md` §1).
- **Swappable models.** Model IDs live in config, because Haiku 4.5 is listed as "not before 2026-10-15".
- **Cheap batch work.** Extraction runs through the Batch API (50% off). System prompts and tools are prompt-cached.
- **Cost answer.** The "multi-agent ≈ 15× chat" figure (`architecture.md` §1.2) comes from per-query research fan-out. Here, fan-out happens only in **batch jobs, per card or per source, not per user**. That cost grows with catalogue size, not with users. On the user path a typical turn is Concierge plus one specialist. My estimate is about 1.6–2× the single-agent cost in `models.md` §5: roughly **$90–120 a month at 100 users**, against $55–65 for one agent. That is still about ₹1 per user per month.
- **Privacy.** There is no India inference region, so no PII goes to any LLM. Merchant strings are classified by the local model.

## 7. Scheduling, review queue, notifications

**Temporal schedules** (`frameworks.md` → "Durable execution"):
- `launch_radar` weekly, Monday 06:00 IST
- `profile_refresh` nightly, expired fields only
- `renewal_scan` daily (T−45)
- `news_scan` daily
- `cycle_reset` per statement date

Each workflow **calls the specialist agent as a Temporal activity with `max_turns` and a credit cap**. This removes the "synthetic message to the supervisor" fragility (`architecture.md` §3.3).

**Review queue.** Implemented as a Temporal signal wait, so a review can take days.
- Verifiers vote. If all 3 agree and the field is unchanged, the agent only bumps `as_of`.
- Any changed value needs a human approval.
- Approval emits `profile.changed`, which triggers a replan and a score-table re-sync for every holder of that card (A6, F4).

**Notifications** go through FCM, with dedupe keys, quiet hours and a frequency cap per type.

## 8. Security, privacy, compliance

- **DPDP Act 2023.** Granular consent per purpose (capture, chat, notifications), purpose limitation, deletion on request across ledger, memory and evidence, a published data map (H3), and breach-response runbooks. Check the phased timelines in the DPDP Rules with counsel.
- **Google Play.**
  - Use a NotificationListener, not `READ_SMS`, with a prominent disclosure.
  - Gmail parsing needs the restricted-scope security assessment, so it is deferred.
  - Complete Play's Financial features declaration.
- **Account Aggregator** requires a regulated entity or partner, so it is out of scope (`ideation.md`).
- **RBI.** We never move money and are not a TPAP; UPI is a deep-link hand-off only. The closure workflow (F3) cites RBI's credit-card Master Direction on closure timelines; the exact clause needs a legal check. Affiliate links may need an issuer or DSA agreement.
- **Advice posture.** Disclaimers on every recommendation, a source and date on every fact, and payouts disclosed (B7).
- **Prompt injection.** This is a multi-agent advantage: agents that read web content (verifiers, source workers) have **no write tools beyond `queue_review`**, and the Concierge never sees raw web text, only typed outputs.
- **Hackathon rule.** No keys in the repo or its git history (`hackathon_credits_rules.md` Q4).

## 9. Evals, testing, observability

- **Engine.** Property and golden tests: caps, cycle-correct resets, rounding (the ₹67 floor in the Tata Neu example), UPI channel rules.
- **Per agent:**
  - extraction field precision and recall on 20–30 hand-labelled cards
  - Launch Radar recall, back-tested on the past 12 months of launches using the Reddit archive as ground truth
  - classifier accuracy on about 200 Indian merchants
- **Router accuracy:** about 150 labelled user messages, including multi-flow ones.
- **Trajectories:** about 30 scripted conversations judged by Opus 5.5 against a rubric.
- **Numeric guard:** every ₹ figure in the output must appear in the engine output, or the reply is blocked.
- **Fixtures:** recorded SerpApi responses, so CI spends 0 credits.
- **Load:** a test on the score-table sync.
- **Observability:** OTel GenAI spans with nested agent traces in self-hosted Langfuse. Dashboards for credits per flow, tokens per agent, router misroutes and review-queue age.

## 10. Delivery plan

**Hackathon (Oct 6–10, AI Agents track, Android).**

| Day | Build |
|---|---|
| Oct 6–7 | Schemas; `reward_engine` with tests; 20 hand-verified cards; `serp_gateway` with fixtures; Flutter shell with onboarding (8 questions), manual spends and typed Checkout lookup |
| Oct 8 | ProfileCurator plus 2 verifiers; review-queue admin page; CardScout and Concierge (Pydantic AI agent delegation) |
| Oct 9 | LaunchScout with 4 parallel workers (Ads Transparency, news light, Play diff, autocomplete); scoring against demo users; FCM push; minimal RenewalReview on a fake clock |
| Oct 10 | Evals on fixtures, tracing screenshot, demo recorded from a warm cache, README listing which SerpApi engines are used and why, submit before 23:59 IST |

**Stack:** FastAPI, Pydantic AI 2.54, Claude API, SQLite and APScheduler on the backend, Flutter for the app. The demo's trace view shows the parallel agents at work.

**Three-month product:**
- **Month 1:** Postgres, Temporal, auth and tenant isolation, statement upload (E1 P1), 100 cards, reviewer roles.
- **Month 2:** QR scan and UPI hand-off, notification capture, EligibilityPath, CapWatch, E2/E3 reconciliation, closed beta with TechnoFino and Reddit users.
- **Month 3:** RenewalReview, F5 escalation drafting (a new specialist), model-swap cost tuning, DPDP review, public changelog.

## 11. Top risks

1. Concierge misrouting (mitigation: router evals plus a deterministic pre-router for "which card for X").
2. Stale score table on the phone gives a wrong card at checkout.
3. Verifier fan-out against the 250-search budget (verify only changed or expired fields).
4. Extraction errors in caps and exclusions (review queue, verifier votes).
5. Per-agent token drift (per-agent budgets and alerts).
6. Play rejects notification capture.

---

## Weakest points of my own proposal

- **On the user path, most specialists are thin wrappers around one deterministic tool.** CapWatch and RenewalReview are nearly "LLM writes the sentence". A workflow plus one agent (`architecture.md` §6) gets about 80% of the result for less cost and less to evaluate. My real wins are narrower: Launch Radar and verification fan-out (batch), cross-flow conversations, and prompt-injection isolation.
- **Parallel fan-out is throttled by SerpApi's 50-per-hour cap** (`architecture.md` §1.2). The wall-clock speed-up is mostly illusory on the free tier. The benefit is context isolation, not speed.
- **Two engine implementations** (Python canonical, Dart lookup) can drift.
- **The eval surface is the largest of all the options**, and four days is not enough to do it properly. The hackathon build will ship with thin router evals.
- **Supervisor latency for chat** is 3–8 s for a two-hop answer. It is acceptable for chat but noticeably slower than one agent.
- **Part of the hackathon appeal is narrative.** Judges score idea, originality, complexity, usefulness and SerpApi usage, so "visible agents" helps on complexity only.
