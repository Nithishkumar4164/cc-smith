"""Scheduled card refresh: SerpApi finds the bank's page, the usual checks decide."""

from sqlalchemy import select

from cc_smith.config import Settings
from cc_smith.db import credit_ledger
from cc_smith.knowledge import refresh, store
from cc_smith.knowledge.discover import DiscoveredUrl
from cc_smith.knowledge.pipeline import profile_card
from cc_smith.signals import scheduler


def _official(card) -> list[DiscoveredUrl]:
    urls = sorted({s["url"] for s in _walk(card.model_dump())})
    return [DiscoveredUrl(u, "official page", "", "site: search", "sid") for u in urls]


def _walk(x):
    if isinstance(x, dict):
        if "url" in x and "quote" in x:
            yield x
        for v in x.values():
            yield from _walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from _walk(v)


def test_unchanged_page_bumps_as_of_and_publishes_nothing(db, cards, monkeypatch):
    c = cards["hdfc_millennia"]
    profile_card(c)
    asked = []
    monkeypatch.setattr(refresh, "discover", lambda name, issuer, **kw: asked.append((name, kw)) or (_official(c) if kw.get("page", True) else []))
    r = refresh.refresh_card(c.id)
    assert r.status == "refreshed", r.reason
    assert asked[0][1]["flow"] == "card_profile"  # spends the card-profile SerpApi envelope
    assert r.summary.get("unchanged", 0) > 0 and "published" not in r.summary and "speculation" not in r.summary


def test_value_the_page_does_not_say_is_held_as_speculation(db, cards, monkeypatch):
    c = cards["hdfc_millennia"]
    profile_card(c)
    misread = c.model_copy(deep=True)
    misread.fees.annual_paise = 50_000  # the page still says ₹1,000
    monkeypatch.setattr(refresh, "discover", lambda name, issuer, **kw: _official(c) if kw.get("page", True) else [])
    monkeypatch.setattr(refresh, "extract_terms", lambda *a, **k: misread)
    r = refresh.refresh_card(c.id)
    assert r.summary.get("speculation") == 1
    with db.begin() as conn:
        assert store.current(conn, c.id, "fees").value["annual_paise"] == 100_000


def test_cli_without_a_recorded_search_skips_and_spends_nothing(db, cards, capsys):
    profile_card(cards["hdfc_millennia"])
    assert scheduler.run_refresh_cli(["hdfc_millennia"], 3) == 0
    out = capsys.readouterr().out
    assert "skipped" in out and "no recorded search" in out
    with db.begin() as conn:
        assert conn.execute(select(credit_ledger).where(credit_ledger.c.cached.is_(False))).first() is None


def test_nightly_job_rotates_through_the_catalogue(db, cards, monkeypatch):
    for cid in ("hdfc_millennia", "sbi_cashback", "axis_atlas"):
        profile_card(cards[cid])
    monkeypatch.setattr(refresh, "refresh_card", lambda cid: refresh.CardRefresh(cid, "skipped", "test"))
    first = scheduler.tracked("card_refresh", lambda: scheduler.card_refresh_job(n=2))
    second = scheduler.tracked("card_refresh", lambda: scheduler.card_refresh_job(n=2))
    assert [r["card_id"] for r in first["cards"]] == ["axis_atlas", "hdfc_millennia"]
    assert [r["card_id"] for r in second["cards"]] == ["sbi_cashback", "axis_atlas"]


def test_scheduler_registers_refresh_but_stays_off_by_default():
    assert {j.id for j in scheduler.build_scheduler().get_jobs()} >= {"card_refresh", "launch_radar"}
    assert Settings.model_fields["scheduler_enabled"].default is False
