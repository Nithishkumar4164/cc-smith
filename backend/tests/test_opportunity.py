"""Opportunity cost at checkout: a card is judged by what it earns now plus what the
rest of the month still earns after it is used (owner decision, 2026-10-09)."""

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


def _pay(client, holdings, spends, merchant, amount, channel="online"):
    u = {"X-User-Id": client.post("/users").json()["user_id"]}
    client.put("/me/holdings", json=[{"card_id": h} for h in holdings], headers=u)
    client.put("/me/spends", json={k: v * R for k, v in spends.items()}, headers=u)
    return client.post("/pay", json={"merchant": merchant, "amount_paise": amount * R, "channel": channel}, headers=u).json()


LIGHT = {"swiggy": 6000, "amazon": 8000, "online": 30000, "other": 10000}
HEAVY = {"swiggy": 6000, "amazon": 8000, "online": 90000, "other": 10000}


@pytest.mark.parametrize("spends", [LIGHT, HEAVY])
@pytest.mark.parametrize("order", [["hdfc_millennia", "sbi_cashback"], ["sbi_cashback", "hdfc_millennia"]])
def test_swiggy_uses_millennia_and_keeps_sbi_broad_cap_whatever_the_card_order(client, order, spends):
    """The owner's case: both earn 5% on Swiggy, but SBI Cashback's 5% covers all online
    spends while Millennia's covers 10 merchants, so Millennia should be spent first."""
    r = _pay(client, order, spends, "Swiggy", 1_200)
    assert r["best"]["card_id"] == "hdfc_millennia"
    assert r["best"]["reward_paise"] == 60 * R
    assert "Cashback SBI Card earns the same now" in r["text"]


def test_when_sbi_cap_fills_the_text_names_the_cost(client):
    r = _pay(client, ["sbi_cashback", "hdfc_millennia"], HEAVY, "Swiggy", 1_200)
    ranked = {o["card_id"]: o for o in r["ranked"]}
    assert ranked["hdfc_millennia"]["later_paise"] - ranked["sbi_cashback"]["later_paise"] == 60 * R
    assert "would use up about ₹60" in r["text"]


def test_month_best_card_can_earn_less_on_this_payment(client):
    """Live+ pays 10% on groceries but heavy offline dining already fills its ₹1,200 cap;
    spending the cap on BigBasket costs more later than SBI Cashback's 5% loses now."""
    r = _pay(client, ["hsbc_live_plus", "sbi_cashback"], {"dining": 20000, "bigbasket": 3000, "other": 10000}, "BigBasket", 1_000)
    ranked = {o["card_id"]: o for o in r["ranked"]}
    assert r["best"]["card_id"] == "sbi_cashback"
    assert ranked["hsbc_live_plus"]["reward_paise"] > ranked["sbi_cashback"]["reward_paise"]
    assert ranked["sbi_cashback"]["month_paise"] > ranked["hsbc_live_plus"]["month_paise"]
    assert "less than HSBC Live+ Credit Card now" in r["text"] and "more over the month" in r["text"]


def test_without_spends_pay_ranks_by_this_payment(client):
    u = {"X-User-Id": client.post("/users").json()["user_id"]}
    client.put("/me/holdings", json=[{"card_id": "hsbc_live_plus"}, {"card_id": "sbi_cashback"}], headers=u)
    r = client.post("/pay", json={"merchant": "BigBasket", "amount_paise": 1_000 * R, "channel": "online"}, headers=u).json()
    assert r["best"]["card_id"] == "hsbc_live_plus"
    assert r["best"]["month_paise"] is None
