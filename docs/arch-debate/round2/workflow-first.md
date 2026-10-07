# Round 2 rebuttal: workflow-first

The four proposals agree more than they differ. All four keep money maths deterministic and out of the LLM. All four put every SerpApi call behind one gateway with an Account-API budget guard. All four require human review before a card fact changes, and all four store provenance per field. All four answer Checkout Advisor from a lookup on the phone. Three of four (all except multi-agent) pick DBOS.

## 1. The other proposals

### Multi-agent (supervisor + specialists)

**Strongest points**
- **Cross-flow questions.** Its example is "Should I renew Regalia Gold, and if not, what replaces it and can I get it?" That one question spans three flows: Renewal Review, Card Finder and Eligibility Path. This is the case my fixed workflows handle worst, and `architecture.md` §4.11 names "graph rigidity" as a known risk of Option B.
- **Tool growth.** `features.md` lists about 50 features. By P1 the agent would carry 25–35 tools, and several overlap: `simulate_rewards`, `renewal_review`, `replan_diff` and `optimize_portfolio` all compute value. The split trigger in the OpenAI guide is overlap, not raw count (`architecture.md` §1.3). My "about 10 tools" claim was sized for the hackathon, not for P1.
- **Prompt-injection isolation.** Only the steps that read web content touch it, and they have no write tool beyond `queue_review`. The front agent never sees raw web text.

**Weakest points**
- **Thin specialists.** It concedes that CapWatch and RenewalReview are "nearly LLM writes the sentence". The cross-flow case doesn't need a supervisor either: one agent calling `renewal_review`, then `recommend_cards`, then `eligibility_path` in sequence is ordinary single-agent tool use (`architecture.md` §1.3, "maximize a single agent first").
- **Verifier fan-out against the credit budget.** Three verifiers per card (issuer PDF, AI Mode, DDG/Brave) multiply searches against a 120-search profile envelope on a 250/month free tier (`hackathon_credits_rules.md` Q1). It admits the parallel speed-up is "mostly illusory" under the 50-per-hour cap.
- **Opus for EligibilityPath.** It cites `models.md` §4 for this, but in its own design pass/fail is decided by rules. Paying Opus prices to write a narrative over rule output is hard to justify. It is also the largest build and eval surface of the four.

### Event-services + MCP

**Strongest points**
- **A concrete event bus.** It specifies a transactional outbox in Postgres, claimed with `FOR UPDATE SKIP LOCKED` and woken by `LISTEN/NOTIFY`, with a 150-line budget. My round-1 "events table" was vague by comparison.
- **The best DPDP deletion design of the four.** Every service must handle a `user.erased` event, CI fails if a handler is missing, and a per-user key is crypto-shredded so backups and outbox history are covered too. Every event also carries a purpose tag.
- **Scoped MCP for operations.** Reviewers and Claude Desktop get read and `propose_correction` access, never publish. It also stores money as integer paise and uses `import-linter` to enforce service boundaries.

**Weakest points**
- **Services in name only.** It admits that for a solo build the services are "naming and folder discipline", so their benefits arrive months after the hackathon.
- **Stale cap counters.** Eventual consistency between `txn.recorded` and `cap_counter` means advice can be one transaction behind. That is exactly the case D1 exists for: a cap that runs out mid-day (`features.md` D1, pain point 2).
- **MCP is not a user feature.** It adds an auth surface, and its value is ops convenience plus a demo moment.

### On-device-first

**Strongest points**
- **Trust users can verify.** "Your transactions never leave your phone" answers the documented distrust of CRED-style aggregators (`technofino-…` 11c, `reddit-…` 11c). It also lets the Play Data Safety form say "not collected".
- **Less leaks by design.**
  - Each bundle contains every card, so the server never learns what a user holds.
  - Launch and change alerts go out as one FCM topic ping, with no per-user targeting.
  - "Why this card?" is templated from the engine's `reason_codes`, so it is free and works offline.
- **Real offline coverage.** Card Finder, Cap Watch and Renewal Review all keep working offline, not only Checkout Advisor.

**Weakest points**
- **It reverses a recorded decision.** `ideation.md` says the app is a thin client, and the proposal admits it gives up the data moat. Crowd MCC maps (D2), rejection intelligence (C3), community signals (H2) and cross-user backtests all need server-side data. `ideation.md` → "Competition" names backtesting on the user's own data as a defensible difference.
- **A Dart engine conflicts with two plans.** `ideation.md` leans to a Python backend (Open decisions #1) and plans a web recommender for SEO. A Dart-only engine forces a WASM build or a second engine.
- **Operational risks.** Losing the phone loses the ledger. Old app versions run old engine semantics. A Kotlin notification listener plus a signing pipeline is a lot to build by Oct 10.

## 2. Concessions

1. **My tool ceiling is a hackathon number.** I now treat "about 10 tools" as a budget to measure against, not a design property.
2. **My pay pack was a half-measure.** The on-device proposal shows that the trust argument, not just latency, justifies doing more on the phone.
3. **Event-services specified the bus and erasure better.** Its outbox and `user.erased` design is better than mine, and I adopt it unchanged.
4. **Merchant classification should run locally.** I allowed Haiku for it. Merchant strings derived from a user's transactions are user data (`models.md` §4), and Claude has no India region, so they should be classified locally. Haiku stays acceptable only for globally seen merchant keys taken from QR codes.
5. **My hackathon plan lacked a cut order.** Event-services and on-device both state one. Mine tried to ship everything.

## 3. What I would adopt into a merged design

- **From event-services:** the outbox bus; per-service Postgres schemas guarded by `import-linter`; integer paise; erasure via `user.erased` with CI enforcement plus crypto-shredding; an MCP server for ops (read and propose only).
- **From on-device:**
  - Parse raw notification text on the device, using signed parser packs.
  - Sign the rule and merchant packs (Ed25519) and pin the key in the app.
  - Announce new packs with an FCM topic ping.
  - Template the "why" reply from `reason_codes`.
  - Offer chat context as an opt-in "capsule" of aggregated spends that the user can preview.
- **From multi-agent:**
  - Web-reading steps get no write tools beyond `queue_review`.
  - A cross-flow conversation eval set, about 30 scripted multi-flow chats.
  - A deterministic pre-router for "which card for X".
  - Verifier fan-out only for high-severity diffs (rate, cap, fee), not every field.
- **Kept from mine:** per-flow workflows as the backbone; a single front agent; Checkout Advisor with no LLM; and AI Mode never the sole source of a published number.

## 4. Decisions still genuinely contested

| # | Decision | My position | Deciding criterion |
|---|---|---|---|
| 1 | **Where the ledger lives** | Server of record (encrypted, row-level security, India region) holding parsed fields only; raw capture stays on the device; offer a "device-only" mode later if demand appears | Closed-beta evidence. How many users opt into server sync? Do the P1 features that need it (E3 evidence for F5, D2 crowd MCC, multi-device) beat "never leaves the phone" in retention? Second deciding input: Play's review of the listener |
| 2 | **AI Mode vs issuer-page extraction** | Issuer pages and MITC documents are the primary source; AI Mode is a cross-check. For the hackathon, AI Mode may seed fields marked `source_type=ai_mode` and flagged unverified | On the 25-card gold set: field accuracy and credits per correct field for (a) fetcher plus extraction vs (b) AI Mode. Also, how often AI Mode's references include the issuer's own domain |
| 3 | **Single agent vs specialists** | One agent, with tools loaded per Skill or deferred | Run tool-selection and cross-flow trajectory evals at the P1 tool count. Below 90%, or growing if/else logic in the prompt, means moving to specialists called as tools (multi-agent's shape, never handoffs) |
| 4 | **DBOS vs Temporal** | DBOS on the same Postgres | Move to Temporal when fan-out over users or review waits outgrow one Postgres, or when the team already runs Temporal. A solo developer should not run a Temporal cluster in month 1 |
| 5 | **Hackathon scope** | Ship the P0 core, the live Card Profile pipeline into the review queue, and Launch Radar, because they are where SerpApi usage is "meaningful" (`hackathon_credits_rules.md` Q4). Cap Watch and Renewal Review run on a fake clock; chat gets 4 tools. Cut order: notification capture → Eligibility Path → MCP/n8n → chat | The unweighted judging criteria plus "materially non-functional" rejection risk. Every demoed flow must run end to end from a warm cache. Submit by Oct 10, 18:00 IST |

A sixth decision is close to settled: Checkout Advisor runs a lookup on the phone over a server-built table. The open question is only whether Card Finder also runs on the device. I say no: the full engine stays in Python, verified against the phone by shared golden vectors.
