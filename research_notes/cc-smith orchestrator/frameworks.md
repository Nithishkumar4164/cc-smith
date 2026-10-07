# cc-smith: agent orchestration framework comparison (as of 2026-10-06)

Versions below were pulled live from PyPI / npm registries on 2026-10-06 (latest tag + upload date). Feature claims are from official docs/GitHub unless marked "(secondary)".

## 0. Latest versions (registry-verified 2026-10-06)

| Package | Latest | Released |
|---|---|---|
| langgraph (Py) | 1.2.14 | 2026-10-06 |
| @langchain/langgraph (JS) | 1.4.19 | 2026-10-03 |
| langgraph-supervisor (Py) | 0.0.31 | 2025-11-19 (effectively frozen) |
| langgraph-swarm (Py) | 0.1.0 | 2025-12-04 |
| openai-agents (Py) | 0.23.1 | 2026-10-02 (still 0.x) |
| @openai/agents (TS) | 0.19.0 | 2026-10-05 |
| claude-agent-sdk (Py) | 0.2.163 | 2026-09-30 (0.x) |
| @anthropic-ai/claude-agent-sdk (TS) | 0.3.291 | 2026-10-06 |
| anthropic (Py client SDK) | 1.11.0 | 2026-09-30 |
| google-adk (Py) | 2.11.0 | 2026-10-02 |
| @google/adk (TS) | 2.2.0 | 2026-09-30 |
| crewai | 1.15.23 | 2026-09-28 |
| pydantic-ai / pydantic-graph | 2.54.0 | 2026-10-03 |
| agent-framework (Microsoft, Py) | 1.20.0 | 2026-10-02 (GA 1.0 was 2026-04-03) |
| agno | 3.1.1 | 2026-10-02 |
| @mastra/core | 1.74.0 | 2026-10-01 (1.0 was Jan 2026) |
| ai (Vercel AI SDK) | 7.0.128 | 2026-10-05 |
| temporalio (Py) | 1.34.0 | 2026-09-30 |
| @temporalio/workflow | 1.24.0 | 2026-09-15 |
| inngest (TS) / inngest (Py) | 4.21.1 / 0.5.19 | 2026-10-01 / 2026-06-23 |
| litellm | 1.104.0 | 2026-10-03 |

Registry URLs: https://pypi.org/project/<name>/ , https://www.npmjs.com/package/<name>

## 1. Per-framework notes

### LangGraph (Python + JS) - LangChain Inc.
- Status: 1.0 GA Oct 2025; 1.1 (Mar 2026, typed streaming v2); 1.2 (2026-05-12, "fault-tolerance release") (secondary: https://releasebot.io/updates/langchain-ai/langgraph). Py 1.2.14 / JS 1.4.19 today.
- Multi-agent: LangChain docs now list 5 patterns: **Subagents** (supervisor calls agents as tools), **Handoffs**, **Skills**, **Router**, **Custom workflow** (raw LangGraph). https://docs.langchain.com/oss/python/langchain/multi-agent
- `langgraph-supervisor` README: "We now recommend using the supervisor pattern directly via tools rather than this library for most use cases." https://github.com/langchain-ai/langgraph-supervisor-py . `langgraph-swarm` still exists (0.1.0, Dec 2025) https://github.com/langchain-ai/langgraph-swarm-py -> treat both libs as legacy convenience; build supervisor-as-tools or explicit graphs.
- Persistence: checkpointers (InMemory, SQLite, Postgres, Redis...), thread_id, time-travel; long-term `Store`.
- HITL: `interrupt()` + `Command(resume=...)`; needs a checkpointer + thread_id; node restarts from the beginning on resume (keep pre-interrupt work idempotent). https://docs.langchain.com/oss/python/langgraph/interrupts  -> maps directly onto the card-profile human review queue.
- MCP client: `langchain-mcp-adapters` (MultiServerMCPClient) converts MCP tools to LangChain tools -> can mount mcp.serpapi.com.
- Models: any LangChain chat model incl. `langchain-ollama` (ChatOllama), Anthropic, OpenAI, Gemini.
- Scheduling: "LangGraph Platform" is now **LangSmith Deployment**; has cron API (`client.crons.create` / `create_for_thread`, UTC only, stateless runs delete thread by default). https://docs.langchain.com/langsmith/cron-jobs . Self-host alternative: own scheduler (APScheduler/Celery beat/Temporal).
- Durable: Temporal LangGraph plugin `temporalio[langgraph]` (Public Preview/experimental; runs StateGraph + Functional API nodes as activities, interrupts as durable signals). https://docs.temporal.io/develop/python/integrations/langgraph , https://temporal.io/blog/temporal-langgraph-plugin-durable-execution
- Observability: LangSmith (first-party), OTel, Langfuse callbacks. Studio for graph debugging.
- Learning curve: medium-high (state schemas, reducers, graph mental model). Maturity: highest adoption, 1.x stable API.

### OpenAI Agents SDK (Python + TS)
- 0.23.1 Py / 0.19.0 TS - still 0.x but very active.
- Primitives: Agents, **handoffs**, **agents-as-tools** (`Agent.as_tool()`), **guardrails** (input/output, tripwires), sessions (SQLite, SQLAlchemy, Redis, MongoDB, Dapr, encrypted), built-in **tracing**, MCP servers (hosted + local), sandbox agents, realtime/voice. https://openai.github.io/openai-agents-python/
- HITL: `needs_approval=True` (or async predicate) on tools -> `result.interruptions` -> `state.approve()/reject()`; `RunState.to_json()` to persist and resume later; works through handoffs and nested as_tool. https://openai.github.io/openai-agents-python/human_in_the_loop/
- Non-OpenAI models: `OpenAIChatCompletionsModel` with `AsyncOpenAI(base_url="http://localhost:11434/v1")` for Ollama; LiteLLM and Any-LLM adapters are **beta** (`openai-agents[litellm]`). Caveats: tracing uploads to OpenAI (disable with `set_tracing_disabled(True)` or set export key); many providers lack Responses API -> use chat_completions; structured-output support varies; unsupported fields silently dropped unless `strict_feature_validation=True`. https://openai.github.io/openai-agents-python/models/
- Durable/scheduling: no built-in scheduler; official Temporal integration `temporalio.contrib.openai_agents` https://docs.temporal.io/ai/cookbook/openai-agents-sdk-python
- Observability: built-in trace UI on OpenAI platform; processors for Langfuse/Logfire/etc.
- Learning curve: low. Maturity: high adoption, 0.x API churn.

### Claude Agent SDK (Py + TS) and Claude API tool use
- Agent SDK = Claude Code's harness as a library (runs the Claude Code binary): built-in tools (files, bash, web search), **subagents**, **MCP**, **hooks** (PreToolUse/PostToolUse/Stop/SessionStart...), **permissions** (approval gates), **sessions** (resume/fork), skills, plugins. https://code.claude.com/docs/en/agent-sdk/overview
- Versions 0.2.163 Py / 0.3.291 TS (0.x, frequent releases). Licensed under Anthropic Commercial ToS; must use API-key auth (no claude.ai login in third-party products).
- Models: Claude (Anthropic API, Bedrock, Vertex, Foundry). Ollama exposes an Anthropic-compatible API (`ANTHROPIC_BASE_URL=http://localhost:11434`, `ANTHROPIC_AUTH_TOKEN=ollama`) usable by Claude Code; quality depends on local model's tool-calling, hosted web search not supported. https://docs.ollama.com/integrations/claude-code
- Best fit: agentic research/extraction tasks (e.g. Flow 4 "profile a new card launch" reading pages, SerpApi MCP). Heavier per-run (spawns a CLI process) - not for the 1 s Flow 2 path.
- **Plain Claude API**: Messages API tool use + **Tool Runner** (beta, in Py/TS client SDKs) that drives the loop over your decorated functions https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-runner ; strict tool use / structured outputs for schema-valid inputs; MCP connector (remote MCP servers directly from Messages API). Also **Managed Agents** (Anthropic-hosted harness) https://platform.claude.com/docs/en/managed-agents/overview . Note: newest models (Opus 5.5 / Sonnet 5.5) reject forced `tool_choice` any/tool - use `auto` + strict tools. https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools
- Orchestration of multiple flows/schedules is DIY with these; pair with Temporal/Inngest/LangGraph.

### Google ADK (Py, TS, Go, Java, Kotlin)
- google-adk 2.11.0 (Py), @google/adk 2.2.0. ADK 2.0 (~May 2026) rewrote the engine to **graph-based workflows** (routing, fan-out/fan-in, loops, retries, nested) alongside classic workflow agents **SequentialAgent / ParallelAgent / LoopAgent**, LLM `sub_agents` transfer and `AgentTool`. Docs moved to https://adk.dev/ (graphs: https://adk.dev/graphs/ , multi-agent: https://adk.dev/workflows/ )
- Models: Gemini native; Claude, OpenAI, Ollama, vLLM via LiteLLM/connectors (https://adk.dev/agents/models/).
- MCP tools (client), OpenAPI tools, A2A; tool **action confirmation** for HITL; sessions/state/memory, context compaction; built-in eval + dev web UI (`adk web`).
- Deploy: Vertex AI Agent Engine/Agent Runtime, Cloud Run, GKE. Temporal plugin `temporalio.contrib.google_adk_agents` + cookbook https://docs.temporal.io/ai/cookbook/multi-agent-adk-python
- Scheduling: none built in (Cloud Scheduler / Temporal). Learning curve: medium. Maturity: good, fast-moving (1.x -> 2.x in 2026).

### CrewAI (Py) 1.15.x
- **Crews** = role-based autonomous agent teams (sequential/hierarchical process). **Flows** = event-driven, deterministic orchestration (`@start`, `@listen`, `@router`), typed Pydantic state, `@persist` (SQLite default; resume/fork), `@human_feedback` approval gates. Flows coordinate Crews. https://docs.crewai.com/en/concepts/flows
- Models via LiteLLM (Ollama OK); MCP via `crewai-tools` MCP adapter. Scheduling/observability via CrewAI AMP (enterprise) or own cron; OTel/Langfuse integrations.
- Learning curve: low for crews; production control requires Flows. Good hackathon velocity, less fine-grained than LangGraph.

### Pydantic AI + pydantic-graph (Py) 2.54
- Type-safe agents, structured outputs, dependency injection, multi-agent via agent delegation (agent called inside a tool), programmatic hand-off, and pydantic-graph (typed state machine, persistence of graph state) for explicit workflows.
- MCP client (stdio/HTTP) and MCP server; model-agnostic incl. Ollama (OpenAI-compatible provider).
- **Durable execution**: Temporal, DBOS, Prefect, Restate, AWS Lambda co-maintained (+ Airflow, Kitaru, Absurd via external SDKs); "each engine wraps every model request and tool call as its own durable unit". https://pydantic.dev/docs/ai/integrations/durable_execution/overview/
- HITL: deferred tools / tool approval. Observability: Pydantic Logfire (OTel), works with any OTel backend.
- Learning curve: low-medium for Python devs; strong fit for "deterministic maths as typed tools". Maturity: v2 line, rapid releases.

### Microsoft Agent Framework (.NET, Py, Go preview)
- 1.0 GA 2026-04-03 (https://devblogs.microsoft.com/agent-framework/microsoft-agent-framework-version-1-0/); Py now 1.20.0. Successor to Semantic Kernel + AutoGen.
- Agents, Harness Agent, **Workflows** (functional + graph, checkpointing, HITL request/response), orchestrations: sequential, concurrent, handoff, group chat, Magentic-One. MCP client + A2A. Providers: Foundry, Azure OpenAI, OpenAI, Anthropic, Bedrock, **Ollama**. OTel telemetry, DevUI; durable hosting via Azure Durable Task/Functions. https://learn.microsoft.com/en-us/agent-framework/overview/
- Best if the GCC is Azure-centric; otherwise more ceremony than needed.

### Agno (Py) 3.1
- Agents, **Teams** (modes: coordinate (default), route, broadcast, tasks) https://docs.agno.com/teams/overview , Workflows, **AgentOS** runtime (FastAPI + MCP server, control-plane UI, scheduling, storage, evals). https://docs.agno.com/introduction
- Model-agnostic incl. Ollama; MCPTools client; HITL via user-confirmation/user-input on tools. Very fast to stand up; smaller ecosystem than LangGraph.

### Mastra (TypeScript) 1.74
- 1.0 Jan 2026. Agents, model router (`provider/model` strings, 40+ providers, Ollama via ai-sdk provider), **workflows** (`createStep/createWorkflow`, `.then/.branch/.parallel`, suspend/resume for HITL, snapshots in storage, nested workflows, time-travel debugging in Studio), agent networks/supervisor agents, memory, MCP client + server, evals, OTel observability; Inngest runner for durable workflows. https://mastra.ai/docs/workflows/overview
- Best TS option for a full-stack dev who wants one Node service.

### Vercel AI SDK (TS) 7.x
- Low-level: `generateText/streamText`, `ToolLoopAgent` (loop control `stopWhen`, `prepareStep`), tool approval, structured output. https://ai-sdk.dev/docs/agents/overview
- MCP: stable `createMCPClient` from `@ai-sdk/mcp` (HTTP recommended, SSE, stdio; OAuth). https://ai-sdk.dev/docs/ai-sdk-core/mcp-tools
- Providers: all majors; Ollama via community provider / OpenAI-compatible. Multi-agent = DIY (agents as tools). Durability via Vercel Workflow DevKit or Temporal cookbook https://docs.temporal.io/ai/cookbook/ai-sdk-by-vercel-typescript
- Great UI streaming (Next.js); not an orchestrator by itself.

### Durable execution / scheduling layer
- **Temporal** (temporalio 1.34): Schedules (cron-like, with overlap policies, backfill, pause), workflows survive crashes, signals for human approval that can wait days, activity retries. Official contrib plugins: `openai_agents`, `langgraph` (preview), `google_adk_agents`, `strands`, `deepagents`, `langsmith`, `opentelemetry`; Pydantic AI ships its own Temporal integration. https://github.com/temporalio/sdk-python/tree/main/temporalio/contrib , https://docs.temporal.io/ai-cookbook . Cost: run a Temporal server (dev server single binary; Temporal Cloud paid).
- **Inngest**: event-driven functions with `step.run`, cron triggers, `step.waitForEvent` (HITL), concurrency/throttling, `step.ai`; TS SDK 4.x mature, Python SDK 0.5.x. **AgentKit** (TS): networks + code/LLM routers, shared state, MCP-as-tools. https://agentkit.inngest.com/ . Great for "event-driven + scheduled" (Flow 3b) with almost no infra (dev server locally).
- Others: DBOS (Postgres-backed durable Python/TS, lightweight), Restate, Prefect (cron deployments) - all supported by Pydantic AI durable execution.
- Pairing rule: framework handles the LLM loop; durable engine owns schedules, retries, fan-out over users, waits for human review. Keep agent runs idempotent and reward maths in pure functions/activities.

### SerpApi MCP
- Hosted at mcp.serpapi.com, streamable HTTP, key via `Authorization: Bearer` (preferred) or `/{KEY}/mcp`; one unified search tool covering all engines (Google AI Mode, News, Maps, Shopping...); self-host via uv/Docker. https://github.com/serpapi/serpapi-mcp
- Corporate proxy: hosted MCP over HTTPS likely OK; for Flow 2/4 batch use direct REST (custom tools) to control cost/caching.

## 2. Comparison matrix

| | Multi-agent patterns | MCP client | Ollama / model-agnostic | State / persistence | Scheduling | HITL | Observability | Curve | Maturity |
|---|---|---|---|---|---|---|---|---|---|
| LangGraph | supervisor-as-tools, handoffs/swarm, router, custom graphs, subgraphs | yes (mcp-adapters) | yes (ChatOllama) | checkpointers (PG/SQLite/Redis), Store | LangSmith Deployment cron; or Temporal plugin | interrupt()/Command | LangSmith, OTel | M-H | 1.x, highest |
| OpenAI Agents SDK | handoffs, agents-as-tools | yes | via chat-completions/LiteLLM (beta), caveats | Sessions, RunState | none (Temporal plugin) | needs_approval + RunState | built-in tracing (OpenAI) | L | 0.x, high |
| Claude Agent SDK | subagents | yes, native | Claude only (Ollama Anthropic-compat hack) | sessions resume/fork | none | permissions, hooks | hooks/OTel | L-M | 0.x |
| Claude API + Tool Runner | DIY | MCP connector | Claude only | DIY | none | DIY | DIY | L | stable API |
| Google ADK 2.x | LLM transfer, AgentTool, Sequential/Parallel/Loop, graph workflows, A2A | yes | via LiteLLM | sessions, state, memory | none (Temporal plugin) | tool confirmation | built-in UI, Cloud Trace, OTel | M | 2.x, fast churn |
| CrewAI | crews (seq/hierarchical), flows (router) | yes | LiteLLM | @persist | AMP/own | @human_feedback | OTel/AMP | L | 1.x |
| Pydantic AI | delegation, hand-off, pydantic-graph | yes | yes | graph persistence | via Temporal/DBOS/Prefect | deferred tools | Logfire/OTel | L-M | 2.x |
| MS Agent Framework | seq, concurrent, handoff, group chat, Magentic | yes + A2A | yes | checkpointed workflows | Azure Durable | workflow req/resp | OTel, DevUI | M | 1.x GA |
| Agno | teams (route/coordinate/broadcast/tasks), workflows | yes | yes | DB storage | AgentOS scheduling | confirmations | AgentOS | L | 3.x |
| Mastra (TS) | supervisor/networks, workflows | yes | yes | storage snapshots | Inngest runner/own cron | suspend/resume | OTel, Studio | L-M | 1.x |
| Vercel AI SDK (TS) | DIY agents-as-tools | yes | yes | DIY | Workflow DevKit | tool approval | OTel | L | 7.x |

## 3. Topology per cc-smith flow

- **Flow 1 (new-card shortlist, on demand)**: supervisor + specialists. Supervisor gathers profile (spend split, income, city) -> parallel specialists: eligibility checker, offer/devaluation researcher (SerpApi AI Mode/News), then deterministic `score_cards(profile, spends)` tool -> explainer writes ranked list. Fan-out is a natural `Send`/ParallelAgent step.
- **Flow 2 (which card at checkout, ~1 s)**: NOT multi-agent. Deterministic router: merchant -> MCC/category lookup (cache, Maps only on miss) -> `best_card()` pure function over cached card profiles + cap state. Optional tiny LLM (or none) to phrase the answer, streamed after the number is shown. Keep outside the agent framework or as a single-node graph.
- **Flow 3a (prerequisites to qualify)**: single agent with tools (profile store + eligibility rules) or a "skills" pattern; LLM explains gaps.
- **Flow 3b (cap tracking/nudges)**: event-driven pipeline: transaction event -> update cap ledger (code) -> threshold rule -> LLM only to word the nudge. Monthly re-check = scheduled fan-out over users. Durable engine (Inngest/Temporal) owns triggers.
- **Flow 3c (keep/convert/close, T-45 days)**: scheduled pipeline per card (Temporal Schedule or cron) -> compute 12-month realised value vs fee (code) -> research retention/downgrade options (agent) -> recommendation -> notify. Human-review interrupt if data stale.
- **Flow 4 (weekly new-launch detection)**: batch pipeline: News/AI Mode search -> dedupe vs store -> extraction agent builds card profile (source+date per field) -> **interrupt for human review** of new/changed fields -> on approval, fan-out score_all_users -> notify top matches. Long-running, needs durability + HITL that can wait days.
- **Shared**: card-profile store (Postgres, field-level provenance), review queue = interrupt/signal, reward engine = pure Python package exposed as tools (and maybe as own MCP server so every framework/agent reuses it).

## 4. Three recommended stacks

### A. Fastest hackathon build (by Oct 10)
- Python FastAPI + **OpenAI Agents SDK** or **Pydantic AI**, model = Claude (Anthropic) or OpenAI via API; SerpApi via hosted MCP; Postgres/SQLite; APScheduler for cron flows; review queue = a DB table + simple admin page.
- Alternative "Claude-native": Claude API + Tool Runner for chat flows, Claude Agent SDK for Flow 4 research agent.
- Topology: one triage/router agent with handoffs to Flow1/3a specialists; Flow 2 as plain endpoint; scheduled flows as Python functions calling agents.
- Benefits: smallest concept count, working demo in 2-3 days. Tradeoffs: no durable retries, HITL is hand-rolled, rewrite likely for scale.

### B. Production-grade
- **LangGraph 1.x** (Py) for agent graphs (supervisor-as-tools for Flow 1, explicit StateGraphs for 3b/3c/4) + **Postgres checkpointer** + `interrupt()` for review queue + **Temporal** (Schedules, fan-out over users, signals) via `temporalio[langgraph]` plugin or by calling graphs inside activities; LangSmith or Langfuse/OTel; reward engine as pure package + MCP server.
- Alternative: Pydantic AI + pydantic-graph + Temporal/DBOS (typed, less magic, Logfire).
- Benefits: durable, auditable, HITL that waits days, replay/time-travel, model-agnostic. Tradeoffs: steeper curve, Temporal infra (or Cloud cost), LangGraph-Temporal plugin is preview.

### C. Local-first / Ollama
- **Pydantic AI** (or LangGraph) with Ollama via OpenAI-compatible endpoint (set proxy NO_PROXY=localhost), Qwen3/Llama-class tool-capable model; **DBOS** or Inngest dev server for schedules; Langfuse self-hosted / Phoenix for traces; SQLite/Postgres.
- Design for weak models: deterministic code does all maths and routing; LLM only extracts and explains with strict schemas; fall back to Claude for Flow 4 extraction where accuracy matters (model-agnostic framework makes this a config switch).
- Benefits: no data leaves the laptop, zero token cost, works behind proxy. Tradeoffs: lower tool-calling reliability, slower, OpenAI Agents SDK tracing/Responses API caveats, Claude Agent SDK only via Anthropic-compat shim.

### TypeScript variant
- Mastra (agents + workflows + MCP + Studio) with Inngest for cron/events, or Vercel AI SDK for the UI layer + Inngest AgentKit. Good if the front end is Next.js; Python ecosystem is richer for scraping/eval.
