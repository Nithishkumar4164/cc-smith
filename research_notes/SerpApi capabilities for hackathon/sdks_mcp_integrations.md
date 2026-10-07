# SerpApi Developer Tooling, SDKs, MCP and AI-Agent Integrations (as of Oct 2026)

## Official SDKs (Python new vs legacy, JavaScript, other languages)

### Takeaway
Use `pip install serpapi` (v1.1.2, import `serpapi`, `serpapi.Client(api_key=...).search({...})`). It is synchronous, and pagination is built into the result object (`next_page()` / `yield_pages()`). The legacy `google-search-results` package (last release 2.4.2, March 2023) also installs a module named `serpapi`, so the two packages clash. LangChain's `SerpAPIWrapper` still depends on the legacy one. For JS, use `npm install serpapi` (v2.2.1, `getJson`), which has no built-in pagination. Official repos also exist for Ruby, Go, PHP, Java, Rust, .NET, Swift and C++, plus a CLI.

### Cited Findings
**Python (new `serpapi` package)**
- Install with `pip install serpapi`. The README says: "this package is separate from the legacy `serpapi` module, which is available on PyPi as `google-search-results`. This package is maintained by SerpApi, and is the recommended way to access the SerpApi service from Python." — [serpapi-python README](https://github.com/serpapi/serpapi-python)
- Latest PyPI version is 1.1.2, requires_python `>=3.6`. For comparison, legacy `google-search-results` is at 2.4.2, uploaded 2023-03-10. — [PyPI serpapi](https://pypi.org/project/serpapi/), [PyPI google-search-results](https://pypi.org/project/google-search-results/)
- Basic usage: — [README](https://github.com/serpapi/serpapi-python)
  ```python
  import os, serpapi
  client = serpapi.Client(api_key=os.getenv("SERPAPI_KEY"), timeout=10)
  results = client.search({"engine": "google", "q": "coffee"})   # SerpResults (dict-like)
  ```
- `results` is a `SerpResults` object, "which acts just like a standard dictionary, with some convenient functions added on top." — [README](https://github.com/serpapi/serpapi-python)
- The source of `serpapi/models.py` shows `SerpResults(UserDict)` with methods `as_dict()`, `next_page_url`, `next_page()` and `yield_pages(max_pages=1_000)`. These are the pagination helpers. — [models.py](https://github.com/serpapi/serpapi-python/blob/master/serpapi/models.py)
- The source of `serpapi/core.py` shows `Client(HTTPClient)` with `__init__(self, *, api_key=None, timeout=None)` and the methods `search()`, `search_archive()`, `upload_image()`, `locations()` and `account()`. — [core.py](https://github.com/serpapi/serpapi-python/blob/master/serpapi/core.py)
- Errors: unsuccessful requests raise `serpapi.HTTPError` (with `.status_code`, e.g. 401 invalid key, 400 missing param, 429 throughput or credits exhausted) or `serpapi.TimeoutError`. — [README](https://github.com/serpapi/serpapi-python)
- Markdown output for LLMs: `client.search({..., "output": "md"})` returns a plain string that uses "roughly half the tokens of JSON on average". `output="html"` returns raw HTML. — [README](https://github.com/serpapi/serpapi-python)
- Docs are on Read the Docs: https://serpapi-python.readthedocs.io/en/latest/ — [README](https://github.com/serpapi/serpapi-python)
- Engine-specific query keys (an easy source of bugs): Yahoo `p`, YouTube `search_query`, Walmart/Naver `query`, eBay `_nkw`, Apple App Store `term`, Amazon `k`. — [README](https://github.com/serpapi/serpapi-python); [serpapi-mcp README](https://github.com/serpapi/serpapi-mcp)

**Legacy Python (`google-search-results`)**
- The legacy module is also imported as `serpapi`, for example `from serpapi import GoogleSearch`. LangChain's `SerpAPIWrapper` imports exactly that (`from serpapi import GoogleSearch`) and tells you to `pip install google-search-results`. — [langchain-community serpapi.py](https://github.com/langchain-ai/langchain-community/blob/main/libs/community/langchain_community/utilities/serpapi.py); [LangChain reference (GoogleJobs/Finance/Lens wrappers)](https://reference.langchain.com/python/langchain-community/utilities/google_jobs/GoogleJobsAPIWrapper)
- The legacy repo `google-search-results-python` still has the most stars in the org (757, against 175 for the new `serpapi-python`). — [GitHub API org listing](https://github.com/serpapi)

**JavaScript / TypeScript (`serpapi` on npm)**
- Install with `npm install serpapi`. The latest npm version is 2.2.1. — [serpapi-javascript](https://github.com/serpapi/serpapi-javascript); [npm registry](https://www.npmjs.com/package/serpapi)
- Usage: — [serpapi-javascript README](https://github.com/serpapi/serpapi-javascript)
  ```js
  import { config, getJson } from "serpapi";
  config.api_key = process.env.SERPAPI_KEY; config.timeout = 60000; // ms, default 60s
  const res = await getJson({ engine: "google", q: "coffee", location: "Austin, Texas" });
  ```
  A callback style also works: `getJson({...}, (json) => ...)`. Settings passed per request override the global `config`.
- Also provides `getHtml()` and `getMd()` (token-efficient Markdown). Supports Node.js 7.10.1+, Deno (`https://deno.land/x/serpapi/mod.ts`) and TypeScript. — [serpapi-javascript README](https://github.com/serpapi/serpapi-javascript)
- "Built-in pagination is not supported". Manual pagination examples are in the repo's examples folder. — [serpapi-javascript README](https://github.com/serpapi/serpapi-javascript)

**Other languages and the CLI (repos listed on the official integrations hub)**
- Ruby `serpapi-ruby`, Go `serpapi-golang`, PHP `serpapi-php`, Java `serpapi-java`, Rust `serpapi-rust`, .NET `serpapi-dotnet`, Swift `serpapi-swift`, C++ `serpapi-cpp`, CLI `serpapi-cli`, and MCP `serpapi-mcp`. — [serpapi.com/integrations](https://serpapi.com/integrations)
- Repo activity (last push, from the GitHub org API): serpapi-java 2026-09-24, serpapi-rust 2026-09-10, serpapi-javascript 2026-09-10, serpapi-golang 2026-09-09, serpapi-cli 2026-09-03, serpapi-php 2026-09-03, serpapi-ruby 2026-08-31, serpapi-cpp, serpapi-dotnet and serpapi-swift 2026-08-16. An unlisted `serpapi-zig` repo also exists (pushed 2026-09-24, 0 stars). The .NET repo description still says "for dotnet 5 and 6". — [github.com/serpapi](https://github.com/serpapi)

### Inferences
- **Dependency clash:** you cannot reliably install the new `serpapi` and the legacy `google-search-results` in the same environment, because both provide the `serpapi` module. A project that uses LangChain's built-in SerpApi wrappers *and* the new client will run into this.
- The Python SDK is built on `requests` and is synchronous. The source shows no async client. For async agents, use `asyncio.to_thread` or call `https://serpapi.com/search` directly with aiohttp/httpx. (LangChain's legacy wrapper has its own aiohttp path for `aresults`.)
- A first-class async Python client and a JS pagination helper are both small, real gaps.

### Gaps
- Exact package or install names for Ruby (gem), Go module path, Java (Maven coordinates), PHP (composer), .NET (NuGet) were not checked one by one. Only the repo names are confirmed.
- I did not read the bodies of `yield_pages()` and `next_page()`. They appear to follow `serpapi_pagination.next`, but that was not confirmed.

## "SerpApi Search Tools" package (hackathon resource)

### Takeaway
`serpapi-search-tools` (PyPI v1.0.0, Python ≥3.10, MIT) is SerpApi's official agent-tool package. It provides nine ready-made tool constructors (web, news, maps, images, shopping, videos, hotels, flights, travel explore). It detects whichever of 14 agent SDKs is installed and returns that SDK's native tool type. It is Python-only.

### Cited Findings
- The hackathon resources page describes it as providing "native tools for web, news, maps, shopping, image, video, hotel, flight, and travel search", with docs at https://serpapi.github.io/serpapi-search-tools-python/ — [Hackathon resources](https://serpapi.github.io/serpapi-india-hackathon-2026/)
- Install with `pip install serpapi-search-tools`, or with an extra such as `pip install "serpapi-search-tools[openai-agents]"`. Key comes from the env var `SERPAPI_API_KEY` (`SERPAPI_KEY` also works); `api_key=` passed directly takes precedence. — [README](https://github.com/serpapi/serpapi-search-tools-python)
- PyPI releases are 0.1.0, 0.1.1, 0.2.0 and 1.0.0 (current). Requires Python ≥3.10. — [PyPI](https://pypi.org/project/serpapi-search-tools/); [docs](https://serpapi.github.io/serpapi-search-tools-python/)
- "When one supported agent SDK is installed, the package detects it and creates tools ready for that SDK." — [README](https://github.com/serpapi/serpapi-search-tools-python)
- Supported SDKs, the extra to install, and the tool type returned: — [README](https://github.com/serpapi/serpapi-search-tools-python); [frameworks guide](https://serpapi.github.io/serpapi-search-tools-python/user-guide/frameworks.html)

  | SDK | Extra | Returned tool | Pinned version |
  |---|---|---|---|
  | OpenAI Agents SDK | `openai-agents` | `FunctionTool` | >=0.18.3,<1 |
  | Pydantic AI | `pydantic-ai` | `Tool` | >=1.30.1,<3 |
  | LangChain | `langchain` | `StructuredTool` | >=1.3.11,<2 |
  | LangGraph | `langgraph` | LangChain-compatible structured tool | >=1.2.6,<2 |
  | CrewAI | `crewai` | `BaseTool` | >=1.6.1,<2 |
  | LlamaIndex | `llamaindex` | `FunctionTool` | core >=0.14.22,<0.15 |
  | Claude Agent SDK | `claude-agent-sdk` | Claude SDK MCP tool | >=0.2.108,<1 |
  | Microsoft Agent Framework | `microsoft-agent-framework` | `FunctionTool` | >=1.10.1,<2 |
  | AutoGen | `autogen` | `FunctionTool` | >=0.7.5,<0.8 |
  | Haystack | `haystack` | `Tool` | >=2.30.2,<4 |
  | Semantic Kernel | `semantic-kernel` | function | >=1.36,<2 |
  | Agno | `agno` | `Function` | >=2.6.19,<3 |
  | smolagents | `smolagents` | `Tool` | >=1.26,<2 |
  | Google ADK | `google-adk` | `FunctionTool` | >=2.3,<3 |
- Tool constructors, their engines, and required inputs: `web_search` (google, google_light [default], bing, yahoo, duckduckgo; `query`), `news_search` (google_news), `maps_search` (google_maps; optional `location`, `zoom` 3–30, `nearby`), `images_search` (google_images), `shopping_search` (google_shopping, amazon, walmart, ebay), `videos_search` (youtube), `hotels_search` (`query`, `check_in_date`, `check_out_date`), `flights_search` (`departure_id`, `arrival_id`, `outbound_date`), `travel_explore_search` (google_travel_explore; `departure_id`). — [README](https://github.com/serpapi/serpapi-search-tools-python)
- You can restrict which engines a tool may use: `web_search(allowed_engines=[WebSearchEngine.GOOGLE_LIGHT, WebSearchEngine.BING], default_engine=WebSearchEngine.GOOGLE_LIGHT)`. `ShoppingSearchEngine` works the same way. Place details, reviews and directions are *not* covered by `maps_search`. — [README](https://github.com/serpapi/serpapi-search-tools-python)
- LangChain quickstart: — [README](https://github.com/serpapi/serpapi-search-tools-python)
  ```python
  from langchain.agents import create_agent
  from langchain_openai import ChatOpenAI
  from serpapi_search_tools import maps_search, news_search, web_search
  agent = create_agent(model=ChatOpenAI(model="gpt-5.4-mini", temperature=0),
                       tools=[web_search(), news_search(), maps_search()])
  agent.invoke({"messages": [{"role": "user", "content": "..."}]})
  ```
- The docs include runnable examples and an "agent cookbook" with complete agents for every supported SDK. — [README](https://github.com/serpapi/serpapi-search-tools-python)
- The hackathon's Open-Source Integrations track links to this package's frameworks page as its "Agent framework integrations" reference. — [Hackathon resources](https://serpapi.github.io/serpapi-india-hackathon-2026/)

### Inferences
- **Ollama / local models:** Ollama is not listed as a supported SDK and the README never mentions it. Because the tools are native to frameworks that are model-agnostic, swapping in a local model should be possible. Examples: replace `ChatOpenAI` with `langchain_ollama.ChatOllama` in the LangChain quickstart, or use Pydantic AI / Agno / smolagents with an Ollama model. The local model needs reliable tool calling (e.g. Qwen 3, Llama 3.x tool-capable tags). This is my inference and has not been documented or tested.
- There is no JS/TS equivalent (no `serpapi-search-tools` for Vercel AI SDK, Mastra, LangChain.js or the OpenAI Agents JS SDK). This is an obvious open-source gap.

### Gaps
- I did not see an explicit-selection API for environments with several SDKs installed (the frameworks guide mentions it). Exact function or parameter names were not captured.
- The package does not document Ollama or local-model support anywhere.

## SerpApi MCP server

### Takeaway
The official server is `github.com/serpapi/serpapi-mcp` (Python 3.13+, FastMCP, MIT, 178 stars, active as of 2026-09-22). It runs hosted at `https://mcp.serpapi.com/mcp` (Bearer header auth or key-in-path) or locally over HTTP, stdio or as a Claude Desktop `.mcpb` bundle. It exposes one `search` tool that covers every engine, two optional MCP Apps UI tools, and per-engine schema resources.

### Cited Findings
- Hosted endpoint: `https://mcp.serpapi.com`. Auth is either the header `Authorization: Bearer KEY` ("recommended: the key stays out of URLs and logs") or path-based `/KEY/mcp` "for clients that cannot set headers". "No key is needed to connect, list tools or read resources." — [serpapi-mcp README](https://github.com/serpapi/serpapi-mcp)
- Client setup commands: — [README](https://github.com/serpapi/serpapi-mcp)
  - Claude Code: `claude mcp add --transport http serpapi https://mcp.serpapi.com/mcp --header "Authorization: Bearer YOUR_SERPAPI_API_KEY"`
  - Claude Desktop JSON: `{"mcpServers":{"serpapi":{"type":"http","url":"https://mcp.serpapi.com/YOUR_SERPAPI_API_KEY/mcp"}}}`
  - Codex: `codex mcp add serpapi --url https://mcp.serpapi.com/mcp --bearer-token-env-var SERPAPI_API_KEY`
  - OpenClaw: `openclaw mcp add serpapi --url https://mcp.serpapi.com/KEY/mcp --transport streamable-http`
  - Hermes: `hermes mcp add serpapi --url https://mcp.serpapi.com/KEY/mcp`
  - VS Code and Cursor: one-click install badges
- Self-hosting: `git clone https://github.com/serpapi/serpapi-mcp.git && cd serpapi-mcp && uv sync && uv run src/server.py`, which serves `http://localhost:8000/KEY/mcp`. Docker also works: `docker build -t serpapi-mcp . && docker run -p 8000:8000 serpapi-mcp`. — [README](https://github.com/serpapi/serpapi-mcp)
- stdio for any local MCP host: `{"command":"uv","args":["run","--directory","/path/to/serpapi-mcp","--frozen","--no-dev","src/stdio.py"],"env":{"SERPAPI_API_KEY":"..."}}`. A Claude Desktop `.mcpb` bundle is attached to each release; it asks for the key and runs locally over stdio. — [README](https://github.com/serpapi/serpapi-mcp)
- Tools: `search` (main tool, all engines; `params.engine` defaults to `google_light`; `params.output="md"` for Markdown; `mode` is `"compact"` or `"complete"`), plus opt-in MCP Apps (SEP-1865) tools `search_table` and `search_dashboard`. These render UI "so the bulk SERP JSON never enters the model's context window". — [README](https://github.com/serpapi/serpapi-mcp)
- Resources: `serpapi://engines` (index) and `serpapi://engines/<engine>` (per-engine parameter schemas, generated from the Playground), with argument completion for engine names. — [README](https://github.com/serpapi/serpapi-mcp)
- Markdown output cuts tokens "by 50% on average and by more than 90% for APIs with complex nested JSON". — [README](https://github.com/serpapi/serpapi-mcp)
- Guided input: clients on MCP spec 2026-07-28 that support form elicitation get a form for missing required parameters (e.g. Google Flights departure/arrival/date, Google Hotels check-in/check-out, Maps Directions endpoints) before any search runs. Older clients get an error that lists the missing fields. The response is wrapped in `structuredContent.result` (a string). — [README](https://github.com/serpapi/serpapi-mcp)
- Example call: `{"name":"search","arguments":{"params":{"engine":"google_scholar","q":"retrieval augmented generation"}}}` — [README](https://github.com/serpapi/serpapi-mcp)
- Pushing a release tag deploys the hosted server, publishes an entry to the MCP Registry, and builds the bundle. — [README](https://github.com/serpapi/serpapi-mcp)

### Inferences
- To use it from Ollama, you need an MCP-capable client that can drive a local model, such as Open WebUI's MCP support, LangChain's `langchain-mcp-adapters` with ChatOllama, or the stdio entry point. SerpApi does not document this pairing.
- Contributing a new engine's guided-search rules (`engines/<engine>.json` + `src/engine_input_rules.py`) is a well-defined, easy-to-scope contribution.

### Gaps
- I did not verify a public MCP Registry ID/name or rate limits on the hosted server.

## Framework integrations (LangChain, LlamaIndex, CrewAI, Haystack, AutoGen, OpenAI Agents, Vercel AI SDK, n8n, Zapier/Make, plugins)

### Takeaway
SerpApi now maintains its own integrations (search-tools package, MCP, n8n node, coding-agent plugins). Third-party wrappers vary in quality. LangChain-community's SerpApi wrappers are legacy: they rely on `google-search-results`. CrewAI's tools have moved to the new `serpapi` client. LlamaIndex and Haystack have no first-party SerpApi tool package (I found none), so the search-tools package covers them.

### Cited Findings
**LangChain**
- `langchain_community.utilities.SerpAPIWrapper` imports the *legacy* `from serpapi import GoogleSearch`, reads `SERPAPI_API_KEY`, and makes async requests to `https://serpapi.com/search` via aiohttp. — [langchain-community source](https://github.com/langchain-ai/langchain-community/blob/main/libs/community/langchain_community/utilities/serpapi.py)
- langchain-community also has SerpApi-backed `GoogleJobsAPIWrapper`, `GoogleFinanceAPIWrapper`, `GoogleLensAPIWrapper` (plus tools such as Google Trends and Google Scholar). They read `SERPAPI_API_KEY` and say to install `google-search-results`. — [LangChain ref GoogleJobs](https://reference.langchain.com/python/langchain-community/utilities/google_jobs/GoogleJobsAPIWrapper); [GoogleFinance](https://reference.langchain.com/python/langchain-community/utilities/google_finance/GoogleFinanceAPIWrapper); [GoogleLens](https://reference.langchain.com/python/langchain-community/utilities/google_lens/GoogleLensAPIWrapper)
- The latest `langchain-community` is 0.4.2 (2026-05-22). There is no `langchain-serpapi` partner package on PyPI. — [PyPI langchain-community](https://pypi.org/project/langchain-community/) (PyPI lookup for `langchain-serpapi` returned not found)
- SerpApi's own route for LangChain/LangGraph is `serpapi-search-tools[langchain]`, which returns a `StructuredTool`. — [README](https://github.com/serpapi/serpapi-search-tools-python)
- Note: `GoogleSerperAPIWrapper` in LangChain is for **Serper.dev**, a different company. It is not SerpApi. (Common knowledge; I did not fetch a specific source this session.)

**CrewAI**
- `crewai_tools`' `SerpApiBaseTool` uses the **new** client (`from serpapi import Client`, `package_dependencies=["serpapi"]`, env `SERPAPI_API_KEY`). It offers to `uv add serpapi` if the package is missing. crewai-tools is at v1.15.23 (2026-09-28). — [crewAI source](https://github.com/crewAIInc/crewAI/blob/main/lib/crewai-tools/src/crewai_tools/tools/serpapi_tool/serpapi_base_tool.py); [PyPI crewai-tools](https://pypi.org/project/crewai-tools/)

**LlamaIndex / Haystack / AutoGen / OpenAI Agents / others**
- No `llama-index-tools-serpapi` package exists on PyPI. — [PyPI lookup](https://pypi.org/project/llama-index-tools-serpapi/) (not found)
- Haystack core (haystack-ai 3.3.0, 2026-10-01) has a `serper_dev.py` websearch component and a `searchapi.py` one. Neither is SerpApi. — [haystack repo](https://github.com/deepset-ai/haystack/tree/main/haystack/components/websearch)
- LlamaIndex, Haystack, AutoGen, OpenAI Agents SDK, Pydantic AI, Google ADK, Semantic Kernel, Agno, smolagents, Microsoft Agent Framework and Claude Agent SDK are all covered by `serpapi-search-tools` extras. — [frameworks guide](https://serpapi.github.io/serpapi-search-tools-python/user-guide/frameworks.html)

**Vercel / JS AI frameworks**
- Vercel Connect has an official SerpApi integration (`npm install @vercel/connect`, `vercel connect create serpapi --name acme-serpapi`, `getToken('serpapi/acme-serpapi')`). It handles **credential management** and is not a ready-made AI SDK tool. — [vercel.com/connect/serpapi](https://vercel.com/connect/serpapi)
- The only Vercel AI SDK v6 + SerpApi tool guide I found comes from a third party, Composio's tool router. — [Composio](https://composio.dev/toolkits/serpapi/framework/ai-sdk)

**No-code**
- n8n has an official, *verified* community node, "SerpApi Official" (repo `serpapi/n8n-nodes-serpapi`, last pushed 2026-08-25), announced 2025-05-27. It shipped with 22 APIs (Google Search/Light/Maps/Maps Directions/Maps Reviews/Local/News/Images/Videos/Shopping/Product/Jobs/Lens/Scholar/Trends/Flights/Autocomplete, Bing, Bing Images, Baidu, DuckDuckGo, eBay) and can be connected to n8n AI Agents as a tool. For anything else, use the HTTP Request node. — [SerpApi blog](https://serpapi.com/blog/boost-your-n8n-workflows-with-serpapis-verified-node/); [github.com/serpapi](https://github.com/serpapi)
- Zapier / Make: no official SerpApi integration showed up in the sources I reviewed (see Gaps).

**SerpApi-authored agent plugins (2026)**
- Hermes Agent plugin (Nous Research), published 2026-07-22. Install with `pip`/`uv` `serpapi-hermes-plugin` (v1.1.1, 2026-09-28), then `hermes plugins enable serpapi`. Tools: `web_search` (Google Light), `serpapi_maps_search`, `serpapi_news_search` (Google News Light), `serpapi_shopping_search` (Google Shopping Light). No separate server is needed. — [SerpApi blog](https://serpapi.com/blog/introducing-serpapis-hermes-agent-plugin/); [PyPI](https://pypi.org/project/serpapi-hermes-plugin/)
- Other official plugin repos in the GitHub org: `serpapi-claude-plugin` (Claude, pushed 2026-10-05), `serpapi-cursor-plugin` (2026-10-05), `serpapi-codex-plugin` ("Codex & ChatGPT Plugin", 2026-10-02), `opencode-serpapi` (OpenCode, 2026-09-30), `serpapi-openclaw-plugin` ("web search provider and 25+ specialized tools", 2026-08-20). — [github.com/serpapi](https://github.com/serpapi)
- The org also hosts forks of `litellm` and `hermes-agent`. These may be upstream PRs for SerpApi search providers; I did not verify that. — [github.com/serpapi](https://github.com/serpapi)

### Inferences
- **Maintained and current:** the serpapi Python and JS SDKs, serpapi-search-tools, serpapi-mcp, the n8n node, the Hermes/Claude/Cursor/Codex/OpenCode/OpenClaw plugins, and the CrewAI tools.
- **Legacy or outdated:** the LangChain-community SerpApi wrappers (they depend on the 2023 `google-search-results` package and only cover a handful of engines), and the `google-search-results-*` libraries.
- Migrating LangChain-community's `SerpAPIWrapper` and the `Google*APIWrapper` family to the new `serpapi.Client`, or shipping a `langchain-serpapi` partner package, is a concrete gap that fits the hackathon track.

### Gaps
- I did not confirm whether Zapier or Make offer a SerpApi app (no source found). AutoGen-native or LlamaIndex-hub SerpApi tools beyond the search-tools package were not found.
- I did not open LlamaHub to look for community SerpApi readers.

## BuiltWithSerpApi gallery, API Playground, and other resources

### Takeaway
The BuiltWithSerpApi gallery lists about 190 community projects across 65 engines, and you submit to it through a GitHub issue. The Playground at serpapi.com/playground lets you try engines and parameters and generates code. SerpApi also publishes many small open-source reference apps.

### Cited Findings
- Gallery: https://serpapi.github.io/BuiltWithSerpApi/ has "190 projects" using "65 different API engines". Categories include travel, e-commerce, research/intelligence, document verification, beauty/fashion, security/verification, and healthcare/education. Stacks include Python, JS, Streamlit, n8n and CrewAI. Projects are submitted through a GitHub issue template. — [BuiltWithSerpApi](https://serpapi.github.io/BuiltWithSerpApi/)
- Playground: "Test engines, adjust parameters, and inspect JSON responses" at https://serpapi.com/playground. The Python README points to it to "generate your own code". — [Hackathon resources](https://serpapi.github.io/serpapi-india-hackathon-2026/); [serpapi-python README](https://github.com/serpapi/serpapi-python)
- The engine catalog is at https://serpapi.com/search-engine-apis. API docs are at https://serpapi.com/search-api. The `tutorials` repo holds blog and video demo code. — [Hackathon resources](https://serpapi.github.io/serpapi-india-hackathon-2026/); [github.com/serpapi](https://github.com/serpapi)
- Recent open-source reference apps from SerpApi: `apptrail` (app visibility across the App Store, Google Play and AI search), `reviewaudit` (checks Google Maps review authenticity), `serptrail` (SEO tracking, 50 stars), `creator-lens` (YouTube strategy, SerpApi + Kimi K3 + DeepSeek), `byline`, `serpapi-superapp`, `vibecoding-series`, and an `import_bengaluru` event repo. — [github.com/serpapi](https://github.com/serpapi)
- SerpApi keeps a public roadmap repo (`public-roadmap`, 151 stars). — [github.com/serpapi](https://github.com/serpapi)

### Inferences
- The gallery's tag mix (Streamlit, n8n, CrewAI) suggests that many past entries are thin wrappers. An integration that ships to a package registry (PyPI, npm, crates, a marketplace) would stand out in the Open-Source Integrations track.

### Gaps
- The gallery's per-project tech-stack counts and dates were not extracted.

## Integration gaps (Open-Source Integrations track)

### Takeaway
The track asks entrants to "Bring SerpApi to a new open-source package or platform in any programming language. Build a plugin, provider, or connector for an agent framework, MCP client, or developer tool." The biggest gaps are on the JS/TS agent side, the legacy LangChain wrappers, and local-model (Ollama) tooling.

### Cited Findings
- Track description quoted above, with references to the search-tools frameworks page and the Hermes plugin as examples. — [Hackathon resources](https://serpapi.github.io/serpapi-india-hackathon-2026/)
- The search-tools package is Python-only, covering 14 SDKs. The JS SDK has no pagination helper. The only Vercel AI SDK tool guide is third-party (Composio). — [search-tools README](https://github.com/serpapi/serpapi-search-tools-python); [serpapi-javascript](https://github.com/serpapi/serpapi-javascript); [Composio](https://composio.dev/toolkits/serpapi/framework/ai-sdk)
- LangChain-community wrappers are still on `google-search-results`. No `langchain-serpapi` or `llama-index-tools-serpapi` package exists, and Haystack core ships Serper/SearchApi components but not a SerpApi one. — sources above

### Inferences (candidate projects, all unverified as "unclaimed")
- A TypeScript `serpapi-search-tools` equivalent for Vercel AI SDK `tool()`, Mastra, LangChain.js / LangGraph.js and the OpenAI Agents JS SDK.
- A `langchain-serpapi` partner package (or a PR) that moves the community wrappers to `serpapi.Client` and adds `output="md"`.
- A Haystack 3.x `SerpApiWebSearch` component or integration package (`serpapi-haystack`).
- A LlamaHub `llama-index-tools-serpapi` ToolSpec covering several engines.
- Ollama/local-first tooling: an Open WebUI tool or function for SerpApi, an Ollama-friendly MCP-bridge recipe, or a LiteLLM / OpenAI-compatible "web search" provider (SerpApi's fork of litellm hints at interest).
- Editor and terminal clients not yet covered: Zed, Continue, Cline/Roo, Goose, Raycast, Obsidian, Neovim. Desktop tools: Zapier/Make apps if absent.
- An async Python client (`httpx`-based) or JS pagination helpers in the official SDKs.

### Gaps
- I did not check whether any of the candidate gaps already have unofficial community packages (npm search, LlamaHub, Open WebUI community tools). Verify this before choosing a project.
