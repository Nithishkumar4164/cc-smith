# cc-smith: Agent Orchestrator Architecture Options (as of Oct 2026)

Researched 2026-10-06. Design principles come from the sources in section 1, fetched that day. SerpApi limits come from serpapi.com/pricing.md, fetched the same day, and from the earlier notes in `research_notes/SerpApi capabilities for hackathon/platform_pricing_limits.md`. Claude prices come from the Claude API skill's model table (cached 2026-09-25). Lines marked "Inference" are my design judgement and are not quoted from a source.

---

## 0. TL;DR

- **Recommendation: Option B as the backbone, with Option C's conversational layer on top.** That means deterministic per-flow graphs (workflows) plus a scheduler and event bus. A single conversational agent calls cc-smith's own tools, and the tools can also be exposed as an MCP server. Option A (a supervisor with 6 specialist agents) is the weakest fit. Every source below says to start with one agent or a workflow, and cc-smith's flows have fixed steps, are mostly deterministic, and depend on each other.
- **Flow 2 (1 s budget) uses no LLM on the hot path in any option.** It runs on a precomputed per-user scoring table, a merchant-to-category cache, rule tables and pure-Python scoring (p50 under 50 ms). Unknown merchants get an immediate answer from the user's default card, and the merchant is classified asynchronously afterwards.
- **SerpApi credits are the scarcest resource,** with 250 searches a month and 50 an hour on the free plan. You need a durable query cache that is checked before SerpApi's own 1-hour cache (cached SerpApi searches are free), a credit ledger with a budget per flow, and batched weekly refreshes.
- **Model tiers:** Sonnet 5.5 for the conversational agent and for profile extraction. Haiku 4.5 or local Ollama for merchant classification, dedupe and news triage. Opus 5.5 only offline: building evals and reviewing hard extraction diffs. Reward maths is never done by an LLM.

---

## 1. Grounding: what the authoritative sources say

### 1.1 Anthropic, "Building effective agents"
Source: https://www.anthropic.com/engineering/building-effective-agents
- Definitions: **Workflows** are "systems where LLMs and tools are orchestrated through predefined code paths." **Agents** are "systems where LLMs dynamically direct their own processes and tool usage."
- "Find the simplest solution possible, and only increasing complexity when needed." Many apps need only "optimizing single LLM calls with retrieval and in-context examples".
- Use agents for "open-ended problems where it's difficult or impossible to predict the required number of steps". Agents bring "higher costs, and the potential for compounding errors" and need "extensive testing in sandboxed environments, along with the appropriate guardrails".
- The five workflow patterns are prompt chaining (with programmatic "gates"), routing, parallelization (sectioning and voting), orchestrator-workers, and evaluator-optimizer.
- On frameworks: they "often create extra layers of abstraction that can obscure the underlying prompts and responses". Start with direct API calls.
- Tool design (the ACI): invest as much effort in tools as in prompts, use poka-yoke arguments, and write thorough documentation and examples.
- **How this maps to cc-smith:** flows 1, 2, 3b, 3c and 4 have known steps, so they should be workflows. Only "gather user context" (a conversation), "find launches / check recent changes" (open-ended web research) and "explain the recommendation" are agent-shaped.

### 1.2 Anthropic, "How we built our multi-agent research system"
Source: https://www.anthropic.com/engineering/multi-agent-research-system
- Cost: "agents typically use about 4× more tokens than chat interactions, and multi-agent systems use about 15× more tokens than chats."
- **When NOT to use multi-agent:** "some domains that require all agents to share the same context or involve many dependencies between agents are not a good fit for multi-agent systems today." Also: "most coding tasks involve fewer truly parallelizable tasks than research".
- Where it wins: breadth-first parallel research. Opus 4 as the lead with Sonnet 4 subagents "outperformed single-agent Claude Opus 4 by 90.2%" on their internal research eval.
- Bottleneck: "lead agents execute subagents synchronously … creates bottlenecks in the information flow".
- Evals: start small, with "about 20 queries representing real usage patterns", and use an "LLM judge that evaluated each output against criteria in a rubric", plus human testing.
- Reliability: errors compound in stateful agents. They "built systems that can resume from where the agent was when the errors occurred". They use "full production tracing" and "rainbow deployments" so running agents are not broken mid-run.
- **How this maps to cc-smith:** the only place parallel multi-agent research pays off is Flow 4 (launch discovery across sources) and possibly bulk profile refresh. Even there, SerpApi's 50 searches an hour cap kills most of the parallel speed-up. Flows 1 and 2 share user and portfolio state heavily, which is the "many dependencies" anti-pattern.

### 1.3 OpenAI, "A practical guide to building agents"
Source: https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf (text extracted locally from the PDF)
- Build an agent only for "complex decision-making", "difficult-to-maintain rules" or "heavy reliance on unstructured data". Otherwise, "a deterministic solution may suffice."
- "Our general recommendation is to maximize a single agent's capabilities first … often a single agent with tools is sufficient."
- Split into multiple agents only for complex logic ("many conditional statements") or tool overload, where "the issue isn't solely the number of tools, but their similarity or overlap. Some implementations successfully manage more than 15 well-defined, distinct tools while others struggle with fewer than 10 overlapping tools."
- There are two multi-agent patterns. In the **Manager** pattern, agents are called as tools. In the **Decentralized** pattern, agents hand off to each other.
- Models: "build your agent prototype with the most capable model for every task to establish a performance baseline", then swap in smaller models where the evals still pass. "Not every task requires the smartest model": retrieval and intent classification can use small models.
- Human intervention has two triggers: "exceeding failure thresholds" and "high-risk actions … sensitive, irreversible, or have high stakes … making payments".
- Use prompt templates with policy variables instead of many separate prompts or agents.

### 1.4 LangChain / LangGraph docs
Sources: https://docs.langchain.com/oss/python/langchain/multi-agent, https://docs.langchain.com/oss/python/langgraph/workflows-agents, https://docs.langchain.com/oss/python/langgraph/interrupts
- "Not every complex task requires this approach—a single agent with the right (sometimes dynamic) tools and prompt can often achieve similar results."
- Multi-agent helps "when a single agent has too many tools and makes poor decisions about which to use, when tasks require specialized knowledge with extensive context, or when you need to enforce sequential constraints."
- Patterns: Subagents (a supervisor that calls agents as tools), Handoffs, Skills (load prompts on demand inside one agent), Router, and Custom Workflow ("mixing deterministic and agentic logic").
- "At the center of multi-agent design is context engineering—deciding what information each agent sees."
- Workflows "have predetermined code paths"; agents "define their own processes and tool usage".
- Interrupts give human-in-the-loop. You need a checkpointer and a thread_id, and you resume with `Command(resume=…)`. "The node re-executes from the beginning when resumed", so side effects before an `interrupt()` must be idempotent.

### 1.5 Counterpoint: Cognition, "Don't build multi-agents"
Source: https://cognition.com/blog/dont-build-multi-agents
- Principles: "Share context, and share full agent traces, not just individual messages" and "Actions carry implicit decisions, and conflicting decisions carry bad results". Their default is a single-threaded linear agent, with a compression model added for long tasks.

### 1.6 Anthropic, "Writing effective tools for agents"
Source: https://www.anthropic.com/engineering/writing-tools-for-agents
- Don't build "tools that merely wrap existing software functionality or API endpoints". Build "a few thoughtful tools targeting specific high-impact workflows" and consolidate (for example `schedule_event` rather than list plus create).
- Namespace tools, return meaningful context (names rather than UUIDs), offer `response_format` with concise and detailed options, paginate and truncate, and write actionable error messages. Evaluate the tools themselves.

### 1.7 Design principles derived for cc-smith (Inference)
1. **Deterministic first.** Reward maths, cap tracking, channel rules, eligibility thresholds and scheduling are code. LLMs only read unstructured text (extraction, classification), converse, and explain.
2. **One conversational agent, many tools.** Add a second agent only when evals show tool confusion. Use the OpenAI rule of more than about 15 overlapping tools as the signal.
3. **The hot path (flow 2) is LLM-free.** Budget it like a payments API, not like a chat.
4. **Credits are a first-class resource.** Every SerpApi call goes through one gateway that has a cache, a ledger and per-flow quotas.
5. **Humans gate writes to the card profile store.** Changed values go to a review queue, never straight into production numbers. This is the "high-stakes action" trigger: a wrong reward rate gives a wrong payment recommendation.
6. **Durable, resumable runs** for batch flows: checkpoint after each node and make steps idempotent.

---

## 2. Shared building blocks (used by all three options)

### 2.1 Data stores
| Store | Contents | Tech (hackathon → product) |
|---|---|---|
| `card_profiles` | One row per card, with field-level values. Each field has `value, source_url, source_type (ai_mode/news/issuer_page/manual), checked_at, expires_at (=checked_at+30d), confidence, version` | SQLite/JSON → Postgres (JSONB per field) |
| `profile_review_queue` | Proposed field changes: `card_id, field, old, new, evidence[], extractor_model, diff_reason, status (pending/approved/rejected), reviewer, decided_at` | same DB |
| `users`, `holdings` | Income, city, credit score band, spend profile per category, held cards, renewal dates, fee waiver progress | same DB |
| `ledger_payments` | Recorded payments: `user, card, merchant_id, mcc/category, amount, channel, ts, reward_est` | same DB |
| `cap_counters` | Per user/card/cap-bucket/cycle: spent, earned, cap, reset date | Redis or a DB table, recomputed from the ledger |
| `merchant_cache` | `merchant_key → category, mcc_guess, source (maps/search/llm/manual), confidence, ttl` | SQLite → Redis + Postgres |
| `offers_index` | Active offers: `card/network/bank, merchant/category, value, min_txn, valid_from/to, source` | DB table, rebuilt by a batch job |
| `serp_cache` | `hash(engine, normalized params) → response JSON/md, fetched_at, ttl, credits_spent` | SQLite/files → Postgres/S3 |
| `credit_ledger` | Each SerpApi call: `flow, engine, query_hash, cache_hit, ts`. Used for monthly and hourly quota enforcement | DB table |
| `user_score_table` | Precomputed per user: `category → ranked [card, effective_rate, cap_left, milestone_bonus]` | Redis hash / in-process dict |
| `run_state` | Checkpoints for workflow runs (LangGraph checkpointer or a DB table) | SQLite → Postgres |
| `events` | Event log: `payment.recorded, cap.threshold, profile.changed, review.approved, launch.found, renewal.due, news.devaluation` | In-proc queue → Redis Streams / Postgres LISTEN/NOTIFY → a proper queue |

### 2.2 The SerpApi credit gateway (`serp_gateway`)
The free plan gives 250 successful searches a month and 50 an hour. "Only successful searches are counted… Cached, errored, and failed searches are not." SerpApi's own cache "expires after 1h" (`no_cache` param). Sources: https://serpapi.com/pricing.md and the earlier SerpApi notes.
- **Layer 1: cc-smith durable cache.** The key is a normalized query (lowercased, sorted params, location pinned to a canonical name). TTL by engine: AI Mode card facts 30 days (matches profile expiry), News 24 hours, Maps place category 180 days (merchants rarely change category), Shopping 24 hours.
- **Layer 2: SerpApi's 1-hour server cache.** Never send `no_cache=true` except for a manual force-refresh. Retries within an hour are then free.
- **Layer 3: avoid the call.** Before searching, check `card_profiles` freshness. Batch-refresh only fields that are expired or flagged. Prefer one AI Mode query per card that returns all fields, using `output=md`, which the SerpApi Python README says is roughly half the tokens of JSON. Use `subsequent_request_token` follow-ups only where the first answer had gaps.
- **Quota manager:** a token bucket of 50 an hour and a monthly budget split per flow. Suggested free-tier split: Flow 4 launches 40, scheduled profile refresh 120, on-demand enquiry 50, merchant classification 25, news/devaluation 15. If the budget is exhausted, degrade: serve stale data with a "last checked" stamp and queue the work for the next window.
- **Replay mode for dev and tests:** recorded fixtures, so evals and CI spend 0 credits.
- **Merchant classification ladder (to protect credits):** (1) exact `merchant_cache`, (2) rules (UPI VPA handle and merchant name patterns such as "*swiggy*" → food delivery, "*irctc*" → travel/rail, "*bpcl|hpcl|iocl*" → fuel), (3) local LLM or Haiku over the name with no search, (4) Maps search (1 credit) only if confidence is below the threshold, (5) write-back to the cache.

### 2.3 Human review queue
- Every extraction produces a candidate profile. The diff against the current profile is computed in code. Unchanged fields only get `checked_at` bumped (auto-approve). **Changed or new values go to `profile_review_queue`.** The current value keeps serving until approval, and the field is marked `pending_change` so answers can say "rate may have changed, under review".
- Severity routing: reward rate, cap or fee changes mean high severity, review within 24 hours, and on approval emit `profile.changed`. Cosmetic fields (lounge count text) mean low severity, and the review can be batched.
- Reviewer UI: a simple admin page showing old vs new, the evidence snippets with source URLs, approve, reject or edit. An LLM "second opinion" (Sonnet 5.5, or Opus 5.5 for disputes) can pre-annotate, but a human decides.
- On approval, the event triggers 3b/3c re-routing for every holder of that card.

### 2.4 Scheduler and events
- Hackathon: APScheduler (Python) or node-cron inside the app process, with jobs persisted in SQLite. Product: a durable job runner (Temporal, or Celery/RQ with beat, or managed cron plus queue workers). Inference: Temporal fits best if you want resumable multi-step runs. Celery or RQ with idempotent steps is enough below about 10k users.
- Jobs: `weekly_launch_scout` (Mon 06:00 IST), `nightly_profile_refresh` (only expired fields, under the credit budget), `nightly_offers_rebuild`, `monthly_cap_rule_recheck` (1st of month), `daily_renewal_scan` (finds holdings with renewal in 45 days), `hourly_news_devaluation_scan` (better daily on the free tier).

---

## 3. Option A: Supervisor/router agent + specialist sub-agents

### 3.1 Diagram
```
                         +------------------------------+
  User (chat/app) ------>|  Supervisor / Router Agent   |<---- Scheduler (cron) sends
                         |  (Sonnet 5.5, tool-calling)  |      synthetic "task" messages
                         +---+----+----+----+----+---+--+
             agent-as-tool   |    |    |    |    |   |
        +--------------------+    |    |    |    |   +-------------------+
        v               v         v    v    v                            v
 +-------------+ +-----------+ +-------+ +------+ +-----------+ +---------------+
 |Card Research| |Eligibility| |Payment| | Caps | | Lifecycle | | Launch Scout  |
 | (Sonnet)    | | (Sonnet)  | |(Haiku)| |(Haiku| | (Sonnet)  | | (Sonnet,      |
 |             | |           | |       | |      | |           | |  parallel)    |
 +------+------+ +-----+-----+ +---+---+ +--+---+ +-----+-----+ +-------+-------+
        |              |           |        |           |               |
        +--------------+-----------+--------+-----------+---------------+
                                   v
        +------------------------------------------------------------------+
        | Tool layer: serp_gateway | reward_engine (deterministic) | DBs   |
        | card_profiles | review_queue | ledger | merchant_cache | notify  |
        +------------------------------------------------------------------+
                 ^
                 |  FAST PATH (bypasses all agents): /pay endpoint -> reward_engine
```

### 3.2 Agents and tools
| Agent | Role | Tools | Model tier |
|---|---|---|---|
| Supervisor | Intent routing, conversation, composing the final reply | the agents below, `get_user_context`, `notify_user` | Sonnet 5.5 (low/medium effort) |
| Card Research | Freshness checks, profile extraction, recent changes | `get_card_profile`, `refresh_card_profile`, `search_changes`, `queue_review` | Sonnet 5.5 (extraction); Haiku 4.5 for triage |
| Eligibility | Eligibility and prerequisites (3a) | `check_eligibility`, `plan_prerequisites` | Sonnet 5.5 |
| Payment | Merchant classification fallback and explanation (fast path is code) | `classify_merchant`, `get_offers`, `score_held_cards`, `record_payment` | Haiku 4.5 / local |
| Caps | Nudges and monthly cap-rule re-check | `cap_status`, `refresh_card_profile(fields=caps)`, `notify_user` | Haiku 4.5 |
| Lifecycle | Keep, convert or close | `renewal_review`, `simulate_rewards`, `get_card_profile` | Sonnet 5.5 |
| Launch Scout | Weekly launches | `find_launches`, `dedupe_launch`, `refresh_card_profile`, `optimize_portfolio`, `notify_user` | Sonnet 5.5 lead, Haiku workers |

### 3.3 Cross-cutting concerns
- **Flow 2 in 1 s:** the supervisor cannot be in the path. A Sonnet tool-call round trip is roughly 1 to 3 s and a two-hop supervisor-to-subagent call roughly 3 to 8 s (Inference: typical latencies, not measured). So A needs a **separate non-agent `/pay` endpoint** anyway, which is already a step toward B. The Payment agent then only handles "why?" follow-ups and unknown merchants, asynchronously.
- **Scheduled flows:** the cron job sends a synthetic message ("run weekly launch scout") to the supervisor. This is fragile: whether the run completes depends on the LLM choosing the right steps every week.
- **State and memory:** a shared conversation thread plus DB. Subagents get compressed briefs, so context loss between agents is a real risk (Cognition principle 1).
- **Failure handling:** the supervisor retries subagents, with a max-turn cap. Partial failures are hard to resume unless you add checkpointing per subagent call.
- **Evals:** you need per-agent unit evals, router-accuracy evals (intent → right agent) and end-to-end trajectory evals. That is the largest eval surface of the three options.
- **Observability:** nested traces (Langfuse or LangSmith, or OpenTelemetry GenAI spans). Mandatory, because routing errors are invisible without them.
- **Cost drivers:** every request costs at least two LLM calls (supervisor plus specialist), and sometimes four. Token use follows the "multi-agent ≈15× chat" curve. The scheduled flows burn LLM tokens on orchestration that code could do for free.
- **Build effort:** hackathon, about 2.5 days to wire 7 agents with fragile prompts, leaving little time for evals. Product, about 3 months, with a lot of time going into router tuning and inter-agent context bugs.
- **Key risks:** misrouting; LLM-decided step order in money-related flows; non-determinism in scheduled jobs; cost blow-up; hard debugging; contradicts the "maximize a single agent first" guidance. **Upside:** a demo narrative that is easy to explain ("6 specialist agents"), and clean team ownership if several people build in parallel.

---

## 4. Option B: Deterministic workflow graph per flow + LLM nodes only where needed (RECOMMENDED backbone)

### 4.1 Diagram
```
 Triggers                       Orchestrator (code)                     Shared services
 --------                       -------------------                     ---------------
 User chat --> Intent router ---+--> G1 Enquiry graph ----------------+
 (rules + Haiku              |    gather_ctx*(LLM conv) -> candidates |
  classifier fallback)       |    -> ensure_fresh -> recent_changes*  |    +-----------------+
                             |    -> simulate -> marginal -> elig     +--->| reward_engine   |
 POST /pay (no LLM) ---------+--> G2 Payment fast path (pure code)    |    | (pure Python)   |
                             |    merchant_cache -> rules -> offers   |    +-----------------+
                             |    -> score_table -> reply (<1s)       |    +-----------------+
                             |      \-> async: classify*(LLM/Maps)    +--->| serp_gateway    |
 Event bus  -----------------+--> G3a Prereq graph (rules + LLM text*) |    | cache+ledger    |
 (payment.recorded,          +--> G3b Caps: counters -> nudge         |    +-----------------+
  profile.changed,           |      monthly: recheck* -> diff -> HRQ  |    +-----------------+
  review.approved, ...)      +--> G3c Renewal: simulate keep/convert/ +--->| card_profiles + |
                             |      close -> explain*                 |    | review_queue    |
 Scheduler (cron) -----------+--> G4 Launch: find* -> dedupe(code+LLM*)|    +-----------------+
                                  -> build_profile* -> HRQ -> score    |    +-----------------+
                                  all users (code) -> notify            +--->| notify, ledger, |
                                                                             | user store      |
  * = LLM node (bounded: one call or a small loop, structured output)       +-----------------+
  Checkpointer persists state after every node; HRQ = human review queue (interrupt)
```

### 4.2 LLM nodes (there are no free-roaming agents) and model tier
| Node | Flow | Kind | Model tier |
|---|---|---|---|
| `gather_user_context` | 1 | Short conversational loop with a slot-filling schema (income, city, spend split, existing cards, goals) | Sonnet 5.5 (low effort), or Haiku 4.5 if evals pass |
| `extract_profile` | 1, 3b, 4 | Single call: AI Mode markdown in, structured JSON out (strict schema, each field with an evidence quote) | Sonnet 5.5. Haiku 4.5 / local after an eval baseline |
| `detect_recent_changes` | 1, 3c | Classify News items: devaluation, fee change, new benefit, irrelevant | Haiku 4.5 / local Ollama |
| `classify_merchant` | 2 (async) | Name plus Maps place types → category | Haiku 4.5 / local (offline) |
| `dedupe_launch` | 4 | Code first (normalized bank + card name, fuzzy match). LLM only for ambiguous pairs | Haiku 4.5 |
| `explain_*` | 1, 3a, 3c | Turn the deterministic results into a friendly explanation, with numbers injected and not generated | Sonnet 5.5 (low) or Haiku |
| `plan_prerequisites_text` | 3a | Routes and dates computed by rules; LLM only writes the narrative | Haiku 4.5 |
| Offline: `review_assist`, `eval_judge` | all | Second opinion on diffs; rubric grading | Opus 5.5 (rare, batch) |

**Open-ended steps** use small bounded agent loops inside a node, each with a max-turn and credit cap: "find launches" (search, read, decide whether more searching is needed) and "recent changes" research when News is ambiguous. That is the "agents only for open-ended steps" principle.

### 4.3 Flow 2 fast path (meets ~1 s; target p95 under 300 ms excluding network)
1. `merchant_key` normalisation (UPI VPA / name / MCC if the app provides it) → `merchant_cache` lookup (Redis / in-proc LRU, under 5 ms).
2. Miss → rules regex table → if still unknown, use category `unknown`, apply the user's **default best card for general spend**, mark `confidence=low`, and **enqueue async classification** (Maps search via serp_gateway, then a Haiku/local LLM). The next payment at that merchant hits the cache.
3. Channel rules in code: on UPI, only RuPay credit cards are eligible. Card-specific UPI exclusions (many cards exclude UPI, rent or wallet loads from rewards) are a profile field.
4. `offers_index` lookup by (merchant, category, card/bank/network, date), precomputed nightly.
5. `score_held_cards`: for each held card, compute `effective_value = amount × rate(category, channel) bounded by cap_left + offer_value + milestone_delta_value − forex/fee_penalty`. Pure Python over at most ~10 cards takes under 1 ms.
6. Reply from a template ("Use HDFC Millennia: ₹50 (5%), cap ₹750 left this month"). No LLM. An optional "why?" button calls an LLM asynchronously.
7. `record_payment` happens after the user confirms. It writes to the ledger and emits `payment.recorded`, which updates `cap_counters` and recomputes that user's `user_score_table` rows asynchronously.
- Precompute: `user_score_table` is rebuilt on `payment.recorded`, `profile.changed`, cycle reset and `holdings.changed`, so the request path is essentially a lookup plus offer adjustment.
- Tail-latency guardrails: hard 800 ms timeout on any I/O. If the offers lookup fails, answer without offers and flag it. Never block on SerpApi.

### 4.4 Scheduled flows
- The scheduler starts graph runs with a `run_id`. Graphs are checkpointed, so a crash resumes at the last node. LangGraph checkpointer if you use LangGraph; otherwise a `run_state` table with plain Python step functions.
- 3b continuous: an event consumer on `payment.recorded` checks thresholds (70% / 90% / 100% of a cap) and calls `notify_user` with dedupe (once per threshold per cycle).
- 3b monthly: for each card with caps, `refresh_card_profile(fields=['caps'])` (cache-aware) → diff → HRQ. On approval: `profile.changed` → recompute the score table for every holder → send a "routing changed" message only if the user's best card for any category changed.
- 3c: a daily scan finds renewals 45 days ahead, or a `news.devaluation` event fires. The graph runs `simulate_rewards(keep)`, `simulate_rewards(convert to X)` and `simulate_rewards(close; shift spend)` and compares fee vs value, including fee waiver progress. An LLM explains the result and `notify_user` sends it.
- 4 weekly: `find_launches` (News plus AI Mode, bounded) → dedupe → `build_profile` (extraction) → **HRQ before scoring** (a new card's profile is unverified) → `score_all_users` (vectorized code over users × 1 card) → notify where `marginal_gain ≥ threshold` (e.g. ₹2,000 a year and over 15% of the fee).

### 4.5 State and memory
- Short-term: the graph state per run (a typed dict). Conversation memory only for G1 (thread_id). Long-term: structured user profile in the DB (no vector memory needed). A per-user "preferences and facts" table is filled by `gather_user_context`, and the user confirms it.
- Card knowledge is the structured profile store, not RAG over web pages. Evidence snippets are stored per field for audit.

### 4.6 Failure handling
- Per node: retry with backoff on 429/5xx (SerpApi 429 means throughput or credits exhausted, so do not retry within the hour; reschedule instead). Schema-validation failure on extraction: retry once with the validation error appended, then send the whole profile to the HRQ marked `extraction_failed`.
- Idempotency keys on `record_payment`, `notify_user` and `queue_review`, because LangGraph re-executes a node on resume.
- Circuit breakers: credit budget exhausted, LLM provider down (fall back to local Ollama for classification), or Maps failure (fall back to rules or unknown).
- Dead-letter queue for failed events, with a daily digest.

### 4.7 Evals and testing
- **Deterministic core (most of the value):** unit and property tests on `reward_engine` (cap boundaries, milestone thresholds, UPI channel exclusions, rounding, cycle resets) with golden worked examples taken from issuer T&Cs. This is where wrong answers cost users money.
- **LLM nodes:** per-node offline evals on fixtures (recorded SerpApi responses, so 0 credits):
  - `extract_profile`: field-level exact or tolerance match against a hand-labelled gold set of about 20 to 30 cards (matching Anthropic's "about 20 queries" start). Metrics: field precision and recall, hallucinated-field rate, and evidence-quote presence.
  - `classify_merchant`: accuracy on about 200 labelled Indian merchants (UPI handles, Swiggy, Zepto, BPCL, IRCTC, MakeMyTrip, utility billers).
  - `detect_recent_changes` and `dedupe_launch`: precision and recall on labelled news items and launch pairs.
  - `explain_*`: LLM-as-judge with a rubric (numbers match the engine output exactly, no invented benefits, mentions caps and conditions) plus a deterministic check that every ₹ figure in the text appears in the engine output.
- **End-to-end:** scenario tests per flow with a fake clock (renewal at 45 days, cycle reset, cap hit) and a fake SerpApi.
- **Latency test:** a load test on `/pay` (e.g. Locust or k6) asserting p95 under 300 ms and p99 under 1 s.
- **Model-swap protocol (OpenAI guide):** baseline every LLM node on Sonnet 5.5 (or Opus 5.5), then try Haiku and local; keep the cheapest one that holds the metric.

### 4.8 Observability
- One trace per run or request (OpenTelemetry spans; Langfuse self-hosted or LangSmith for LLM spans). Attributes: flow, node, model, tokens, cost, credits spent, cache hit, latency.
- Dashboards: SerpApi credits used vs budget per flow; cache hit rate per engine; `/pay` p50/p95/p99; HRQ backlog age; extraction failure rate; notification send and opt-out rates.
- Alerts: credits at 80% of the monthly budget, HRQ high-severity item older than 24 hours, `/pay` p95 over 500 ms, scheduled run failed.

### 4.9 Cost-per-month drivers (illustrative; Inference except the listed prices)
Prices (Claude API, per 1M tokens, input/output): Opus 5.5 $4/$20, Sonnet 5.5 $2/$10, Haiku 4.5 $1/$5. Prompt-cache reads on Sonnet 5.5 are $0.20/MTok (about 10% of input). The Message Batches API is 50% off for async jobs. SerpApi: free 250/mo; Starter $25/1k; Developer $75/5k; Production $150/15k (serpapi.com/pricing.md).
| Driver | Hackathon / demo month | Product @ ~1k active users (rough) |
|---|---|---|
| G1 enquiries (≈20–30k input incl. cached system+tools, ≈2k output, Sonnet) | ~50 runs → <$5 | ~1,500 runs × ~$0.05–0.08 → ~$75–120 |
| `/pay` fast path | $0 LLM | $0 LLM; "why?" explanations ~5% of payments on Haiku → <$10 |
| Merchant classification | local Ollama → $0 | new merchants only, Haiku → <$5 |
| Profile extraction (≈150 Indian cards × 1 refresh/30 d, ~6k in / 1.5k out, Sonnet; Batch API) | ~30 cards → <$1 | ~$1–3 |
| Launch scout and news triage | <$1 | <$10 |
| SerpApi | free 250 (tight; see the budget split in 2.2) | Developer $75 (5k searches) is likely enough with caching |
| Infra | laptop | ~$20–60 (small VM + Postgres + Redis) |
**The biggest drivers** are conversation volume on G1 and SerpApi plan size. The multi-agent overhead in Option A would multiply the first.

### 4.10 Build effort
- **4-day hackathon (solo full-stack dev):** Day 1: schemas, `reward_engine` with tests, seed about 20 card profiles (hand-checked), and the `/pay` fast path. Day 2: serp_gateway with cache and ledger, `extract_profile` plus the review-queue admin page, and G1 with a conversation node. Day 3: G4 weekly launch (triggered manually for the demo), 3b nudges on `payment.recorded`, 3c renewal on a fake clock, and a basic 3a. Day 4: evals on fixtures, tracing, demo script, and buffer. Plain Python step functions plus APScheduler is enough. LangGraph is optional; use it only if you already know it (interrupts and the checkpointer are nice for the HRQ demo).
- **3-month product:** Month 1: Postgres, a durable job runner, real event bus, full card catalogue (~100–150 cards), HRQ tooling with reviewer roles, and auth. Month 2: offers ingestion, Account Aggregator or SMS parsing for spend import (a separate compliance track), notification channels, and eval suites in CI. Month 3: load and latency hardening, model-swap cost tuning, monitoring and alerts, user-facing explanations, A/B testing of thresholds, and DPDP Act privacy review.

### 4.11 Key risks
- Wrong reward rules from T&C ambiguity (e.g. "excluding fuel, rent, wallet, govt"). Mitigation: the HRQ, a gold test set, showing "last verified" dates, and a conservative estimate when unsure.
- SerpApi free credits are too few to keep about 150 cards fresh every 30 days (about 150 or more searches a month just for refresh). Mitigation: refresh only expired or high-traffic cards, take hackathon prize credits, and upgrade to Starter or Developer.
- AI Mode answers are themselves LLM summaries and can be stale or wrong. Mitigation: require an evidence URL, prefer issuer pages, and cross-check with News.
- Graph rigidity: new kinds of user questions fall outside the intent router. Mitigation: a "general Q&A" node with read-only tools, which is where Option C's agent comes in.
- Legal and compliance: this is financial advice with no bank data integration. Add disclaimers, use no card numbers (only card product IDs), and treat spend data as personal data under the DPDP Act 2023.

---

## 5. Option C: Event-driven services, with batch pipelines separate from a conversational agent, and an MCP server over cc-smith's engine and data

### 5.1 Diagram
```
                     +---------------------------------------------+
  User chat -------->|  Conversational Agent (single, Sonnet 5.5)  |
  (web / WhatsApp)   |  prompt-cached system + tool defs           |
                     +----------------------+----------------------+
                                            | MCP (stdio/HTTP) tool calls
                     +----------------------v----------------------+
                     |   cc-smith MCP server (FastMCP / TS SDK)    |
                     |   tools: get_card_profile, simulate_rewards,|
                     |   optimize_portfolio, check_eligibility,    |
                     |   cap_status, renewal_review, plan_prereqs, |
                     |   score_held_cards, record_payment, ...     |
                     |   resources: card://{id}, user://me/summary |
                     +----+-----------------+-----------------+----+
                          |                 |                 |
         +----------------v--+   +----------v--------+  +-----v-------------+
         | Engine service    |   | Data service      |  | Payment API       |
         | reward_engine,    |   | profiles, users,  |  | POST /pay (no LLM)|
         | eligibility rules |   | ledger, HRQ, cache|  | <1s, same engine  |
         +-------------------+   +---------+---------+  +-------------------+
                                           ^
         Event bus (Redis Streams / NATS)  |  writes via pipelines only
  +----------------+  +------------------+ +----------------+ +-----------------+
  | Pipeline:      |  | Pipeline:        | | Pipeline:      | | Pipeline:       |
  | profile_refresh|  | launch_scout     | | caps_monitor   | | renewal_review  |
  | (nightly, LLM  |  | (weekly, bounded | | (stream consumer| | (daily scan +  |
  |  extraction)   |  |  research agent) | |  + monthly job)| |  news trigger) |
  +-------+--------+  +--------+---------+ +-------+--------+ +--------+--------+
          +----------> serp_gateway (cache+ledger) <----------+
                                   |
                         Human review queue (admin UI)
```

### 5.2 Agents and tools
- **One** conversational agent (Sonnet 5.5) with about 12 to 15 well-separated read and compute tools exposed via MCP. Write tools (`record_payment`, `notify_user` for itself) are allowed. Profile writes are **not** exposed to the agent; only pipelines propose them, through `queue_review`.
- Pipelines are plain workers. They contain bounded LLM steps: extraction (Sonnet or Haiku), news and launch triage (Haiku or local), and a bounded research loop in launch_scout (Sonnet, with max N searches per run).
- The MCP server also lets you plug the same tools into Claude Desktop, Claude Code or any MCP client for internal ops ("show me pending reviews", "simulate the Axis Atlas devaluation on all holders"). That is useful for the builder, and makes a nice hackathon demo.

### 5.3 Cross-cutting concerns (differences from B)
- **Flow 2:** the same `/pay` service as B. It calls the engine library directly, not via MCP or an LLM. MCP's JSON-RPC hop is fine for chat but adds overhead you don't need on the hot path.
- **Scheduled flows:** independent workers subscribed to the bus and cron, each deployable and scalable separately. You get less end-to-end graph visibility than with B unless you add tracing correlation IDs.
- **State and memory:** the agent is stateless apart from the chat thread. All durable state sits behind the data service. Pipelines checkpoint per item (per card, per user) rather than per graph.
- **Failure:** service isolation, so a failing launch pipeline doesn't affect payments. Per-consumer retries and DLQ. Tool errors reach the agent as actionable messages (Anthropic tool-writing guidance).
- **Evals:** tool-level contract tests (MCP tool schemas and golden outputs), agent tool-selection evals (about 50 prompts → expected tool sequence), and pipeline evals the same as B's node evals.
- **Observability:** distributed tracing across services (OTel), plus MCP server request logs per tool, recording latency, error and caller.
- **Cost drivers:** like B for pipelines. Conversation cost depends on how many tools are loaded per turn: prompt caching of the tool definitions matters, and tool search / deferred loading helps once the tool count grows.
- **Build effort:** hackathon, about 3.5 days. The MCP server adds about half a day, the separate services add plumbing, and it is doable if kept in one repo and one process with logical separation. Product, about 3 months and comparable to B. It scales better for teams, because services own their boundaries.
- **Key risks:** distributed-system overhead too early (an event bus and several services for one developer); the agent may chain tools in the wrong order on complex enquiries (mitigation: expose consolidated tools such as `recommend_new_card` that run the G1 workflow internally); MCP security (auth on the HTTP transport, no profile-write tools, per-user scoping of `user://` resources).

---

## 6. Comparison and recommendation

| Criterion | A: Supervisor + specialists | B: Workflow graphs + LLM nodes | C: Services + MCP + 1 agent |
|---|---|---|---|
| Fit to source guidance | Weak (shared context, dependent steps, 15× tokens) | Strong ("predefined code paths"; deterministic first) | Strong (single agent with tools; workflows for batch) |
| Flow 2 1 s | Needs a bypass anyway | Native fast path | Native fast path |
| Determinism of money maths | Risky step order | Guaranteed | Guaranteed in tools |
| Handling open-ended chat | Good | Weaker (intent router) | Good |
| Credit control | Hard (agents choose to search) | Easy (only specific nodes search) | Easy (pipelines own search) |
| HRQ integration | Ad hoc | Native (interrupt/pending state) | Native (pipelines → queue) |
| Eval surface | Largest | Smallest (per node) | Medium |
| Hackathon effort (4 days) | ~2.5 d wiring, fragile | ~3 d, robust | ~3.5 d |
| Product (3 mo) | Router/context debugging | Smooth, monolith-friendly | Best for multi-team scale |
| Demo "wow" | High | Medium | High (MCP in Claude Desktop) |

**Recommended path (Inference):** build **B's graphs as the core** (G1–G4 plus the `/pay` fast path), and put **C's single conversational agent** in front, calling consolidated tools: `recommend_new_card` runs G1, `explain_payment_choice` reads the stored G2 result, and so on. Expose those tools through an MCP server in the last hackathon day if time allows. Use Option A's idea in one place only: the weekly launch scout may use a lead/worker research loop (Sonnet lead, Haiku readers) if credits allow. Move to more agents only when the evals show tool confusion (more than about 15 overlapping tools) or prompts full of if/else branches (the OpenAI guide's split criteria).

---

## 7. cc-smith internal tool catalogue

Conventions (from Anthropic's "Writing effective tools for agents"): verb_noun names in a `cc_` namespace when exposed over MCP (e.g. `cc_get_card_profile`); IDs are human-readable slugs (`hdfc-millennia`), not UUIDs; money is in INR with `amount_inr: number`; dates are ISO (IST). Every tool returns `{ok, data, warnings[], as_of}` or `{ok:false, error:{code, message, fix_hint}}`. Read tools accept `response_format: "concise"|"detailed"`. Agent-visible tools are marked [A]. Pipeline or internal-only tools are marked [P].

### 7.1 Card knowledge
| Tool | Inputs | Outputs | Notes |
|---|---|---|---|
| `get_card_profile` [A] | `card_id`, `fields?[]`, `response_format?` | `{card_id, bank, network, variant, fees:{joining,annual,waiver_rule}, reward_rules[{category, rate, unit, cap:{amount,period}, exclusions[]}], milestones[], lounge, forex_markup, upi_eligible, eligibility:{min_income, min_age, score_band, cities?}, field_meta:{field:{source_url, checked_at, expires_at, pending_change}}}` | Never calls SerpApi; flags stale fields |
| `list_candidate_cards` [A] | `user_id` or `{income, city, spend_profile, goals[], network_pref?}`, `limit` | `[{card_id, why_candidate}]` | Code filter over the store, before simulation |
| `refresh_card_profile` [P] | `card_id`, `fields?[]`, `force?=false`, `reason` | `{refreshed_fields[], unchanged_fields[], queued_review_ids[], credits_spent, cache_hits}` | Uses serp_gateway; writes changes only to the HRQ |
| `search_card_changes` [P] | `card_id` or `bank`, `since` | `[{headline, url, date, change_type (devaluation/fee/benefit/none), affected_fields[], confidence}]` | News engine + Haiku triage |
| `queue_review` [P] | `card_id`, `field`, `old`, `new`, `evidence[{url, quote}]`, `severity`, `origin` | `{review_id, status:"pending"}` | Idempotent on (card, field, new) |
| `resolve_review` [P, admin] | `review_id`, `decision (approve/reject/edit)`, `edited_value?`, `reviewer` | `{status, emitted_event?}` | Emits `profile.changed` |

### 7.2 Reward engine (deterministic, pure code)
| Tool | Inputs | Outputs | Notes |
|---|---|---|---|
| `simulate_rewards` [A] | `card_id`, `spend_profile {category: monthly_inr}`, `months=12`, `channel_mix?`, `assumptions?` | `{gross_rewards_inr, by_category[{category, spend, rate, capped_at?, value}], milestones_hit[], fees_inr, fee_waived:bool, net_value_inr, caveats[]}` | Point-to-INR valuation from a profile-defined redemption value |
| `optimize_portfolio` [A] | `user_id`, `candidate_ids[]`, `max_new_cards=1` | `[{card_id, marginal_gain_inr, new_routing {category: card_id}, net_value_after_fees}]` sorted | Computes the marginal gain vs the existing holdings with optimal routing |
| `score_held_cards` [A, fast-path] | `user_id`, `merchant_id?`, `category`, `amount_inr`, `channel (card/upi/online/wallet)`, `ts?` | `[{card_id, effective_value_inr, rate, cap_left_inr, offer_applied?, milestone_progress, reason_codes[]}]` | Reads `user_score_table` + `offers_index` |
| `cap_status` [A] | `user_id`, `card_id?` | `[{card_id, bucket, spent_inr, cap_inr, pct, resets_on, suggested_alt_card?}]` | |
| `renewal_review` [A/P] | `user_id`, `card_id` | `{renewal_date, fee_inr, waiver_progress, value_last_12m_inr, options[{action: keep/convert/close, target_card?, net_delta_inr, steps[]}], recommendation}` | Uses `simulate_rewards` internally |

### 7.3 Eligibility and prerequisites
| Tool | Inputs | Outputs |
|---|---|---|
| `check_eligibility` [A] | `user_id` or `{age, income, employment, city, credit_score?, existing_cards[]}`, `card_id` | `{status: eligible/likely/ineligible/unknown, failed_criteria[{criterion, required, actual}], confidence}` |
| `plan_prerequisites` [A] | `user_id`, `target_card_id`, `failed_criteria[]` | `{routes[{type: fd_backed/card_to_card/savings_account/score_building, steps[{action, due_date, detail}], est_time_to_eligible_days}], recommended_route}` |

### 7.4 Payments
| Tool | Inputs | Outputs |
|---|---|---|
| `classify_merchant` [P, async] | `merchant_name`, `vpa?`, `city?`, `allow_search=true` | `{merchant_id, category, mcc_guess?, source (cache/rules/llm/maps), confidence, credits_spent}` |
| `get_offers` [A] | `merchant_id?` or `category`, `card_ids[]`, `date` | `[{offer_id, card_id/bank/network, value_type, value, min_txn_inr, max_benefit_inr, valid_to, source_url}]` |
| `recommend_payment` [fast-path] | `user_id`, `merchant`, `amount_inr`, `channel` | `{best:{card_id, value_inr, why}, alternatives[], confidence, latency_ms}` (composite: cache → rules → offers → score) |
| `record_payment` [A] | `user_id`, `card_id`, `merchant_id`, `amount_inr`, `channel`, `ts`, `idempotency_key` | `{payment_id, cap_updates[], nudges_triggered[]}` |

### 7.5 Discovery and engagement
| Tool | Inputs | Outputs |
|---|---|---|
| `find_launches` [P] | `since`, `max_searches=8` | `[{name, bank, launch_date, source_urls[], raw_snippet}]` |
| `dedupe_launch` [P] | `candidate` | `{is_new:bool, matched_card_id?, similarity}` |
| `score_all_users` [P] | `card_id`, `min_gain_inr`, `min_gain_pct` | `[{user_id, marginal_gain_inr}]` |
| `notify_user` [A/P] | `user_id`, `type (nudge/launch/renewal/prereq/routing_change)`, `payload`, `channel`, `dedupe_key` | `{sent:bool, suppressed_reason?}` (quiet hours, frequency caps, opt-outs) |
| `get_user_context` [A] | `user_id` | `{profile, holdings[], spend_profile, goals, missing_fields[]}` |
| `update_user_context` [A] | `user_id`, `patch`, `confirmed_by_user:bool` | `{updated_fields[]}` |

### 7.6 Infrastructure (internal, never agent-visible)
| Tool | Inputs | Outputs |
|---|---|---|
| `serp_search` (gateway) | `engine (google_ai_mode/google_news/google_maps/google_shopping)`, `params`, `flow`, `ttl_override?`, `force?` | `{data, cache_hit, credits_spent, remaining_month, remaining_hour}` |
| `credit_budget` | `flow?` | `{month_used, month_limit, hour_used, per_flow{}}` |
| `schedule_job` | `job`, `run_at`/`cron`, `payload` | `{job_id}` |

**Consolidated agent-facing tools** (for Option C's agent): `recommend_new_card(user_id, constraints?)` runs G1 and returns the ranked shortlist with marginal gains and eligibility, plus prerequisites for ineligible cards. `explain_payment_choice(payment_id)`, `review_my_cards(user_id)` (runs 3c for all holdings), and `my_caps(user_id)`. This keeps the agent's tool list at about 10 distinct tools. That is safely under the "<10 overlapping tools" failure zone described in the OpenAI guide.

---

## 8. Model-tier summary

| Work | Tier | Why |
|---|---|---|
| Conversation / user-context gathering / explanations | Sonnet 5.5 (low–medium effort) | Quality UX at $2/$10; prompt-cache system and tools |
| Profile extraction from AI Mode/issuer pages | Sonnet 5.5 → test Haiku 4.5 | Accuracy matters; batch, so use the Batch API (50% off) |
| Merchant classification, news triage, dedupe | Haiku 4.5 or local Ollama (e.g. a 7–8B instruct model) | Small, structured, high-volume; local works offline and costs nothing |
| Review assist, eval judge, gold-set creation | Opus 5.5 | Rare, offline; highest accuracy |
| Reward maths, caps, eligibility thresholds, scoring | No LLM | Deterministic, testable, under 1 ms |

**Local Ollama note (corporate proxy):** Ollama serves on `localhost:11434`. Set `NO_PROXY=localhost,127.0.0.1` so proxy env vars don't intercept local calls, while `HTTPS_PROXY` stays set for SerpApi and Claude. Local models are not on the 1 s path either, because laptop inference often takes over 1 s for a structured answer (Inference). Use them for async classification and dev or eval runs.

---

## 9. Open questions and gaps
- Measured latencies: the LLM round-trip numbers in this doc are estimates. Benchmark Sonnet 5.5 and Haiku 4.5 from your network (the corporate proxy adds overhead) before committing.
- Where offers data comes from: SerpApi Shopping and News give partial coverage. Bank offer pages may need direct scraping (check the terms) or manual curation.
- The UPI-on-RuPay-credit reward rules vary by card and change often. Treat them as profile fields under review, not constants.
- The OpenAI guide PDF was read via local text extraction. Quotes are verbatim from the extracted text, but the page layout was not checked.
