from datetime import date
from pathlib import Path

from sqlalchemy import select

from cc_smith.db import offer
from cc_smith.knowledge import offers

BATCH = Path(__file__).resolve().parents[1] / "fixtures" / "offers" / "batch1.json"
R = 100


def test_recorded_offers_pass_the_quote_and_number_checks(db):
    with db.begin() as c:
        counts = offers.load(c, BATCH)
    assert counts == {"fact": 21, "speculation": 0}


def test_offer_with_a_number_not_in_its_quote_is_speculation(db, tmp_path):
    import json

    data = json.loads(BATCH.read_text())
    bad = next(o for o in data["offers"] if o["id"] == "hdfc_myntra_10_1000")
    bad["max_paise"] = 300_000  # page says ₹1,000; ₹3,000 appears nowhere in the quote
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"offers": [bad]}))
    with db.begin() as c:
        assert offers.load(c, path) == {"fact": 0, "speculation": 1}
        assert "max_paise" in c.execute(select(offer.c.reason)).scalar_one()


def test_checkout_offers_match_issuer_card_and_date(db):
    with db.begin() as c:
        offers.load(c, BATCH)
        held = [("hdfc_millennia", "HDFC Bank"), ("hsbc_live_plus", "HSBC")]
        found = offers.for_checkout(c, "myntra", "online", held, today=date(2026, 10, 10))
        ids = {f["offer"].id: f["card_ids"] for f in found}
        assert ids["hdfc_myntra_10_1000"] == ["hdfc_millennia"]
        assert "hdfc_myntra_tataneu_6cb" not in ids  # Tata Neu card not held
        assert "hsbc_taj_myntra_20" not in ids  # HSBC Taj card not held
        later = {f["offer"].id for f in offers.for_checkout(c, "myntra", "online", held, today=date(2026, 10, 26))}
        assert "hdfc_myntra_10_1000" not in later  # ended 25 Oct
        o = next(f["offer"] for f in found if f["offer"].id == "hdfc_myntra_10_1000")
        assert offers.estimate(o, 4_000 * R) == 0  # below ₹5,000 minimum
        assert offers.estimate(o, 20_000 * R) == 1_000 * R  # 10% capped at ₹1,000


def test_up_to_percentage_offers_show_a_ceiling_and_no_estimate(db):
    with db.begin() as c:
        offers.load(c, BATCH)
        rows = {o.id: o for o in c.execute(select(offer)).all()}
    mmt = rows["hdfc_makemytrip_easyemi_25"]   # "Up to 25% … max ₹11,300, min ₹5,000"
    myntra = rows["hdfc_myntra_10_1000"]        # "10% up to ₹1,000": fixed rate with a cap
    assert offers.is_up_to(mmt) and not offers.is_up_to(myntra)
    assert offers.estimate(mmt, 20_000 * R) is None
    assert offers.up_to_ceiling(mmt, 20_000 * R) == 5_000 * R      # 25% of ₹20,000, under the ₹11,300 max
    assert offers.up_to_ceiling(mmt, 100_000 * R) == 11_300 * R    # the offer's own maximum
    assert offers.estimate(myntra, 8_000 * R) == 800 * R
