# Round 2 rebuttal: Event-driven services + MCP

I read `round1/workflow-first.md`, `round1/multi-agent.md` and `round1/on-device-first.md` against my own `round1/event-services.md`. All four of us already agree on a lot:
- Flutter, Android-first, as the client.
- Checkout Advisor runs with no LLM and answers from data precomputed on the phone.
- A single SerpApi gateway is the only holder of the key.
- A human review queue (HRQ) gates every write to card knowledge.
- The B7 payout table is unreadable by the engine, enforced by database grants or bundle separation.
- No PII goes to Anthropic, which has no India region (`models.md` §1).

The real disagreements are narrower than the four labels suggest.

## 1. The other proposals

### Workflow-first

**Strongest points**
- **It is the simplest shape the research supports.** "Find the simplest solution possible" and workflows for fixed-step flows (`architecture.md` §1.1, §6). Every flow has a step table with a trigger, so it is buildable as written.
- **AI Mode is never the sole source of a published number** (§5). That is right for pain point 16 (`features.md`): users distrust stale and LLM-generated rates, and `reddit…pain-points.md` §12b records a 3x hallucinated Swiggy rate. `architecture.md` §4.11 itself warns that AI Mode answers "are themselves LLM summaries".
- **A deterministic quote check** (code verifies that the extracted `quote` appears in the fetched text, §6) and a ₹-figure guard on explanations. Both are cheap, high-value controls.

**Weakest points**
- **It needs events anyway but doesn't design them.** Its diagram has an `events` table, and Replan is triggered by `profile.changed`. What it doesn't specify is idempotent consumers, ordering, or which projections rebuild. My proposal specified those.
- **Fetcher-first sourcing will cover fewer cards in 4 days**, as it admits. Issuer sites are JS-heavy and behind bot walls (its risk 2).
- **The agent is reachable only through `/chat`.** There is no ops surface for the reviewer or the developer.

### Multi-agent

**Strongest points**
- **Prompt-injection isolation.** Agents that read web content hold only `queue_review`, and the Concierge never sees raw web text (§8). This is the best security idea of the round.
- **The tool-overlap trigger is real.** By P1 there are about 50 features, and tools such as `simulate_rewards`, `renewal_review` and `replan_diff` all "compute value". The OpenAI guide's split criterion is overlap, not count (`architecture.md` §1.3).
- **Scheduled flows call specialists from durable workflows**, not through synthetic chat messages. That fixes the fragility `architecture.md` §3.3 identified.

**Weakest points**
- **It concedes most of its own case.** "Most specialists are thin wrappers… workflow + one agent gets ~80%". CapWatch on Haiku is a sentence writer.
- **Fan-out buys nothing on the free tier.** It is throttled to 50 searches an hour (`architecture.md` §1.2). Three verifiers per field also spend 3× the credits from a 250-search month with no top-ups (`hackathon_credits_rules.md` Q1).
- **Its cross-flow example doesn't need a supervisor.** "Renew Regalia, what replaces it, can I get it?" is three sequential tool calls, which one agent with `renewal_review`, `recommend_new_card` and `check_eligibility` handles. Add to that a 150-message router eval, Temporal and Opus for an eligibility planner whose pass/fail is already decided by rules: none of it fits 4 days for one developer.

### On-device-first

**Strongest points**
- **Privacy that users can verify.** Raw transactions never leave the phone, so Play's Data Safety form can honestly say "not collected". That directly answers the distrust of aggregators in `reddit…` and `technofino…` §11 and is a real competitive difference (`ideation.md` → "Competition").
- **Signed, user-agnostic rule bundles on a CDN.** The server never learns which cards a user holds. One FCM topic ping replaces per-user fan-out. Launch Radar matching runs locally.
- **"Why this card?" is templated from engine `reason_codes`.** It costs nothing and works offline.

**Weakest points**
- **It reverses a recorded decision** ("the app is a thin client", `ideation.md` → "The app is the only surface") and loses backend debuggability.
- **It structurally blocks features the docs value.**
  - Crowd-sourced MCC per acquirer (D2) and community signals (H2) need cross-user data.
  - Device loss destroys the ledger that E2, E3 and F2 depend on; its own risk 3.
  - The Web recommender (`ideation.md`) needs the engine off the phone.
- **A Dart-only engine plus a client-side tool relay** puts a mobile round trip inside each agent tool call. Add the signing pipeline, and the 4-day plan is the tightest of the four.

## 2. Concessions

1. **My services are folder discipline for at least 3 months.** I said so in my own weakest points. Workflow-first delivers the same demo with fewer concepts. I should not ask a solo developer to name five services on day 1. The useful parts are the module boundaries and schema-per-domain.
2. **A general event bus at the hackathon is premature.** About 5 event types, each with one consumer, are function calls plus a durable job, which is my own stated threshold for changing my mind.
3. **On-device-first is better on privacy, and I underweighted it.** I uploaded `{amount, last4, merchant_text}`. Merchant text is a user's spending trail. The default should keep the ledger on the device, with server sync **opt-in**.
4. **Multi-agent's injection rule is stronger than my MCP scoping.** Scoping controls who calls a tool. It doesn't stop web text from steering an agent that holds broader tools.
5. **Workflow-first's "AI Mode is cross-check only" is more defensible** than treating AI Mode as a primary source.

## 3. What I would adopt into a merged design

- **From workflow-first, the backbone.**
  - Plain Python step functions, checkpointed per step.
  - APScheduler for the hackathon, then DBOS on the same Postgres.
  - Per-flow step tables.
  - The quote check and the ₹ guard.
- **From multi-agent:**
  - The isolation rule: any step that reads web content holds only `queue_review`.
  - Two independent sources (issuer page plus AI Mode) for **high-severity diffs only**, not three verifiers on every field.
  - The deterministic pre-router for "which card for X".
- **From on-device-first:**
  - The **card bundle** (signed, user-agnostic) as the shared half of my Checkout pack. The user overlay (caps, holdings) is computed on the phone.
  - Templated reason codes.
  - On-device alert parsing with the raw ledger kept local by default.
- **What I keep from mine:**
  - Exposing the same consolidated tools over **MCP**, with an ops scope for Claude Desktop and the reviewer (read plus `propose_correction`, never publish). It costs about half a day and makes the review queue and "simulate this devaluation on all holders" usable by one person.
  - A **transactional outbox** for the few events that truly fan out: `card.version_published`, `launch.published`, `user.erased`. These need a reliable "happened once, every consumer handles it" guarantee, especially for erasure under the DPDP Act.

## 4. Contested decisions that remain

| # | Decision | My position | Deciding criterion |
|---|---|---|---|
| 1 | **Where the ledger and engine live** | Ledger local by default; opt-in encrypted sync to the server for backup and multi-device; canonical engine in Python, with a Dart lookup for pay time | If the beta shows that most users reinstall or change phones, or want web/backtest features (E3, B3), server sync must be the default. If Play's Data Safety review or users react strongly against "collected", keep it local. Measure opt-in rates in the closed beta. |
| 2 | **AI Mode vs issuer-page extraction** | Issuer page or MITC is the only *publishable* source. AI Mode discovers URLs, cross-checks, and fills a field only as `pending` with an "unverified" badge | Run 3–5 sample queries (`serpapi_tool_surface.md` "Gaps") and check whether AI Mode `references[]` cite issuer domains or MITC PDFs. Then measure fetch success on the 20 seed cards: if fewer than 60% fetch cleanly, AI Mode-assisted entry is needed to reach coverage. |
| 3 | **Single agent vs specialists** | One Sonnet 5.5 agent with about 10 consolidated tools, and web-reading isolated in pipelines | Tool-selection eval on about 50 prompts: if accuracy is below 90%, or the tool list grows past 15 with overlap (`architecture.md` §1.3), split along multi-agent's lines. |
| 4 | **DBOS vs Temporal; events vs workflows** | DBOS plus an outbox in Postgres; no Temporal and no broker until measured need | Temporal or NATS only when we need long fan-outs (over about 100k users) or a team owns separate deploys. Until then, run no infrastructure that one person cannot operate. |
| 5 | **Hackathon scope** | Card Finder, typed Checkout and QR→UPI, Card Profile with HRQ, and Launch Radar as the SerpApi showcase. Cut notification capture, Eligibility Path, bundle signing and multi-agent fan-out. MCP only if Oct 9 finishes on time | Judges score "meaningful SerpApi usage" plus usefulness (`hackathon_credits_rules.md` Q4). Prefer features that spend credits visibly and work on a cold demo. Submit by 18:00 IST on Oct 10. |
