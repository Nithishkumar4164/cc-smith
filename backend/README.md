# cc-smith backend

FastAPI BFF, deterministic rewards engine and the knowledge pipeline described in
`docs/architecture-plan.md`. Money is integer paise everywhere.

## Run

```
uv sync
uv run cc-smith seed                     # profile the seed cards from recorded official evidence
uv run cc-smith radar --as-of 2026-10-07 # one Launch Radar sweep (replay fixtures were recorded on 2026-10-07)
uv run cc-smith serve --host 0.0.0.0     # http://127.0.0.1:8000/docs
uv run pytest -q
```

`MODE=replay` (default) never calls SerpApi or Anthropic and never fetches pages: everything
comes from `fixtures/`. `MODE=live` with keys in `.env` fetches official pages, records new
evidence and SerpApi responses as fixtures, and calls the models.

## How a card fact gets in

1. `fixtures/extractions/<card>.json` (or `knowledge/extract.py` live) proposes a `CardProfile`
   where every element carries `{url, quote}`.
2. `knowledge/pipeline.py` checks, per field:
   - the URL is on the official allow-list for that field (`knowledge/allowlist.py`,
     `docs/research/official-domains.yaml`; partners only for the fields they own);
   - the quote appears in the fetched page or PDF (`knowledge/quotes.py`; exact, or a
     same-window word match for PDF table rows);
   - every rupee amount, cap and percentage published is written in its own quote;
   - range checks (earn rate ≤ 25%, fee ≤ ₹1 lakh).
3. Pass: published as a new version (old one kept for rollback). Fail: stored as speculation,
   shown as "reported, not confirmed by the bank", never used by the engine. No human step.
4. Every change raises an owner alert (`notify/alerts.py`, `var/owner-alerts.log`, `/ops/alerts`).

`scripts/import_research_facts.py` turns the hand-collected official quotes in
`docs/research/*card-facts*.json` into extraction fixtures.

## Layout

| Module | Owns |
|---|---|
| `knowledge` | schema, allow-list, fetcher, quote check, pipeline, store, extraction, discovery |
| `rewards` | engine (`reward()` per purchase), Card Finder simulation, pay text |
| `ledger` | confirmed checkout transactions, cap usage per period |
| `users` | anonymous users, profile, holdings, spends |
| `signals` | Launch Radar (news, Ads Transparency), triage, scheduler |
| `ops` | outbox, SerpApi gateway (cache, budget, credit ledger) |
| `notify` | owner change alerts |
| `api` | FastAPI routes |
