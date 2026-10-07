# cc-smith: model choices per agent role

Researched 2026-10-06. Every figure is from the official page cited next to it, fetched that day. Where something could not be verified it says so.

---

## 1. Anthropic models (Claude API, first-party)

Sources:
- Models overview: https://platform.claude.com/docs/en/about-claude/models/overview
- Pricing: https://platform.claude.com/docs/en/about-claude/pricing
- Structured outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Prompt caching: https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- Deprecations: https://platform.claude.com/docs/en/about-claude/model-deprecations

| | Fable 5.1 | Opus 5.5 | Sonnet 5.5 | Haiku 4.5 |
|---|---|---|---|---|
| API ID | `claude-fable-5-1` | `claude-opus-5-5` | `claude-sonnet-5-5` | `claude-haiku-4-5-20251001` (alias `claude-haiku-4-5`) |
| Input / output $ per MTok | 10 / 50 | 4 / 20 | 2 / 10 | 1 / 5 |
| 5-min cache write / 1-h write | 12.50 / 20 | 5 / 8 | 2.50 / 4 | 1.25 / 2 |
| Cache hit | 0.25 (0.025x) | 0.20 (0.05x) | 0.20 (0.1x) | 0.10 (0.1x) |
| Batch input / output (50% off) | 5 / 25 | 2 / 10 | 1 / 5 | 0.50 / 2.50 |
| Context window | 1M | 1M | 1M | 200K |
| Max output | 128K | 128K | 128K | 64K |
| Comparative latency (Anthropic's wording) | Slower | Moderate | Fast | Fastest |
| Thinking | Adaptive, always on | Adaptive, always on (default effort `medium`) | Adaptive (default effort `high`); can be turned off only with `{type:"between_tools"}` | Extended (`budget_tokens`); off unless you enable it; no `effort` |
| Minimum cacheable prefix | 512 tok | 512 tok | 512 tok | **4,096 tok** |
| Reliable knowledge cutoff | Jun 2026 | Jun 2026 | Jun 2026 | Feb 2025 |
| Retirement (Anthropic platforms) | not before 2027-09-01 | not before 2027-09-22 | not before 2027-09-28 | **not before 2026-10-15** (Active, no deprecation notice yet) |

Key facts and caveats:
- **Structured outputs are GA on all four models**: JSON outputs (`output_config.format`) and strict tool use (`strict: true`). Schema limits: no recursive schemas; no `minimum`/`maximum`/`minLength`/`maxLength`; `additionalProperties` must be `false`; at most 20 strict tools, 24 optional params and 16 union-typed params per request. Going over returns a 400 "Schema is too complex" (structured-outputs page). Enforce numeric ranges such as "cap <= 100000" in your own validator (Pydantic), not in the schema.
- **Citations can't be combined with `output_config.format`** (that returns a 400; Anthropic's claude-api skill reference, consistent with the citations docs). For source references in the extractor, put a `source_ref` field such as `{url, quote}` in the schema instead of using native citations.
- **Forced `tool_choice` (`any`/`tool`) returns a 400 on Fable 5.1, Opus 5.5 and Sonnet 5.5.** Use `auto` plus `strict: true`, or structured outputs. Haiku 4.5 still allows forced tool choice. Source: model migration notes in Anthropic's claude-api reference. The pricing page's tool-use token table also leaves the "any, tool" column blank for Opus 5.5 and Sonnet 5.5.
- **`temperature`/`top_p`/`top_k` return a 400 when set to non-default values on Claude 4.7 and later** (deprecations page, "API parameter deprecations"). You can't set temperature 0 for determinism on Opus 5.5 or Sonnet 5.5. Rely on the schema plus prompt instead. Haiku 4.5 still accepts temperature.
- **Batch API is 50% off input and output.** It stacks with caching multipliers (pricing page, "Batch processing" and "How do discounts stack?"). Good for weekly card sweeps and news backlogs.
- **Haiku 4.5 caching trap**: prompts under 4,096 tokens silently don't cache (prompt-caching page). A small router prompt on Haiku won't benefit from caching. On Sonnet 5.5 and Opus 5.5 the minimum is 512.
- **Haiku 4.5 lifecycle**: it shows "not sooner than Oct 15, 2026" and is still Active. Anthropic gives at least 60 days' notice before retiring a model (deprecations page, "Notifications"), so it is safe through the Oct 10 hackathon. For anything long-lived, keep the model ID in config so you can swap it.
- **Tokenizer**: Claude 4.7 and later models produce about 30% more tokens for the same text than Sonnet 4.6, Haiku 4.5 and earlier (pricing page). Per-token prices therefore understate the cost gap between Haiku 4.5 and Sonnet 5.5 a little.
- **Long context**: the 1M window is billed at standard rates with no surcharge (pricing page, "Long context pricing").
- **Privacy**: Anthropic does not use API data for training without your express permission. By default, prompts and outputs are not retained, except for Covered Models (Fable 5.x and Mythos), which need 30-day retention and can't run under zero data retention (ZDR). Source: https://platform.claude.com/docs/en/manage-claude/api-and-data-retention
- **Data residency**: `inference_geo` accepts only `"global"` or `"us"` (US costs 1.1x). Workspace storage geo is `"us"` only. **There is no India region** (https://platform.claude.com/docs/en/manage-claude/data-residency). For Indian users' financial data, minimise what you send (no card numbers, PAN or names), or keep classification on a local model.
- Fast mode on Opus 5.5 costs $8/$40 (2x) and is Claude API only. It is not available with Batch (pricing page).

## 2. Local models on Ollama

Ollama docs:
- Structured outputs: https://docs.ollama.com/capabilities/structured-outputs. Pass a JSON schema (or Pydantic/Zod) in `format`. Ollama recommends **temperature 0** and also putting the schema in the prompt. It works through the OpenAI-compatible `response_format` too. **Ollama Cloud doesn't support structured outputs**; they work only on a local server.
- Tool calling: https://docs.ollama.com/capabilities/tool-calling. Supports parallel tool calls and streaming tool calls. With streaming, collect `thinking`, `content` and `tool_calls` separately and send them back together. The docs use Qwen3 for all examples.
- **Context default is 4,096 tokens and does not scale with VRAM** (https://docs.ollama.com/faq). Long Google AI Mode markdown gets cut off silently. Set `OLLAMA_CONTEXT_LENGTH=16384` or pass `num_ctx` per request.
- Keep-alive is 5 minutes by default. Set `keep_alive: -1` during a demo to avoid cold-load latency (FAQ).

**Corporate proxy (FAQ)**:
- Set `HTTPS_PROXY` (pulls use HTTPS only). **Do not set `HTTP_PROXY`**, because it "may interrupt client connections to the server".
- Install the corporate MITM root certificate in the system trust store, or pulls fail TLS.
- On macOS the menu-bar app does not read your shell environment. Run `launchctl setenv HTTPS_PROXY http://proxy:port` and then restart Ollama.
- Make sure `NO_PROXY` includes `localhost,127.0.0.1` so your app's calls to `localhost:11434` don't go to the proxy. This is general proxy practice, not from Ollama's docs.
- In Docker, pass `-e HTTPS_PROXY=...` and build the certificate into the image.

Candidate models (Ollama library pages):

| Model | Laptop-sized tags | Tools / thinking | Notes | Source |
|---|---|---|---|---|
| `qwen3` | 4b (2.5 GB), 8b (5.2 GB), 14b (9.3 GB) | tools, thinking | Used in Ollama's own tool-calling docs. 8b is the default choice for classifier and triage. About a year old. | https://ollama.com/library/qwen3 |
| `qwen3.6` | 27b (18–19 GB), 35b (23–24 GB); MLX builds | tools, thinking, vision, 256K | Newest Qwen. Needs a 32 GB+ Mac. License not shown on the Ollama page (unverified). | https://ollama.com/library/qwen3.6 |
| `gemma4` | e2b/e4b (4.6–9.5 GB), 12b (7.7 GB), 26b MoE with 4B active (16–19 GB) | native function calling, thinking | 26b MoE gives good quality per unit of speed. License not verified. | https://ollama.com/library/gemma4 |
| `gpt-oss` | 20b (14 GB, needs 16 GB+ RAM) | function calling, structured outputs, reasoning effort low/medium/high | Apache 2.0. Strongest reasoning option at laptop size. | https://ollama.com/library/gpt-oss |
| `granite4.1` | 3b (2.1 GB), 8b (5.3 GB), 30b (17 GB) | tool use, structured JSON | Apache 2.0. IBM lists classification and extraction among its intended uses. Small and fast. | https://ollama.com/library/granite4.1 |

The Ollama tools catalogue (https://ollama.com/search?c=tools) also lists qwen3.8 (27B), nemotron-3.5-lightning (30B MoE, 3B active), mistral-medium-3.5 (128B) and others. I did not evaluate them. Llama 3.x/4 and Mistral Small were not checked this session (unverified).

Practical guidance:
- For the merchant classifier and news triage, run `qwen3:8b` or `granite4.1:8b` with `format=<schema>` at temperature 0. If the model supports it, set `think:false` for latency (I didn't verify this flag for each model).
- For card-terms extraction, local 8B models are noticeably less reliable on long, nested schemas (caps, exclusions, tiers). Use them only as an offline fallback (`gpt-oss:20b` or `gemma4:26b`) and validate with Pydantic plus one retry.

## 3. Other hosted options (price comparison only)

- **Gemini** (https://ai.google.dev/gemini-api/docs/pricing):
  - 3.8 Flash and 3.7 Flash: $0.75 in / $3.75 out per MTok through 2026-12-31, rising to $1.50 / $7.50 in 2027.
  - 3.5 Flash-Lite: $0.30 in / $2.50 out (as summarised by my fetch tool; worth a direct check on the page).
  - Batch is 50% off.
  - **Free tier: "Content used to improve our products"**. Don't send user financial data on the free tier.
- **OpenAI** (https://developers.openai.com/api/docs/pricing):
  - GPT-6-Luna: $0.10 in / $0.01 cached / $0.50 out.
  - GPT-5.4-Nano: $0.20 / $0.02 / $1.25.
  - GPT-5-Nano: $0.05 / $0.005 / $0.40.
  - Flagship GPT-6-Astra: $10 / $1 / $50.
  - Batch is 50% off.
  - Mid-tier "mini" prices were not captured (unverified).
- Takeaway: for tiny classification calls, the cheapest OpenAI nano and Gemini Flash-Lite models cost 5–20x less per token than Haiku 4.5. At cc-smith's volume, though, Haiku-based classification is only about $1–3 a month. Adding another vendor (another key, another privacy review) isn't worth it in a 4-day hackathon. I have no first-party latency numbers for these, beyond Anthropic's relative ranking (Haiku is fastest).

## 4. Recommendation per agent role

| Role | Primary | Alternatives | Why / tradeoffs |
|---|---|---|---|
| **Supervisor / router** (conversational, tool routing) | **Sonnet 5.5**, effort `low` (or `between_tools` for thinking off) | Haiku 4.5 (cheaper and faster, but prompts under 4K tokens don't cache and it's an older generation); Opus 5.5 at effort `low` | Routing errors cascade into every later step, so it's worth paying for Sonnet. Cache tools and system prompt (512-token minimum). Use `tool_choice:auto` plus `strict:true`; forced tool choice returns a 400. |
| **Card-terms extractor** (AI Mode markdown to strict JSON with `source_ref`) | **Opus 5.5** via **Batch**, effort `medium`, `output_config.format` | Sonnet 5.5 via Batch (half the price; check on a 10-card golden set); local `gpt-oss:20b` as an offline fallback | Highest-stakes output, because wrong caps mean wrong reward maths. Runs only weekly on 30 cards, so even Opus is cheap. Validate with Pydantic. Diff against the last snapshot so a human reviews changed fields. No native citations together with JSON output. |
| **News triage** (is article X a devaluation or launch for card Y?) | **Haiku 4.5**, structured output `{card_id, event_type, confidence, evidence_quote}` | local `qwen3:8b` / `granite4.1:8b`; Sonnet 5.5 for low-confidence escalation | High volume, simple task. Pre-filter with keywords or bank names first. Send articles that pass to Sonnet or the extractor. Batch works if you don't need real time. |
| **Merchant classifier** (merchant to category/MCC) | **Local `qwen3:8b`** (merchant strings are user data and stay on device) plus a deterministic lookup cache | Haiku 4.5; `granite4.1:3b` for speed | Deterministic lookup first, LLM only on a cache miss. Use an enum schema. Privacy is the deciding factor. |
| **Explainer** (final user reply) | **Sonnet 5.5** | Opus 5.5 for the demo "wow" (2x the cost, moderate latency); Haiku 4.5 for terse replies | Must explain numbers from the deterministic engine without changing them. Pass the computed figures in and tell it not to recompute. Stream the output. |
| **Eligibility / prerequisite planner** (multi-step reasoning on income, LTF, relationship rules) | **Opus 5.5**, effort `medium` | Sonnet 5.5 at effort `high`; Fable 5.1 only if evals show a need (2.5x Opus price, slower, 30-day retention required) | Low volume, reasoning-heavy, and errors are costly. |

Don't use Fable 5.1 anywhere by default. It costs $10/$50, is slower, and as a Covered Model it requires 30-day retention, which is a worse posture for financial data.

## 5. Monthly cost estimate (100 users, 30 cards, weekly sweeps)

Assumptions: each user has about 20 chat turns a month, so 2,000 turns. Prices are list prices with global routing. Thinking tokens are billed as output, so I add about 1.5x headroom on output.

| Workload | Volume / month | Tokens | Model | ≈ $ |
|---|---|---|---|---|
| Router | 2,000 turns | 3K in (about 80% cache hits), 300 out | Sonnet 5.5 | ~$10 |
| Explainer | 2,000 turns | 4K in (about 50% cached), 600 out | Sonnet 5.5 | ~$25 |
| Extractor | 30 cards × 4.3 sweeps = 130 | 8K in, 2K out | Opus 5.5 Batch | ~$5 (Sonnet Batch ~$2.5) |
| News triage | ~1,500 articles after pre-filter | 1.5K in, 100 out | Haiku 4.5 | ~$3–4 (Batch ~$2) |
| Merchant classifier | ~2,000 cache misses | 500 in, 50 out | local (Haiku would cost ~$1.5) | $0 |
| Eligibility planner | ~300 runs | 6K in, 1K out | Opus 5.5 | ~$15 |
| **Total** | | | | **≈ $55–65 / month** (about ₹5k) |

- Running everything on Sonnet 5.5 brings this to about $40. Running the user-facing roles on Opus 5.5 brings it to about $100.
- A 4-day hackathon (development, evals and demo) should cost about $20–50 in API usage.
- These are estimates from assumed volumes, not measurements. Log `usage` on every call and check against `cache_read_input_tokens`.
