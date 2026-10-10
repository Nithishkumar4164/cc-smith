
from sqlalchemy import select

from cc_smith.db import owner_alert, speculation
from cc_smith.knowledge import store
from cc_smith.knowledge.pipeline import profile_card
from cc_smith.ops.outbox import drain


def test_seed_cards_publish_as_facts_from_recorded_evidence(db, cards):
    # Scapia's exclusions are only in a Scapia-hosted copy; the bank's page is bot-walled.
    expected = {("scapia_federal", "exclusions")}
    for c in cards.values():
        r = profile_card(c)
        spec = {(c.id, f.field) for f in r.fields if f.outcome == "speculation"}
        assert spec <= expected, (c.id, [f for f in r.fields if f.outcome == "speculation"])
    with db.begin() as conn:
        prof, meta = store.profile(conn, "hdfc_regalia_gold")
    assert prof.assessable()
    assert prof.fees.annual_paise == 250_000
    assert all(ref["official"] and ref["evidence_id"] for ref in meta["fees"]["refs"])


def test_rerun_with_same_values_only_bumps_as_of(db, cards):
    profile_card(cards["hdfc_millennia"])
    r = profile_card(cards["hdfc_millennia"])
    assert set(r.summary()) <= {"unchanged", "empty"}


def _bank_page_says(monkeypatch, old: str, new: str):
    """Simulate the issuer editing its page: recorded evidence with `old` replaced by `new`."""
    from dataclasses import replace

    from cc_smith.knowledge import pipeline
    from cc_smith.knowledge.fetcher import fetch as real_fetch

    def fake(url, refresh=False):
        ev = real_fetch(url)
        return replace(ev, id=ev.id + "-v2", text=ev.text.replace(old, new))

    monkeypatch.setattr(pipeline, "fetch", fake)


def test_bank_page_change_publishes_new_version_and_alerts(db, cards, monkeypatch):
    c = cards["hdfc_millennia"]
    profile_card(c)
    drain()
    _bank_page_says(monkeypatch, "fee: ₹1,000 plus", "fee: ₹2,500 plus")
    changed = c.model_copy(deep=True)
    changed.fees.annual_paise = 250_000
    changed.fees.joining_paise = 250_000
    changed.fees.src[0].quote = changed.fees.src[0].quote.replace("₹1,000", "₹2,500")
    r = profile_card(changed)
    assert {f.field: f.outcome for f in r.fields}["fees"] == "published"
    drain()
    with db.begin() as conn:
        alerts = [a.payload for a in conn.execute(select(owner_alert)).all()]
        assert store.current(conn, c.id, "fees").version == 2
    fee_alert = [a for a in alerts if a["field"] == "fees" and a["event_type"] == "published" and a["old"]]
    assert fee_alert and fee_alert[0]["large_change"] is True
    assert "₹2,500" in fee_alert[0]["refs"][0]["quote"]


def test_misread_value_with_a_genuine_quote_is_speculation(db, cards):
    c = cards["hdfc_millennia"]
    profile_card(c)
    misread = c.model_copy(deep=True)
    misread.fees.annual_paise = 50_000  # the quote on the page still says ₹1,000
    r = profile_card(misread)
    assert {f.field: f.outcome for f in r.fields}["fees"] == "speculation"
    with db.begin() as conn:
        assert store.current(conn, c.id, "fees").value["annual_paise"] == 100_000


def test_unofficial_source_becomes_speculation_and_never_a_fact(db, cards):
    c = cards["hdfc_millennia"]
    profile_card(c)
    bad = c.model_copy(deep=True)
    bad.fees.annual_paise = 0
    bad.fees.src[0].url = "https://www.paisabazaar.com/hdfc-millennia"
    r = profile_card(bad)
    assert {f.field: f.outcome for f in r.fields}["fees"] == "speculation"
    with db.begin() as conn:
        assert store.current(conn, c.id, "fees").value["annual_paise"] == 100_000
        spec = conn.execute(select(speculation)).all()
    assert spec[0].origin == "not_official"


def test_quote_not_on_page_becomes_speculation(db, cards):
    bad = cards["axis_atlas"].model_copy(deep=True)
    bad.earn_rules[0].src[0].quote = "Earn 10 EDGE Miles for every Rs. 100 spent on all travel with no cap"
    r = profile_card(bad)
    assert {f.field: f.outcome for f in r.fields}["earn_rules"] == "speculation"


def test_range_check_failure_is_speculation(db, cards):
    bad = cards["hdfc_millennia"].model_copy(deep=True)
    bad.earn_rules[0].rate.bp = 5_000
    r = profile_card(bad)
    assert {f.field: f.outcome for f in r.fields}["earn_rules"] == "speculation"


def test_rollback_restores_previous_version(db, cards, monkeypatch):
    c = cards["hdfc_millennia"]
    profile_card(c)
    _bank_page_says(monkeypatch, "fee: ₹1,000 plus", "fee: ₹2,500 plus")
    changed = c.model_copy(deep=True)
    changed.fees.annual_paise = 250_000
    changed.fees.joining_paise = 250_000
    changed.fees.src[0].quote = changed.fees.src[0].quote.replace("₹1,000", "₹2,500")
    assert {f.field: f.outcome for f in profile_card(changed).fields}["fees"] == "published"
    with db.begin() as conn:
        assert store.rollback(conn, c.id, "fees", "re-check mismatch")
        assert store.current(conn, c.id, "fees").value["annual_paise"] == 100_000


def test_card_with_unconfirmed_exclusions_is_not_scored(db, cards):
    """Earn rules are facts but exclusions failed the checks: scoring would let the card
    earn on fuel or rent, so it stays 'can't assess yet' until they are confirmed."""
    bad = cards["hdfc_millennia"].model_copy(deep=True)
    bad.exclusions[0].src[0].url = "https://www.paisabazaar.com/hdfc-millennia"
    profile_card(bad)
    with db.begin() as conn:
        prof, meta = store.profile(conn, "hdfc_millennia")
    assert not prof.assessable()
    assert meta["earn_rules"]["blocked"] == "exclusions not confirmed"
