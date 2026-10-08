import json

import httpx
import pytest
from sqlalchemy import select

from cc_smith.config import settings
from cc_smith.db import credit_ledger, engine, serp_cache
from cc_smith.ops import serp

NEWS = {"q": "launches new credit card India when:30d", "gl": "in", "hl": "en"}


def _ledger():
    with engine().begin() as c:
        return [(r.flow, r.engine, r.cached, r.search_id) for r in c.execute(select(credit_ledger).order_by(credit_ledger.c.id))]


@pytest.fixture
def live(db, tmp_path, monkeypatch):
    """Live mode against a fake SerpApi; recorded fixtures go to tmp, not the repo."""
    monkeypatch.setattr(settings, "mode", "live")
    monkeypatch.setattr(settings, "serpapi_api_key", "test-key")
    monkeypatch.setattr(settings, "fixtures_dir", tmp_path / "fixtures")
    calls: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        n = len(calls)
        return httpx.Response(200, json={"search_metadata": {"id": f"sid{n}", "status": "Success"}, "organic_results": [{"link": f"https://x/{n}"}]})

    return httpx.Client(transport=httpx.MockTransport(handler)), calls


def test_cache_key_ignores_order_none_and_api_key():
    a = serp.cache_key("google", {"q": "x", "gl": "in", "hl": None})
    b = serp.cache_key("google", {"gl": "in", "api_key": "secret", "q": " x "})
    assert a == b
    assert a != serp.cache_key("google_light", {"q": "x", "gl": "in"})


def test_replay_serves_recorded_fixture_and_ledgers_it_as_free(db):
    res = serp.search("launch_radar", "google_news", NEWS)
    assert res.source == "replay" and res.cached
    assert any("Google Pay Flex SBI Card" in n["title"] for n in res.data["news_results"])
    assert _ledger() == [("launch_radar", "google_news", True, "r17-google-news-launch")]


def test_replay_missing_fixture_is_a_clear_error_and_spends_nothing(db):
    with pytest.raises(serp.ReplayMissing) as e:
        serp.search("launch_radar", "google", {"q": 'site:hdfc.bank.in "never recorded"'})
    assert "fixtures/serp/google/" in str(e.value) and "MODE=live" in str(e.value)
    assert _ledger() == []


def test_live_call_is_ledgered_cached_and_recorded_then_served_from_cache(live):
    client, calls = live
    first = serp.search("card_profile", "google", {"q": 'site:axis.bank.in "ACE"'}, client=client)
    assert first.source == "live" and not first.cached and first.search_id == "sid1"
    assert calls[0].url.params["api_key"] == "test-key" and calls[0].url.params["engine"] == "google"
    recorded = json.loads(serp.fixture_path("google", {"q": 'site:axis.bank.in "ACE"'}).read_text())
    assert "test-key" not in json.dumps(recorded)
    with engine().begin() as c:
        assert c.execute(select(serp_cache.c.search_id)).scalar_one() == "sid1"

    again = serp.search("card_profile", "google", {"q": 'site:axis.bank.in "ACE"'}, client=client)
    assert again.source == "cache" and again.data == first.data and len(calls) == 1
    assert _ledger() == [("card_profile", "google", False, "sid1"), ("card_profile", "google", True, "sid1")]


def test_hourly_limit_blocks_before_the_http_call(live, monkeypatch):
    client, calls = live
    monkeypatch.setattr(settings, "serp_hourly_limit", 2)
    for i in range(2):
        serp.search("dev", "google", {"q": f"q{i}"}, client=client)
    with pytest.raises(serp.BudgetExceeded, match="hourly"):
        serp.search("dev", "google", {"q": "q2"}, client=client)
    assert len(calls) == 2
    # A cache hit costs nothing, so it is still served.
    assert serp.search("dev", "google", {"q": "q0"}, client=client).source == "cache"


def test_monthly_budget_and_flow_envelope(live, monkeypatch):
    client, _ = live
    monkeypatch.setitem(serp.FLOW_BUDGETS, "launch_radar", 1)
    serp.search("launch_radar", "google", {"q": "a"}, client=client)
    with pytest.raises(serp.BudgetExceeded, match="launch_radar envelope"):
        serp.search("launch_radar", "google", {"q": "b"}, client=client)
    monkeypatch.setattr(settings, "serp_monthly_budget", 2)
    serp.search("dev", "google", {"q": "c"}, client=client)
    with pytest.raises(serp.BudgetExceeded, match="monthly"):
        serp.search("dev", "google", {"q": "d"}, client=client)


def test_serpapi_error_payload_raises_but_no_results_does_not(live):
    _, _ = live

    def handler(req):
        q = req.url.params["q"]
        err = "Google hasn't returned any results for this query." if q == "empty" else "Invalid API key."
        return httpx.Response(200 if q == "empty" else 401, json={"search_metadata": {"id": "e"}, "error": err})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert serp.search("dev", "google", {"q": "empty"}, client=client).data["error"].startswith("Google hasn't")
    with pytest.raises(serp.SerpError, match="Invalid API key"):
        serp.search("dev", "google", {"q": "bad"}, client=client)


def test_rejects_known_bad_params_and_user_data(db):
    with pytest.raises(ValueError, match="`so`"):
        serp.search("launch_radar", "google_news", {"q": "x", "so": "1"})
    with pytest.raises(ValueError, match="user data"):
        serp.search("dev", "google", {"q": "x", "user_id": "u1"})
    with pytest.raises(ValueError, match="personal data"):
        serp.search("dev", "google", {"q": "card for 9876543210"})
    with pytest.raises(ValueError, match="unknown flow"):
        serp.search("finder", "google", {"q": "x"})
