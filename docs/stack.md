# Stack

The stack is decided in [architecture-plan.md](architecture-plan.md) (judge's ruling on the four-way debate in `arch-debate/`, with owner decisions dated 2026-10-06/07). This page is a one-screen summary plus the deltas from the earlier stack recommendation made in chat, so nobody has to reconcile two documents.

## Summary (from architecture-plan.md)

| Layer | Choice | Where decided |
|---|---|---|
| Backend language | Python; one repo, one Postgres, modules with import-linter contracts (`knowledge`, `rewards`, `ledger`, `signals`, `notify`, `users`, `ops`) | §2 |
| API | FastAPI BFF: `/pay` (code only, p95 < 300 ms), `/chat`, `/screens/*` | §2, DR-6 |
| Rewards engine | Pure Python, integer paise, property + golden tests; phone gets a signed lookup table from M2 | DR-3 |
| Durable execution | Hackathon: step functions + `run_state` + APScheduler. M1: DBOS on the same Postgres. Temporal only on a measured trigger | DR-7 |
| Events | 5-topic Postgres outbox (`FOR UPDATE SKIP LOCKED`, `LISTEN/NOTIFY`), idempotent consumers, DLQ after 5 attempts | DR-7 |
| Knowledge sourcing | Own fetcher (httpx + trafilatura + pdfplumber, Playwright fallback) → extract into strict schema with `{url, quote}` → code checks the quote → official-source facts auto-publish, everything else is speculation. No human review (DR-12). SerpApi only for discovery, behind one gateway | DR-4, DR-5, DR-10, DR-12 |
| Models | Sonnet 5.5 for chat and extraction (Batch); Opus 5.5 offline for gold set, disputed diffs and weekly re-check; Haiku 4.5 for triage/dedupe; self-hosted `qwen3:8b` in India for user-derived merchant text; templated reasons on `/pay` | DR-8 |
| Client | Flutter, Android builds first; iOS after M3. Drift/SQLCipher local queue; QR decode on the phone; NotificationListener with on-device parsing (M2); FCM data messages | §2, DR-6, DR-9 |
| Data residency and privacy | Postgres with RLS in India region; no PII to any LLM or to SerpApi; product + last4 only; purpose-tagged consent; `user.erased` with crypto-shredding | DR-2, DR-9 |
| Ops | Read-only admin (change feed, speculation list, rollback); FastMCP ops scope (read + `trigger_refetch`) in M1; OTel + self-hosted Langfuse | §2, DR-11, DR-12 |
| Hosting | Not fixed in the plan beyond "India region". Earlier recommendation: GCP asia-south1 (Cloud Run, Cloud SQL, Secret Manager, Cloud Storage for statements). Decide at M1 | — |

## Deltas from the chat recommendation (2026-10-06)

These were recommended in chat before the architecture plan was found in the repo. They are **not** decisions; listed so the reasoning is not lost.

| Topic | Chat recommendation | Plan | Note |
|---|---|---|---|
| Web framework | Django + django-ninja, Django admin for the review queue | FastAPI BFF, read-only admin, no review queue | With DR-12 (no human review) the main reason for Django admin disappears. Follow the plan. |
| Jobs | Procrastinate (Postgres-backed queue) | APScheduler → DBOS | DBOS gives checkpointed workflows, which Procrastinate does not. Follow the plan; keep the outbox as designed. |
| Extraction model | Opus 5.5 | Sonnet 5.5 via Batch, Opus for gold set and disputes | The 25-card gold set decides (DR-8). |
| Client state | Riverpod + generated OpenAPI client | Not specified | Still a reasonable choice inside the plan; generate the Dart client from the FastAPI OpenAPI spec. |
| Auth | Firebase Auth | "auth" in M1, provider not named | Open; Firebase Auth remains the default suggestion. |
| Hosting | GCP asia-south1 | "India region" | Open; see table above. |

## Not chosen

Node/TypeScript backend (weaker Decimal/PDF story; would split the engine language from the API), Redis/Celery (outbox + DBOS cover it), a separate admin SPA (nothing to approve), storing full card numbers anywhere.
