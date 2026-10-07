# Architecture debate — index

A structured debate on cc-smith's architecture. Four architects each argued one position in round 1, then rebutted the others in round 2. A neutral judge consolidated the result.

**Outcome:** [../architecture-plan.md](../architecture-plan.md). It contains the decision table, decision records, delivery plan, risks, open questions and a scorecard.

## Positions

| Position | Core claim | Round 1 | Round 2 |
|---|---|---|---|
| Workflow-first | Deterministic per-flow workflows, LLMs only in bounded steps, one chat agent | [round1/workflow-first.md](round1/workflow-first.md) | [round2/workflow-first.md](round2/workflow-first.md) |
| Multi-agent | Supervisor with specialist agents as tools; parallel research fan-out | [round1/multi-agent.md](round1/multi-agent.md) | [round2/multi-agent.md](round2/multi-agent.md) |
| Event-services | Modular services over a Postgres outbox; tools published once over MCP | [round1/event-services.md](round1/event-services.md) | [round2/event-services.md](round2/event-services.md) |
| On-device-first | Ledger and engine on the phone; the server is a user-agnostic card-intelligence service | [round1/on-device-first.md](round1/on-device-first.md) | [round2/on-device-first.md](round2/on-device-first.md) |

## Where it landed

**The backbone came from Workflow-first:**
- deterministic workflows, plus one chat agent
- issuer-first card facts with a quote check
- server `/pay` for the hackathon

**Adopted from the other positions:**
- Event-services: the outbox, DPDP erasure, and an ops MCP server
- On-device-first: parsing notifications on the phone, signed pay packs, and templated reasons
- Multi-agent: prompt-injection isolation, and batch fan-out for Launch Radar only

**Still open:** where the ledger lives. The vote was 2–2. A closed-beta consent test decides it in M2.

## Inputs the architects cited

- `README.md`, `docs/ideation.md`, `docs/features.md`, `docs/research/`
- `research_notes/cc-smith orchestrator/` (architecture, models, frameworks, SerpApi surface)
- `research_notes/SerpApi capabilities for hackathon/` and `reports/`
