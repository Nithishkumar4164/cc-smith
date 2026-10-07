# Round 2: rebuttal from the on-device-first architect

All four proposals now agree on the following:
- Flutter, Android-first.
- A deterministic engine.
- One SerpApi gateway.
- A human review queue (HRQ) on every write to card facts.
- No LLM in Checkout Advisor.
- Bank alert notifications parsed on the device.

Three proposals also put a Checkout lookup table on the phone. What remains in dispute is **where the ledger of record lives**, and therefore where the engine runs. Most of my disagreements below follow from that one question.

## 1. The other proposals

### Workflow-first

**Strongest points**
- **AI Mode is never the sole source of a published number** (its §5). This follows from `architecture.md` §4.11, which notes that AI Mode is itself an LLM summary, and pain point 16 in `features.md`. My round-1 design used AI Mode for cited summaries alongside the fetcher without ranking the two. Workflow-first ranks them correctly.
- **The explanation guard plus a template fallback** (§6): if any ₹ figure in the prose is missing from the engine output, the reply falls back to a template. B7 is enforced by database grants. Both are cheap and can be checked.
- **The most realistic hackathon plan.** It submits at 18:00 IST, not 23:59. Server `/pay` is the only advice path in the MVP. The pay pack waits for M2.

**Weakest points**
- **The server ledger of record contradicts the evidence on trust.** Users distrust aggregator apps (`technofino-…pain-points.md` 11c, `reddit-…` 10b), and H3 asks for "local-first capture where possible". Uploading parsed transactions makes cc-smith one more CRED-style data holder.
- **Merchant keys go to the LLM.** `models.md` §4 says merchant strings "are user data and stay on device". Workflow-first sends merchant keys to Haiku and its §8 treats this as PII-free.
- **Two scorers remain.** The Dart pay pack duplicates part of the Python engine, which the proposal admits. It also bets that `/pay` latency on 4G will be good enough. That has not been measured (`architecture.md` §9).

### Multi-agent

**Strongest points**
- **Prompt-injection isolation** (its §8). Agents that read web pages hold only `queue_review`, and the Concierge never sees raw web text. This is the best security idea in round 1, and nobody else addressed injection.
- **A backtest for Launch Radar recall:** replay 12 months of launches against the Reddit archive as ground truth. This is a real eval, where the rest of us only have hand-labelled sets.
- **A concrete cross-flow example:** "Renew Regalia Gold? If not, what replaces it, and can I get it?". This is the honest test for whether one agent with ~10 tools is enough.

**Weakest points**
- **Its own admission:** user-path specialists are "thin wrappers around one deterministic tool". The 50-searches-per-hour cap makes parallel fan-out mostly illusory (`architecture.md` §1.2, `platform_offerings.md` §4.2).
- **Higher cost and operations load.** Chat costs $90–120 per month for 100 users, against $55–65 (`models.md` §5). It adds Temporal and per-agent eval suites to a 4-day solo build. `architecture.md` §6 rates this option "fragile" for the hackathon.
- **`agent_memory.plan_state` per user** is a new store of personal data with no deletion story beyond "delete on request".

### Event-services

**Strongest points**
- **The most rigorous answer on DPDP of the three.** Every event carries a purpose tag. A `user.erased` handler is required in every service, and CI fails if one is missing. A per-user data key can be crypto-shredded, which also covers backups.
- **An outbox table in Postgres instead of a broker** (`FOR UPDATE SKIP LOCKED`), within a 150-line budget. Money is stored as integer paise.
- **An MCP server with ops scope**, used from Claude Desktop with read and propose-only access ("simulate this devaluation on all holders"). It suits a user-agnostic knowledge service.

**Weakest points**
- **It still uploads `last4` and `merchant_text`** from every captured notification. "Raw text never leaves the phone" is weaker than it sounds.
- **Eventual consistency for cap advice.** Advice can be one transaction stale, which the proposal admits. On-device counters are consistent by construction.
- **The services are mostly naming discipline in v1**, which the proposal also admits. Its §1 condition for switching back to plain function calls (fewer than about 5 event types) probably holds at the hackathon.

## 2. Concessions

1. **Issuer-first extraction.** My round 1 put AI Mode on equal footing with the fetcher. Published numbers should come from issuer pages and MITC documents, with AI Mode as a cross-check, or as a fallback flagged for review when a fetch is blocked.
2. **Dart-only engine.** I said it removed duplication. It actually moves the duplication elsewhere:
   - The Python-side evals, the bundle gate and the future web recommender all need a Dart CLI or a WASM build.
   - Server-side `score_all_users` for Launch Radar analytics is impossible.

   The other three keep Python canonical. That fits the "Python backend" default in `ideation.md` → "Open decisions" better.
3. **My hackathon scope is the largest:** a Kotlin listener, a signing pipeline, and chat with tools that run on the phone. Workflow-first's plan is safer.
4. **Recovery and support.** A server ledger gives backup, multi-device use and support for free. My design pays for each of these separately. Encrypted backup in M1 is real work, not a footnote.
5. **Injection isolation.** I did not cover prompt injection at all. Multi-agent did.

## 3. What I would adopt in a merged design

| From | Adopt |
|---|---|
| Workflow-first | Workflow backbone for every server flow. Issuer-first sourcing with an `{url, quote}` check against the fetched text. The ₹-figure guard with template fallback. DBOS. An early submission target (Oct 10, 18:00 IST). |
| Multi-agent | Readers of web content hold no write tools beyond `queue_review` (applied to the extract and triage nodes, with no agents needed). Independent verifier votes, but only for high-severity changed fields, to protect credits. The Launch Radar recall backtest. |
| Event-services | Outbox-in-Postgres for server events. A purpose tag on any user data that does leave the device. Crypto-shredding for optional encrypted backup. An ops-scoped MCP server over the card knowledge base and the review queue, which suits a user-agnostic backend. |
| Mine (kept) | Rule bundles that are the same for every user, signed, and delivered over a CDN. The ledger, counters and Coach jobs on the device by default. Launch Radar matched on the device from the published feed. A chat capsule that previews what will be sent. |

**Merged default.** The server is workflow-first card intelligence plus one chat agent. The phone is the ledger of record and runs the full engine. The server ledger becomes an **opt-in, end-to-end encrypted sync**: the server stores only ciphertext. That gives the backup and multi-device benefits without the server holding readable transactions.

For the hackathon, the engine stays canonical in Python on the server, because the demo has only manual and typed data. The engine is ported to Dart in M1, but only if decision 1 below lands on the device.

## 4. Decisions still genuinely contested

| # | Decision | My position | Deciding criterion |
|---|---|---|---|
| 1 | **Where the ledger of record lives** | On the device, with opt-in encrypted sync | Closed-beta A/B on consent copy ("never leaves your phone" vs "synced securely"). Measure the opt-in rate for notification capture and 30-day retention. Also check whether any P1 feature needs readable ledgers across users. D2 crowd MCC and C3 rejection intelligence can use opt-in aggregates, so I expect not. |
| 2 | **Engine canonical language** | Follows from #1. If the ledger is on the device, the full engine is in Dart, with Python calling it through a CLI. If the ledger is on the server, the engine is Python with a Dart lookup table. | Measured Dart/Python parity-bug rate and the effort of porting the A2 rule DSL. Do not decide on taste. |
| 3 | **Extraction source** | Issuer page or MITC primary. AI Mode as a cross-check, or as a flagged fallback when a fetch is blocked. | On a 20-card gold set: field-level precision, and fetch success rate per issuer. If more than 30% of issuers block the fetcher, AI Mode-first plus verifiers becomes the pragmatic choice. |
| 4 | **One chat agent vs specialists** | One agent with about 10 consolidated tools | Tool-selection evals under 90%, or a failure rate above 20% on a labelled set of multi-flow prompts (multi-agent's Regalia example), means split. |
| 5 | **Hackathon scope** | Android only. Typed and QR checkout, Card Finder, Card Profile pipeline with the HRQ, and a thin Launch Radar. Cap Watch and Renewal on a fake clock. Cut notification capture and bundle signing first. Chat runs on the server with no tools on the phone. | The judging criteria: "meaningful SerpApi usage", usefulness, and a working local demo submitted before 18:00 IST on Oct 10 (`hackathon_credits_rules.md` Q4). |

**DBOS vs Temporal** is nearly settled: three of us chose DBOS. Revisit only if human-review waits and fan-out outgrow Postgres.
