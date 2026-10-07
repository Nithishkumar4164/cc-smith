# SerpApi Non-Engine Offerings and Platform Features for cc-smith (verified 2026-10-06)

Builds on `../SerpApi capabilities for hackathon/sdks_mcp_integrations.md`, `../SerpApi capabilities for hackathon/platform_pricing_limits.md`, and `serpapi_tool_surface.md`. Those notes are only repeated here where they had gaps that this pass closed.

Method: on 2026-10-06 I fetched serpapi.com pages (HTML and `.md` variants), the SDK and plugin repos on GitHub, the npm registry, the Google Workspace Marketplace, status.serpapi.com, and the SerpApi blog RSS. I also called the free Locations API (no key) and sent one invalid-key request to read the response headers.

Labels: **V** means verified at the cited source. **I** means my own inference, not tested.

---

## 0. Answers to the important questions

| Question | Answer | Source |
|---|---|---|
| Can SerpApi fetch or convert an arbitrary URL, such as a bank T&C or MITC page or PDF? | **No (V).** Every engine returns a search-engine result page. SerpApi's own comparison blog says: "Tavily, Exa, and Firecrawl convert the pages a search found. SerpApi converts the search itself… **Nothing inside the linked pages is fetched**." There is no extract, crawl or fetch endpoint in the integrations list, the features menu, the Extra APIs list (Account, Image, Locations, Pixel Position, Search Archive, Status), or the public roadmap issue titles (searched "fetch url", "page content", "webhook"). | [blog: Markdown SerpApi vs Exa/Tavily/Firecrawl, 2026-10-01](https://serpapi.com/blog/markdown-search-results-serpapi-vs-exa-tavily-firecrawl/); [playground menu](https://serpapi.com/playground); [public-roadmap](https://github.com/serpapi/public-roadmap) |
| Then how does cc-smith get full T&C text? | SerpApi **discovers** the URL: `google` with `q="<card> MITC filetype:pdf site:hdfcbank.com"`, or the `references[].link` returned by AI Mode. cc-smith then **fetches the page itself** with httpx plus trafilatura for HTML or pypdf/pdfplumber for PDFs, through the corporate proxy. It stores the raw bytes, a sha256 hash and the fetch date. AI Mode `text_blocks` and `references` give a pre-digested second opinion with citations. (I) | — |
| Webhooks or callbacks? | **None (V by absence).** `async=true` only works by polling the Search Archive. The only webhook-like feature is on status.serpapi.com (Atlassian Statuspage), which can notify by email, SMS, Slack, a Microsoft Teams webhook, RSS or Atom. | [search-api](https://serpapi.com/search-api); [status.serpapi.com](https://status.serpapi.com/) |
| Rate-limit headers? | **None seen (V, partial).** A 401 response carries only `x-request-id`, `x-runtime` and Cloudflare headers, with no `X-RateLimit-*` or `Retry-After`. I could not test a 200 response because I had no key. Use the Account API (`this_hour_searches`, `account_rate_limit_per_hour`) for budgeting instead. | curl of `https://serpapi.com/search.json?...&api_key=invalid` |

---

## 1. Integrations hub, item by item

Source: [serpapi.com/integrations](https://serpapi.com/integrations) ([.md](https://serpapi.com/integrations.md)). The hub lists only **12 entries**: Ruby, Python, JavaScript, Golang, PHP, Java, Rust, .NET, **MCP**, Swift, C++ and **CLI**, all marked "Available". The hub does not list agent plugins, n8n or no-code tools. Those live in GitHub, the blog and marketplaces.

| Offering | What it is (V) | cc-smith use | Cost impact | Maturity |
|---|---|---|---|---|
| **Python SDK** `pip install serpapi` | `serpapi.Client(api_key, timeout)` has `.search()`, `.search_archive()` (output `json`/`html`/**`md`**), `.upload_image()`, `.locations()` and `.account()`. Errors raise `serpapi.HTTPError(.status_code)` or `TimeoutError`. `output="md"` returns a str. [integrations/python](https://serpapi.com/integrations/python), [core.py](https://github.com/serpapi/serpapi-python/blob/master/serpapi/core.py) | The base of the gateway. It is synchronous, so wrap it in `asyncio.to_thread` for FastAPI. | None | Official, recommended. [Libraries status page](https://serpapi.com/libraries) marks Python "Done" for version, test and example. Java and Swift tests are "Limited". |
| **CLI** `brew install serpapi/homebrew-tap/serpapi-cli` | `serpapi search k=v…`, `--fields` (= `json_restrictor`, server-side), `--jq` (embedded jq), `--all-pages/--max-pages`, plus `serpapi account`, `serpapi locations` (no key needed) and `serpapi archive <id>`. Errors are JSON on stderr, with exit codes 0/1/2. Key lookup order: flag, then `SERPAPI_KEY`, then `~/.config/serpapi/config.toml`. [integrations/cli](https://serpapi.com/integrations/cli) | Ops scripts and cron ("credits left?", "re-read archive id"). Claude Code can call it as a Bash tool when MCP is not wanted. | `--all-pages` burns 1 credit per page | Official, Go binary |
| **MCP server** (hosted `https://mcp.serpapi.com/mcp`, self-host, stdio, or `.mcpb` Claude Desktop bundle) | One `search` tool, optional `search_table`/`search_dashboard` MCP Apps tools, and `serpapi://engines/<e>` schema resources. Auth is a Bearer header or a key in the path. "No key is needed to connect, list tools or read resources." [integrations/mcp](https://serpapi.com/integrations/mcp), [repo](https://github.com/serpapi/serpapi-mcp) | **Dev and ops only.** Claude Code or Desktop can explore engines and draft `json_restrictor` strings. Not for production, because it has no allow-list, cache or budget guard (see `serpapi_tool_surface.md` §3). | Same per search. Schema reads are free. | Official, v2.x, active |
| **Claude plugin** `serpapi/serpapi-claude-plugin` | `/plugin marketplace add serpapi/serpapi-claude-plugin` then `/plugin install serpapi@serpapi-plugins`. Works in Claude Code, claude.ai, the desktop app and Cowork, and adds a `/serpapi:search` command. In claude.ai it is added as a connector with an `authorization: Bearer KEY` header. The README states the cache is free on repeats within 1 h. [README](https://github.com/serpapi/serpapi-claude-plugin) (pushed 2026-10-06) | The team's own Claude workspace for research and for demoing the "Launch Radar" idea. | 1 per search | Brand new (Oct 2026) |
| Cursor, Codex/ChatGPT, OpenCode, OpenClaw, Hermes plugins | Official repos and blog posts. OpenClaw was announced 2026-10-06 and OpenCode 2026-10-03. [blog RSS](https://serpapi.com/blog/rss/), [github.com/serpapi](https://github.com/serpapi) | Not needed for cc-smith | — | New |
| **serpapi-search-tools** (PyPI) | Typed tools for 14 agent SDKs, including **Pydantic AI and LangGraph**. It has a `client=` hook. It does not cover AI Mode. (Covered in `serpapi_tool_surface.md` §4.) | Wire `news_search` into the chat agent through the gateway's caching client. | — | v1.0.0 |
| **n8n node** `n8n-nodes-serpapi` | npm v0.1.10 (2026-03-26), "Official n8n node". The repo has description files for **GoogleAIMode, GoogleAIOverview**, GoogleNews/NewsLight, GoogleSearch/Light, GoogleMaps(+Reviews, Directions), Lens, Shopping, Trends, Finance and about 20 more, plus a generic `SerpApiDescription`. The README says to use the HTTP Request node for anything missing. [repo tree](https://github.com/serpapi/n8n-nodes-serpapi), [npm](https://registry.npmjs.org/n8n-nodes-serpapi) | No-code weekly sweeps (§4.5) | 1 per search | Verified community node. Small and stable. |
| **Google Sheets add-on** "SerpApi - Search Engine Results and Ranks" (developer `serpapi.llc`) | Custom functions `=SERPAPI_RESULT("q=coffee&engine=google&location=austin","organic_results.0.title")` and `=SERPAPI_RANK(query, "site.com")`. The listing still says "100 monthly searches for free", which is outdated. [Workspace Marketplace](https://workspace.google.com/marketplace/app/serpapi_search_engine_results_and_ranks/562749385480) | A curated card-list sheet for analysts, e.g. tracking the issuer-page rank for a card name. Optional. | **Risky:** sheet recalcs re-fire queries. Results stay free only inside the 1 h cache. | Old, low-maintenance (I) |
| Zapier / Make | Zapier `/apps/serpapi` returns **404**. Make returned 403 (bot-blocked, so unverified). **No official app (V for Zapier).** | Use n8n or a webhook into FastAPI instead | — | — |
| Vercel Connect | Credential management only (earlier note). | n/a (the cc-smith backend is Python) | — | — |
| LangChain / LlamaIndex / CrewAI | LangChain-community wrappers use the legacy `google-search-results` package, which **clashes** with `serpapi`. CrewAI uses the new client. There is no LlamaIndex package. (Earlier note.) | Avoid the LangChain wrappers. Use the gateway plus LangGraph tools. | — | Legacy |

---

## 2. Search API common parameters (all engines)

Source: [search-api](https://serpapi.com/search-api) ([.md](https://serpapi.com/search-api.md)). The same block appears on [search-index-api](https://serpapi.com/search-index-api).

| Param | Behaviour (V) | Gateway use |
|---|---|---|
| `async` | `true` submits and returns immediately. Fetch the result later with `/searches/{id}`. "Should not be used together" with `no_cache`, or on Ludicrous Speed accounts. | Weekly sweeps: fire N searches, then poll |
| `no_cache` | Forces a fresh fetch. "A cache is served only if the query and all parameters are exactly the same. Cache expires after 1h. Cached searches are free." | Never set by default. Allowed only for a manual "force refresh" admin action. |
| `zero_trace` | **Enterprise only.** Nothing is stored, so the Search Archive has nothing to retrieve. [zero-trace-mode](https://serpapi.com/zero-trace-mode) | Do not use. It would break archive provenance, and the Free plan can't use it anyway. |
| `output` | `json` (default), `html` (raw HTML of the SERP), or `md`. Markdown also works via the `/search.md` route or an `Accept: text/markdown` header. md "strips tracking fields, opaque tokens, and duplicated values" and is about 50% smaller (Google Search 74%, Shopping 90%). [markdown-output](https://serpapi.com/markdown-output) | `md` for LLM-facing steps. `json` wherever tokens or ids are needed (AI Mode continuation, `search_metadata.id`). |
| `json_restrictor` | "Supported for all engines". Syntax: `a, b`, `arr[0:3]`, `arr[].{f1,f2}`. **It also works with Markdown output** (V, per the blog). [json-restrictor](https://serpapi.com/json-restrictor) | Fixed strings per call type. Note that it is part of the cache key. |
| `output=json_with_pixel_position` | Adds x/y/w/h rectangles. Google Search and Google Ads only. Also available on archive reads. [pixel-position-api](https://serpapi.com/pixel-position-api) | Not needed |
| `device` | `desktop`/`tablet`/`mobile` | Keep `desktop` (layout differs on mobile) |
| `location` / `uule` / `lat`+`lon` (+`radius`) | Mutually exclusive. An omitted `location` falls back to the proxy location. Docs say use `gl` with `location` for country consistency. | Always `location="Mumbai,Maharashtra,India"` with `gl=in`, `hl=en`, `google_domain=google.co.in` |
| Status codes | 200, 400, 401, 403, 404, **410 (archive expired)**, **429 (hourly limit OR out of searches)**, 500/503. `search_metadata.status` is Queued, Processing, Success or Error. Empty results return "Success" with an `error` string and **are billed**. [api-status-and-error-codes](https://serpapi.com/api-status-and-error-codes) | Treat a 200 with `error` and `*_results_state: "Fully empty"` as "billed, no data" |

---

## 3. Extra APIs and platform features

| Offering | What it is (V) | cc-smith use (flow) | Credits | Maturity |
|---|---|---|---|---|
| **Account API** `GET /account.json` | "Free of charge… not counted toward your monthly quota". Fields include `plan_searches_left`, `extra_credits`, `total_searches_left`, `this_month_usage`, `this_hour_searches`, `last_hour_searches`, `account_rate_limit_per_hour` and `plan_renewal_date` (null with no plan). [account-api](https://serpapi.com/account-api) | Gateway budget guard before every batch, plus an admin dashboard tile | 0 | Stable |
| **Locations API** `GET /locations.json?q=&limit≤10` | "Free to use". A full JSON download is available. I **tested it without a key**: `Bengaluru` → `canonical_name "Bengaluru,Karnataka,India"`, id `585069a8ee19ad271e9b64e4`, reach 31.5M. `Mumbai` → `"Mumbai,Maharashtra,India"`. The response has `cache-control: max-age=604800`. [locations-api](https://serpapi.com/locations-api) | One-time seed of a `locations` table with metro cities. A user's city maps to `location`. | 0 | Stable |
| **Search Archive API** `GET /searches/{id}(.json/.html/.md)` | Retrieve results up to **31 days** after completion. "Searches don't have to be completed to be retrieved" (status Queued/Processing). Python SDK `search_archive` accepts `md`. Markdown frontmatter carries `markdown_endpoint` "…/{id}.md". "Open the URL later and you get the same document back." Expired searches return **410**. [search-archive-api](https://serpapi.com/search-archive-api), [blog](https://serpapi.com/blog/markdown-search-results-serpapi-vs-exa-tavily-firecrawl/) | Async polling. Re-reading a profile's source SERP in a different format (json to md) without paying again (I). **Archive is not durable**, so cc-smith must copy evidence into its own store. | Not stated. Very likely free, since it is not a search (I). | Stable |
| **Image API** `POST /image` (multipart) | JPG/PNG/WebP, max **500 KB**. Returns `image_id`, which **expires after 10 minutes**. It is used as `engine=google_lens&image_id=…`. [image-api](https://serpapi.com/image-api), [lens upload](https://serpapi.com/google-lens-upload-an-image) | **Card Finder / Card Profile:** a user photographs a card (or a Launch Radar ad creative), Lens `visual_matches`/`products` identify the card variant, and the result maps to `card_id`. Mask the PAN and CVV first, client-side, by cropping to the card art only. (I) | Upload cost not stated. The Lens search is 1. | Stable. Note "about_this_image" Lens type discontinued 2026-10. [changelog](https://serpapi.com/blog/serpapi-weekly-changelog-sep-28-oct-04-2026/) |
| **Search Index** `engine=search_index` | "SerpApi's own, LLM-first web index with 6.12 billion pages… No proxies and no external search API calls at query time." **Currently in preview.** Params: `q`, `num` (default 10, **works here** unlike Google), `start`, `safe`, and `mode=deep` ("parallel sub-query fan-out… decomposing the query into multiple aspects"). Results are `organic_results[].{title, link, displayed_link, snippet, date, language, image_url, sitelinks}` plus `related_searches`. **No full page text** and no HTML ("only text"). The example `total_time_taken` is 0.05 s, page uptime 99.974%. [search-index-api](https://serpapi.com/search-index-api), [schema](https://github.com/serpapi/serpapi-mcp/blob/main/engines/search_index.json) | (a) Cheap, fast **URL discovery** for issuer T&C pages in the Card Profile refresh (`mode=deep` on "HDFC Infinia MITC fees rewards"). (b) Grounding snippets for the chat agent. (c) Possibly the only engine fast enough to consider near the Checkout Advisor path, though it should still stay off the hot path. Freshness and India coverage are unknown, so cross-check against `google`. (I) | Presumably 1 per search. Pricing is not stated. Cache rules match other engines. | **Preview.** No API-metrics page found. Treat as experimental. |
| **Playground** [serpapi.com/playground](https://serpapi.com/playground?utm_source=india_hackathon_26) | Every engine (including `search_index`, `google_ai_mode`) with forms. Shows **HTML URL / JSON URL / Markdown URL** of the result, has **"Export To Code"** and **"Engine History"**, and links to Docs and API Metrics. Account-side menu: API Key, Billing, Extra Credits, Invoices, **Team**, Your Plan, **Your API Metrics** (absolute numbers, engines, response times, success rates, users), **Your Searches**, Your Playground. (V from page markup; signed-out view.) | Design `json_restrictor` strings and AI Mode queries for Indian cards, export the Python snippet, and save the JSON URL as a fixture. | Playground searches **consume credits** (I, since they are real searches). | Stable |
| **X-Ray** | Click a SERP element to see its JSON path, and the reverse, on every engine. "Included at no extra cost… no cap". [xray](https://serpapi.com/xray) | Debugging which `text_blocks`/`references` hold fee tables | 0 | Stable |
| **Team Management** | Unlimited members, **multiple API keys per member or environment**, roles Admin/Developer/Billing/Viewer, per-member usage reports. "Included in all our plans at no extra cost". [team-management](https://serpapi.com/team-management) | Separate keys for `dev`, `sweep` and `chat` let usage be attributed per flow in "Your API Metrics". **They share one credit pool.** (I) | 0 | Stable |
| **Ludicrous Speed / Max** | About 2.2x faster on average and 4.2x at p99 (Max is about 9.6% faster still), using 2x or 4x resources. Billed at **2x or 4x price**, paid plans only. **Incompatible with `async`.** [ludicrous-speed](https://serpapi.com/ludicrous-speed), [max](https://serpapi.com/ludicrous-speed-max) | Not on Free. Even so, AI Mode at roughly 4 s would not meet the Checkout Advisor's 1 s budget. | 2–4x | Paid |
| **ZeroTrace** | Enterprise-only, nothing stored. [zero-trace-mode](https://serpapi.com/zero-trace-mode) | n/a. Queries carry no user PII if designed right. | — | Enterprise |
| **U.S. Legal Shield** | Up to $2M, **Production plan and above only** (not Free, Starter or Developer). Excludes copyright, IP, privacy and other illegal use. [us-legal-shield](https://serpapi.com/us-legal-shield) | Not available for cc-smith on Free. Storing and redisplaying bank T&C text is cc-smith's own copyright/ToS question either way. | — | — |
| **Security / compliance** | SOC 2 Type II, SOC 3, ISO 27001, **ISO 27701 (announced 2026-10-01)**, GDPR in progress. Search data expires after 31 days. [security](https://serpapi.com/security) | Pitch point: no user data leaves cc-smith except anonymised queries. | — | — |
| **Status page** [status.serpapi.com](https://status.serpapi.com/) | Atlassian Statuspage with email, SMS, Slack, Teams-webhook, RSS and Atom subscriptions. **A "Performance Degradation" partial outage across multiple APIs was open on 2026-10-06 15:51 UTC** ([roadmap #4426](https://github.com/serpapi/public-roadmap/issues/4426)). | Subscribe the RSS feed into ops alerts. The gateway circuit-breaker opens on 5xx bursts, and the sweep is deferred. | 0 | — |
| API Metrics (public), Release Notes, Public Roadmap, `.md` docs | Per-engine latency and success pages ([api-metrics](https://serpapi.com/api-metrics)). Release notes are updated daily ([release-notes](https://serpapi.com/release-notes)). **"Plain Text or .md Documentation Files" shipped 2026-10-01**, so any doc page has a `.md` variant (V for /search-api.md, /markdown-output.md, /integrations.md; Extra-API pages such as /account-api.md returned "Unsupported request format"). | Feed `*.md` docs to Claude Code as context when building the gateway | 0 | — |

---

## 4. Design: the "SerpApi gateway" for cc-smith (I unless cited)

A single Python module, `cc_smith/serpapi_gateway.py`. It is the **only** code that holds the key. LangGraph or Pydantic AI tools, sweeps and admin all call it.

### 4.1 Interface
```python
class SerpCall(BaseModel):          # canonical, hashable
    engine: Literal["google","google_ai_mode","google_news","google_news_light",
                    "google_maps","google_lens","search_index"]   # allow-list
    params: dict[str, str]          # sorted; India defaults injected
    restrictor: str | None          # from RESTRICTORS[purpose]
    output: Literal["json","md"]
    purpose: Literal["profile_refresh","launch_radar","cap_watch","eligibility",
                     "merchant_resolve","chat_grounding","card_photo"]
    max_age: timedelta              # local-cache freshness requirement

async def search(call) -> SerpResult        # sync path (chat, admin)
async def submit_batch(calls) -> list[str]  # async=true → search_ids
async def collect(ids) -> list[SerpResult]  # poll Search Archive
async def budget() -> Budget                # Account API (free)
```

### 4.2 Pipeline per call
1. **Canonicalise.** Inject India defaults (`gl=in`, `hl=en`, `google_domain=google.co.in` where valid, `location` taken from the Locations table). Sort the params and attach the fixed `json_restrictor` for the purpose. Compute `key = sha256(engine+params+restrictor+output)`.
2. **Local cache** (SQLite/Postgres `serp_cache`). If the row is younger than `max_age`, return it at zero cost. This is the real cache. SerpApi's own cache lasts only 1 h ([search-api](https://serpapi.com/search-api)).
3. **Budget guard.** Call `GET /account.json` (free; [account-api](https://serpapi.com/account-api)), memoised for 60 s. Refuse the call if `total_searches_left` is below a reserve for that purpose, or if `this_hour_searches` ≥ 45 (the cap is 50). Monthly envelope on 250: Card Profile refresh 120, Launch Radar 40, Cap Watch 30, Eligibility 20, chat 20, reserve 20.
4. **Call.** `output=md` for LLM-only reads (chat grounding, news triage). `output=json` with a restrictor for extraction (AI Mode needs `subsequent_request_token`, `reference_indexes` and `search_metadata.id`, which md strips; see [markdown-output](https://serpapi.com/markdown-output)).
5. **Provenance.** Persist `search_metadata.id`, `json_endpoint`, `created_at`, params, and the raw (restricted) body in `serp_evidence`. Every Card Profile field points to an `evidence_id` (a SERP or a fetched page). The **Search Archive** acts as the 31-day re-read window, for example re-reading the same search as `.md` for an LLM re-summary at no search cost. After 31 days you get 410, so the local copy is canonical.
6. **Errors.** On 429, read `account.json` to tell "hourly" apart from "exhausted". Back off until the next hour or stop the sweep. On 5xx, retry once (failed searches aren't billed, per [pricing](https://serpapi.com/pricing)). When the status RSS shows an active incident, open the circuit breaker. A 200 with `error` and "Fully empty" counts as billed, so log it and widen the query only once.

### 4.3 Restrictor presets (all are part of the cache key, so keep them constant)
- `ai_mode_extract`: `text_blocks, reconstructed_markdown, references[].{index,title,link,source,snippet}, subsequent_request_token, error, search_metadata.{id,status}`
- `google_urls`: `organic_results[].{position,title,link,snippet,date}, knowledge_graph.{title,website,description}, search_metadata.{id,status}`
- `news`: `news_results[].{title,link,source,iso_date}, search_metadata.{id}`
- `search_index`: `organic_results[].{title,link,snippet,date}, search_metadata.{id}`
- `maps_merchant`: `local_results[].{title,type,types,type_ids,place_id,address}, place_results.{title,type,types}`

### 4.4 Weekly sweep (async batch)
1. `budget()` checks that this week's envelope is within the hourly cap (50/h).
2. `submit_batch()` sends N calls with `async=true` (no `no_cache`, as the docs require). For example: Launch Radar `google_news_light` queries such as "credit card launch" and per-issuer queries, Cap Watch "devaluation" news, and `search_index mode=deep` for URL discovery.
3. The returned `search_metadata.id` values are persisted to `sweep_jobs`.
4. `collect()` polls `/searches/{id}.json` with backoff, which is allowed even while a search is queued ([search-archive-api](https://serpapi.com/search-archive-api)).
5. Dedupe on link and title, then send the new items to the LLM triage step (`output=md` re-read from the archive).
6. New candidate URLs go to cc-smith's **own fetcher** (httpx with trafilatura/pypdf), then to Claude extraction into the profile, a diff, and human review.
7. Keep below 45 submissions per hour and spread the batch across hours if needed.

### 4.5 n8n as the no-code alternative
A Schedule Trigger (weekly) feeds SerpApi nodes (Google News and Google AI Mode exist in `n8n-nodes-serpapi`; use the HTTP Request node with `async=true` and the archive for anything else). Then:
- Code node: dedupe.
- HTTP Request: `POST https://<cc-smith>/ingest/serp`.
- An optional n8n AI Agent node with Claude.

Pros: visual scheduling, retry handling, and judges can see it. Cons: **it bypasses the gateway's budget guard and cache**, unless n8n calls the cc-smith `/gateway/search` endpoint instead of SerpApi directly. **Recommendation:** n8n calls cc-smith endpoints and only cc-smith holds the SerpApi key.

### 4.6 Dev and ops
- **MCP** in Claude Code (`claude mcp add --transport http serpapi https://mcp.serpapi.com/mcp --header "Authorization: Bearer …"`) or the Claude plugin, using a separate **dev key** from Team Management. Use it to explore AI Mode answers for Indian cards and prototype restrictors. Read `serpapi://engines/google_ai_mode` for free.
- **CLI** for `serpapi account` and `serpapi archive <id> --jq …` in runbooks.
- **Playground** "Export To Code" for fixtures, and **X-Ray** for picking JSON paths.

### 4.7 Per-flow mapping

| Flow | SerpApi offering used | Not used |
|---|---|---|
| Card Profile (refresh) | `search_index mode=deep` and `google` (`site:`/`filetype:pdf`) for URL discovery. `google_ai_mode` JSON with the restrictor for cited summaries. Archive for re-reads. The own fetcher handles the actual T&C. | ZeroTrace, Ludicrous |
| Card Finder | Local store only. Optional Lens via `/image` upload for "identify my card from a photo". | — |
| Checkout Advisor (~1 s) | **None live.** A precomputed merchant→category cache, filled offline by `google_maps`. | Everything else |
| Eligibility Path | `google_ai_mode` (continuable) runs offline into the profile | — |
| Cap Watch | Weekly `google_news_light` async sweep, then AI Mode re-extraction on a hit | — |
| Renewal Review | Local store, plus at most one news check for "<card> devaluation" | — |
| Launch Radar | Weekly async sweep (news plus `search_index`), Lens on ad creatives (optional), n8n option | — |
| Chat agent | One `gateway.search` tool, allow-listed engines, `output=md`, `purpose=chat_grounding`, hard cap of 2 per session | Raw MCP |

---

## Gaps / unverified
- Credit cost of `search_index` (preview), Image API uploads and Search Archive reads is not stated anywhere I found.
- Search Index freshness, its coverage of Indian bank domains and PDFs, and its latency outside the doc example are untested. Run 5 test queries.
- I could not inspect rate-limit headers on a successful response (no key was available). None appear on 401.
- The Playground's signed-in features (code-export languages, saved history depth, sharing) were seen only as menu labels.
- Make.com integration is unverified (403).
- The Sheets add-on's maintenance status is unknown, and its listing text is outdated.
