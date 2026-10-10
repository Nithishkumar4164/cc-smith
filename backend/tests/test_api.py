import pytest
from fastapi.testclient import TestClient

from cc_smith.api.main import app
from cc_smith.knowledge.pipeline import profile_card

R = 100


@pytest.fixture
def client(db, cards):
    for c in cards.values():
        profile_card(c)
    return TestClient(app)


@pytest.fixture
def user(client):
    uid = client.post("/users").json()["user_id"]
    return {"X-User-Id": uid}


def test_catalogue_lists_seed_cards_with_provenance(client):
    cards = client.get("/cards").json()
    assert {c["id"] for c in cards} >= {"hdfc_millennia", "axis_atlas"}
    d = client.get("/cards/hdfc_millennia").json()
    ref = d["fields"]["fees"]["refs"][0]
    assert ref["url"].startswith("https://www.hdfc.bank.in/") and ref["quote"] and ref["official"]


def test_checkout_picks_best_held_card_and_caps_after_confirm(client, user):
    client.put("/me/holdings", json=[{"card_id": "hdfc_millennia"}, {"card_id": "hdfc_regalia_gold"}], headers=user)
    r = client.post("/pay", json={"merchant": "Amazon", "amount_paise": 10_000 * R}, headers=user).json()
    assert r["best"]["card_id"] == "hdfc_millennia"
    assert r["best"]["reward_paise"] == 500 * R
    assert "Millennia" in r["text"]
    # Use ₹1,000 of the ₹1,000 monthly 5% cap: 2 × ₹10,000.
    for i in range(2):
        client.post("/pay/confirm", json={"card_id": "hdfc_millennia", "merchant": "Amazon", "amount_paise": 10_000 * R,
                                          "idempotency_key": f"k{i}"}, headers=user)
    r = client.post("/pay", json={"merchant": "Amazon", "amount_paise": 10_000 * R}, headers=user).json()
    assert r["best"]["card_id"] == "hdfc_regalia_gold"
    mill = next(o for o in r["ranked"] if o["card_id"] == "hdfc_millennia")
    assert mill["reward_paise"] == 0


def test_checkout_fuel_says_no_card_earns(client, user):
    client.put("/me/holdings", json=[{"card_id": "hdfc_millennia"}], headers=user)
    r = client.post("/pay", json={"merchant": "BPCL", "amount_paise": 2_000 * R}, headers=user).json()
    assert r["best"]["reward_paise"] == 0
    assert "No card earns" in r["text"]


def test_finder_recommends_portfolio_in_rupees(client, user):
    client.put("/me/profile", json={"flags": ["amazon_prime"]}, headers=user)
    client.put("/me/spends", json={"amazon": 8_000 * R, "swiggy": 6_000 * R, "flipkart": 3_000 * R, "travel": 10_000 * R,
                                   "grocery": 8_000 * R, "fuel": 4_000 * R, "other": 10_000 * R}, headers=user)
    out = client.post("/finder", json={"max_new": 3}, headers=user).json()
    assert out["portfolios"], out
    top = out["portfolios"][0]
    assert top["gain_paise"] > 0
    assert sum(c["net_paise"] for c in top["cards"]) == top["gain_paise"] + out["base_net_paise"]
    assert out["unearned"].get("fuel") == 48_000 * R


def test_user_report_becomes_speculation(client, user):
    r = client.post("/cards/axis_atlas/report", json={"field": "earn_rules", "message": "Travel miles now 4 per ₹100"}, headers=user)
    assert r.status_code == 202
    spec = client.get("/cards/axis_atlas").json()["speculation"]
    assert spec[0]["origin"] == "user_report"


def test_tie_prefers_uncapped_card(client, user):
    client.put("/me/profile", json={"flags": ["amazon_prime"]}, headers=user)
    client.put("/me/holdings", json=[{"card_id": "hdfc_millennia"}, {"card_id": "icici_amazon_pay"}], headers=user)
    r = client.post("/pay", json={"merchant": "Amazon", "amount_paise": 3_000 * R}, headers=user).json()
    assert r["best"]["card_id"] == "icici_amazon_pay"
    assert "earns the same" in r["text"]
    assert r["best"]["notes"] == ["5% on Amazon"]


def test_upi_with_no_rupay_card_says_so(client, user):
    client.put("/me/holdings", json=[{"card_id": "hdfc_millennia"}], headers=user)
    r = client.post("/pay", json={"merchant": "chai stall", "amount_paise": 50 * R, "channel": "upi"}, headers=user).json()
    assert r["best"] is None
    assert "RuPay" in r["text"]


def test_checkout_shows_bank_offer_hint_without_changing_the_pick(client, user, monkeypatch):
    from datetime import date
    from pathlib import Path

    from cc_smith.db import engine
    from cc_smith.knowledge import offers

    with engine().begin() as c:
        offers.load(c, Path(__file__).resolve().parents[1] / "fixtures" / "offers" / "batch1.json")
    real = offers.for_checkout
    monkeypatch.setattr(offers, "for_checkout", lambda *a, **k: real(*a, today=date(2026, 10, 10)))
    client.put("/me/holdings", json=[{"card_id": "hdfc_millennia"}, {"card_id": "hsbc_live_plus"}], headers=user)
    r = client.post("/pay", json={"merchant": "myntra.com", "amount_paise": 8_000 * R}, headers=user).json()
    assert r["best"]["card_id"] == "hsbc_live_plus"
    assert r["offers"][0]["issuer"] == "HDFC Bank" and r["offers"][0]["tier"] == "fact"
    assert r["offers"][0]["est_saving_paise"] == 800 * R
    assert "₹1,200 in all" in r["text"]


def test_logged_payments_build_the_airtel_base_and_unlock_the_bill_cap(client, user):
    client.put("/me/holdings", json=[{"card_id": "axis_airtel"}], headers=user)
    first = client.post("/pay", json={"merchant": "Airtel", "amount_paise": 999 * R}, headers=user).json()
    assert first["best"]["reward_paise"] == 0
    assert any("twice the base cashback" in n for n in first["best"]["notes"])
    client.post("/pay/confirm", json={"card_id": "axis_airtel", "merchant": "DMart", "amount_paise": 3_000 * R,
                                      "idempotency_key": "base-1"}, headers=user)
    after = client.post("/pay", json={"merchant": "Airtel", "amount_paise": 999 * R}, headers=user).json()
    assert after["best"]["reward_paise"] == 60 * R  # 2 x ₹30 base from the ₹3,000 DMart payment
