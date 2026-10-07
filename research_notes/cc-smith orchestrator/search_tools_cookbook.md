# serpapi-search-tools: tools, cookbook, extension, and how they map to cc-smith

Researched 2026-10-06. Sources:
- The docs site [serpapi.github.io/serpapi-search-tools-python](https://serpapi.github.io/serpapi-search-tools-python/): user guide, cookbook, SDK examples, reference, [changelog](https://serpapi.github.io/serpapi-search-tools-python/changelog.html), [skills page](https://serpapi.github.io/serpapi-search-tools-python/skills.html), [llms.txt](https://serpapi.github.io/serpapi-search-tools-python/llms.txt).
- A clone of [github.com/serpapi/serpapi-search-tools-python](https://github.com/serpapi/serpapi-search-tools-python) (HEAD `6051ec2`, 2026-09-09; PyPI **1.0.0**).
- Shallow clones of related repos in the SerpApi org.

**Verification.** The custom-tool and client sketches in §3 ran in a venv (Python 3.12) with these packages: `serpapi-search-tools 1.0.0`, `serpapi 1.1.2`, `pydantic-ai-slim 2.54`, `openai-agents 0.23.1`, `langchain-core 1.6.7`, `claude-agent-sdk 0.2.163`. A fake client was used, so no SerpApi credits were spent and no LLM ran.

This file builds on `serpapi_tool_surface.md` §4, which already covered the exports, the basic signature and the provider list. Below, **(verified)** means I executed it. **(inference)** means my own judgement.

Path shorthand used below:
- `src/…` means `https://github.com/serpapi/serpapi-search-tools-python/blob/main/src/serpapi_search_tools/…`
- `docs:` means `https://serpapi.github.io/serpapi-search-tools-python/…`

---

## 1. Tools: exact signatures, parameters and engines

### 1.1 Shared constructor contract

Every constructor is keyword-only and returns one native tool for the chosen SDK.

```python
<tool>(*, provider="auto", include_examples=True, api_key=None, client=None,
       default_params=None, timeout=None, mode=SearchResultMode.COMPACT,
       response_format=SearchResultFormat.MARKDOWN, result_limit=<tool default>, name="<tool>")
# web_search / shopping_search add: allowed_engines=None, default_engine=None
```

Sources: `src/_query_tools.py`, `src/_travel_tools.py`, [docs: configuration](https://serpapi.github.io/serpapi-search-tools-python/user-guide/configuration.html).

**`provider`**
- Accepted values: `auto | function | langchain | langgraph | crewai | llamaindex | openai-agents | claude-agent-sdk | pydantic-ai | microsoft-agent-framework | autogen | haystack | semantic-kernel | agno | smolagents | google-adk`.
- Many aliases are accepted, e.g. `claude_agent_sdk`, `maf` and `adk` (`src/_providers.py`).
- `auto` detects SDKs by distribution name. If more than one SDK family is installed, it raises `RuntimeError`. LangChain and LangGraph count as one family.
- **Gotcha (verified):** auto-detection looks for the `pydantic-ai` distribution, so `pydantic-ai-slim` is **not** detected. In a venv with openai-agents, langchain-core and claude-agent-sdk, `auto` raised "Multiple supported agent SDKs are installed…".
- → **cc-smith must always pass `provider=` explicitly.**

**`default_params`**
- Application-fixed SerpApi params that the model never sees.
- They cannot set `api_key`, `async`, `engine` or `output`; these raise `ValueError` (`_RESERVED_DEFAULT_PARAMS`, `src/_shared.py`).
- Merge order in `SearchRuntime.execute`:
  1. Start from the defaults.
  2. Apply the typed (model) params on top. A typed value of `None` **deletes** the key.
  3. Force `engine` and run the validator.
  4. Add `output=md` when the format is Markdown.
- **Gotcha (verified):** `maps_search` always sends `location=None, z=None, nearby=None` as typed params. A `default_params={"location": "Mumbai"}` is therefore **silently dropped** unless the model supplies `location`. Travel tools behave the same way for the fields they type (`children_ages`, `type`, `arrival_id`, …).
- `json_restrictor`, `no_cache`, `gl`, `hl`, `google_domain`, `location`, `currency` and so on are all allowed in `default_params`.
- A multi-engine tool sends the **same** defaults to every allowed engine. The docs advise making one named instance per engine or locale ([docs: configuration](https://serpapi.github.io/serpapi-search-tools-python/user-guide/configuration.html)).

**`allowed_engines` and `default_engine`**
- Only `web_search` and `shopping_search` have these.
- They build a per-instance `Enum`, so the schema `enum` contains only the allowed values.
- `default_engine` must be inside the allowed set. When omitted, it falls back to the preferred engine: `google_light` for web, `google_shopping` for shopping.
- Passing a vertical engine raises an error with a hint, e.g. "Use news_search() instead".

**`client`**
- Any object with a synchronous `search(params: dict) -> Mapping | str`.
- In Markdown mode it **must return `str`**; in JSON mode it must return a `Mapping`. Otherwise `TypeError`.
- When a client is supplied, no key is read and no built-in client is created.
- The built-in client is a thread-local `serpapi.Client(api_key, timeout)`.
- **Error handling (verified):**
  - Built-in client failures become `SerpApiSearchError("SerpApi request failed: <provider error, key redacted>")`.
  - **Any exception from a custom client is collapsed** to `SerpApiSearchError("Custom search client request failed.")`; the original message is lost (`raise … from None`).

**`response_format`**
- `MARKDOWN` is the default since v1.0.0. The changelog says it uses "40-50% fewer tokens on average" ([changelog](https://serpapi.github.io/serpapi-search-tools-python/changelog.html)).
- `JSON` returns a compact JSON string with separators `(",", ":")`.
- The format is fixed at construction; the model cannot change it.

**`mode`**
- `COMPACT` (the default) keeps only the per-engine result families listed in `_COMPACT_RESULT_KEYS_BY_ENGINE`.
- In Markdown, compact keeps only the matching `##` headings plus any `## Error` section, and strips the front matter.
- In JSON, compact keeps `error` plus the result families. If none is present, it returns `{"search_information":…, "search_metadata":{"status"}, "no_results":true}`.
- Compact also drops noisy per-item keys, e.g. shopping `immersive_product_page_token`.
- `FULL` keeps everything (subject to `result_limit`).

**`result_limit`**
- A post-hoc trim of each top-level result list or Markdown table. It does **not** change the SerpApi request or credit cost.
- `None` keeps everything.
- Nested lists (flight legs, offers) and the single `place_results` object are not trimmed.

**`include_examples`** appends "Example: query='coffee'…" to the description.

**`name`** must match `^[A-Za-z0-9_-]{1,64}$`.

### 1.2 Per-tool table

Sources: `src/_query_tools.py`, `src/_travel_tools.py`, `src/__init__.py::_SUPPORTED_ENGINES_BY_TOOL`, `src/_shared.py::_COMPACT_RESULT_KEYS_BY_ENGINE`, and the per-tool docs pages `docs:user-guide/<tool>.html`.

| Tool | Engine(s) | Model-visible inputs (schema, `additionalProperties:false`) | Default `result_limit` | Compact keeps | Built-in validation |
|---|---|---|---|---|---|
| `web_search` | `google`, `google_light`(default), `bing`, `yahoo`, `duckduckgo` | `query` (req), `engine` enum. `query` maps to `q`, or `p` for Yahoo | 10 | **google:** answer_box, knowledge_graph, **ai_overview**, organic_results. **google_light:** answer_box, knowledge_graph, organic_results, related_questions, related_searches, top_stories. **bing:** + copilot_answer. **yahoo:** answer_box, knowledge_graph, organic_results. **ddg:** knowledge_graph, organic_results | google: `location` vs `uule/lat/lon`, lat+lon together. light: `location`+`uule`. ddg: `search_assist`+`m`, query ≤500 chars |
| `news_search` | `google_news` (query mode) | `query` | 20 | news_results | rejects `topic_token`, `kgmid`, `publication_token`, `section_token`, `story_token`, `so` even when they come from defaults |
| `maps_search` | `google_maps`, `type=search` | `query`, `location?`, `zoom` 3–30 (default 14, sent as `z` only when location is set), `nearby` (requires location) | 10 | local_results, place_results (kept whole) | rejects `place_id`/`data_cid` ("require a separate place-details tool"), `location`+`ll/lat/lon`, `open_state`+`open_on_day` |
| `images_search` | `google_images` | `query` | 50 | images_results | `location`+`uule`; relative period vs `start_date/end_date` |
| `shopping_search` | `google_shopping`(default), `amazon`, `walmart`, `ebay` | `query` (→ `q`/`k`/`query`/`_nkw`), `engine` | 60 | google_shopping: shopping_results. Others: organic_results | `location`+`uule` (gshopping); amazon `node` |
| `videos_search` | `youtube` | `query` (→ `search_query`) | 10 | video, shorts, channel, playlist, movie, category results | — |
| `hotels_search` | `google_hotels` | `query`, `check_in_date`, `check_out_date` (ISO, out>in), `adults`=2, `children`=0, `children_ages[]` (1–17, one per child) | 20 | properties | date and occupancy rules |
| `flights_search` | `google_flights` | `departure_id`, `arrival_id` (IATA uppercased, or kgmid), `outbound_date`, `return_date?` (selects round trip: `type`=1, else 2), `travel_class` enum (economy…first → 1–4), `adults`=1, `children`, `infants_in_seat`, `infants_on_lap` | 10 per list | best_flights, other_flights | passenger and filter rules |
| `travel_explore_search` | `google_travel_explore` | `departure_id` (req), `arrival_id?` or `arrival_area_id?`, dates, class, passengers | 50 | destinations | `travel_mode`+`interest` |

**Exceptions and enums.** `SerpApiSearchError` (a RuntimeError). Enums: `WebSearchEngine`, `ShoppingSearchEngine`, `TravelClass`, `SearchResultMode`, `SearchResultFormat`. The API reference has one page per public symbol: [docs: reference](https://serpapi.github.io/serpapi-search-tools-python/reference/index.html).

### 1.3 What each adapter returns

Source: `src/_adapters.py` (verified for the four cc-smith SDKs).

| Provider | Native object | Invocation | Validation-error behaviour |
|---|---|---|---|
| `pydantic-ai` | `pydantic_ai.Tool` (sync function with `Annotated` + `Field` annotations) | Pydantic AI runs sync tools in a thread | `ValueError` and `SerpApiSearchError` become **`ModelRetry`**, so the model sees the message and retries (verified) |
| `openai-agents` | `agents.FunctionTool(params_json_schema=…, strict_json_schema=False)` | async `on_invoke_tool` → `asyncio.to_thread` | Pydantic or `ValueError` problems come back to the model as the string `{"error":"Invalid tool arguments.","details":…}` (verified). `SerpApiSearchError` is **not** caught there and propagates to the Runner's failure handling |
| `langchain` / `langgraph` | `StructuredTool.from_function(args_schema=<pydantic model, extra=forbid>)` | `.invoke`, or `ToolNode` (whose `handle_tool_errors` turns exceptions into ToolMessages) | — |
| `claude-agent-sdk` | `SdkMcpTool` via `claude_agent_sdk.tool(name, desc, input_schema, annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))`. The handler returns `{"content":[{"type":"text","text":…}]}` | `asyncio.to_thread` | The handler re-raises (verified), but `create_sdk_mcp_server` reports handler exceptions to Claude as error results (SDK docstring) |
| others | crewai `BaseTool`, llamaindex `FunctionTool`, MAF `FunctionTool`, autogen `FunctionTool`, haystack `Tool`, SK `kernel_function`, agno `Function(strict=False)`, smolagents `Tool`, ADK `FunctionTool` subclass | | |

---

## 2. Cookbook and examples, and how each maps to cc-smith

### 2.1 Cookbook

All 14 cookbook entries write a Markdown report to `cookbook-output/`. They use the default compact Markdown and never parse JSON. The prompt is overridable via the `COOKBOOK_PROMPT` env var. Sources: [docs: cookbook index](https://serpapi.github.io/serpapi-search-tools-python/docs/cookbook/index.html) and `cookbook/<sdk>/main.py`.

Every recipe uses `web_search(allowed_engines=["google_light","bing"], result_limit=5)` and `news_search(default_params={"hl":"en","gl":"us"}, result_limit=5)` where those tools appear. The shared lesson: **small result_limit, a narrowed engine enum, and locale in defaults.**

| # | SDK, file | What it builds | Shape | Tools | Notable pattern | cc-smith adaptation (concrete) |
|---|---|---|---|---|---|---|
| 1 | LangChain `cookbook/langchain/main.py` | Deep market-research brief (after "Deep Agents from scratch") | Single agent, `create_agent` | web + news, `include_examples=False` | System prompt: "make a short plan before searching, separate current reporting from durable background, never present an unsupported claim as fact". Uses the xAI OpenAI-compatible `base_url` | **Launch Radar weekly brief.** Role: "Indian credit-card launch analyst". Tools: `news_search(provider="langchain", default_params={"gl":"in","hl":"en"}, result_limit=5, name="india_card_news")` + `web_search(allowed_engines=["google"], default_params={"google_domain":"google.co.in","gl":"in","hl":"en"})` (google keeps knowledge_graph/ai_overview). Swap `ChatOpenAI(base_url=…)` for `ChatOllama` |
| 2 | LangGraph `cookbook/langgraph/main.py` | Product-launch intelligence graph (after the Agentic RAG notebook) | Single model node ↔ `ToolNode` loop, `MessagesState`, `tools_condition` | web, news, shopping | Explicit graph with one tool node for all tools | **Launch Radar per-card pipeline.** Keep the loop for *exploration* only, then add deterministic nodes: `dedupe_news` → `ai_mode_extract` (custom tool §3) → `diff_vs_profile` → `interrupt()` review → `upsert_profile`. Shopping is irrelevant to cc-smith; replace it with `ai_mode_search` |
| 3 | CrewAI `cookbook/crewai/main.py` | Collaborative trip planner | **Multi-agent**, sequential crew: researcher (tools, `max_iter=7`) → editor (no tools, `context=[research_task]`) | flights, hotels, maps | Researcher/editor split: the editor "never invents prices" | **Card Finder.** Researcher ("card evidence researcher": `ai_mode_search`, `news_search`) collects fees, caps and recent devaluations for 5–8 candidate cards. The editor has **no search** and ranks via the deterministic `score_cards()` tool and the profile store. Tool budget = `max_iter` |
| 4 | LlamaIndex `cookbook/llamaindex/main.py` | Remote-work destination brief | Single `FunctionAgent`, `initial_tool_choice="required"` | travel_explore, web, maps | Forces a first tool call. Custom `OpenAICompatible` LLM subclass to run non-OpenAI models | **Checkout Advisor offline merchant resolver** (batch, not the 1 s path): `maps_search(default_params={"gl":"in","hl":"en"})` + custom `place_details` → `type_ids` → category table. Forced tool choice is useful with small local models |
| 5 | OpenAI Agents `cookbook/openai-agents/main.py` | Managed research report (after `research_bot`) | **Multi-agent, agents-as-tools**: editor owns the answer and calls `researcher.as_tool("research_with_serpapi")`; `max_turns=10` | web, news | The researcher must return URLs and label uncertainty | **Card Coach → Renewal Review.** Editor = "renewal reviewer" with local tools (`get_profile`, `get_user_spend`, `compute_net_value`). The researcher-as-tool has `news_search` (India) + `ai_mode_search` and answers "what changed for <card> since <last renewal date>?" Only the researcher spends credits |
| 6 | Claude Agent SDK `cookbook/claude-agent-sdk/main.py` | Source-verification memo | Single agent; in-process MCP via `create_sdk_mcp_server`; `allowed_tools=["mcp__serpapi__web_search","mcp__serpapi__news_search"]`; `max_turns=16` | web, news | Prompt: "search before concluding, prefer primary sources, expose conflicting evidence" → confirmed / overstated / differences / URLs | **Card Profile store verification.** For each extracted field (fee, cap, milestone), verify it against issuer pages: confirmed, conflicting, or stale. Add a `PreToolUse` hook as a credit guard (§3.4) |
| 7 | Pydantic AI `cookbook/pydantic-ai/main.py` | Visual location scout | Single agent | images (`safe=active`), maps, web | "Do not infer access from an image alone" (cross-verify) | **Chat agent** ("which card should I use / what is this card?"). Pydantic AI + `web_search` + custom `lens_search` to identify a card from a photo, then `get_profile`. The same "don't infer from one surface" rule applies to Lens |
| 8 | Microsoft Agent Framework `cookbook/microsoft-agent-framework/main.py` | Technology due-diligence memo | Single agent | news (limit 8), web (6) | Discover via news, verify via web; separate verified facts / vendor claims / inference | **Cap Watch.** Discover cap or devaluation news, verify on the issuer's MITC page, and label each item "issuer-confirmed / media-reported / inferred" |
| 9 | AutoGen `cookbook/autogen/main.py` | Company intelligence memo | Single `AssistantAgent`, `reflect_on_tool_use=True`, `max_tool_iterations=8` | web, news | Reflection pass after tools; "do not invent financial figures" | **Launch Radar issuer memo** (per bank: new cards, offers, partner changes). `max_tool_iterations` acts as a hard credit cap |
| 10 | Haystack `cookbook/haystack/main.py` | Weekly industry newsletter | Single `Agent`, `max_agent_steps=8` | news (7), web (5) | Deduplicate syndicated stories | **Launch Radar user digest.** Dedupe rewritten press releases (one launch → 10 articles) |
| 11 | Semantic Kernel `cookbook/semantic-kernel/main.py` | Plan-and-execute competitor brief | Single kernel prompt, `FunctionChoiceBehavior.Auto()` | web, news (as an SK plugin `"serpapi"`) | Plan → search each open question → write | **Card Finder "compare these 3 cards" brief** |
| 12 | Agno `cookbook/agno/main.py` | Market research report | Single agent, `tool_call_limit=10` | web, news, shopping | "Use the most specific tool for each question" | **Card Finder category scan** ("best fuel / travel cards"). `tool_call_limit` acts as the credit cap |
| 13 | smolagents `cookbook/smolagents/main.py` | Purchase research | Single `ToolCallingAgent`, `max_steps=8` | shopping, images, videos | Three evidence surfaces for one decision | **Card Finder reviewer opinions.** `videos_search(default_params={"gl":"in","hl":"en"})` + custom `video_transcript` to summarise Indian YouTube card reviews (treat them as opinion, not terms) |
| 14 | Google ADK `cookbook/google-adk/main.py` | Retail location strategy | Single agent, `InMemorySessionService`; retries 503s with backoff (`MAX_ATTEMPTS=3`) | maps, web, news | Consistent comparison across candidates plus transient-error retry | **Eligibility Path.** Compare paths (FD-backed, card-to-card, salary account) consistently. Reuse the retry wrapper for Gemini or local-model hiccups |

### 2.2 `examples/`

Sources: [`examples/README.md`](https://github.com/serpapi/serpapi-search-tools-python/blob/main/examples/README.md) and [docs: examples](https://serpapi.github.io/serpapi-search-tools-python/user-guide/examples.html).

- **`direct_*.py`** run with `provider="function"` and no LLM. They are good templates for cc-smith's **deterministic pipelines**.
  - `direct_multi_search.py`: web, news, maps and shopping in JSON, reduced to titles.
  - `direct_marketplace_comparison.py`: normalises four response shapes.
  - `direct_regioned_search.py`: two named tools, `web_search_us` and `web_search_de`, with different `default_params`. This is the pattern for `india_web` vs a global tool.
  - `direct_cached_search.py`: an in-memory `CachingClient` keyed on `json.dumps(params minus api_key, sort_keys=True)`. It is JSON-only; see §3.3 for an md-safe version.
  - `direct_travel.py` and `direct_search.py` (md vs JSON).
- **`_logging_client.py`**: `LoggingClient` wraps `serpapi.Client`, logs the params without `api_key`, and logs `{engine, status, result_keys}` or the md character count. Used by `openai_agents_travel_planner.py` (three typed travel tools, with instructions dictating the tool order) and `claude_agent_sdk_sonnet.py`.
- One-file agent examples exist for all 14 SDKs (`*_openai.py`, `*_grok.py`, `google_adk_gemini.py`, `claude_agent_sdk_sonnet.py`). Default models: `gpt-5.4-mini`, `claude-sonnet-5`, `gemini-flash-lite-latest`, `grok-4.5`.

### 2.3 Related SerpApi org repos and gallery entries

- **[serpapi/import_bengaluru](https://github.com/serpapi/import_bengaluru)**. This is the talk kit for the 6 Sep 2026 event, which promoted the **SerpApi India Hackathon** (serpapi.com/indiahackathon).
  - `demo_scripts/` holds seven Pydantic AI demos served with `agent.to_web()` + uvicorn:
    - `4_web_search.py`: `web_search(provider="pydantic-ai", api_key=…)`.
    - `5_mcp_search.py` and `6_mcp_shopping.py`: `MCPToolset("https://mcp.serpapi.com/mcp", auth=KEY)`, with a `gl=in` shopping prompt.
    - `7_skills_travel.py`: `pydantic_ai_harness` Skills + read-only FileSystem + Shell running the `serpapi` CLI, with `currency=INR`.
  - **This is the closest thing to a hackathon starter kit.** cc-smith's chat agent can start from demo 4 plus `to_web()` for a free UI.
- **[serpapi/local-llm-web-search](https://github.com/serpapi/local-llm-web-search)** (TS, LM Studio). Seven named tools, each sending a **fixed `json_restrictor`**. It reports "around 99 percent" payload reduction (`src/server/restrictors.ts`, which documents the restrictor syntax and that it is whitelist-only with no renaming).
  - It keeps `search_metadata.<engine>_url` for a Sources panel, then strips it before the model sees the result.
  - It recommends **Qwen 3.5 9B**: "models below 7B are unreliable with `tool_choice: "auto"`".
  - It warns that LM Studio's default 4096-token context is too small and should be set explicitly.
- **[serpapi/babyagent](https://github.com/serpapi/babyagent)**. A teaching SDK with an `OllamaModel` provider; examples `3c_shopping_assistant_mcp_ollama.py` and `2b_tool_calling.py` use `gemma4:e4b`.
- **[serpapi/claude-agent-with-web-search](https://github.com/serpapi/claude-agent-with-web-search)**. Hand-written `@tool` + `create_sdk_mcp_server`, MCP, skills, and a multi-turn session travel agent. It is a reference for writing a raw Claude SDK tool without the package.
- **[serpapi/competitive-intelligence-agent](https://github.com/serpapi/competitive-intelligence-agent)**. OpenAI + raw `google`/`google_news`/`google_jobs` functions + optional HubSpot. A single agent with a tool loop.
- **[serpapi/serpapi-hermes-plugin](https://github.com/serpapi/serpapi-hermes-plugin)**. Dedicated Maps, News and Shopping tools that use **`google_news_light` and `google_shopping_light`**. Those are faster engines (about 1.4 s vs about 5 s per the metrics in `serpapi_tool_surface.md`) that serpapi-search-tools does not expose.
- **[BuiltWithSerpApi gallery](https://serpapi.github.io/BuiltWithSerpApi/)** (data in `src/_data/projects.json`, 190 entries). Agent entries relevant to cc-smith:
  - **signalwatch** ([angpt/signalwatch](https://github.com/angpt/signalwatch)): scheduled Google Search + News keyword monitor, SQLite URL dedupe, **local LLM (Ollama)** digest with sentiment and suggested action. → the template for **Launch Radar / Cap Watch** jobs.
  - **DriftWatch** ([faisalshariff123/DriftWatch](https://github.com/faisalshariff123/DriftWatch)): news vs historical baseline → narrative drift. → Cap Watch "change detected" logic.
  - **AI Travel Planner** ([sagarsrao/ai-travel-agent](https://github.com/sagarsrao/ai-travel-agent)): Agno, two agents (researcher → planner), **Ollama llama3.2**.
  - **FlightDeals Tracker** ([akhil99558/FlightDeals_Test](https://github.com/akhil99558/FlightDeals_Test)): rule-based scoring + local Ollama.
  - **TruthStream** ([himanshusalve16/…](https://github.com/himanshusalve16/TruthStream-Multi-Agent-Fact-Checking-Pipeline)): multi-agent claim extraction → verification.
  - **Chancery, Campaign Weather**: Google Ads Transparency usage.
  - **RentRadar**: an India app.
  - Several APIDays-hackathon "evidence gate + human approval" agents, which match the cc-smith review queue.

---

## 3. Extending the package

### 3.1 How to write a custom tool in the same style

The public API exposes only constructors. The building blocks live in private modules:
- `serpapi_search_tools._shared`: `SearchRuntime`, `ToolDefinition`, `object_schema`, `require_nonempty`, `SearchResultMode`, `SearchResultFormat`.
- `serpapi_search_tools._adapters`: `as_provider_tool`.

They work (verified), but they are **underscore modules, so pin `serpapi-search-tools==1.0.0`** and keep a contract test.

Recipe for each tool:
1. Build a `SearchRuntime`.
2. Write a typed inner function that calls `runtime.execute(engine=…, typed_params=…, validator=…)`.
3. Set `fn.__annotations__` to real types (the adapters call `get_type_hints`).
4. Build a strict schema with `object_schema(...)`.
5. Return `as_provider_tool(ToolDefinition(fn, name, desc, schema), provider)`.

**Important (verified):** for engines the package doesn't know, `COMPACT`+JSON returns `{"search_metadata":{"status":"Success"},"no_results":true}`, because there is no compact profile. COMPACT+Markdown returns the whole body. So use **`mode=FULL, response_format=JSON, result_limit=None` and trim server-side with `json_restrictor`** in `default_params`.

The full verified file is a temporary scratchpad copy at `/private/tmp/claude-501/-Users-A3119363-Documents-Projects/13f3c928-647d-4e4f-a496-22b1e946ed0d/scratchpad/cc_tools.py`; it is reproduced in condensed form here. Engine params come from `serpapi.com/<engine>.md`: [google-ai-mode-api](https://serpapi.com/google-ai-mode-api), [google-ads-transparency-center-api](https://serpapi.com/google-ads-transparency-center-api), [google-lens-api](https://serpapi.com/google-lens-api), [google-maps-api](https://serpapi.com/google-maps-api), and the YouTube transcript docs (`engine=youtube_video_transcript&v=<id>&language_code=en&type=asr`, per [youtube-video-transcript-scraper](https://github.com/serpapi/youtube-video-transcript-scraper)).

```python
from serpapi_search_tools._adapters import as_provider_tool
from serpapi_search_tools._shared import (SearchResultFormat, SearchResultMode, SearchRuntime,
                                          ToolDefinition, object_schema, require_nonempty)
INDIA = {"gl": "in", "hl": "en"}

def _runtime(*, client, api_key, default_params, timeout):
    return SearchRuntime(api_key=api_key, client=client, default_params=default_params,
                         timeout=timeout, mode=SearchResultMode.FULL,
                         response_format=SearchResultFormat.JSON, result_limit=None)

AI_MODE_RESTRICTOR = ("text_blocks,reconstructed_markdown,references[].{index,title,link,source,snippet},"
                      "subsequent_request_token,error,search_metadata.{id,status}")

def ai_mode_search(*, provider="auto", client=None, api_key=None, default_params=None,
                   timeout=None, name="ai_mode_search"):
    defaults = {**INDIA, "continuable": "true", "json_restrictor": AI_MODE_RESTRICTOR,
                **(default_params or {})}
    rt = _runtime(client=client, api_key=api_key, default_params=defaults, timeout=timeout)
    def ai_mode_tool(query: str, follow_up_token: str | None = None) -> str:
        return rt.execute(engine="google_ai_mode",
                          typed_params={"q": query, "subsequent_request_token": follow_up_token},
                          validator=lambda p: require_nonempty(p, "q", label="query"))
    ai_mode_tool.__annotations__ = {"query": str, "follow_up_token": str | None, "return": str}
    schema = object_schema({
        "query": {"type": "string", "description": "Question for Google AI Mode."},
        "follow_up_token": {"type": "string",
            "description": "subsequent_request_token from a previous ai_mode_search result."}},
        required=["query"])
    return as_provider_tool(ToolDefinition(ai_mode_tool, name,
        "Ask Google AI Mode (India); answer with numbered references. Cite references[].link.",
        schema), provider)
```

The other custom tools use the same skeleton (all verified with `function`, `pydantic-ai`, `openai-agents`, `langgraph` and `claude-agent-sdk`):

| Tool | Engine and typed params | Model inputs | `json_restrictor` default | cc-smith use |
|---|---|---|---|---|
| `place_details` | `google_maps`, `{"place_id": id}` (no `type` needed) | `place_id` | `place_results.{title,place_id,data_cid,type,types,type_ids,address,gps_coordinates,website},error` | Checkout Advisor merchant → category (offline, cache for 1 year) |
| `ads_transparency_search` | `google_ads_transparency_center`, `{"advertiser_id": id}` if it starts with `AR`, else `{"text": domain}`, plus `start_date` YYYYMMDD | `advertiser_or_domain`, `start_date?` | `ad_creatives[0:20].{advertiser,format,link,first_shown,last_shown,total_days_shown},error`; also `num=20`. Add `region` from the [regions list](https://serpapi.com/google-ads-transparency-center-regions) (the India code is not verified here) | Launch Radar: a new issuer ad campaign is an early launch or offer signal |
| `video_transcript` | `youtube_video_transcript`, `{"v": id}`, `language_code=en` | `video_id` | `transcript[].{start_ms,end_ms,snippet},error` (field names inferred from the scraper repo; check against a live response) | Card Finder reviewer sentiment |
| `lens_search` | `google_lens`, `{"url": u, "type": t}`, `country=in` | `image_url`, `search_type` enum (default `visual_matches`) | `visual_matches[0:10].{title,link,source},error` | Chat agent: "what card is this?" |

Notes:
- For AI Mode multi-turn, keep the same `gl/hl/location` on follow-ups. The defaults guarantee this.
- `output=md` strips `subsequent_request_token`, so the JSON format is mandatory for AI Mode (see `serpapi_tool_surface.md` §1.5).

### 3.2 Alternative: no private imports

Write a plain typed function that calls `serpapi.Client(...).search({...})`, then register it natively in each SDK:
- `Agent(tools=[fn])` (Pydantic AI)
- `@function_tool` (OpenAI Agents)
- `@tool` (LangChain)
- `@tool(name, desc, schema)` (Claude SDK)

You lose the multi-SDK adapter but gain stability. **(inference)** For cc-smith, which uses one or two SDKs, this is the lower-risk option for the AI Mode extractor. That extractor should anyway live in a deterministic pipeline, not be model-chosen.

### 3.3 Caching + credit-budget client

Pass the same object as `client=` to every tool (verified with md and JSON tools):

```python
class BudgetedCachingClient:
    TTL_BY_ENGINE = {"google_maps": 365*86400, "google_ai_mode": 14*86400, "google": 7*86400,
                     "google_light": 7*86400, "google_news": 6*3600, "youtube_video_transcript": 365*86400}
    def __init__(self, api_key, db_path="serpapi_cache.sqlite", monthly_budget=250, reserve=25, upstream=None):
        self._up = upstream or serpapi.Client(api_key=api_key, timeout=30)
        self._budget = monthly_budget - reserve
        self._db = sqlite3.connect(db_path, check_same_thread=False)   # tools run in worker threads
        ...  # tables: cache(k, ts, body), spend(month, ts, engine, k)
    def search(self, params):
        is_md = params.get("output") == "md"           # package adds output=md in Markdown mode
        k = sha256(json.dumps({k: v for k, v in params.items() if k != "api_key"}, sort_keys=True))
        if fresh cache row: return body if is_md else json.loads(body)
        if spent(this_month) >= self._budget:          # never raise: custom-client exceptions are
            msg = "SerpApi monthly credit budget reached; answer from stored card profiles."
            return f"## Error\n\n{msg}\n" if is_md else {"error": msg}   # compact keeps "## Error"/"error"
        result = self._up.search(params)               # SerpResults (UserDict) or str for md
        record spend; cache unless JSON has "error"; return result if str else dict(result)
```

Why it is shaped this way:
1. **Never raise from a custom client.** The package rewrites any exception to "Custom search client request failed." (verified). Return an error payload instead. Compact mode preserves `## Error` sections and the `error` key, so the model reads the reason.
2. **Handle both return types.** The client sees `output=md` and must return `str`; in JSON it must return a Mapping.
3. **The cache key includes `json_restrictor` and `output`,** so keep them constant per tool.
4. **SerpApi's own cache.** Identical requests within 1 h are free and don't count against the quota. That is the documented `no_cache` behaviour (e.g. [google-lens-api](https://serpapi.com/google-lens-api)). So keep params canonical, and do not set `no_cache`.
5. **Optional sync with the account.** Use `serpapi.Client.account()` (the Account API; free per prior notes) to sync `this_month_usage` / `plan_searches_left` at startup, instead of trusting only the local counter.
6. **Thread safety.** The OpenAI Agents and Claude adapters call the sync tool via `asyncio.to_thread`, so use `check_same_thread=False` + a lock, or one connection per thread.

### 3.4 Per-framework wiring

All four were verified to construct and invoke with a fake client. Model calls were not run.

```python
# common
from serpapi_search_tools import news_search, web_search, maps_search
from cc_tools import ai_mode_search, place_details, BudgetedCachingClient
cc = BudgetedCachingClient(os.environ["SERPAPI_API_KEY"], monthly_budget=250, reserve=25)
IN = {"gl": "in", "hl": "en"}
```

**Pydantic AI.** The tool is a `pydantic_ai.Tool`; `ValueError` and `SerpApiSearchError` become `ModelRetry`.

```python
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider          # import verified
model = OpenAIChatModel("qwen3:8b", provider=OllamaProvider(base_url="http://localhost:11434/v1"))
chat = Agent(model, instructions="You are cc-smith's card assistant…",
             tools=[news_search(provider="pydantic-ai", client=cc, default_params=IN, result_limit=5),
                    ai_mode_search(provider="pydantic-ai", client=cc)])
# chat.to_web() gives the import_bengaluru-style UI for free
```

**OpenAI Agents SDK.** `FunctionTool` with `strict_json_schema=False`; bad arguments come back to the model as an error string.

```python
from agents import Agent, Runner, OpenAIChatCompletionsModel, set_tracing_disabled
from openai import AsyncOpenAI
local = OpenAIChatCompletionsModel(model="qwen3:8b",
          openai_client=AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama"))
researcher = Agent(name="card-researcher", model=local,
    instructions="Return compact notes with URLs; label uncertainty.",
    tools=[news_search(provider="openai-agents", client=cc, default_params=IN, result_limit=5),
           ai_mode_search(provider="openai-agents", client=cc)])
reviewer = Agent(name="renewal-reviewer", model=local, instructions="Own the verdict…",
    tools=[researcher.as_tool(tool_name="research_card_changes",
                              tool_description="What changed for a card recently?"),
           get_profile, get_user_spend])                         # your @function_tool's
await Runner.run(reviewer, "Should I renew my HDFC Regalia Gold?", max_turns=8)
```

**LangGraph.** `StructuredTool`; `ToolNode` turns tool exceptions into ToolMessages.

```python
from langchain_ollama import ChatOllama
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
tools = [news_search(provider="langgraph", client=cc, default_params=IN, result_limit=5),
         ai_mode_search(provider="langgraph", client=cc)]
llm = ChatOllama(model="qwen3:8b", num_ctx=16384).bind_tools(tools)
g = StateGraph(MessagesState)
g.add_node("research", lambda s: {"messages": [llm.invoke(s["messages"])]})
g.add_node("tools", ToolNode(tools))
g.add_edge(START, "research"); g.add_conditional_edges("research", tools_condition); g.add_edge("tools", "research")
# Launch Radar: wrap this as one node inside a larger StateGraph with dedupe/diff/interrupt nodes
```

**Claude Agent SDK.** Uses `create_sdk_mcp_server`; tool names become `mcp__<server>__<tool>`.

```python
from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, query, HookMatcher
server = create_sdk_mcp_server(name="cc", version="1.0.0", tools=[
    news_search(provider="claude-agent-sdk", client=cc, default_params=IN, result_limit=5),
    ai_mode_search(provider="claude-agent-sdk", client=cc),
    place_details(provider="claude-agent-sdk", client=cc)])     # returns {"type":"sdk","name","instance"}
opts = ClaudeAgentOptions(model="claude-sonnet-5", mcp_servers={"cc": server},
    allowed_tools=["mcp__cc__news_search", "mcp__cc__ai_mode_search", "mcp__cc__place_details"],
    max_turns=12, system_prompt="Source-verification analyst for Indian card terms…")
# optional: hooks={"PreToolUse": [HookMatcher(matcher="mcp__cc__.*", hooks=[budget_guard])]}
async for m in query(prompt="Verify the HDFC Infinia profile fields…", options=opts): ...
```

The handler's exceptions are reported to Claude as error results (`create_sdk_mcp_server` docstring). The tool annotations are `readOnlyHint=True` and `openWorldHint=True`.

---

## 4. Gaps, limitations, and local models

### Coverage gaps

- **No AI Mode, AI Overview, Brave AI Mode, Lens, Ads Transparency, YouTube transcript or video, Maps place details, reviews or directions, Google Local, Finance, Trends or Jobs.**
- **No "light" variants:** `google_news_light`, `google_shopping_light` and `google_images_light` (the Hermes plugin uses them). Web has `google_light`.
- No Account, Locations or Archive helpers.
- Google News token modes are explicitly refused.

### Behaviour gaps

- **Provenance loss.** Compact or Markdown drops `search_metadata.id`, `search_parameters`, tokens, `serpapi_*` links and pagination. Use FULL+JSON (or a logging client) wherever cc-smith must store per-field provenance.
- **`result_limit` is client-side only.** It saves tokens, not credits. Use engine params (`num`, or `m` for DuckDuckGo, `_ipg` for eBay) to fetch less.
- **No pagination input for the model.** There is no page or `start` field, so pagination can only be set in defaults.
- **Everything is synchronous.** Async SDKs use `asyncio.to_thread`. There are no async or batch calls and no `async=true` (reserved).
- **No built-in caching, retries, budget, rate limiting or telemetry.** All of it goes through `client=`. Custom-client error messages are swallowed (§3.3).
- **`default_params` can be silently overridden** by typed fields: maps `location`, travel fields.
- **The extension API is private** (`_shared`, `_adapters`) and the package is v1.0.0 "Beta" (`Development Status :: 4 - Beta` in `pyproject.toml`).
- **Auto-detection is fragile** in multi-SDK environments and misses `pydantic-ai-slim` (verified). Always pass `provider=`.
- **Inconsistent error surfacing across SDKs.** Pydantic AI → `ModelRetry`. OpenAI Agents → validation errors only. Claude SDK → error result. LangGraph → `ToolNode` error message.
- **Docs drift.** The repo's own AGENTS.md says Great Docs requires Python 3.11+. The docs examples are US-centric (`gl=us`, USD), with no India examples. `json_restrictor` is never mentioned in the package docs; it only appears in the local-LLM demo repo.
- **The docs site is built only on GitHub Releases**, so the docs track v1.0.0.

### Ollama / local models (cc-smith runs local Ollama behind a corporate proxy)

- The package is **model-agnostic**. It only produces tool objects; the SDK talks to the model.
- The repo's own opt-in suite tests against **OpenAI-compatible local servers** (LM Studio at `127.0.0.1:1234/v1`; preferred model `google/gemma-4-e2b`). Sources: `tests/openai_compat_llm_tests/conftest.py`, [AGENTS.md](https://github.com/serpapi/serpapi-search-tools-python/blob/main/AGENTS.md), `docs/development/testing.md`.
  - Ollama's `/v1` endpoint should work the same way (inference; not tested here).
- Helpful defaults for small models:
  - Markdown output (40–50% fewer tokens).
  - Strict small schemas (`additionalProperties:false`; one required `query`).
  - `strict_json_schema=False` on OpenAI Agents and `strict=False` on Agno, so models or servers without strict-mode support still work.
- Recommended settings for local models (inference, and per the local-llm-web-search README):
  - Expose ≤3 tools.
  - Set `allowed_engines` to a single engine so the enum is trivial.
  - Use `result_limit` 3–5 and keep `include_examples=True`.
  - Use ≥7–9B tool-calling models (Qwen 3.5 9B or Llama 3.1 8B; "models below 7B are unreliable").
  - **Set the context size explicitly**: `num_ctx` for Ollama. LM Studio's default 4096 is too small for multi-turn tool results.
  - For JSON tools, add a `json_restrictor` in `default_params` to cut payloads by up to about 99%.
  - Use LlamaIndex `initial_tool_choice="required"` or similar to force the first search.
- **The Claude Agent SDK needs Claude models.** It runs the Claude Code CLI. Pointing it at Ollama via `ANTHROPIC_BASE_URL` is unverified. Use Pydantic AI, OpenAI Agents or LangGraph for local runs.
- **Corporate proxy.** The built-in client is `serpapi.Client` → `requests.Session`, which honours `HTTPS_PROXY` and `REQUESTS_CA_BUNDLE` from the environment (`serpapi/http.py`). A custom `client=` can also set proxies explicitly.
  - Local Ollama traffic is localhost, so set `NO_PROXY=localhost,127.0.0.1`.

### Credit planning, 250 searches/month (inference)

- Every tool call that misses both caches costs one credit, whatever `result_limit` is.
- Each AI Mode follow-up turn is another search.
- Cap agent loops with the SDK knob in each recipe: Agents `max_turns`, Claude `max_turns`, CrewAI `max_iter`, Agno `tool_call_limit`, AutoGen `max_tool_iterations`, Haystack `max_agent_steps`, smolagents `max_steps`.
- Keep the budget client as the hard stop.
- **No search on the Checkout Advisor hot path:** use only cached `place_details` / `maps_search` results.
