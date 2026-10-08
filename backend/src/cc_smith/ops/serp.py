"""SerpApi gateway (DR-5). The only module that holds the SerpApi key.

Every call goes through `search`: cache lookup in serp_cache, budget guard, then a live
call, and every call (cache hit, replay or live) is written to credit_ledger so
/ops/credits shows spend per flow. In replay mode responses come from
fixtures/serp/<engine>/<key>.json and nothing touches the network.

Queries carry card, issuer and domain names only, never user data: SerpApi is a third
party and the hackathon has no processor agreement with it (DR-9). `_assert_no_user_data`
rejects the obvious leaks (emails, phone and card numbers, user ids)."""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from sqlalchemy import func, insert, select, update

from cc_smith.config import settings
from cc_smith.db import credit_ledger, engine, now, serp_cache

ENDPOINT = "https://serpapi.com/search.json"

# Monthly envelopes per flow from DR-5 (the 50-search demo reserve is deliberately
# unallocated so it can only be spent by raising an envelope on purpose).
FLOW_BUDGETS: dict[str, int] = {
    "card_profile": 70,
    "launch_radar": 45,
    "cap_watch": 25,
    "checkout_merchant": 15,
    "commerce_offers": 10,
    "dev": 35,
}
FLOW_TTL: dict[str, timedelta] = {
    "card_profile": timedelta(days=30),
    "launch_radar": timedelta(days=7),
    "cap_watch": timedelta(hours=24),
    "checkout_merchant": timedelta(days=180),
    "commerce_offers": timedelta(hours=6),
    "dev": timedelta(days=30),
}

# SerpApi returns this as `error` with HTTP 200 when a query simply has no hits.
_EMPTY = "hasn't returned any results"
_SECRET_KEYS = {"api_key", "serp_api_key"}
_USER_KEYS = {"user_id", "email", "phone", "last4", "pan"}
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
# A bare 10-19 digit run is a phone or card number; ids like AR1234… are prefixed.
_LONG_DIGITS = re.compile(r"(?<!\w)\+?\d{10,19}(?!\w)")


class SerpError(Exception):
    pass


class BudgetExceeded(SerpError):
    pass


class ReplayMissing(SerpError):
    pass


@dataclass
class SerpResult:
    engine: str
    params: dict
    key: str
    data: dict
    search_id: str | None
    cached: bool  # True when no credit was spent (cache hit or replay)
    source: str  # cache | replay | live


def _canonical(params: dict) -> dict:
    out = {}
    for k, v in sorted(params.items()):
        if k in _SECRET_KEYS or v is None:
            continue
        out[k] = v.strip() if isinstance(v, str) else v
    return out


def cache_key(engine_name: str, params: dict) -> str:
    body = json.dumps({"engine": engine_name, **_canonical(params)}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(body.encode()).hexdigest()[:24]


def fixture_path(engine_name: str, params: dict) -> Path:
    return settings.fixtures_dir / "serp" / engine_name / f"{cache_key(engine_name, params)}.json"


def _assert_no_user_data(params: dict) -> None:
    for k, v in params.items():
        if k in _USER_KEYS:
            raise ValueError(f"serp params must not carry user data ({k})")
        if isinstance(v, str) and (_EMAIL.search(v) or _LONG_DIGITS.search(v)):
            raise ValueError(f"serp param {k} looks like personal data; queries carry card and issuer names only")


def _validate(engine_name: str, params: dict) -> None:
    # Live run R9: google_news rejects `q` together with `so`.
    if engine_name == "google_news" and "q" in params and "so" in params:
        raise ValueError("google_news: `q` and `so` can't be used together (SerpApi error, live run R9)")


def _ledger(flow: str, engine_name: str, search_id: str | None, cached: bool) -> None:
    with engine().begin() as c:
        c.execute(insert(credit_ledger).values(flow=flow, engine=engine_name, search_id=search_id, cached=cached))


def usage(flow: str | None = None, since: datetime | None = None) -> int:
    """Live (credit-spending) calls since `since`, optionally for one flow."""
    q = select(func.count()).select_from(credit_ledger).where(credit_ledger.c.cached.is_(False))
    if since is not None:
        q = q.where(credit_ledger.c.ts >= since)
    if flow is not None:
        q = q.where(credit_ledger.c.flow == flow)
    with engine().begin() as c:
        return c.execute(q).scalar_one()


def _month_start(at: datetime) -> datetime:
    return at.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def check_budget(flow: str, at: datetime | None = None) -> None:
    at = at or now()
    hour = usage(since=at - timedelta(hours=1))
    if hour >= settings.serp_hourly_limit:
        raise BudgetExceeded(f"hourly limit reached ({hour}/{settings.serp_hourly_limit})")
    month = _month_start(at)
    total = usage(since=month)
    if total >= settings.serp_monthly_budget:
        raise BudgetExceeded(f"monthly budget reached ({total}/{settings.serp_monthly_budget})")
    spent = usage(flow, since=month)
    if spent >= FLOW_BUDGETS[flow]:
        raise BudgetExceeded(f"flow {flow} envelope reached ({spent}/{FLOW_BUDGETS[flow]})")


def _cached(key: str, ttl: timedelta):
    with engine().begin() as c:
        row = c.execute(select(serp_cache).where(serp_cache.c.key == key)).first()
    if row is None:
        return None
    fetched = row.fetched_at if row.fetched_at.tzinfo else row.fetched_at.replace(tzinfo=UTC)
    return row if fetched + ttl > now() else None


def _store(key: str, engine_name: str, params: dict, data: dict, search_id: str | None) -> None:
    values = {"engine": engine_name, "params": params, "response": data, "search_id": search_id, "fetched_at": now()}
    with engine().begin() as c:
        if c.execute(select(serp_cache.c.key).where(serp_cache.c.key == key)).first():
            c.execute(update(serp_cache).where(serp_cache.c.key == key).values(**values))
        else:
            c.execute(insert(serp_cache).values(key=key, **values))


def record(engine_name: str, params: dict, data: dict) -> Path:
    """Save a live response as a replay fixture. Responses never contain the key
    (SerpApi echoes search_parameters without it), but strip it defensively."""
    path = fixture_path(engine_name, params)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {**data, "search_parameters": _canonical(data.get("search_parameters", {}))}
    body = {"_recorded": {"engine": engine_name, "params": _canonical(params), "at": now().isoformat()}, **data}
    path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n")
    return path


def _search_id(data: dict) -> str | None:
    return (data.get("search_metadata") or {}).get("id")


def _live(engine_name: str, params: dict, client: httpx.Client | None) -> dict:
    if not settings.serpapi_api_key:
        raise SerpError("SERPAPI_API_KEY is not set (mode=live)")
    own = client is None
    client = client or httpx.Client(timeout=60)
    try:
        resp = client.get(ENDPOINT, params={**params, "engine": engine_name, "api_key": settings.serpapi_api_key, "output": "json"})
    except httpx.HTTPError as e:
        raise SerpError(f"{engine_name}: {e}") from e
    finally:
        if own:
            client.close()
    try:
        data = resp.json()
    except ValueError as e:
        raise SerpError(f"{engine_name}: HTTP {resp.status_code}, non-JSON body") from e
    err = data.get("error")
    if resp.status_code >= 400 or (err and _EMPTY not in err):
        raise SerpError(f"{engine_name}: HTTP {resp.status_code}: {err or resp.text[:200]}")
    return data


def search(flow: str, engine_name: str, params: dict, ttl: timedelta | None = None, client: httpx.Client | None = None) -> SerpResult:
    if flow not in FLOW_BUDGETS:
        raise ValueError(f"unknown flow {flow!r}; add it to FLOW_BUDGETS with its DR-5 envelope")
    params = _canonical(params)
    _assert_no_user_data(params)
    _validate(engine_name, params)
    key = cache_key(engine_name, params)
    ttl = ttl if ttl is not None else FLOW_TTL[flow]

    if (row := _cached(key, ttl)) is not None:
        _ledger(flow, engine_name, row.search_id, cached=True)
        return SerpResult(engine_name, params, key, row.response, row.search_id, True, "cache")

    if settings.mode == "replay":
        path = fixture_path(engine_name, params)
        if not path.exists():
            raise ReplayMissing(
                f"no recorded SerpApi response for engine={engine_name} params={json.dumps(params, ensure_ascii=False)} "
                f"(expected {path.relative_to(settings.fixtures_dir.parent)}); record it with MODE=live")
        data = json.loads(path.read_text())
        sid = _search_id(data)
        _ledger(flow, engine_name, sid, cached=True)
        return SerpResult(engine_name, params, key, data, sid, True, "replay")

    check_budget(flow)
    data = _live(engine_name, params, client)
    sid = _search_id(data)
    # Ledger first: the credit is spent even if caching or recording fails.
    _ledger(flow, engine_name, sid, cached=False)
    _store(key, engine_name, params, data, sid)
    record(engine_name, params, data)
    return SerpResult(engine_name, params, key, data, sid, False, "live")
