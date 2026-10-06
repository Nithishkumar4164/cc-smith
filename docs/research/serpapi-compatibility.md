# SerpApi compatibility with the feature list (Oct 2026)

Source: https://serpapi.com/ and its Google News / Google Maps API docs, read 2026-10-06. Feature IDs refer to `docs/features.md`.

## What SerpApi is

A hosted scraper for search engines. One call = one search; the response is the structured SERP (organic results, news cards, shopping offers, local places, knowledge panels) as JSON. It does **not** fetch or parse arbitrary web pages — it tells us *where* something is, not *what it says*. Any content extraction (issuer T&C pages, MITC PDFs, forum threads) needs our own fetcher.

Engines relevant to us: Google Search, Google News, Google Forums, Google Shopping / Google Product, Google Maps / Google Local, Google Flights / Google Hotels, Google Autocomplete / Related Questions, Google Trends, YouTube Search / Video Transcript, Google Play Store / Apple App Store, Google Lens.

Parameters that matter: `gl=in`, `hl=en`, `location` (Indian cities) — SerpApi localises Google results per country/city. Google News supports `so=1` (sort by date) and `when:` operators. Google Maps returns `type` / `types` per place.

Pricing (per month): Free 250 searches · Starter $25 / 1,000 · Developer $75 / 5,000 · Production $150 / 15,000 · Big Data $275 / 30,000. Hourly throughput = 20% of plan volume. Responses cached one hour; `no_cache` forces fresh. SOC 2 Type II, ISO 27001, 99.95% SLA. "U.S. Legal Shield" on Production and above covers scraping/parsing liability under US law only.

## Feature-by-feature fit

| Feature | Engine | Fit | How it would be used — and the limit |
|---|---|---|---|
| A1 Card profiles (sourcing) | Google Search | **Partial** | Discover the canonical T&C / MITC / fees page URL per card (`"Axis Atlas" MITC site:axisbank.com`). Extraction is ours. One-off per card, plus re-discovery when a URL dies. |
| A6 Change pipeline | Google Search, Google Forums | **Partial** | Weekly query per card for new issuer pages and community "devaluation" threads to feed the reviewer queue. Snippets only; our fetcher reads the page. TechnoFino is behind Cloudflare and Reddit blocks fetches, so for those two sources the snippet may be all we get — the reviewer follows the link by hand, or we use Reddit's archive API as in the research sweep. |
| A7 News / devaluation ingestion | Google News (`gl=in`, `so=1`) | **Good** | Per-bank and generic queries ("HDFC credit card", "credit card devaluation") sorted by date, polled daily; returns title, source, link, `iso_date`. Tie items to card IDs ourselves. Best single fit in the catalogue. |
| A8 User corrections | — | None | Internal. |
| B1–B7 Recommend | — | None | Engine over our KB and user data. |
| C1–C2 Eligibility, enquiry hygiene | — | None | User data + KB. |
| C3 Rejection intelligence | Google Forums, Google Search | **Weak** | Discover threads about rejections per card; extraction is ours and sources are hard to fetch. |
| D1 Which card now (live offers input) | Google Search | **Weak** | Could discover bank offer pages ("HDFC Amazon offer October 2026"), but offer terms are on bank/merchant pages we must parse. Not in the hot path: D1 must answer in ~1 s; SerpApi calls take seconds and cost a search each. Batch overnight. |
| D2 Merchant → MCC map | Google Maps / Google Local | **Good (as a seed)** | Resolve a merchant name (+ city or GPS from the QR scan) to a Google place with `type`/`types` (restaurant, grocery store, fuel station…). Map Google category → *expected* MCC family. This is the "new merchant: classify it" step. It is not the acquirer's real MCC; real MCCs come from user statements and corrections. Cache by place ID forever. |
| D3 UPI logic | — | None | KB rules. |
| D4 Online checkout assist | Google Shopping | **Weak** | Not needed to recognise a domain; could show alternative sellers. |
| D5–D6 Forex, surcharges | — | None | KB rules. |
| D7 Effective price across stores | Google Shopping / Google Product (`gl=in`) | **Good** | Product → sellers and prices; subtract each card's reward per seller. Verify Indian merchant coverage with the free tier before committing. |
| E1–E7 Ledger, trackers, reconciliation | — | None | User data. |
| F1–F4, F7 Action centre, closure, replan | — | None | User data + KB. |
| F5 Escalation helper | Google Search | **Weak** | Discover current PNO / nodal officer contact pages per bank. One-off, refreshed quarterly. |
| F6 New-launch heads-up | Google News, Google Search | **Good** | "new credit card launch" queries; new card → profile once → score against users. |
| G1 Redemption optimiser (realised value) | Google Flights, Google Hotels | **Partial** | Cash price of a flight/hotel to compare against the points price → realised ₹/point for a specific redemption. Flights API supports Indian origins; call only when the user asks, not in bulk. |
| G2 Partner-programme tracking | Google News | **Good** | Same pipeline as A7 with partner names (Accor, Marriott, airline programmes). |
| H1 Provenance | — | None | Internal; SerpApi's result URL becomes the source link. |
| H2 Community signals | — | None | Our users' reports. |
| H3 Privacy | — | None | No user data ever goes to SerpApi — queries are about cards, banks, merchants and products, not people. Keep it that way. |
| Information-quality checks (pain point 16) | YouTube Search + Video Transcript, Google Autocomplete / Related Questions | **Useful side use** | Pull influencer-claimed reward rates from transcripts into the reviewer queue as *claims to verify*, never as facts. Autocomplete/Related Questions surface what people ask about a card — input for FAQ content and pain-point mining. |

Fit counts: Good 5 (A7, D2, D7, F6, G2) · Partial 3 (A1, A6, G1) · Weak 4 · None for everything built on user data (about 30 features).

## Cost model

| Workload | Searches / month | Plan |
|---|---|---|
| KB discovery, 300 cards one-off + 10% monthly churn | ~300 then ~30 | Free |
| News polling: 20 banks × 2 queries + 10 generic/partner queries, daily | ~1,500 | Developer ($75) if combined with below |
| Weekly per-card change check, 300 cards | ~1,300 | |
| Merchant classification, new merchants only (cached by place) | depends on user base; 10k users × 2 new merchants/month = 20k | Big Data ($275) or Enterprise — or cache aggressively and fall back to our own merchant list |
| Product price comparison, on demand | user-driven | |

Merchant classification is the only workload that scales with users. Mitigate: normalise merchant names so one lookup serves many users, and lookup only when our own merchant table has no match.

## Gaps SerpApi does not fill

- **Page content**: issuer T&C / MITC pages and PDFs → our own fetcher + LLM extraction (A1, A6).
- **Community content**: TechnoFino (Cloudflare) and Reddit (blocked) → Reddit archive API as used in the research sweep; TechnoFino via snippets or manual review.
- **Bank offer feeds**, **real MCCs**, **transactions**, **credit scores** — none of these are search data.
- **Latency**: never in the pay-time path; everything SerpApi provides is precomputed.
- **India coverage**: Google Search/News/Maps are solid in India; Google Shopping/Product coverage of Indian sellers and Google Flights for domestic routes should be tested on the free tier before D7/G1 depend on them.
- **Legal**: Legal Shield is US-law coverage. We send no personal data, so exposure is limited to search-engine ToS; acceptable, but not covered in India.

## Alternatives, briefly

- Google Programmable Search JSON API: official, 100 free/day then $5 per 1,000, 10k/day cap, no news/maps/shopping structure. Fine for A1 discovery alone.
- Brave Search API: cheaper web + news search, less structure, no maps/shopping.
- Google Places API (official): better for D2 than SerpApi's Maps engine if we only need place classification — official terms, generous free credit, place types directly.
- Our own fetcher is required regardless (e.g. Playwright-based, or a fetch-to-markdown service).

## Recommendation

Use SerpApi for A7/G2 (news), F6 (launch discovery), A1/A6 (URL discovery), and D7 (price comparison) on the Developer plan. For D2, prefer the official Google Places API for classification and keep SerpApi Maps as a fallback. Build the fetcher/extractor as our own component from the start — it is the actual hard part of the knowledge base, and no search API substitutes for it.

Verify on the free tier (250 searches) before buying: Google News with `gl=in` returns Indian banking press and community posts; Google Shopping `gl=in` returns Indian sellers for a phone model; Google Maps resolves a small Chennai/Bengaluru merchant name from a UPI QR to a typed place.
