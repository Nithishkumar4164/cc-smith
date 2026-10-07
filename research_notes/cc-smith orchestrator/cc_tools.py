"""cc-smith custom SerpApi tools in the serpapi-search-tools style (verified against v1.0.0).

Uses the package's *private* building blocks (_shared / _adapters). Pin serpapi-search-tools==1.0.0.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from serpapi_search_tools._adapters import as_provider_tool
from serpapi_search_tools._shared import (
    SearchResultFormat,
    SearchResultMode,
    SearchRuntime,
    ToolDefinition,
    object_schema,
    require_nonempty,
)

INDIA = {"gl": "in", "hl": "en"}


def _runtime(*, client, api_key, default_params, timeout) -> SearchRuntime:
    # Unknown engines have no compact profile in the package: COMPACT+JSON would return
    # {"no_results": true}. Use FULL + JSON and trim server-side with json_restrictor.
    return SearchRuntime(
        api_key=api_key,
        client=client,
        default_params=default_params,
        timeout=timeout,
        mode=SearchResultMode.FULL,
        response_format=SearchResultFormat.JSON,
        result_limit=None,
    )


# ---------------------------------------------------------------- google_ai_mode
AI_MODE_RESTRICTOR = (
    "text_blocks,reconstructed_markdown,references[].{index,title,link,source,snippet},"
    "subsequent_request_token,error,search_metadata.{id,status}"
)


def ai_mode_search(*, provider="auto", client=None, api_key=None, default_params=None,
                   timeout=None, name="ai_mode_search"):
    defaults = {**INDIA, "continuable": "true", "json_restrictor": AI_MODE_RESTRICTOR,
                **(default_params or {})}
    runtime = _runtime(client=client, api_key=api_key, default_params=defaults, timeout=timeout)

    def ai_mode_tool(query: str, follow_up_token: str | None = None) -> str:
        def validate(params: dict[str, Any]) -> None:
            require_nonempty(params, "q", label="query")

        return runtime.execute(
            engine="google_ai_mode",
            typed_params={"q": query, "subsequent_request_token": follow_up_token},
            validator=validate,
        )

    ai_mode_tool.__annotations__ = {"query": str, "follow_up_token": str | None, "return": str}
    schema = object_schema(
        {
            "query": {"type": "string", "description": "Question for Google AI Mode."},
            "follow_up_token": {
                "type": "string",
                "description": "subsequent_request_token from a previous ai_mode_search "
                               "result, to ask a follow-up in the same conversation.",
            },
        },
        required=["query"],
    )
    desc = ("Ask Google AI Mode (India) and get an answer with numbered references. "
            "Use for card fees, reward rates, caps and eligibility; cite references[].link.")
    return as_provider_tool(ToolDefinition(ai_mode_tool, name, desc, schema), provider)


# ------------------------------------------------- google_maps place details
def place_details(*, provider="auto", client=None, api_key=None, default_params=None,
                  timeout=None, name="place_details"):
    defaults = {**INDIA, "json_restrictor": (
        "place_results.{title,place_id,data_cid,type,types,type_ids,address,"
        "gps_coordinates,website},error"), **(default_params or {})}
    runtime = _runtime(client=client, api_key=api_key, default_params=defaults, timeout=timeout)

    def place_tool(place_id: str) -> str:
        return runtime.execute(
            engine="google_maps",
            typed_params={"place_id": require_nonempty({"p": place_id}, "p", label="place_id")},
        )

    place_tool.__annotations__ = {"place_id": str, "return": str}
    schema = object_schema(
        {"place_id": {"type": "string", "description": "Google Maps place_id from maps_search."}},
        required=["place_id"])
    return as_provider_tool(ToolDefinition(
        place_tool, name, "Get Google Maps details (category, types) for one place_id.", schema),
        provider)


# --------------------------------------------- google_ads_transparency_center
def ads_transparency_search(*, provider="auto", client=None, api_key=None, default_params=None,
                            timeout=None, name="ads_transparency_search"):
    # add "region": <India code from serpapi.com/google-ads-transparency-center-regions>
    defaults = {"num": 20,
                "json_restrictor": "ad_creatives[0:20].{advertiser,format,link,first_shown,"
                                   "last_shown,total_days_shown},error",
                **(default_params or {})}
    runtime = _runtime(client=client, api_key=api_key, default_params=defaults, timeout=timeout)

    def ads_tool(advertiser_or_domain: str, start_date: str | None = None) -> str:
        text = require_nonempty({"t": advertiser_or_domain}, "t", label="advertiser_or_domain")
        typed = {"advertiser_id": text} if text.startswith("AR") else {"text": text}
        if start_date is not None:
            if len(start_date) != 8 or not start_date.isdigit():
                raise ValueError("start_date must be YYYYMMDD.")
            typed["start_date"] = start_date
        return runtime.execute(engine="google_ads_transparency_center", typed_params=typed)

    ads_tool.__annotations__ = {"advertiser_or_domain": str, "start_date": str | None,
                                "return": str}
    schema = object_schema({
        "advertiser_or_domain": {"type": "string",
                                 "description": "Advertiser ID (AR...) or a domain such as hdfcbank.com."},
        "start_date": {"type": "string", "description": "Optional YYYYMMDD lower bound."},
    }, required=["advertiser_or_domain"])
    return as_provider_tool(ToolDefinition(
        ads_tool, name, "List recent Google ads run by a bank/issuer (offer and launch signals).",
        schema), provider)


# ------------------------------------------------- youtube_video_transcript
def video_transcript(*, provider="auto", client=None, api_key=None, default_params=None,
                     timeout=None, name="video_transcript"):
    defaults = {"language_code": "en", "json_restrictor": "transcript[].{start_ms,end_ms,snippet},error",
                **(default_params or {})}
    runtime = _runtime(client=client, api_key=api_key, default_params=defaults, timeout=timeout)

    def transcript_tool(video_id: str) -> str:
        return runtime.execute(engine="youtube_video_transcript",
                               typed_params={"v": require_nonempty({"v": video_id}, "v")})

    transcript_tool.__annotations__ = {"video_id": str, "return": str}
    schema = object_schema({"video_id": {"type": "string",
                                         "description": "YouTube video id (watch?v=...)."}},
                           required=["video_id"])
    return as_provider_tool(ToolDefinition(
        transcript_tool, name, "Fetch the transcript of a YouTube video (e.g. a card review).",
        schema), provider)


# --------------------------------------------------------------- google_lens
def lens_search(*, provider="auto", client=None, api_key=None, default_params=None,
                timeout=None, name="lens_search"):
    defaults = {"country": "in", "hl": "en",
                "json_restrictor": "visual_matches[0:10].{title,link,source},error",
                **(default_params or {})}
    runtime = _runtime(client=client, api_key=api_key, default_params=defaults, timeout=timeout)

    def lens_tool(image_url: str, search_type: str = "visual_matches") -> str:
        if search_type not in {"all", "products", "exact_matches", "visual_matches"}:
            raise ValueError("search_type must be all, products, exact_matches or visual_matches.")
        return runtime.execute(engine="google_lens",
                               typed_params={"url": require_nonempty({"u": image_url}, "u"),
                                             "type": search_type})

    lens_tool.__annotations__ = {"image_url": str, "search_type": str, "return": str}
    schema = object_schema({
        "image_url": {"type": "string", "description": "Public URL of the card image."},
        "search_type": {"type": "string", "enum": ["all", "products", "exact_matches",
                                                   "visual_matches"],
                        "default": "visual_matches", "description": "Lens search type."},
    }, required=["image_url"])
    return as_provider_tool(ToolDefinition(
        lens_tool, name, "Identify a credit card from a photo via Google Lens.", schema), provider)


# ------------------------------------------------ caching + credit-budget client
class BudgetedCachingClient:
    """`client=` for every tool: SQLite cache + hard monthly credit budget.

    - Never raises on budget exhaustion: returns an error payload the model can read
      (custom-client exceptions are collapsed by the package into the generic
      "Custom search client request failed." message).
    - Handles both formats: JSON (Mapping) and Markdown (str, when output=md).
    """

    TTL_BY_ENGINE = {  # seconds
        "google_maps": 365 * 86400, "google_ai_mode": 14 * 86400, "google": 7 * 86400,
        "google_light": 7 * 86400, "google_news": 6 * 3600, "youtube_video_transcript": 365 * 86400,
    }

    def __init__(self, api_key: str | None, db_path: str = "serpapi_cache.sqlite",
                 monthly_budget: int = 250, reserve: int = 25, upstream: Any = None):
        if upstream is None:
            import serpapi
            upstream = serpapi.Client(api_key=api_key, timeout=30)
        self._up = upstream
        self._budget = monthly_budget - reserve
        self._db = sqlite3.connect(db_path, check_same_thread=False)
        self._db.execute("CREATE TABLE IF NOT EXISTS cache(k TEXT PRIMARY KEY, ts REAL, body TEXT)")
        self._db.execute("CREATE TABLE IF NOT EXISTS spend(month TEXT, ts REAL, engine TEXT, k TEXT)")

    @staticmethod
    def _key(params: Mapping[str, Any]) -> str:
        safe = {k: v for k, v in params.items() if k != "api_key"}
        return hashlib.sha256(json.dumps(safe, sort_keys=True, default=str).encode()).hexdigest()

    def _spent(self, month: str) -> int:
        return self._db.execute("SELECT COUNT(*) FROM spend WHERE month=?", (month,)).fetchone()[0]

    def search(self, params: dict[str, Any]) -> Mapping[str, Any] | str:
        is_md = params.get("output") == "md"
        k = self._key(params)
        ttl = self.TTL_BY_ENGINE.get(params.get("engine", ""), 86400)
        row = self._db.execute("SELECT ts, body FROM cache WHERE k=?", (k,)).fetchone()
        if row and time.time() - row[0] < ttl:
            return row[1] if is_md else json.loads(row[1])
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        if self._spent(month) >= self._budget:
            msg = "SerpApi monthly credit budget reached; answer from stored card profiles."
            return f"## Error\n\n{msg}\n" if is_md else {"error": msg}
        result = self._up.search(params)
        body = result if isinstance(result, str) else json.dumps(dict(result), default=str)
        with self._db:
            self._db.execute("INSERT INTO spend VALUES (?,?,?,?)",
                             (month, time.time(), params.get("engine"), k))
            if is_md or "error" not in json.loads(body):
                self._db.execute("INSERT OR REPLACE INTO cache VALUES (?,?,?)", (k, time.time(), body))
        return result if isinstance(result, str) else dict(result)
