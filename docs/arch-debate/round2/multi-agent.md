# Round 2 rebuttal: multi-agent architect

All four proposals share the core: the LLM is never the calculator, one `serp_gateway`, field-level provenance, a human review queue (HRQ) before publishing, no LLM in Checkout Advisor, no engine grant on affiliate payouts (B7), and Android first. The real debate is narrower: where the ledger and engine live, how card facts are sourced, how much agency the chat layer gets, and what we cut for Oct 10.

## 1. The other proposals

### Workflow-first (WF)

**Strongest points**
- **Evidence checks in code.** Every extracted field carries `{url, quote}`, and code checks that the quote appears in the fetched page (WF §6). Native citations can't be combined with JSON output (`models.md` §1), so this is the right workaround, and it is cheaper and stronger than my verifier vote.
- **AI Mode is never the only source of a published number** (WF §5). The case rests on `architecture.md` §4.11 ("AI Mode answers are themselves LLM summaries") and pain point 16 in `features.md`: users already distrust stale or hallucinated rates.
- **The smallest eval surface.** There is one eval per node and one agent with about 10 tools. This matches `architecture.md` §1.1, §1.3 and §6. It is the most likely of the four to ship working by Oct 10.

**Weakest points**
- **It admits its own conversational ceiling** (WF "Weakest points"). `reddit-…pain-points.md` §1a records about 5,000 "profile dump" posts that ask about keeping, closing and applying at once, and about 10 consolidated tools will answer those rigidly.
- **Every changed value waits for a human**, and nothing triages the queue apart from a severity label. At 150 cards with monthly churn, human review becomes the freshness limit (WF Risk 1).
- **Its day plan is the most aggressive of the four.** QR scan, UPI hand-off, Launch Radar, Cap Watch and Renewal all land on Oct 9, and the UPI deep-link behaviour is still unverified (`ideation.md`, "To verify").

### Event services + MCP (ES)

**Strongest points**
- **Each tool is written once** and exposed over MCP with scopes. The ops scope can read and propose, and "nothing in MCP can publish". A reviewer can then work inside Claude Desktop ("simulate this devaluation on all holders"). That is real value for reviewer throughput, which is the shared bottleneck, and `architecture.md` §5.2 rates it a strong demo.
- **DPDP erasure is enforced by code.** CI fails if a service has no `user.erased` handler, and crypto-shredding covers backups and outbox history. This is the most concrete DPDP design of the four.
- **The outbox lives in a Postgres table** (`SKIP LOCKED` plus `LISTEN/NOTIFY`). That gives events with no new infrastructure.

**Weakest points**
- **It admits the "services" are folder discipline** for a solo four-day build.
- **Its own stated cost is eventual consistency on cap state.** Advice can be one transaction behind, and the cap counter is exactly what pay-time advice depends on (`ideation.md`, "Cap state").
- **MCP over HTTP adds an auth surface** that no end user benefits from at the MVP stage.

### On-device first (OD)

**Strongest points**
- **The privacy promise is the strongest of the four.** Every user downloads all cards, so the server never learns holdings. On-device parsing lets the Play Data Safety form honestly say "not collected". This matters because Anthropic has no India region (`models.md` §1) and distrust of aggregators is documented (`reddit-…` 11c).
- **Offline coverage goes beyond Checkout.** Finder, Cap Watch and Renewal also work offline, and payments often happen in basements and kirana stores.
- **Signed, versioned rule bundles** give a clean rollout unit: staged channels, plus `min_engine_version`.

**Weakest points**
- **It reverses a recorded decision** ("the app is a thin client", `ideation.md`). It also gives up the shared data loop that `ideation.md` calls the moat: the crowd MCC map (D2), community signals (H2) and rejection intelligence (C3).
- **Losing the phone loses months of ledger.** OD Risk 3 says so, and cap and milestone tracking depend on that ledger.
- **The engine is written in Dart.** That rules out Python reuse for the web recommender (`ideation.md`). Server-side Launch Radar scoring becomes impossible, and the duplication moves rather than disappears.
- **It is the heaviest four-day plan:** a Kotlin listener, a signing pipeline and client-side tool relay.

## 2. Concessions

1. **Most of my "specialists" were LLM nodes in disguise.** CapWatch, RenewalReview and the Explainer each wrap one engine call plus prose, so calling them agents added hops and eval surface with no gain. I said this in round 1 under "Weakest points" and should have acted on it. WF is right about them.
2. **My three-verifier vote was weaker than WF's quote check.** AI Mode, DDG and Brave are all LLM summaries of overlapping sources, so their errors are correlated, not independent votes. A quote that matches the issuer's MITC text is real evidence.
3. **DBOS beats Temporal for this team.** It runs on the same Postgres with no cluster, and it can still wait days for a reviewer (WF §7, ES §7, OD §7). Temporal is the move only at large scale.
4. **I didn't specify on-device parsing of notifications.** OD and ES both do it. Raw alert text should never leave the phone; I had capture on the device but parsing unspecified.
5. **My cost estimate (about 1.6–2× a single agent) had no accuracy evidence behind it.** Until an eval shows multi-agent answers are better, the cheaper design should win.

## 3. What I would adopt into a merged design

| From | Adopt |
|---|---|
| WF | The backbone: workflows as step functions with idempotent, checkpointed steps. `{url, quote}` checked against fetched text. Issuer page and MITC as the primary source, AI Mode for discovery and cross-checks. Guard that every ₹ figure in prose comes from the engine. The day-1 engine and golden tests |
| ES | Postgres outbox for the few events that fan out (`profile.changed`, `txn.recorded`, `launch.candidate`). Purpose-tagged consent, plus the `user.erased` CI contract. An MCP server with ops scope for reviewers, in month 1 rather than at the hackathon |
| OD | Notification parsing on the device. Signed, versioned card bundles as the delivery unit for the phone's Checkout pack. Minimal, previewable "capsules" of what is sent for chat. `min_engine_version` gating. "Report wrong answer" with redacted repros |
| Mine (kept) | Agents-as-tools only where the work is open-ended. LaunchScout is a lead with parallel workers in batch, one per source family, and fans out per source, not per user. A `card_research` sub-agent for open chat questions ("Atlas vs Infinia for a Europe trip") is added only when the trigger in decision 4 below fires. Tool isolation for prompt injection: anything that reads web text has no write tool except `queue_review` |

The merged design is WF's design plus ES's outbox and MCP, OD's privacy edges, and one batch multi-agent component.

## 4. Decisions still contested

1. **Where the ledger and engine live**
   - **Options:** a server ledger with the engine in Python (WF, ES, me), or a phone ledger with the engine in Dart (OD).
   - **My position:** server ledger of record, holding a minimal set of fields: `amount, merchant_key, last4?, ts, card_id`, with parsing on the device. The Python engine is canonical, and a Dart lookup runs only over a precomputed table.
   - **Deciding criteria:** whether Play review treats a server-side ledger as a problem for the notification-listener declaration, and whether closed-beta users rank privacy above multi-device use and backups. If both point OD's way, I switch.

2. **How card facts are sourced**
   - **Options:** AI Mode as primary (`serpapi_tool_surface.md` §1), or issuer pages and MITC as primary.
   - **My position:** issuer and MITC primary. An AI Mode value may be published only with a matching issuer quote. Otherwise it stays `pending` with low confidence.
   - **Deciding criterion:** field-level accuracy of each source on the 20–25-card gold set, together with the issuer fetch success rate. If issuer fetches fail on more than 30% of cards (bot walls, JavaScript-rendered pages), AI Mode with mandatory review becomes the practical fallback.

3. **One chat agent or specialists**
   - **My position:** for the hackathon and the beta, one Concierge with about 10 consolidated tools. Split into specialist agents (agents-as-tools, never handoffs) only when one of these fires:
     - tool selection drops below 90% on a 150-message eval that includes multi-flow questions (WF's own trigger)
     - more than 15 overlapping tools (OpenAI guide, `architecture.md` §1.3)
   - **Deciding criterion:** that eval, run at each milestone as features from `features.md` sections C, E, F and G land.

4. **Durable execution: DBOS or Temporal**
   - I now back DBOS.
   - **Deciding criterion:** Temporal only if we need workers in more than one language, or workflow volume beyond what one Postgres can handle.

5. **Hackathon scope (Oct 10)**
   - **Must ship:**
     - P0 v1 scope (`features.md`)
     - the Card Profile pipeline through to the HRQ
     - Launch Radar as the main use of SerpApi ("meaningful usage", `hackathon_credits_rules.md` Q4), with 3–4 parallel source workers over fixtures plus a few live calls
   - **Thin versions:** Cap Watch and Renewal Review on a fake clock.
   - **Cut:** the on-device pack (use a server `/pay`), notification capture, client-side tool relay, MCP and Eligibility Path.
   - **Deciding criteria:** a demo that is reliable from a warm cache, and finished by Oct 10 18:00 IST.
