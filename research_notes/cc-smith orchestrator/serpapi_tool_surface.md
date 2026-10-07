# SerpApi Tool Surface for the cc-smith Orchestrator (verified 2026-10-06)

Method: I re-checked the earlier notes in `research_notes/SerpApi capabilities for hackathon/` against the live docs on 2026-10-06. Sources were the `https://serpapi.com/<slug>.md` pages, the HTML doc pages (which carry the "JSON Structure Overview" blocks), per-engine `…/api-metrics` pages, and shallow clones of `serpapi/serpapi-mcp` (HEAD 2026-09-22, v2.0.0) and `serpapi/serpapi-search-tools-python` (HEAD 2026-09-09, v1.0.0).

Labels used below: "Verified" means read directly in a doc or in source code. "Inference" means my own reasoning and has not been tested.

---

## 0. Headline facts that change the design

| Fact | Source |
|---|---|
| **google_ai_mode averages 8.91 s per call** (98.2% success). google_ai_overview averages 9.24 s, brave_ai_mode 20.42 s, `google` 8.81 s, google_light 3.69 s, google_news 5.11 s, google_news_light 1.42 s, google_maps 0.72 s, google_shopping 5.09 s, google_shopping_light 1.36 s. The all-engine average is 1.33 s. | [AI Mode metrics](https://serpapi.com/google-ai-mode-api/api-metrics), [AI Overview metrics](https://serpapi.com/google-ai-overview-api/api-metrics), [Brave metrics](https://serpapi.com/brave-ai-mode-api/api-metrics), [Search metrics](https://serpapi.com/search-api/api-metrics), [Light](https://serpapi.com/google-light-api/api-metrics), [News](https://serpapi.com/google-news-api/api-metrics), [News Light](https://serpapi.com/google-news-light-api/api-metrics), [Maps](https://serpapi.com/google-maps-api/api-metrics), [Shopping](https://serpapi.com/google-shopping-api/api-metrics), [Shopping Light](https://serpapi.com/google-shopping-light-api/api-metrics), [All engines](https://serpapi.com/api-metrics) |
| Consequence for Flow 2 ("which card to use", about 1 s): **Flow 2 must make no live SerpApi call.** Only google_maps (0.72 s) comes close, and only when there is no cache hit. Flow 2 should read from the card-profile store and a local merchant→category cache. | Inference from the metrics above |
| `output=md` strips "tracking fields, **opaque tokens**, and duplicated values". So when you need `subsequent_request_token`, `immersive_product_page_token` or `ai_overview.page_token`, request JSON. | [Markdown Output](https://serpapi.com/markdown-output) |
| The cache serves a result "only if the query and all parameters are exactly the same", and it lasts 1 h. Cached searches are free. | [AI Mode docs](https://serpapi.com/google-ai-mode-api) |
| The MCP server has **no engine allow-list**. Unknown engines pass straight through to SerpApi. | [serpapi-mcp README](https://github.com/serpapi/serpapi-mcp) ("Unknown engines pass through to SerpApi"); source `src/mcp_components/tools.py` |
| serpapi-search-tools **does not cover google_ai_mode, google_ai_overview, brave_ai_mode or knowledge-graph lookups**. The only Google engines it covers are google/google_light (web), google_news, google_maps, google_images, google_shopping, google_hotels, google_flights and google_travel_explore. | [`__init__.py` _SUPPORTED_ENGINES_BY_TOOL](https://github.com/serpapi/serpapi-search-tools-python/blob/main/src/serpapi_search_tools/__init__.py) |

---

## 1. `engine=google_ai_mode`: the primary card-terms extractor

### 1.1 Parameters (complete list from the docs)
Source: [google-ai-mode-api](https://serpapi.com/google-ai-mode-api) and [.md](https://serpapi.com/google-ai-mode-api.md)

| Param | Req | Notes |
|---|---|---|
| `q` | yes | "anything that you would use in a regular Google AI Mode search". Multi-language: "not all are available yet". |
| `location` | no | City-level is recommended. It can't be combined with `uule`. "If omitted, the search may take on the location of the proxy", so **always set it for India**. |
| `uule` | no | Mutually exclusive with `location`. A coordinate-based uule needs a matching `gl`. |
| `gl` | no | Two-letter country code (`in`). |
| `hl` | no | Language code (`en`, `hi`, `en-in`…). |
| `continuable` | no | Default `false`. **It must be `true` for the response to contain `subsequent_request_token`.** |
| `subsequent_request_token` | no | Continues the conversation. Send a new `q` with it, and "reuse the same localization settings (`gl`, `hl`, and location)". |
| `image_url` | no | "URL of an image to include in the prompt". Possible use: a photo of a card's fee table or MITC page. |
| `device` | no | `desktop` (default), `tablet` or `mobile`. |
| `no_cache`, `async`, `zero_trace` (Enterprise), `api_key`, `output` (`json`/`html`/`md`), `json_restrictor` | no | Standard SerpApi params. `async` + `no_cache` must not be combined. |

There is **no** `google_domain`, `start`, `safe` or `num` on this engine. Those parameters are not listed. ([docs](https://serpapi.com/google-ai-mode-api))

### 1.2 Response keys
Source: the "JSON Structure Overview" on [google-ai-mode-api](https://serpapi.com/google-ai-mode-api)

- `text_blocks[]`. The listed `type` values are `heading`, `paragraph`, `list`, `expandable`, `comparison` and `code_block`. The doc examples also show **`table`** and **`chart_block`**.
  - Common fields: `snippet`, `snippet_highlighted_words`, `snippet_inline_code`, `snippet_links`, `reference_indexes[]`, which index into root `references`.
  - `list` blocks: `list[]` items carry `title`, `snippet`, `reference_indexes`, `thumbnail`, an optional `shopping_result{…}` or `local_result{…}`, nested `list[]`, and nested `text_blocks[]`.
  - **`table` blocks:** `table` is an array of rows of strings, with the header row first. `formatted` is an array of objects keyed by snake_cased headers, for example `{"team":…, "seasons_played":…}`. `reference_indexes` is also present. **This is the most useful shape for fee/earn-rate tables.**
  - `code_block`: `language`, `code`.
  - `chart_block`: `title`, `chart_type` (bar or line), `data[].series_label`, `data[].points[{x,y}]`, `reference_indexes`.
- `reconstructed_markdown` (string): "Markdown reconstruction of the answer generated from text_blocks and references". It ends with a `### References` list in the form `[n] [title](link) — snippet`, and inline `[n]` markers. Chart blocks appear as a blockquote with an "_[Interactive bar chart omitted…]_" note.
- `references[]`: `title`, `link` (often has a `#:~:text=` fragment), `snippet` (often starts with a date such as "Sep 18, 2025 — …"), `source`, `thumbnail`, `source_icon`, `index`.
- Other keys: `quick_results[]` (`title`, `link`, `snippet`, `source`, `displayed_link`, `favicon`); `shopping_results[]` (with `immersive_product_page_token`); `local_results[]`; `inline_images[]`; `inline_products`; `inline_videos[]`; `related_questions[]` (`question`, `serpapi_link`); `subsequent_request_token`; `error` ("if the AI Mode results are not available"); plus `search_metadata.status` (Processing → Success | Error).

### 1.3 How multi-turn works
1. First call: `engine=google_ai_mode&q=…&continuable=true&location=…&gl=in&hl=en`. The response includes `subsequent_request_token`. ([docs](https://serpapi.com/google-ai-mode-api))
2. Follow-up call: `subsequent_request_token=<tok>&q=<new question>` with the same gl/hl/location. The follow-up "includes the prior exchange as context". (Same source.)
3. **Token expiry: not documented** for AI Mode. I found no "expires" wording on the page, unlike AI Overview's `page_token` ("expires within 1 minute"). Inference: treat the token as short-lived, use it immediately inside the same job, and never persist it.
4. Each turn is a separate search request, so it should cost 1 credit. Inference: billing is per successful search ([pricing](https://serpapi.com/pricing)), but no doc spells out the cost for this engine. Multi-turn is also **cache-unfriendly**, because the token differs on every run.

### 1.4 India
- Google rolled AI Mode out to all Indian users in July 2025, added Hindi in Sep 2025, and then added Bengali, Kannada, Malayalam, Marathi, Tamil, Telugu and Urdu. ([Google India blog](https://blog.google/intl/en-in/products/google-search-ai-mode-now-available-in-hindi/), [TechCrunch 2025-10-08](https://techcrunch.com/2025/10/08/googles-search-live-comes-to-india-ai-mode-gets-more-languages/))
- SerpApi documents no India-specific restriction for this engine. The docs warn that without `location` you get the proxy's location, which skews results toward US issuers. ([docs](https://serpapi.com/google-ai-mode-api))
- Inference: use `gl=in&hl=en&location=<canonical name from locations.json>`, for example "Mumbai,Maharashtra,India", and put the issuer and product name in `q`. A query like "HDFC Infinia reward rate, caps, exclusions, fee waiver 2026" should push the model toward issuer pages and their MITC documents.

### 1.5 `output=md` and `json_restrictor`
- `output=md` works on this engine: "Markdown output … uses tables, markdown links, and YAML frontmatter… use `output=md`, `/search.md`, or `Accept: text/markdown`". ([docs](https://serpapi.com/google-ai-mode-api)) It **drops opaque tokens** ([markdown-output](https://serpapi.com/markdown-output)), so md mode cannot be used for multi-turn or for drilling into immersive products.
- In JSON mode the `reconstructed_markdown` field already gives you markdown. That makes the best setting **JSON plus `json_restrictor`**.
- `json_restrictor` "is supported for all engines". Its syntax: `key`, `a, b`, `arr[0]`, `arr[0:3]`, `arr[].field`, `arr[].{f1, f2}` and `arr[].{f1, nested.inline[].link}`. ([JSON Restrictor](https://serpapi.com/json-restrictor))
- Recommended value for extraction: `json_restrictor=text_blocks, reconstructed_markdown, references[].{index, title, link, source, snippet}, subsequent_request_token, error, search_metadata.{id, status}`. It "reduc[es] payload size for faster response". Inference: it is still billed and it is part of the cache key, so keep it constant.

### 1.6 Fallbacks for extraction
**`google_ai_overview`**
- Its only query param is `page_token` (required), taken from `ai_overview.page_token` in a `engine=google` response. The token "**expires within 1 minute**". Common params work, including `output=md` and `json_restrictor`. ([docs](https://serpapi.com/google-ai-overview-api))
- The AI Overview block "is only seen for English searches (hl=en) with a limited range of countries (gl)", and "Google sometimes requires an additional request". ([AI Overview results](https://serpapi.com/ai-overview))
- `text_blocks.type` can be heading, paragraph, list, expandable or comparison. Tables appear as `table` with `detailed` and `formatted`. There is a `references[]` array, and an `error` such as "Can't generate an AI overview right now." (Same source.)
- Cost: 2 searches when a token hop is needed (inference). Latency: 8.81 s plus 9.24 s.
- Use it only as a secondary cross-check, because it is not conversational.

**`brave_ai_mode`**
- Params: `q`, `location` or `lat`+`lon`, `country`, `language`, `safeSearch`, `units_of_measurement` and `subsequent_request_token`. There is no `continuable` flag; the token is always returned. ([docs](https://serpapi.com/brave-ai-mode-api))
- India is in [brave-countries](https://serpapi.com/brave-countries.json), per the earlier notes.
- Response: `markdown`, `text_blocks` (the paragraph type has `segments[].citations[{reference_index, cited_snippet}]`, and there are `table` and `formatted` types), `references`, `web_results` and `related_questions`.
- The **segment-level `cited_snippet` is the best provenance shape** of the three engines, because it maps each claim to the exact supporting text. That fits a "source + date per field" profile very well.
- Downsides: 20.42 s average latency and 96.25% success. ([metrics](https://serpapi.com/brave-ai-mode-api/api-metrics))
- Use it as a fallback when AI Mode returns `error` or when its references don't include an issuer domain.
- `bing_copilot` (17.83 s) is another option, but it adds little here. ([metrics](https://serpapi.com/bing-copilot-api/api-metrics))

---

## 2. Per-flow engine map

All engines below use `GET https://serpapi.com/search?engine=…`. Shared India defaults are `gl=in`, `hl=en`, and `google_domain=google.co.in` where that param exists. Flows 1, 3a, 3b and 3c should mostly **read the card-profile store**. SerpApi feeds an offline "profile refresh" job, so it does not sit on the user path.

| Flow | Engine / endpoint | Key params | Fields to read | Notes |
|---|---|---|---|---|
| **Profile build/refresh** (shared by all flows) | `google_ai_mode` | `q="<Issuer> <Card> reward rate caps exclusions milestone annual fee waiver lounge eligibility <year>"`, `continuable=true`, `location`, `gl=in`, `hl=en`, `json_restrictor` (§1.5) | Tables come from `text_blocks[type=table].formatted` and `.table`. Bullets come from `text_blocks[type=list].list[].snippet`. Provenance comes from `reference_indexes` → `references[].{link, source, snippet-date}`. | Follow-up turns via `subsequent_request_token`, e.g. "list excluded MCCs", "what are the monthly caps per category". An LLM maps the text into the profile schema with a source and date per field. Code validates numbers against references. |
| Profile refresh (cross-check) | `google` (web) | `q="<card> MITC site:<issuer domain>"` or `"<card> fees and charges"`, `location`, `gl=in`, `google_domain=google.co.in`, `json_restrictor=organic_results[].{title,link,snippet,date},knowledge_graph,ai_overview` | `organic_results[].link` (issuer PDF/MITC URL), `knowledge_graph`, `ai_overview.page_token` | The `site:` operator is supported on `google` ([search-api](https://serpapi.com/search-api)). Take the URL and fetch the PDF yourself (not SerpApi). |
| Profile refresh (fallback) | `brave_ai_mode` | `q`, `country=in`, `language=en` | `text_blocks[].segments[].citations[].cited_snippet`, `references[].link` | Slow (about 20 s). Use only for batch jobs. |
| **1 New card enquiry** | No live call (reads profile store). An optional `google_news` check for "<card> devaluation" before ranking. | `engine=google_news&q="<card name>" when:30d&gl=in&hl=en&so=1` | `news_results[].{title, link, source.name, date, iso_date}` | `q` supports `site:` and `when:` on google_news. `so=1` sorts by date. `q` can't be combined with token params. ([google-news-api](https://serpapi.com/google-news-api.md)) |
| **2 Which card to use (about 1 s)** | **No SerpApi call on the hot path.** Offline/async only: `google_maps` resolves an unknown merchant to a category. | `engine=google_maps&type=search&q="<merchant> <city>"&location=…&z=14` **or** `place_id` / `data_cid` for a known place | `local_results[].{title, type, types[], type_id, type_ids[], place_id, data_cid, address, gps_coordinates}` (or `place_results`) | Google place types are **not MCCs**. A deterministic `type_ids → spend category` table is still needed, and the bank's actual MCC can differ. Cache per merchant permanently. ([google-maps-api](https://serpapi.com/google-maps-api.md)) |
| 2 (offer lookup, async) | `google_news` or `google` | `q="<card> offer <merchant>"` | `news_results` / `organic_results` | Precompute nightly. Never run per-tap. |
| **3a Prerequisites** | `google_ai_mode` (multi-turn) | `q="How to get <card> against FD / card-to-card / with savings account <bank>"`, `continuable=true` | `text_blocks` (list/table), `references` | Store as profile `eligibility.paths[]` with a source per path. |
| **3b Cap tracking + re-routing on cap change** | `google_news` (detect change) → `google_ai_mode` (re-extract) | news: `q="<issuer> credit card reward cap change" when:7d`, `so=1`; also `publication_token` / `topic_token` for business sections | `news_results[].{title, link, iso_date, source}` | Diff the new extraction against the profile. Deterministic code recomputes routes. User-spend tracking is local. |
| **3c Keep/convert/close** | No live call (profile + user spend). Optional `google_ai_mode` for "<card> upgrade / product change path". | `q`, `continuable=false` | `text_blocks`, `references` | — |
| **4 New card launch detection** | `google_news` (scheduled) | `q="new credit card launch India" when:7d`, `so=1`, `gl=in`, `hl=en`; per-issuer `q="<issuer> launches credit card"` | `news_results[].{title, link, source.name, iso_date, stories?}` | Dedupe by title/link. Then `google` + `knowledge_graph` (`q="<card name>"`, read `knowledge_graph.{title, description, website, source}`) and `google_ai_mode` to build the profile. |
| 4 (co-brand partner context) | `google_shopping` (rarely useful) | `q`, `gl=in`, `google_domain=google.co.in`, `location` | `shopping_results[].{title, extracted_price, source, product_id}` | Shopping returns about 40 items and ignores `start` ([docs](https://serpapi.com/google-shopping-api.md)). Card terms are not products, so **drop it from the MVP** unless you compute "₹ value of a co-brand voucher". |

**Free endpoints** (no credits):
- **Account API**: `GET https://serpapi.com/account.json?api_key=…`. It is "free of charge… not counted toward your monthly quota". Read `plan_searches_left`, `total_searches_left`, `this_hour_searches`, `last_hour_searches`, `account_rate_limit_per_hour`. Use it as the budget guard before every batch. ([account-api](https://serpapi.com/account-api))
- **Locations API**: `GET https://serpapi.com/locations.json?q=Bengaluru&limit=5`. It is "free to use", max 10 results, sorted by reach. Pass `canonical_name` or `id` as `location`. You can also download the full JSON. ([locations-api](https://serpapi.com/locations-api))
- **Search Archive API**: `GET https://serpapi.com/searches/{search_id}.json`. It returns json or html "up to 31 days after the search has been completed", and pairs with `async=true`. ([search-archive-api](https://serpapi.com/search-archive-api)) Whether archive reads are free is **not stated** (gap). Use it to re-parse old AI Mode answers for provenance or audit without paying for a re-search. Inference: store `search_metadata.id` alongside every profile field.

**Credit budget** (250 per month, 50 per hour on Free; [pricing](https://serpapi.com/pricing)). Inference:
- Profile build for 30 cards: about 3 AI Mode turns per card, so about 90.
- Weekly news sweeps: 4 queries × 4 weeks = 16.
- Merchant resolution: about 30.
- Total is about 140, which leaves headroom. That only holds with local persistence. The 1 h SerpApi cache is not enough.

---

## 3. SerpApi MCP server (`serpapi/serpapi-mcp`, v2.0.0)

Sources: [README](https://github.com/serpapi/serpapi-mcp) and source files `src/server.py`, `src/mcp_components/tools.py` and `apps.py`.

**Tools exposed**
1. `search(params: dict, mode: "complete"|"compact" = "complete")`.
   - `params` is free-form SerpApi params. `engine` defaults to `google_light`.
   - `output` must be `json` or `md`. `html` is rejected: "Invalid output. Use either 'md' or 'json'".
   - `compact` drops `search_metadata`, `search_parameters`, `search_information`, `pagination` and `serpapi_pagination`. Note that this also drops `search_metadata.id`, which you need for provenance.
   - The result arrives as a **string** in `structuredContent.result` (serialized JSON or Markdown). Failures set `isError: true`.
   - Annotations: `readOnlyHint=true`, `idempotentHint=false`, `openWorldHint=true`.
2. `search_table(params)` and `search_dashboard(params)`: opt-in MCP Apps (SEP-1865) UI tools. "Hosts that don't support MCP Apps simply ignore these tools." They have engine-specific builders for flights, jobs and shopping.

**Resources**
- `serpapi://engines` is the index (118 engine JSON files in `engines/`, including `google_ai_mode.json`, `google_ai_overview.json`, `brave_ai_mode.json`, `google_news.json`, `google_maps.json`, `google_shopping.json` and `google.json`).
- `serpapi://engines/{engine_name}` gives per-engine param schemas scraped from the Playground, with descriptions, groups and select options.
- There is argument completion on engine names.

**Guided input (elicitation)**
- Clients on MCP 2026-07-28 get a form for missing required params before any search runs.
- Older clients get an error that lists the missing fields.
- Rules exist for flights, hotels, maps_directions, google_maps, amazon, ebay, walmart, scholar, shopping and others. Unknown engines pass through.

**Transport and auth**
- Hosted URL: `https://mcp.serpapi.com/mcp`. It is FastMCP `http_app(stateless_http=True, json_response=True)`, i.e. **Streamable HTTP, stateless, JSON responses** with no SSE streaming. CORS is `*`.
- Auth is `Authorization: Bearer <key>` (recommended) or `/<key>/mcp` in the path. "No key is needed to connect, list tools or read resources." The hosted server "records request metrics… stores no queries or results".
- Self-host with `uv run src/server.py` (`MCP_HOST`/`MCP_PORT`, port 8000) or Docker. Stdio runs via `src/stdio.py` with `SERPAPI_API_KEY`. Python 3.13+.

**Connecting from agent frameworks** (inference, using standard MCP client APIs):
- Claude Agent SDK: `mcp_servers={"serpapi": {"type":"http","url":"https://mcp.serpapi.com/mcp","headers":{"Authorization":"Bearer …"}}}` with `allowed_tools=["mcp__serpapi__search"]`.
- OpenAI Agents SDK: `MCPServerStreamableHttp(params={"url":…, "headers":{…}})`.
- LangGraph: `langchain-mcp-adapters` `MultiServerMCPClient({"serpapi":{"transport":"streamable_http","url":…,"headers":{…}}})`.
- Pydantic AI: `MCPServerStreamableHTTP(url, headers=…)`.
- CrewAI: `MCPServerAdapter({"url":…, "transport":"streamable-http", "headers":…})`.

**Limitations for cc-smith**
- There is one generic `search` tool with an untyped `params: dict`. The model has to read `serpapi://engines/<e>` (more tokens and more turns) or guess param names. Mistakes such as `q` vs `k` vs `search_query` burn credits.
- **There is no engine allow-list, no budget cap, no caching layer and no per-tool typing.** The only server-side knobs are the API key and `mode`. The tool description even lists a non-existent engine name, `youtube_search` (the real id is `youtube`).
- No tool exposes Account, Locations or Archive.
- The result is a JSON-in-a-string, which the app must re-parse.
- Inference: an allow-list is possible only by (a) self-hosting a fork that filters `params.engine`, or (b) wrapping the client-side tool call in a guard, e.g. a Claude Agent SDK `PreToolUse` hook or a LangGraph tool-node wrapper that rejects engines outside the set.

---

## 4. `serpapi-search-tools` (PyPI 1.0.0, Python ≥3.10)

Source: [repo](https://github.com/serpapi/serpapi-search-tools-python), `src/serpapi_search_tools/*.py` and the docs at [serpapi.github.io/serpapi-search-tools-python](https://serpapi.github.io/serpapi-search-tools-python/).

**Exports:**
- Tool constructors: `web_search`, `news_search`, `maps_search`, `images_search`, `shopping_search`, `videos_search`, `hotels_search`, `flights_search`, `travel_explore_search`.
- Enums and types: `WebSearchEngine` (GOOGLE, GOOGLE_LIGHT, BING, YAHOO, DUCKDUCKGO), `ShoppingSearchEngine` (GOOGLE_SHOPPING, AMAZON, WALMART, EBAY), `TravelClass`, `SearchResultMode` (COMPACT/FULL), `SearchResultFormat` (MARKDOWN/JSON), `SerpApiSearchError`.

**Common constructor signature** (keyword-only):
```python
web_search(*, provider="auto", allowed_engines=None, default_engine=None, include_examples=True,
           api_key=None, client: SearchClient|None=None, default_params: Mapping|None=None,
           timeout=None, mode=SearchResultMode.COMPACT, response_format=SearchResultFormat.MARKDOWN,
           result_limit=10, name="web_search")
```
- `shopping_search` has the same signature but `result_limit=60`.
- `news_search`, `maps_search`, `images_search` and `videos_search` have no `allowed_engines` (fixed engine). `news_search` has `result_limit=20`.

**Model-facing inputs**
- `web_search` takes `query` plus an `engine` enum restricted to `allowed_engines`.
- `news_search` takes `query` only (Google News query mode; the topic/story token params are refused by a validator).
- `maps_search` takes `query`, `location?`, `zoom` (3–30, default 14) and `nearby` (which requires `location`). `place_id`/`data_cid` are rejected: "require a separate place-details tool".
- `shopping_search` takes `query` plus an `engine` enum.

**`allowed_engines`** exists only on `web_search` and `shopping_search`. It narrows the enum shown to the model. `default_engine` must be inside that set.

**`default_params`** carries app-level params such as `{"gl":"in","hl":"en","google_domain":"google.co.in","location":…}` that the model can't see. It cannot set `api_key`, `async`, `engine` or `output`. Typed (model) params override defaults, and a `None` value removes the key. (`_shared.py` `execute`)

**`client`**: any object with `.search(params) -> Mapping | str`. This is the **hook for caching, budget guards and logging**.

**Output defaults**
- Markdown via `output=md`, plus compact filtering per engine. For `google`, compact keeps only `answer_box`, `knowledge_graph`, `ai_overview` and `organic_results`. For `google_news` it keeps `news_results`; for `google_maps`, `local_results` and `place_results`; for `google_shopping`, `shopping_results`.
- Shopping compact drops `immersive_product_page_token`.

**Engine coverage for cc-smith**
- Covered: news (`google_news`), maps (search mode only), shopping, and web (`google`, which includes `knowledge_graph` in compact mode).
- **Not covered: `google_ai_mode`, `google_ai_overview`, `brave_ai_mode`, maps place details, Account/Locations/Archive.**

**Frameworks.** `provider` is one of: `auto | function | langchain | langgraph | crewai | llamaindex | openai-agents | claude-agent-sdk | pydantic-ai | microsoft-agent-framework | autogen | haystack | semantic-kernel | agno | smolagents | google-adk`. Auto-detect raises "Multiple supported agent SDKs are installed… Pass provider=... explicitly" if it finds more than one family. (`_providers.py`) Usage, from `docs/sdk_examples/*.qmd`:
- **LangGraph**: `tool = web_search()`, then `model.bind_tools([tool])` and `ToolNode([tool])`. It returns a LangChain `StructuredTool`.
- **OpenAI Agents SDK**: `Agent(tools=[web_search(), news_search()])`. It returns a `FunctionTool`, and the invoke is async.
- **Claude Agent SDK**: `create_sdk_mcp_server(name="serpapi", version="1.0.0", tools=[web_search(), news_search()])`, then `ClaudeAgentOptions(mcp_servers={"serpapi": server}, allowed_tools=["mcp__serpapi__web_search", …])`. The adapter wraps the sync call in `asyncio.to_thread` and uses `claude_agent_sdk.tool` with `readOnlyHint`.
- **Pydantic AI**: `Agent(model, tools=[web_search(), …])`. It returns a `Tool`, and errors map to `ModelRetry`.
- **CrewAI**: `crewai.Agent(tools=[news_search(), web_search()])`. It returns a `BaseTool` (crewai ≥1.6.1,<2, Python <3.14).

---

## 5. Recommendation: what to use for each flow

| Flow | Recommended | Why |
|---|---|---|
| Profile build/refresh (AI Mode, Brave fallback, KG) | **Typed custom tools** in your own Python module: `extract_card_terms(issuer, card, aspect, turn_token?)`, `fetch_ai_overview(q)`, `kg_lookup(card)`. Use the official `serpapi` client (`serpapi.Client.search`), JSON output, a fixed `json_restrictor`, `continuable=true`, and a persistent cache keyed on the canonical param dict. | Search-tools has no AI Mode tool, and MCP's untyped `params` invites param drift. You need `reference_indexes→references` and `search_metadata.id` for per-field provenance, but md/compact modes strip tokens and ids. Deterministic param construction makes the cache hit reliably. |
| 1 Enquiry, 3c Keep/close | **No search tool exposed to the LLM.** Read from the profile store. Optionally give the agent a `news_search` from search-tools with `default_params={"gl":"in","hl":"en"}`, `result_limit=5` and a caching `client`. | Ranking is deterministic code, so the LLM only explains. That is the lowest credit spend. |
| 2 Which card (about 1 s) | **No SerpApi at request time.** A background typed `resolve_merchant(name, city)` uses google_maps → `type_ids` → category map, with a permanent cache. | Even a Maps miss is 0.72 s on average, and every LLM hop adds more. |
| 3a Prerequisites | Typed `extract_card_terms` with aspect `"eligibility"` (AI Mode multi-turn). | Same reasons as profile build. |
| 3b Cap-change detection | Scheduled job: typed or search-tools `news_search` (`default_params` with `gl=in`, `hl=en`) → diff → typed AI Mode re-extract. | A fixed engine with typed inputs is cheap, and the `client=` hook gives caching and budget control. |
| 4 Launch detection | Same as 3b, plus `web_search(allowed_engines=[WebSearchEngine.GOOGLE], default_engine=WebSearchEngine.GOOGLE, default_params={…India…})` for the knowledge graph. | `allowed_engines` keeps the model away from Bing/Yahoo. |
| Exploratory / dev-time | **Hosted MCP** (`https://mcp.serpapi.com/mcp`) in Claude Code or the Inspector, plus the `serpapi://engines/<e>` resources. | It is the quickest way to try engines and read schemas. It is not for production on 250 credits: no allow-list, no cache, untyped. |

**Tradeoffs**

| | Typed custom tools | MCP `search` | serpapi-search-tools |
|---|---|---|---|
| Credit control | Full control: budget guard via Account API, persistent cache, engine whitelist in code | None server-side. You need a client hook or a fork. | Via the `client=` hook and `allowed_engines` (web and shopping only) |
| Caching | Your own (DB, keyed on canonical params), plus SerpApi's 1 h cache | Only SerpApi's 1 h cache | Via the custom `client` |
| Schema precision | Exact per-flow Pydantic args and outputs | `params: dict` (model must read resources) | Typed, but generic query-level inputs, md output by default |
| Engines | Any, including AI Mode, AI Overview and Brave | Any (118 schema files) | 9 tools. **No AI Mode, AI Overview, Brave or place details** |
| Latency overhead | Direct HTTPS | Plus a hop through mcp.serpapi.com and resource reads | Direct (sync, run in a thread for async SDKs) |
| Provenance | Keep `search_metadata.id`, `references`, dates | Lost in `compact`; JSON string must be re-parsed | Lost in compact/md (tokens and ids stripped) |

**Bottom line** (inference): build one small typed module, `serpapi_tools.py`, with 4–5 functions. Expose only `news_search` (from search-tools, with a caching client) to the LLM agents, and keep AI Mode extraction in a deterministic pipeline that is not left to the model's discretion. Use MCP only during development.

---

## Gaps / unverified
- AI Mode `subsequent_request_token` lifetime is undocumented.
- Credit cost per AI Mode turn and per AI Overview `page_token` hop is assumed to be 1 search each.
- It is not stated whether Search Archive reads are free.
- `json_restrictor` behaviour with `output=md` is untested.
- Whether AI Mode answers in India reliably cite issuer domains or MITC PDFs is unverified. Run 3–5 sample queries and inspect `references[].link`.
- The framework MCP-client snippets in §3 come from those frameworks' standard MCP APIs and have not been tested against mcp.serpapi.com.
