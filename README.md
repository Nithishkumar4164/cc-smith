# cc-smith

AI agent that recommends credit cards from your category-wise spends, tells you which card to use for each purchase, how to acquire new cards, and delivers news that affects your stack.

- Market: India
- Audience: public product
- Surface: Flutter app (Android first) over a backend API
- Status: hackathon build (SerpApi India Hackathon 2026, Commerce & Market Intelligence track). Plan: [docs/architecture-plan.md](docs/architecture-plan.md). Also [docs/prd.md](docs/prd.md), [docs/user-stories.md](docs/user-stories.md), [docs/decisions.md](docs/decisions.md), [docs/features.md](docs/features.md), [docs/research/](docs/research/).

## What works

- **Checkout Advisor** (`POST /pay`): type a merchant or scan a UPI QR; the best card you hold for this payment in rupees, after caps used this month, exclusions, minimums and UPI rules, plus live bank offers from the banks' own offer pages. No LLM on this path.
- **Card Finder** (`POST /finder`): the best 1–3 new cards for your monthly spends, net of fees (with GST), fee waivers and milestones, with per-category rupee lines; keep-or-close values for cards you hold.
- **Card knowledge with provenance**: every fact is a verbatim quote from an allow-listed official page, checked in code (quote present, numbers stated in the quote, range checks). Anything else is "reported, not confirmed by the bank" and never used in the maths. No human review step; every change raises an owner alert.
- **Launch Radar** (`uv run cc-smith radar`): Google News and Google Ads Transparency (India) through one SerpApi gateway with cache, budget guard and credit ledger. New cards are profiled from the bank's own pages when found, otherwise listed as reported.

## Run

```
cd backend
uv sync
uv run cc-smith seed
uv run cc-smith radar --as-of 2026-10-07
uv run cc-smith serve --host 0.0.0.0 --port 8000      # docs at /docs
uv run pytest -q

cd ../app
flutter run --dart-define=CC_SMITH_API=http://10.0.2.2:8000   # Android emulator
```

With no keys, everything replays recorded fixtures (official page text under `backend/fixtures/evidence`, SerpApi responses under `backend/fixtures/serp`). Put `SERPAPI_API_KEY` / `ANTHROPIC_API_KEY` in `backend/.env` and `MODE=live` to fetch and record new ones. See [backend/README.md](backend/README.md).
