# SerpApi Platform Mechanics: Parameters, Pricing, Limits, Caching, Supporting APIs (as of Oct 2026)

Note: sources were fetched 2026-10-05 from serpapi.com. Account API example shows a renewal date of "2026-11-04", which suggests the doc page is current. Page summaries came through a fetch tool, so check exact wording on the live page before quoting it.

## Common request parameters and how `location` works

### Takeaway
Every call is a GET to `https://serpapi.com/search(.json)` with `engine`, `api_key` and engine-specific parameters (`q` for Google). Location targeting uses exactly one of `location` (a canonical name from the free Locations API), `uule`, or `lat`+`lon`, paired with matching `gl`/`hl`/`google_domain`. `num` no longer works on Google, so paginate with `start`.

### Cited Findings
- `q` (required): the query. Supports Google operators such as `site:`, `inurl:` and `intitle:`. "You can use anything that you would use in a regular Google search." — [SerpApi Google Search API](https://serpapi.com/search-api)
- `engine`: defaults to `google`. `api_key` is required. — [SerpApi Google Search API](https://serpapi.com/search-api)
- `location`: the place the search originates from. "If several locations match the location requested, we'll pick the most popular one." City-level is recommended. It can't be combined with `uule` or `lat`/`lon`. — [SerpApi Google Search API](https://serpapi.com/search-api)
- `uule`: Google-encoded location. It is mutually exclusive with `location`, a UULE Generator tool is provided, and a matching `gl` is advised. `lat`/`lon` (both required together) is a third, mutually exclusive option, and a matching `gl` is recommended there too. — [SerpApi Google Search API](https://serpapi.com/search-api)
- `google_domain`: defaults to `google.com` (use `google.co.in` for India). `gl` is a 2-letter country code. `hl` is a language code that can carry a region (for example `en-gb`). `cr` and `lr` restrict by country and language (`countryIN`, `lang_hi`). — [SerpApi Google Search API](https://serpapi.com/search-api)
- `tbs`: advanced filters such as date ranges and verticals. `safe` takes `active` or `off`. `nfpr=1` excludes auto-corrected results. `filter=0` disables the "similar/omitted results" filters. — [SerpApi Google Search API](https://serpapi.com/search-api)
- `start`: result offset (0, 10, 20 …). `device`: `desktop` (default), `tablet` or `mobile`. — [SerpApi Google Search API](https://serpapi.com/search-api)
- `no_cache`: `true` forces a fresh fetch. "Cache expires after 1h." Cached searches are free. It can't be combined with `async`. — [SerpApi Google Search API](https://serpapi.com/search-api)
- `async`: `true` submits the search and returns right away. Results are then fetched through the Searches Archive API. It is incompatible with `no_cache` and with Ludicrous Speed accounts. — [SerpApi Google Search API](https://serpapi.com/search-api)
- `zero_trace`: an enterprise privacy mode that stops SerpApi storing parameters and metadata. — [SerpApi Google Search API](https://serpapi.com/search-api). The pricing table marks ZeroTrace as "No" on the Free plan — [Pricing](https://serpapi.com/pricing.md)
- `output`: `json` (default), `html` (raw HTML), or `md` (Markdown for LLMs). `md` appears to be a recent addition. `json_restrictor` trims response fields to shrink the payload. — [SerpApi Google Search API](https://serpapi.com/search-api)
- Locations API: `GET https://serpapi.com/locations.json?q=<string>&limit=<n>` (max 10). Results are sorted by reach. Fields: `id`, `google_id`, `name`, `canonical_name` (pass this as `location`), `country_code`, `target_type`, `reach`, `gps`. "This API is free to use." The full dataset can be downloaded as JSON. — [Locations API](https://serpapi.com/locations-api)
- `num` on Google is effectively dead. On Sept 11, 2025 Google stopped honouring `&num=100` and now caps results at 10 per page — [apiserpent blog](https://apiserpent.com/blog/google-num-100-removed-rank-tracker-fix). SerpApi says "Google has discontinued support for the num parameter" (post updated Dec 9, 2025) — [SerpApi blog](https://serpapi.com/blog/minimum-amount-of-results-per-page-across-serpapis-supported-google-engines.md). `num` is no longer listed on the Search API docs page — [SerpApi Google Search API](https://serpapi.com/search-api)
- SerpApi released a workaround, `engine=google_light_fast` with `num=100` (Sept 24, 2025), and then discontinued it because "Google now limits the underlying endpoint to only 3 organic results". SerpApi recommends the Google Light API instead. — [SerpApi blog](https://serpapi.com/blog/solution-to-scrape-100-search-results-on-google-google-fast-light-api.md)

### Inferences
- For Indian searches, call `locations.json?q=Bengaluru` (free), take `canonical_name` (it will look something like "Bengaluru,Karnataka,India"), and send it with `gl=in`, `hl=en` and `google_domain=google.co.in`.
- Each page of 10 results costs 1 credit. Getting the top 30 takes 3 credits.

### Gaps
- I didn't confirm the exact canonical_name strings for Indian cities. Query the API to get them.
- Per-engine parameter differences (Google Flights, Hotels, Maps and so on) weren't covered here.

## Free plan, what counts as a search, paid tiers

### Takeaway
The Free plan gives 250 successful searches a month with a 50-searches-per-hour throughput cap. It has no Legal Shield, ZeroTrace or priority support. Only successful searches are counted. Cached, errored and failed searches are free.

### Cited Findings
- Free: 250 searches a month and 50 per hour. Legal Shield, ZeroTrace and Priority Support are all "No". — [Pricing](https://serpapi.com/pricing.md)
- "Only successful searches are counted toward your monthly searches. Cached, errored, and failed searches are not." — [Pricing](https://serpapi.com/pricing)
- Credit card: the official pricing page doesn't mention one. Third-party sources say no card is needed — [costbench / search summary](https://costbench.com/software/web-scraping/serpapi/free-plan/), [apiserpent](https://apiserpent.com/blog/serp-api-no-minimum-free-tier). User reviews say phone number verification is required for free accounts — [Trustpilot via search](https://uk.trustpilot.com/review/serpapi.com). Sign-up works through GitHub or Google OAuth — [Sign up page](https://serpapi.com/users/sign_up)
- Conflicts: one aggregator claims the Free plan includes Legal Shield, ZeroTrace and priority support, and another says "100 searches/month". Both contradict the official pricing page (250/mo, those features "No") and should be treated as wrong or outdated. — [Pricing](https://serpapi.com/pricing.md)
- Paid tiers (monthly searches / hourly throughput / price): Starter 1,000 / 200 / $25. Developer 5,000 / 1,000 / $75. Production 15,000 / 3,000 / $150. Big Data 30,000 / 6,000 / $275. Searcher 100,000 / 20,000 / $725. Volume 250,000 / 50,000 / $1,475. Infrastructure 500,000 / 100,000 / $2,750. Cloud plans run from Cloud 1M ($3,750) up to Cloud 52M ($102,175). — [Pricing](https://serpapi.com/pricing)
- Ludicrous Speed is available on any plan at 2x or 4x the base price. It is faster than the default "Best Effort". — [Pricing](https://serpapi.com/pricing.md)
- Plans can be upgraded, downgraded or cancelled at any time. Downgrading moves the remaining searches into "Extra Credits". Automatic Early Renewal can renew the plan when searches run out. — [Pricing](https://serpapi.com/pricing.md)
- Refunds: "full refund within 7 days of the day you subscribed to a plan unless you've used more than 20% of your searches." — [Legal](https://serpapi.com/legal)
- Pagination: each extra page costs 1 credit. UI-only actions such as "show more", which load nothing new from the server, are free. — [SerpApi blog: credit usage](https://serpapi.com/blog/calculating-search-credit-usage-with-serpapi/)

### Inferences
- 250 credits over 5 days is about 50 a day. The 50/hour cap matters only for bulk scripts. Seed data once, store it locally, and lean on the 1-hour cache during demos.
- The 2025 Google price-hike headlines don't change the Free plan, which is still 250.

### Gaps
- I found no official statement on whether the Free plan needs a credit card or a phone number. Third-party sources say no card. Phone verification is anecdotal.
- I couldn't confirm whether any engines cost more than 1 credit per request.
- I couldn't confirm the reset timing for free accounts, which is presumably monthly from sign-up.

## Caching, no_cache, Account API

### Takeaway
An identical request (every parameter the same) within 1 hour is served from cache for free and doesn't count against quota. `no_cache=true` bypasses the cache and is billed. The Account API is free and shows remaining credits and hourly usage.

### Cited Findings
- "Cache expires after 1h. Cached searches are free." — [SerpApi Google Search API](https://serpapi.com/search-api)
- "A cache is served only if the query and all parameters are exactly the same", and cached searches "are not counted towards your searches per month." — quoted in [LangChain SerpAPIParameters docs](https://reference.langchain.com/javascript/langchain-community/tools/serpapi/SerpAPIParameters), which mirror the SerpApi docs
- Account API: `GET https://serpapi.com/account.json?api_key=...`. "Account API is free of charge, and using it will not be counted toward your monthly quota." Fields: `account_id`, `api_key`, `account_email`, `account_status`, `plan_id`, `plan_name`, `plan_monthly_price`, `plan_renewal_date`, `searches_per_month`, `plan_searches_left`, `extra_credits`, `total_searches_left`, `this_month_usage`, `this_hour_searches`, `last_hour_searches`, `account_rate_limit_per_hour`. — [Account API](https://serpapi.com/account-api)

### Inferences
- Any parameter change breaks the cache match, including a different `location` string, a different `hl`, or parameter differences an SDK might add. Keep request construction deterministic.
- Leave `no_cache` off in development. Use it only when freshness matters, because each such call is billed.
- Poll `account.json` from a dashboard or a startup check to guard the budget.

### Gaps
- I didn't confirm whether the cache is per-account or global. Wording such as "exactly the same" suggests matching on parameters, and possibly across users.

## Search Archive API and async mode

### Takeaway
`async=true` returns a `search_id` immediately. You then poll `https://serpapi.com/searches/{id}.json` until the status is Success. Searches are retrievable for 31 days.

### Cited Findings
- Endpoint: `GET https://serpapi.com/searches/{search_id}(.json)` with `api_key`. Statuses are Queued, Processing, Success and Error. "Searches don't have to be completed to be retrieved." Results stay available "up to 31 days after the search has been completed." Output can be `json`, `html` or `json_with_pixel_position`. — [Search Archive API](https://serpapi.com/search-archive-api)
- Search data is deleted after 31 days. ZeroTrace stops storage entirely. — [Legal](https://serpapi.com/legal)
- HTTP 410 Gone means the search has expired and been deleted. — [Status and Error Codes](https://serpapi.com/api-status-and-error-codes)
- `async` is incompatible with `no_cache` and with Ludicrous Speed. — [SerpApi Google Search API](https://serpapi.com/search-api)

### Inferences
- Async mode is useful for firing many queries in parallel without holding connections open. The original search is billed once. Retrieving it from the archive most likely doesn't cost another credit, but that isn't officially stated (see Gaps).

### Gaps
- The Search Archive docs don't say whether archive retrieval is free. No official statement was found.

## Throughput, latency, error codes, running out of credits

### Takeaway
The hourly throughput cap is set by plan (Free is 50/hr). Typical latency is a few seconds. Errors come back as JSON `{"error": "..."}`. Running out of credits, or exceeding the hourly cap, returns HTTP 429 "Your account has run out of searches."

### Cited Findings
- Status codes: 200 OK, 400 missing params, 401 invalid key, 403 forbidden, 404, 410 expired search, 429 hourly limit exceeded or out of searches, 500/503 server error. The error body is `{"error": "..."}`. — [Status and Error Codes](https://serpapi.com/api-status-and-error-codes)
- Out of credits: HTTP 429 with "Your account has run out of searches." — [Fix SerpApi errors guide](https://serpapi.com/blog/fix-serpapi-errors-guide.md)
- An invalid key returns 401 "Invalid API key. Your API key should be here: …". A missing `q` returns "Missing query `q` parameter." Calling the API from the browser can be blocked by CORS/CSP and exposes the key, so route calls through a backend. The JS SDK is now the `serpapi` npm package, and `google-search-results-nodejs` is deprecated. — [Fix SerpApi errors guide](https://serpapi.com/blog/fix-serpapi-errors-guide.md)
- `search_metadata.status` is one of Processing, Queued, Success or Error. Empty results return HTTP 200 with Success. — [Status and Error Codes](https://serpapi.com/api-status-and-error-codes)
- Latency: a sample response shows a total time of 0.87s — [Fix SerpApi errors guide](https://serpapi.com/blog/fix-serpapi-errors-guide.md). A third-party skill doc says typical latency is 2–5s per live search (low reliability) — [claudepluginhub serpapi-performance-tuning](https://www.claudepluginhub.com/skills/luxdevnet-serpapi-pack-plugins-saas-packs-serpapi-pack/serpapi-performance-tuning). Ludicrous Speed (paid add-on) is faster than "Best Effort" — [Pricing](https://serpapi.com/pricing.md)

### Inferences
- Check both the HTTP status and the `error` key in the JSON. A 200 response can still carry an `error` field.
- Budget about 1–5 s per uncached call in the UX: show a spinner and cache server-side.

### Gaps
- I found no official SLA or p50/p95 latency figures.
- I found no documented `Retry-After` header for 429 responses.

## Failed searches and empty results: charged?

### Takeaway
Errored or failed requests are free. Searches where the engine returned no results ("Google hasn't returned any results for this query.") count as successful and are charged.

### Cited Findings
- "Cached, errored, and failed searches are not [counted]." — [Pricing](https://serpapi.com/pricing)
- Empty results still use a credit if the request succeeded. Credits are not charged "in the cases where there's an error/failed request" or when the result was cached. "The search engine is responsible for the content", while SerpApi is responsible for the request/response cycle. — [SerpApi blog: credit usage](https://serpapi.com/blog/calculating-search-credit-usage-with-serpapi/)
- The "Google hasn't returned any results for this query." message comes back with HTTP 200. — [Status and Error Codes](https://serpapi.com/api-status-and-error-codes)

### Inferences
- Validate queries before sending them (no empty or garbage `q`, valid `location`) so credits aren't burned on zero-result searches.

### Gaps
- None significant.

## Legal / ToS and U.S. Legal Shield

### Takeaway
Use must be lawful, and reselling the service is prohibited. The U.S. Legal Shield (up to $2M) covers only Production-tier and higher paid plans, so the Free plan has none.

### Cited Findings
- Legal Shield covers recurring plans other than Free, Starter and Developer, up to $2M, for lawful scraping and parsing claims in U.S. state or federal courts. It excludes copyright infringement, DMCA, IP, privacy violations, fraud, harassment and cybercrime. — [Legal](https://serpapi.com/legal); the pricing page agrees (Production and above) — [Pricing](https://serpapi.com/pricing)
- Prohibited uses include unlawful activity, IP infringement, harassment, malware and circumventing security. You may not "reproduce, duplicate, copy, sell, resell or exploit any portion of the Service" without written permission. SerpApi may terminate "at any time without notice" for violations and may limit quantities per person or household. — [Legal](https://serpapi.com/legal)

### Inferences
- A hackathon prototype on the Free plan is fine, but there's no legal indemnity. Don't build anything that resells raw SERP data.
- "May limit quantities per person or household" suggests that opening several free accounts to stack credits would breach the ToS.

### Gaps
- I didn't review attribution or display requirements for third-party content such as Google images and reviews.

## Known gotchas / limitations

### Takeaway
The big ones: `num` no longer works on Google (10 results per page, and each page costs 1 credit), the cache needs an exact parameter match, empty results are billed, the API key must stay server-side, and the Free plan's 50/hr cap.

### Cited Findings
- Google switched off `num=100` on Sept 11, 2025, and pagination is now needed — [apiserpent](https://apiserpent.com/blog/google-num-100-removed-rank-tracker-fix). From early 2025 SerpApi saw queries ignoring `num`, especially those with a knowledge_graph — [SerpApi blog](https://serpapi.com/blog/google-experiments-with-restricting-results-per-page/)
- The `google_light_fast` engine for 100 results was discontinued after Google limited it to 3 results — [SerpApi blog](https://serpapi.com/blog/solution-to-scrape-100-search-results-on-google-google-fast-light-api.md)
- `location`, `uule` and `lat`/`lon` are mutually exclusive. An ambiguous `location` resolves to "the most popular" match — [SerpApi Google Search API](https://serpapi.com/search-api)
- New `output=md` option for LLM pipelines — [SerpApi Google Search API](https://serpapi.com/search-api)

### Inferences
- SERP content varies with location, device, time and Google experiments, so cache your own snapshots for a stable demo.

### Gaps
- I didn't research quirks specific to Google Flights or Hotels (required params like `departure_id`/`arrival_id`/`outbound_date`, or `check_in_date`/`check_out_date` and currency, plus price variability). Other researchers may cover these engines.
