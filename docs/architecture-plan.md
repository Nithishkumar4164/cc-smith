# cc-smith — Consolidated architecture plan

Judge's ruling on the four-way architecture debate (`docs/arch-debate/`), written 2026-10-06. Inputs: both debate rounds, `README.md`, `docs/ideation.md`, `docs/features.md`, `docs/research/*`, `research_notes/*`, `reports/*` and `git log`. Facts that I could not trace to those files are marked **(unverified)**. Thresholds that I set myself are marked **(judge's threshold)**.

---

## 1. Decision summary

| Area | Decision | Confidence | Main dissent |
|---|---|---|---|
| Orchestration | Deterministic per-flow workflows plus **one** chat agent with about 10 consolidated tools. Multi-agent fan-out is allowed only in batch Launch Radar | High | Multi-agent: specialists will be needed by P1 |
| Ledger location | **Server ledger of record** holding minimal parsed fields. Raw alert text is parsed and kept on the phone. The question is reopened by a closed-beta consent test | Medium | On-device (and event-services after its round-2 switch): local by default, with opt-in E2E sync |
| Rewards engine | One canonical **Python** engine. The phone gets only a lookup over a server-built table (from M2). Golden vectors are shared | High | On-device: full Dart engine |
| Card knowledge | A fact quoted verbatim from an **official bank source** (issuer page, MITC/T&C, official bank notice) is **published automatically**, after a `{url, quote}` check in code. Anything without an official source is stored as **speculation** (labelled, with refs, never used in the maths). **No human in the loop** (DR-12). AI Mode is for discovery and cross-checks | High (owner decision, 2026-10-06) | `serpapi_tool_surface.md` §1 and `engines_for_flows.md` §3 (AI Mode primary); no architect still defends that |
| SerpApi | One gateway holds the only key. Nothing runs on any user hot path. Per-flow envelopes, fixtures, Developer plan in the product | High | — |
| App ↔ backend | Hackathon: server `/pay` with no LLM, typed input first. Product: a signed pay pack on the phone, if the 4G latency test fails | Medium-high | On-device: everything offline |
| Durable execution | APScheduler + `run_state` → **DBOS** (M1) → Temporal only on a measured trigger. A 5-topic Postgres outbox | High | Multi-agent conceded |
| Models | Sonnet 5.5 for chat and extraction (Batch). Haiku 4.5 for triage. A self-hosted small model for user-derived text. Opus 5.5 offline only | Medium-high | models.md §4: Opus for extraction and eligibility |
| Privacy and compliance | No PII to any LLM or to SerpApi. Purpose-tagged consent, `user.erased` with crypto-shredding, NotificationListener rather than `READ_SMS`, **no affiliate money** (owner decision) | High | On-device: server data should be ciphertext only |
| Prompt injection | Any step that reads web text holds only `add_speculation`. Only verbatim quotes from allow-listed official sources become facts. The chat agent never sees raw web text | High | — |
| No human in the loop | Official facts auto-publish; everything else is labelled speculation that never enters the maths; the owner gets an alert with refs for every change (DR-12) | High (owner decision) | — |
| Ops MCP | FastMCP with ops scope (read + trigger re-fetch, never write facts), in **M1**. At the hackathon only if Oct 9 closes on time | Medium | Event-services: ship it at the hackathon |

---

## 2. Architecture overview

```
┌──────────────── PHONE (Flutter; Android builds first) ─────────────────┐
│ Onboarding/prefs · Finder screens · Chat screen · Trackers             │
│ QR decode (upi://pa,pn,mc) → UPI intent hand-off [P1, verify]          │
│ NotificationListener → signed parser pack → {amount,last4,merchant_key}│ [M2]
│ Pay pack: signed per-user decision table + cap_left (lookup only)     │ [M2]
│ Local queue (Drift/SQLCipher), consent screens, "report wrong answer" │
└───────▲ FCM (data msgs, topic pings) ──────────────┬ HTTPS (JWT) ──────┘
        │                                            ▼
┌───────┴──────────── BACKEND (one repo, one Postgres, entrypoints) ─────┐
│ api (FastAPI BFF)                                                      │
│  ├ /pay  Checkout Advisor: code only, p95 < 300 ms                     │
│  ├ /chat Chat agent (Sonnet 5.5, ~10 tools, pre-router for "which card")│
│  └ /screens/* → workflows directly                                     │
│ modules (packages; import-linter contracts; schema per module):        │
│  knowledge  rewards(engine)  ledger  signals  notify  users/consent    │
│ worker: workflows (step fns, checkpointed) ◄── scheduler (APScheduler→DBOS)
│        ▲                         │                                     │
│        └──── ops.outbox (SKIP LOCKED + LISTEN/NOTIFY) ◄────────────────┘
│ LLM steps*: extract_terms · triage_news · dedupe_launch · explain      │
│            · classify_merchant(self-hosted) · audit_recheck(offline)   │
│ serp_gateway ──► SerpApi (only key; cache, budget, fixtures)           │
│ fetcher (httpx+trafilatura+pdfplumber; Playwright fallback) ──► issuers│
│ admin: change feed, speculation list, rollback (read-only, no approvals)│
│ mcp (FastMCP): ops scope read + trigger_refetch [M1]                   │
└────────────────────────────────────────────────────────────────────────┘
```

| Module | Owns (only writer) |
|---|---|
| `knowledge` | `card`, `card_field` (versioned; per-field `source_url`, `evidence_id`, `as_of`, `effective_from`, `status`), `evidence`, `speculation`, `changelog`. Others read the `card_profile_current` view |
| `rewards` | engine (pure functions), `score_table`, pay-pack builder |
| `ledger` | `txn` (integer paise, `source`, `superseded_by`, idempotency key), `cap_counter` (rebuildable), `merchant`, `user_merchant_override` |
| `signals` | `signal_item`, `launch_candidate`, `sweep_job` |
| `notify` | `notification_outbox` (dedupe key, quiet hours, frequency caps) |
| `users` | `profile`, `preferences`, `holding` (card_id, last4?, statement day, renewal month), `consent` |
| `ops` | `outbox`, `serp_cache`, `credit_ledger`, `run_state` |

---

## 3. Decision records

### DR-1 Orchestration topology

**Options.**
- **Workflow-first (WF):** workflows plus one agent.
- **Multi-agent (MA):** a Concierge supervisor with about 8 specialists as tools.
- **Event-services (ES):** one agent over MCP tools.
- **On-device (OD):** workflows, with the agent's tools executed on the phone.

**For specialists.** `features.md` has about 50 features. MA argues that overlapping "compute value" tools (`simulate_rewards`, `renewal_review`, `replan_diff`) meet the OpenAI split criterion, which is overlap rather than raw count (`architecture.md` §1.3). It also offers a fair cross-flow test: "Renew Regalia Gold? If not, what replaces it, and can I get it?"

**Against.**
- Every source in `architecture.md` §1.1–1.3 says to maximise a single agent first. Flows that share user state are the "many dependencies" anti-pattern (§1.2).
- MA conceded in round 2 that CapWatch, RenewalReview and the Explainer are "LLM nodes in disguise".
- MA's claim that a fixed router "cannot" handle the cross-flow case is overstated. Three sequential calls to consolidated tools (`architecture.md` §7, "Consolidated agent-facing tools") are ordinary single-agent tool use.
- Parallel speed-up is capped by the 50-searches-per-hour limit.

**Decision.**
- Workflows are the backbone.
- **One chat agent** with about 10 consolidated tools, plus a deterministic pre-router that sends "which card for X" straight to `/pay`.
- Multi-agent is allowed in two places only:
  - **Launch Radar:** a lead with per-source workers, running in batch, fanned out per source family rather than per user, each worker with a `max_searches` cap.
  - **An optional `card_research` sub-agent** for open comparison questions, added only when the trigger below fires.
- Scheduled flows never send synthetic messages to an agent (`architecture.md` §3.3).

**Consequences.** This gives the smallest eval surface, and SerpApi spend is decided by code. The conversation is less flexible for questions that span many flows.

**Remaining dissent.** MA: specialists will be needed by P1.

**Reopen when** either of these happens:
- Tool selection falls below 90% on the 150-message set, which includes 30 multi-flow chats.
- More than 15 overlapping tools are needed.

Run this test at every milestone.

### DR-2 Ledger location (the one real disagreement)

**Options.**
- Server ledger of record: WF and MA.
- Phone ledger with opt-in E2E-encrypted sync: OD, and ES after its round-2 concession. The panel finished **2–2**.

**For the phone.**
- H3 asks for "local-first capture where possible".
- The Play Data Safety form could say "not collected". OD's definition of collection is **(unverified)**.
- Cap counters are consistent by construction.
- The server never learns which cards a user holds.

**For the server.**
- `ideation.md` records "the app is a thin client" and names backtests on the user's own data as the defensible difference.
- D2 crowd MCC, C3 rejection intelligence, H2 community signals, the web recommender, multi-device use, backup and support all need a server ledger.
- OD itself lists device loss as risk 3, and it gave up the Dart-only engine in round 2.

**Evidence check: the trust argument is thinner than claimed.**
- OD (round 1 §8), WF (round 2) and MA (round 2) cite `reddit-…pain-points.md` **11c** as "distrust of CRED-style aggregators". Reddit 11c is actually "Closing cards to simplify is itself scary".
- OD round 2 also cites Reddit **10b**, which is about bill-payment apps failing silently. That is a reliability complaint, not a privacy one.
- The only distrust evidence is `technofino-…` **11c**: one line, "common", four thread IDs, with no stated reason. Its threads (12439, 40388, 31781) are about due dates and late fees.

**Decision.**
- **Server ledger of record** in India-region Postgres with row-level security, holding only `amount_paise, merchant_key, card_id, last4?, ts, channel, source`.
- Raw notification text is parsed on the device and never uploaded.
- Merchant text derived from a user's transactions goes to no hosted LLM.
- The ledger module sits behind an interface, so a device-only mode stays possible.

**The deciding test** runs in the M2 closed beta as an A/B on the consent copy: "never leaves your phone" against "synced securely". Measure the notification-capture opt-in rate and 30-day retention.

**Flip the default to device + E2E sync if** both of these hold **(judge's threshold)**:
- The device copy lifts opt-in by at least 10 percentage points.
- Retention is no worse.

Play's review of the listener declaration is a second input: if Play objects to server storage, flip.

### DR-3 Rewards engine language and duplication

**Options.**
- Python canonical with a Dart lookup: WF, MA, ES.
- Full Dart engine: OD round 1. OD retracted it in round 2 and made it conditional on DR-2.

**Decision.**
- `rewards` is pure Python with property and golden tests.
- The phone receives a signed table: `(category, channel, amount_band) → ranked cards` plus `cap_left`. It only looks up and subtracts.
- Shared JSON golden vectors run in both CI suites.
- Bundles carry `min_engine_version`.

**Consequences.** The duplication is limited to about one multiply per card.

**Reopen if** either happens:
- DR-2 flips.
- More than 2 parity bugs per month reach beta users **(judge's threshold)**.

### DR-4 Card knowledge sourcing

**The docs conflict.**
- For AI Mode as primary: `serpapi_tool_surface.md` §1 ("the primary card-terms extractor") and `engines_for_flows.md` §3 ("AI Mode stays primary").
- Against it: `serpapi-compatibility.md` ("build the fetcher/extractor as our own component") and `architecture.md` §4.11 ("AI Mode answers are themselves LLM summaries").

By round 2 all four architects had converged on issuer-first sourcing. The evidence is pain point 16, plus a user report of an LLM that was "wrong by 3x" (`reddit-…` 12b).

**Decision.**
1. Discover URLs with `google` (`site:`, `filetype:pdf`).
2. Fetch the page with our own fetcher.
3. Extract with Sonnet 5.5 into a strict schema. Every field carries `{url, quote}`, because native citations cannot be combined with JSON output (`models.md` §1).
4. **Code checks that the quote appears in the fetched text.**
5. Diff against the current value:
   - unchanged: bump `as_of`
   - changed, **and the quote comes from an official bank source**: **publish automatically** as a new version (`card.version_published`), keeping the old version for instant rollback and logging the change with its source link
   - changed, but no official source (AI Mode only, news, forums, user report): store as **speculation** with its refs; the fact stays as it is, and the card shows "reported change, not confirmed by the bank" next to it
   - no source: leave the field empty, so the card shows "can't assess" (A1)
6. **Official source** means a page or document on an allow-listed domain, fetched by our fetcher. There are two kinds, each official **only for the fields it controls** (owner decision, 2026-10-07):
   - **Issuing bank** (product pages, card T&C, MITC/KFS, notices, press releases): fees, charges, waivers, eligibility, network, base earn rate, caps, exclusions, milestones.
   - **Co-brand partner or fintech operator** (`partner_sources`: e.g. Amazon, Tata Digital, Swiggy, Flipkart, Airtel, Scapia, Kiwi): the partner's reward currency and its redemption, partner-platform offers, app features, and for fintech-run cards (Scapia, Kiwi) the reward programme itself.
   - A partner value for a bank-owned field (or the reverse) is stored as speculation. If the bank and partner disagree on a field, the owner of that field wins, both values are kept, and the owner alert flags the conflict.
   - Partner blogs and marketing, app-store listings and social posts are never official. Details published only inside an app stay speculation until they appear on the web. The allow-list is **configurable**: a per-issuer config file (domains plus official notice or press URLs), loaded at runtime. Every edit to it is versioned and triggers an owner alert, because it is the control that decides what counts as a fact.
7. AI Mode is used for discovery and cross-checks. A value it supplies alone stays `pending` with an "unverified" badge.
8. **Automatic safeguards on auto-published facts (no human step):** schema and range checks must pass (an earn rate above 25% or a fee above ₹1 lakh is stored as speculation instead of a fact); a large change (rate, cap or fee moving more than 50%) publishes and is flagged in the owner alert; a weekly automated re-check re-extracts a sample with a second model and demotes any fact that doesn't reproduce; users see the source and `as_of` on every fact.

**Owner decision (2026-10-06):** an official bank statement is a fact and goes straight into the knowledge base. This replaces the earlier rule that every changed value goes through human review, and drops the second-source requirement for high-severity changes when the source is official. Consequence: freshness is no longer limited by review throughput; the remaining risk is the extractor misreading an official page, which the quote check, range checks, automated re-check and rollback address. A second owner decision the same day removed human review entirely; see DR-12.

**Catalogue growth (owner decision, 2026-10-07).** You seed the 20 cards in `docs/research/seed-cards.md`. After that the system adds cards on its own; nobody adds them by hand. A card enters the catalogue by one of four routes:

| Route | Trigger | Becomes a fact profile when |
|---|---|---|
| Launch Radar | News or a new bank ad mentions a card not in the catalogue | Its terms are found on the issuing bank's (or, for partner-owned fields, the partner's) official page; until then it is a speculative launch, listed but not scored |
| Issuer sitemap sweep | Weekly diff of each allow-listed bank's sitemap (e.g. HDFC's lists every card page) | A new card page appears on the official domain |
| User request | A user names or holds a card the catalogue doesn't have (Card Finder, holdings) | Its official page is found and fetched; meanwhile the user sees "can't assess yet" |
| Variant or relaunch | An official page or notice names a new variant (e.g. Swiggy BLCK and ORNGE) | Always, as a separate profile; the old one is marked closed to new applicants |

The same sweeps also catch removals: a card page that disappears from the sitemap or returns 404 for two runs is marked "closed to new applicants" as speculation until an official notice confirms it. Every addition and removal raises an owner alert with its refs (DR-12).

Hackathon: the 20 seed cards are profiled by the pipeline from official pages (not typed in by hand), and the demo shows Launch Radar adding one new card.

**Remaining dissent.** None among the architects. The research notes still say AI Mode first.

**Reopen if** the fetcher cleanly fetches fewer than 70% of the seed cards (i.e., more than 30% fail; ES proposed a 60% success cut-off): fill the gaps from AI Mode as **speculation** (shown, not used in the maths). Also reopen if the weekly automated re-check finds more than 2% of auto-published facts don't reproduce.

### DR-5 SerpApi engines per flow and budget

**Facts.** The hackathon gives 250 searches a month on the free tier, at 50 per hour, with no top-ups. Participation credits arrive only after judging (`hackathon_credits_rules.md` Q1–Q3). How many searches remain this month on the team's account is **(unverified)**: check the Account API before Oct 7.

| Flow | Engines | Hackathon budget | TTL |
|---|---|---|---|
| Card Profile | `google` `site:`/`filetype:pdf`; `google_ai_mode` as cross-check | 70 | URL 30 d |
| Launch Radar | `google_news` (`so=1`) / `google_news_light`; `google_ads_transparency_center` (India `region=2356`: **verify**, since the cookbook marks it unverified) — never cut in the Commerce track | 45 | 7 d |
| Cap Watch / Replan | `google_news_light` "devaluation" `when:7d`; `google_light site:technofino.in` | 25 | 24 h |
| Checkout merchant seed | `google_maps` on cache and rules miss only (official Places API in the product) | 15 | 180 d |
| Commerce: bank offers at the merchant | `amazon_product` on amazon.in (spike first); issuer offer pages go through the fetcher, not SerpApi | 10 | 6 h |
| Fixture recording / dev | mixed | 35 | — |
| Demo reserve | — | 50 | — |
| Finder, Checkout card choice, Renewal | **none live** | 0 | — |

**Product.** The Developer plan ($75 for 5k) is enough for news, weekly per-card checks and discovery (`serpapi-compatibility.md`). Merchant classification is the only workload that scales with users. It goes to the official Places API, with normalised keys cached by `place_id`.

Eligibility Path routes come from `google_light` with `site:` forum queries, in M3 only.

**Reopen if** credits used per flow exceed 120% of the envelope for 2 consecutive weeks.

### DR-6 App ↔ backend split and the Checkout Advisor path

**Agreement.** All four architects agree that Checkout Advisor uses no LLM.

**Decision.**
- **Hackathon:** typed merchant and amount go to server `/pay`, which reads `score_table`, `merchant_cache` and the rules. An unknown merchant gets the default card with `confidence=low`, and classification runs asynchronously.
- The QR decode runs on the phone, and the `upi://pay` intent is a stretch goal. D8 is P1, and `ideation.md` flags deep-link restrictions as "to verify".
- **M2:** a signed per-user pay pack plus a staleness badge. `profile.changed` triggers a silent FCM invalidation.

**Consequences.** Offline advice is limited to Checkout. Finder and chat need the network.

**Remaining dissent.** OD: Finder and the Coach should work offline too.

**Reopen when** a field test shows `/pay` p95 over Indian 4G below 400 ms. In that case, drop the pay pack (WF's and ES's own trigger).

### DR-7 Durable execution and outbox

**Agreement.** Three architects chose DBOS in round 1. MA switched to it in round 2.

**Decision by stage.**
- **Hackathon:** plain step functions, a `run_state` table and APScheduler.
- **M1:** DBOS on the same Postgres. There is no review wait anywhere (DR-12). WF's claim that DBOS `recv()` can wait days is not documented in `frameworks.md` and is **(unverified)**, so nothing depends on it.
- **Temporal:** only for workers in more than one language, fan-out beyond about 100k users, or a team that already runs it.

**Outbox.** ES's design: Postgres, `FOR UPDATE SKIP LOCKED`, `LISTEN/NOTIFY`, a 150-line budget. Consumers are idempotent on `(topic, key)`, and an item goes to a dead-letter queue after 5 attempts. Topics:

| Topic | Consumers |
|---|---|
| `card.version_published` | score_table rebuild, Replan, pay-pack invalidation |
| `launch.published` | `score_all_users`, notify |
| `txn.recorded` | `cap_counter`, Cap Watch thresholds |
| `knowledge.changed` | changelog, owner change alert (every fact published, speculation added, promoted, expired, demoted or rolled back) |
| `user.erased` | every module. CI fails if a handler is missing |

**Cap consistency.** ES admitted a one-transaction lag on caps. The fix: `/pay` recomputes `cap_left` synchronously from the ledger for the held cards.

### DR-8 Models per role and cost

| Role | Model | Note |
|---|---|---|
| Chat agent | Sonnet 5.5, effort low, cached system and tools | `tool_choice: auto` + `strict`. Forced choice and temperature return a 400 (`models.md` §1) |
| `extract_terms` | Sonnet 5.5 via Batch; Opus 5.5 for the gold set and disputed diffs | `models.md` §4 prefers Opus and `architecture.md` §8 prefers Sonnet. The 25-card gold set decides |
| `triage_news`, `dedupe_launch` | Haiku 4.5 (ID in config; retirement "not before 2026-10-15") | Prompts under 4,096 tokens don't cache on Haiku |
| `classify_merchant` | Rules → self-hosted `qwen3:8b` in the India region for user-derived strings. Haiku only for global keys from QR codes that are not linked to a user | WF conceded this point |
| `explain` | Sonnet 5.5 low → Haiku if evals pass. A **₹ guard** falls back to a template. "Why this card" on `/pay` is templated from `reason_codes` | From OD |
| Eligibility narrative | Haiku or Sonnet, **not Opus**. Rules decide pass or fail | Overrules MA and `models.md` §4 |
| `audit_recheck`, eval judge | Opus 5.5, offline | Weekly re-extraction of a sample; a mismatch demotes the fact automatically |
| Fable 5.x | Never | It needs 30-day retention |

**Cost.** About $55–65 a month at 100 users (`models.md` §5, an estimate), and $20–50 for the hackathon. MA's own estimate for its design was $90–120.

For local development behind the corporate proxy, set `NO_PROXY=localhost,127.0.0.1` for Ollama (`architecture.md` §8).

**Reopen if** the chat cost per monthly active user exceeds ₹10 **(judge's threshold)**.

### DR-9 Privacy, DPDP, Play and RBI

- **Card data.** No card numbers anywhere: product and last4 only. A regex strips runs of 12–19 digits from every inbound payload.
- **DPDP:**
  - consent per purpose, with purpose tags on events
  - export and deletion through `user.erased`, plus crypto-shredding of a per-user key (adopted from ES)
  - a published data map
  - an 18+ age gate
  - The DPDP Rules timelines and the cross-border provisions are **(unverified; counsel)**.
- **LLM data flow.** Anthropic has no India region (`inference_geo` is global or US only), so no PII reaches an LLM. Chat context is a previewable capsule of aggregated spends (adopted from OD).
- **Play:**
  - no `READ_SMS`
  - a NotificationListener with prominent disclosure (M2)
  - the Data Safety form and the Financial features declaration
  - Gmail capture (`gmail.readonly`, a restricted scope) ships in M2; Google OAuth verification and the CASA security assessment start in M1 because they take about 6 weeks (owner decision, 2026-10-08)
- **RBI.** cc-smith moves no money and only hands off to UPI apps. **No affiliate money will be taken** (owner decision, 2026-10-06), so the issuer-agent/DSA question for affiliate links no longer applies.
- **B7, ranking independence.** No affiliate payouts exist, so there is no commercial input to rankings at all. A breakdown is shown on every rank.
- **SerpApi.** Queries never contain user data.

### DR-10 Prompt-injection isolation

Adopted from MA, and accepted by all four architects in round 2:
- Every step that reads web or SERP text (`extract_terms`, `triage_news`, Launch Radar workers) has **no tool except `add_speculation`**, and its output is schema-validated.
- The chat agent sees only typed tool results, never raw page text.
- User-scoped tools get `user_id` injected by the server, never supplied by the model.
- The MCP ops scope cannot write facts or speculation; it can only trigger a re-fetch.
- Only text quoted verbatim from an allow-listed official bank source can become a fact. All other web text can only become speculation, which the engine never reads.

### DR-11 Evals and observability

- **Engine:** property tests (cap boundaries, odd quarters, ₹0 rounding under ₹67 as in the Tata Neu case, `reddit-…` 1d, UPI rules), golden examples from issuer T&Cs, and Python↔Dart parity vectors from M2.
- **LLM nodes, on replay fixtures at 0 credits:**
  - extraction precision and recall, hallucinated-field rate and quote-present rate on 25 cards
  - the merchant classifier on 200 merchants, triage on 100 news items
  - Launch Radar recall backtested on 12 months of launches from the Reddit archive (from MA)
  - chat: 150 messages with expected tool sequences, 30 multi-flow chats judged by Opus, plus the ₹ guard
- **End to end:** a fake clock and fake SerpApi responses, plus a k6 test asserting `/pay` p95 under 300 ms.
- **Observability:** OTel and self-hosted Langfuse with a `correlation_id` in outbox payloads. Dashboards for credits per flow, cache hit rate, facts published and speculation added per week, re-check mismatch rate, outbox lag and DLQ depth, and pack staleness.

### DR-12 No human in the loop: facts, speculation and owner alerts

**Owner decisions (2026-10-06).** There is no human review step anywhere in the product. An official bank statement is a fact. Anything else is speculation. The owner is alerted about every change, with the references used.

**Two tiers in `knowledge`.**

| | Fact | Speculation |
|---|---|---|
| Source | Verbatim quote from an allow-listed official source that owns the field: the issuing bank (issuer page, MITC/T&C PDF, notice, press release) or, for partner-controlled fields, the co-brand partner or fintech operator (DR-4 §6) | Anything else: AI Mode, news, forums, YouTube, ads, user reports, or an official page whose value fails range checks |
| Used in the rewards maths | Yes | **Never** |
| Shown to users | Yes, with source and `as_of` | Yes, labelled "reported, not confirmed by the bank", with its refs |
| Lifecycle | Versioned; rolled back automatically if the weekly re-check can't reproduce it | Promoted to a fact automatically when an official quote confirms it; contradicted by an official source → closed; expires after 60 days unconfirmed |

**Every place that previously needed a human, and what replaces it:**

| Was | Now |
|---|---|
| Review queue for changed values without an official source (DR-4) | Stored as speculation |
| Range-check failures went to review | Stored as speculation, flagged in the owner alert |
| Second source for high-severity changes | Dropped for official sources; non-official ones are speculation anyway |
| New card from Launch Radar without an official page | Speculative launch: listed, not scored, no user notification until promoted |
| User "report wrong answer" corrections (A8) | Become speculation with the user report as the ref, and trigger an immediate re-fetch of the official page |
| Ops MCP `propose_correction` | Replaced by `trigger_refetch`; it can't write facts or speculation |
| Opus `review_assist` pre-annotation | Replaced by `audit_recheck`: a weekly automated re-extraction that demotes facts that don't reproduce |
| Weekly human audit sample | Automated re-check (above) |
| Reviewer roles (M1) | Dropped; replaced by the owner alert channel |
| Prompt-injection defence relied on review (DR-10) | Speculation never reaches the engine, so web text can't change rankings |
| AI Mode-assisted entry with mandatory review (DR-4 fallback) | AI Mode fills gaps as speculation only |

**Owner change alerts.** Every `knowledge.changed` event alerts the owner. Each alert carries:
- card, field, old value → new value, and the tier (fact or speculation)
- the event type: published, speculation added, promoted, contradicted, expired, demoted by re-check, or rolled back
- every reference used: source URL, the quoted text, fetch time, evidence id (the stored copy of the page), and the SerpApi search id that found it
- a large-change flag (rate, cap or fee moving more than 50%) and how many users hold the card

Delivery: an immediate alert per change plus a daily digest. The channel (email, Slack, or push to an owner device) is **decided at implementation**. Alerts are informational: nothing waits for the owner, and rollback stays automatic.

**Humans who remain, outside the product loop.** These are not approvals inside cc-smith, but they still involve people:
- The owner maintains the **configurable** allow-list of official bank domains. A wrong domain on that list would let non-official text become facts, so every edit is versioned and alerted.
- Legal counsel on DPDP Rules before launch (DR-9). No affiliate money will be taken, so no affiliate or DSA review is needed.
- Google Play's review of the NotificationListener declaration and the app listing (an external gate; **not in scope for the hackathon**).
- Releases and deploys (owner and team).

**Consequences.** Freshness is limited only by fetch schedules. The main risk moves from review throughput to the extractor misreading an official page, covered by the quote check, range checks, automated re-check and auto-rollback. Users may see speculation that turns out false, so the label and refs must always be visible.

**Reopen if** the weekly re-check mismatch rate on auto-published facts exceeds 2%, or more than 10% of speculation shown to users is later contradicted by an official source **(judge's thresholds)**.

---

## 4. Feature coverage

**P0 features** (the `features.md` v1 scope):

| ID | Component |
|---|---|
| A1 versioned profiles, empty when unsourced, pending changes applied before scoring | `knowledge.card_field` (`effective_from`, `status`) + Card Profile workflow (auto-publish from official sources; speculation for the rest) |
| A2 earn rules (MCC, caps and reset basis, minimums, rounding, channel) | `card_field.earn_rules` schema; `rewards.rules` |
| A3 typed perks | `card_field.perks`; `rewards.valuation` at the user's own valuations |
| A4 fees and waivers | `card_field.fees`; `rewards.fees` |
| B1 portfolio recommendation | Card Finder workflow: filter → per-category top-K prune → 1–3 card portfolios → marginal gain against held cards |
| B2 "Should I get X?" | Card Finder in single-card mode (`assess_card`), with pending devaluations applied |
| B5 reality check | `rewards.effective_rate()` on the user's spend |
| B6 hard categories | an explicit "earns ₹0 here" result plus the lowest surcharge and whether it counts toward milestones |
| B7 independence | no affiliate money (owner decision), plus a breakdown on every rank |
| D1 typed | Checkout Advisor `/pay` |
| E1 manual | `ledger.txn source=manual_estimate`, superseded by real entries later |
| H1 provenance | every API fact returned as `{value, source_url, as_of}` and rendered in the UI; public changelog view |
| H3 privacy | DR-9; consent screens; data map |

**Named flows end to end.** These flow names are not defined in the repo docs. `features.md` refers to a "Flow Map artifact" that is not committed. The mapping below follows `architecture.md`'s flows 1, 2, 3a–c and 4.

- **Card Profile** (A1–A4, A6):
  1. Trigger: a weekly job for stale fields, a `signals` change suspicion, or a user correction (A8).
  2. Gateway discovers the URL → fetcher → `extract_terms` → quote check → diff.
  3. Changed values quoted from an official bank source publish automatically (`card.version_published`); values without an official source are stored as speculation. Every change triggers an owner alert with its refs.
- **Card Finder** (B1, B2, B5–B7):
  1. The screen or chat calls the workflow.
  2. The engine ranks portfolios with per-line-item ₹.
  3. `explain` writes the prose, and the ₹ guard checks it.
- **Checkout Advisor** (D1):
  1. Input: typed text, or a QR scan (`pn`, `mc`).
  2. `/pay` (later the pay pack) → merchant key → category → channel rules → `cap_left` → best card plus its margin over the next best.
  3. Reply from a template.
  4. The user confirms → `txn.recorded`.
- **Card Coach:**
  - **Eligibility Path** (C1, P1): rules per criterion → failed criteria mapped to KB-sourced routes (FD-backed, card-to-card, relationship account, wait N months) → dated steps → narrative.
  - **Cap Watch** (E2, F4, P1): `txn.recorded` → cycle-correct counters → nudges at 70%, 90% and 100% with dedupe. When a cap rule changes, Replan re-routes first and recommends a new card last.
  - **Renewal Review** (F2, P1): a daily scan at T-45 days → simulate keep, convert-to-LTF and close on 12 months of ledger → convert preferred → notify.
- **Launch Radar** (F6 P2, A7):
  1. A weekly sweep runs per-source workers (news, ads).
  2. `triage_news` → dedupe (code, then `dedupe_launch`).
  3. Card Profile for the new card: auto-published if its terms come from the bank's own launch page or notice; otherwise it is a **speculative launch**: listed as "reported, not confirmed", not scored, and promoted automatically when the bank's own page appears.
  4. `launch.published` → `score_all_users` → notify only above **₹2,000 a year and 15% of the fee**.

---

## 5. Delivery plan

### Hackathon MVP

Submit by **Oct 10, 18:00 IST**. The hard deadline is 23:59, and drafts are never judged. Android build only. **Track: Commerce & Market Intelligence** (owner decision, 2026-10-06). **Hackathon first**, then the product. **Team of 2–5**, so the work runs in parallel workstreams.

**Demo story for the Commerce track:** "cc-smith tells you the cheapest way to pay and what's changing in the card market." The judges see three things:
1. **Checkout Advisor in rupees:** for the merchant the user is paying, the best held card and channel, the reward in rupees, and any live bank offer at that merchant (from issuer offer pages). No cross-store price comparison: effective price across stores (D7) was dropped by the owner on 2026-10-07.
2. **Launch Radar as market intelligence:** new bank card ads detected each night (Ads Transparency) and launch news, each new card profiled from the bank's own page and scored against the user's spends.
3. **Card Finder in rupees:** the best 1–3 card set for the user's spends, with the gain per card and the official source behind every number.

**Workstreams** (assign one owner each; a fourth or fifth person pairs on the riskiest one):

| Workstream | Owns | Depends on |
|---|---|---|
| A. Engine and data | schemas, `rewards` engine and tests, seed cards, Card Finder, `/pay` | Seed card list (`docs/research/seed-cards.md`) |
| B. Market intelligence | SerpApi gateway, fetcher, Card Profile pipeline (facts, speculation, owner alerts), Launch Radar, merchant bank offers | Official-domain allow-list (`docs/research/official-domains.yaml`) |
| C. App | Flutter: onboarding, holdings, spends, rankings, typed Checkout with reward and bank offer, launch feed, QR decode | API contracts agreed on Oct 6 |

| Day | A. Engine and data | B. Market intelligence | C. App | Exit check |
|---|---|---|---|---|
| **Oct 6 (tonight)** | Repo skeleton, `.env` git-ignored, pre-commit secret scan | Account API credit check. Spikes: fetch the 20 seed issuer pages (DR-4 test), Ads Transparency India region, one `amazon_product` page for bank offers | Flutter skeleton; agree API contracts | Fetch-success % recorded; API contracts written |
| **Oct 7** | Schemas (SQLite, integer paise). Engine with property and golden tests. `/pay` | Gateway with cache, budget guard, fixture replay. Record fixtures. Fetcher + extraction for the 20 seed cards | Onboarding, holdings, manual spends | Golden tests green; seed cards profiled from official pages |
| **Oct 8** | Card Finder with breakdowns | Card Profile pipeline: auto-publish, speculation, owner alerts, read-only change feed. Merchant bank offers from issuer pages | Rankings screen; typed Checkout with reward and bank offer | One refresh auto-publishes from a bank page; one forum report lands as speculation; one Checkout shows a live bank offer |
| **Oct 9** | Cap Watch on a fake clock (if time) | Launch Radar end to end: Ads Transparency + news → profile → score | Launch feed; QR decode → `/pay` | Every demo flow runs from a warm cache |
| **Oct 10** | Evals on fixtures | README naming the SerpApi engines and why | Video under 3 minutes, checked in incognito | **Submitted by 18:00**, not left as a draft |

**Cut order** (cut first → last):
1. notification capture and pay pack (already out)
2. MCP and n8n
3. chat agent (the Commerce demo runs on screens; keep at most 2 tools if built)
4. Eligibility Path
5. Renewal Review
6. UPI intent hand-off (keep the QR decode)
7. Cap Watch
8. `amazon_product` bank offers (keep issuer-page offers)

**Never cut:** the engine, P0 Finder, typed Checkout (reward and bank offer), the Card Profile pipeline (facts, speculation, owner alerts), Launch Radar **including the Ads Transparency worker**, which together carry the "meaningful SerpApi usage" criterion.

### Three-month product

- **M1 (Oct 11 – Nov 10):**
  - Postgres with RLS in ap-south-1, DBOS, auth, the outbox
  - consent and `user.erased` with crypto-shredding
  - catalogue grows on its own beyond the 20 seeds (Launch Radar, sitemap sweep, user requests); owner alert channel and digest; ops MCP
  - statement upload (E1 P1), redacted before parsing
  - Places API for D2
  - Play Data Safety draft
  - start Gmail OAuth verification and the CASA assessment (`gmail.readonly`): privacy policy, verified domain, demo video and assessor booked; until verified, testing is capped at 100 users
- **M2 (Nov 11 – Dec 10):**
  - notification capture with on-device parsing for the top 5 issuers
  - Gmail capture of bank transaction alerts, once OAuth verification and CASA have passed
  - pay pack (if DR-6's test fails), trackers (E2), Replan (F4)
  - public changelog, user corrections (A8)
  - **closed beta** with TechnoFino and Reddit users, running the DR-2 consent A/B
- **M3 (Dec 11 – Jan 10):**  
  _(The reduced iOS client comes after M3: owner decision.)_
  - Eligibility Path (C1, C2), Renewal Review live (F2), Launch Radar scoring live
  - evals in CI, DPDP counsel review, load hardening
  - Play listing
  - **the DR-2 ledger decision**


---

## 6. Risks register

| Risk | Likelihood | Impact | Mitigation | Owner signal |
|---|---|---|---|---|
| Wrong card facts reach users | Medium | High | Official-source allow-list, quote check, range checks, automated weekly re-check, auto-rollback on mismatch, owner alerts with refs, `as_of` labels | Corrections per week; re-check mismatch rate over 2% |
| Speculation shown to users turns out false | Medium | Medium | Clear "not confirmed by the bank" label, refs shown, never used in the maths, auto-expiry after 60 days unconfirmed | Share of speculation later contradicted by an official source |
| Issuer fetch blocked (bot walls, JavaScript) | Medium | Medium | Playwright fallback; AI Mode-assisted entry (DR-4 trigger) | Fetch success below 70% |
| SerpApi credits exhausted before the demo | Medium | High | Fixtures, a 35-credit reserve, guard at 45 per hour | Credits at 80% |
| Demo "materially non-functional" | Low-Medium | High | Warm-cache run-through on Oct 9, cut order, 18:00 submit | Oct 9 exit check missed |
| Secret leaked in repo history | Low | Disqualifying | `.env`, pre-commit scan, history check before making the repo public | Scanner hit |
| UPI apps block deep-link hand-off | Medium | Medium | Stretch goal only; fall back to "pay in your UPI app with card X" | Real-QR test fails |
| Play rejects notification listener | Medium | High | Ship without it, separate consent, pre-submission questions | Review outcome |
| Merchant → MCC mismatch | High | Medium | Personal overrides, statement learning, low-confidence flag | Override rate |
| Haiku 4.5 retired | Low near-term | Low | Model ID in config | Deprecation notice |

---

## 7. Owner decisions (answered 2026-10-06)

| # | Question | Answer | Effect on the plan |
|---|---|---|---|
| 1 | Is the reduced iOS client in the 3-month plan? | **After M3** | Android only through M3 |
| 2 | Hackathon first or product first? | **Hackathon first** | §5 day plan takes priority until Oct 10 |
| 3 | Which track? | **Commerce & Market Intelligence** | Demo leads with Checkout Advisor, Launch Radar and Finder; chat agent moves up the cut order; effective price (D7) dropped 2026-10-07 and its Shopping budget moved to the demo reserve; Ads Transparency never cut |
| 4 | Solo or team? | **Team of 2–5** | Three parallel workstreams (§5) |
| 5 | Monetisation | **No affiliate money** | `commerce` module and DSA question removed |
| 6 | Ledger default until the M2 test? | **Server ledger until the A/B** | DR-2 stands as written |
| 7 | Seed cards | **The 20 most popular cards in India** | Researched in `docs/research/seed-cards.md`, with official sources in `docs/research/official-domains.yaml` |
| 8 | Owner alert channel | **Decide at implementation** | DR-12 leaves the channel open |

Also decided: no human in the loop (DR-12); official bank facts auto-publish (DR-4); the official-domain allow-list is configurable; Google Play review is out of hackathon scope.

---

## 8. Appendix — scorecard

| Area | Workflow-first | Multi-agent | Event-services | On-device |
|---|---|---|---|---|
| Orchestration | **Won** (backbone) | Lost, except batch Launch Radar fan-out | Agreed single agent | Agreed |
| Ledger | **Won (provisional)** | Same as WF | Switched to local-default; lost | Lost for now; owns the reopen test |
| Engine | **Won** | Same as WF | Same as WF | Lost (conceded) |
| Sourcing | **Won** (issuer-first, quote check, AI Mode never sole) | Verifier vote lost; second source for high-severity diffs only | Agreed | Conceded |
| Durable / events | DBOS won; event design lost to ES | Temporal lost (conceded) | **Won** the outbox and erasure design | DBOS agreed |
| Privacy | Lost on merchant keys to Haiku (conceded) | Lost on `agent_memory` deletion story | **Won** erasure | **Won** on-device parsing, chat capsule, `reason_codes`, signed packs |
| Injection | — | **Won** | Conceded | Conceded |
| Evals | Per-node design won | **Won** the Launch Radar backtest and the cross-flow set | Won bus contract tests | Won "report wrong answer" |
| Hackathon plan | **Won** (18:00 submit, server `/pay`) | Cut list adopted | Cut order adopted | Over-scoped (conceded) |
| Ops MCP | — | — | **Won**, moved to M1 | — |

**Verification notes.**
- Misreads: `reddit-…` 11c and 10b were cited as aggregator distrust (DR-2), and MA's "router cannot compose flows" was overstated.
- **(Unverified):** OD's Play "collection" definition, WF's DBOS `recv()`, the Ads Transparency India region code, and every DPDP Rules point.
- The latency figures the architects cited match `serpapi_tool_surface.md` §0.
