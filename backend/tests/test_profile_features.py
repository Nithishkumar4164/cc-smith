"""Memberships, spends grouped under categories, held-card LTF/FYF, credit limits and the notice board."""

import pytest
from fastapi.testclient import TestClient

from cc_smith.api.main import app
from cc_smith.knowledge.pipeline import profile_card
from cc_smith.users.service import category_totals, spend_lines

R = 100


@pytest.fixture
def client(db, cards):
    for c in cards.values():
        profile_card(c)
    return TestClient(app)


@pytest.fixture
def user(client):
    return {"X-User-Id": client.post("/users").json()["user_id"]}


def test_category_amount_is_the_total_and_merchants_are_part_of_it():
    lines = {line.key: line.monthly_paise for line in spend_lines({"dining": 6_000 * R, "swiggy": 3_000 * R, "zomato": 1_000 * R})}
    assert lines == {"swiggy": 3_000 * R, "zomato": 1_000 * R, "dining": 2_000 * R}
    # Merchants above the category amount: the category is their sum, nothing left over.
    lines = {line.key: line.monthly_paise for line in spend_lines({"dining": 2_000 * R, "swiggy": 3_000 * R})}
    assert lines == {"swiggy": 3_000 * R}
    assert category_totals({"dining": 2_000 * R, "swiggy": 3_000 * R, "amazon": 5_000 * R}) == {"dining": 3_000 * R, "online": 5_000 * R}


def test_cards_list_their_memberships_and_kiwi_neon_changes_the_pick(client, user):
    cards = {c["id"]: c for c in client.get("/cards").json()}
    assert [m["key"] for m in cards["icici_amazon_pay"]["memberships"]] == ["amazon_prime"]
    assert [m["key"] for m in cards["kiwi_yes_klick"]["memberships"]] == ["kiwi_neon"]
    assert cards["hdfc_millennia"]["memberships"] == []
    client.put("/me/holdings", json=[{"card_id": "kiwi_yes_klick"}], headers=user)
    pay = {"merchant": "chai stall", "amount_paise": 1_000 * R, "channel": "upi"}
    assert client.post("/pay", json=pay, headers=user).json()["best"]["reward_paise"] == 15 * R
    client.put("/me/profile", json={"flags": ["kiwi_neon"]}, headers=user)
    assert client.post("/pay", json=pay, headers=user).json()["best"]["reward_paise"] == 20 * R


def test_ltf_held_card_pays_no_fee_in_finder(client, user):
    client.put("/me/spends", json={"other": 2_000 * R}, headers=user)  # far below Regalia Gold's ₹4 lakh waiver
    client.put("/me/holdings", json=[{"card_id": "hdfc_regalia_gold"}], headers=user)
    std = client.post("/finder", json={"max_new": 1}, headers=user).json()["base_cards"][0]
    assert std["fee_paise"] == 2_950 * R  # ₹2,500 + 18% GST
    client.put("/me/holdings", json=[{"card_id": "hdfc_regalia_gold", "fee_status": "ltf"}], headers=user)
    ltf = client.post("/finder", json={"max_new": 1}, headers=user).json()["base_cards"][0]
    assert ltf["fee_paise"] == 0 and ltf["net_paise"] == std["net_paise"] + 2_950 * R


def test_shared_limit_available_credit_and_checkout_skip(client, user):
    client.put("/me/pools", json=[{"id": "hdfc", "name": "HDFC shared", "limit_paise": 50_000 * R}], headers=user)
    client.put("/me/holdings", json=[
        {"card_id": "hdfc_millennia", "pool_id": "hdfc", "balance_paise": 30_000 * R},
        {"card_id": "hdfc_swiggy_blck", "pool_id": "hdfc", "balance_paise": 15_000 * R},
        {"card_id": "hsbc_live_plus", "credit_limit_paise": 100_000 * R, "balance_paise": 0},
    ], headers=user)
    credit = {c["card_id"]: c for c in client.get("/me/credit", headers=user).json()}
    assert credit["hdfc_millennia"]["available_paise"] == 5_000 * R  # ₹50,000 pool − ₹45,000 across both cards
    assert credit["hdfc_swiggy_blck"]["available_paise"] == 5_000 * R
    assert credit["hdfc_millennia"]["utilisation_bp"] == 9_000
    # Swiggy BLCK would win at Swiggy (10%) but the HDFC pool has only ₹5,000 left.
    r = client.post("/pay", json={"merchant": "Swiggy", "amount_paise": 8_000 * R}, headers=user).json()
    assert r["best"]["card_id"] == "hsbc_live_plus"
    blck = next(o for o in r["ranked"] if o["card_id"] == "hdfc_swiggy_blck")
    assert "insufficient_credit:500000" in blck["reason_codes"]
    # A logged payment uses the pool; paying the bill frees it.
    client.post("/pay/confirm", json={"card_id": "hdfc_millennia", "merchant": "Amazon", "amount_paise": 2_000 * R}, headers=user)
    assert {c["card_id"]: c for c in client.get("/me/credit", headers=user).json()}["hdfc_swiggy_blck"]["available_paise"] == 3_000 * R
    after = {c["card_id"]: c for c in client.post("/me/cards/hdfc_millennia/bill-paid", json={}, headers=user).json()}
    assert after["hdfc_millennia"]["outstanding_paise"] == 0
    assert after["hdfc_swiggy_blck"]["available_paise"] == 35_000 * R


def test_notice_board_explains_fees_utilisation_and_changes(client, user, cards, monkeypatch):
    client.put("/me/spends", json={"other": 10_000 * R, "grocery": 5_000 * R}, headers=user)
    client.put("/me/holdings", json=[{"card_id": "hdfc_regalia_gold", "credit_limit_paise": 100_000 * R, "balance_paise": 60_000 * R, "renewal_month": 3}], headers=user)
    notices = client.get("/me/notices", headers=user).json()
    kinds = {n["kind"] for n in notices}
    assert {"fee", "credit"} <= kinds
    fee = next(n for n in notices if n["id"] == "fee:hdfc_regalia_gold")
    assert "waiver needs ₹4,00,000" in fee["reason"] and fee["refs"] and fee["due"].endswith("-03-01")
    util = next(n for n in notices if n["kind"] == "credit")
    assert util["severity"] == "watch" and "60%" in util["title"]
    assert all(n["reason"] and n["action"] for n in notices)


def test_fee_offer_notice_for_a_card_that_suits_you(client, user):
    from pathlib import Path

    from cc_smith.db import engine
    from cc_smith.knowledge import offers

    with engine().begin() as c:
        counts = offers.load(c, Path(__file__).resolve().parents[1] / "fixtures" / "offers" / "fees1.json")
    assert counts == {"fact": 4, "speculation": 1}
    client.put("/me/spends", json={"swiggy": 8_000 * R, "online": 6_000 * R}, headers=user)
    client.put("/me/holdings", json=[{"card_id": "hdfc_regalia_gold"}], headers=user)
    notices = {n["id"]: n for n in client.get("/me/market/offers", headers=user).json()}
    blck = notices["feeoffer:hdfc_swiggy_blck_joining_waiver_75k"]
    assert blck["kind"] == "fee_offer" and blck["tier"] == "fact" and blck["rupees_paise"] > 0
    assert "waived on ₹75,000 spend" in blck["title"] and blck["refs"][0]["url"].startswith("https://www.hdfc.bank.in/")
    reported = [n for n in notices.values() if n["id"].startswith("feeoffer:cardinsider")]
    assert all(n["tier"] == "speculation" for n in reported)
    finder = client.post("/finder", json={"max_new": 1}, headers=user).json()
    assert any(p["fee_offers"] for p in finder["portfolios"])


STORY_SPENDS = {k: v * R for k, v in {"amazon": 6000, "flipkart": 2000, "swiggy": 5000, "zomato": 2000, "grocery": 10000,
                                      "dining": 4000, "travel": 8000, "fuel": 3000, "utilities": 4000, "other": 10000}.items()}


def test_finder_finds_card_sets_when_greedy_routing_alone_shows_no_gain(client, user):
    """Regression: Millennia + Live+ got no card sets, though adding Swiggy BLCK pays once
    fee waivers and milestones are kept (assess and the notice board both said so)."""
    client.put("/me/profile", json={"flags": ["amazon_prime"]}, headers=user)
    client.put("/me/holdings", json=[{"card_id": "hdfc_millennia"}, {"card_id": "hsbc_live_plus"}], headers=user)
    client.put("/me/spends", json=STORY_SPENDS, headers=user)
    finder = client.post("/finder", json={"max_new": 3}, headers=user).json()
    assess = client.post("/finder/assess", json={"card_id": "hdfc_swiggy_blck"}, headers=user).json()
    assert assess["gain_paise"] > 0
    assert finder["portfolios"], finder
    assert finder["portfolios"][0]["gain_paise"] >= assess["gain_paise"]


def test_pay_text_names_credit_when_no_card_has_enough(client, user):
    client.put("/me/holdings", json=[{"card_id": "hdfc_millennia", "credit_limit_paise": 50_000 * R, "balance_paise": 0}], headers=user)
    r = client.post("/pay", json={"merchant": "MakeMyTrip", "amount_paise": 140_000 * R}, headers=user).json()
    assert r["best"] is None
    assert "credit available" in r["text"] and "UPI" not in r["text"]


def test_notices_hold_only_your_cards_and_offers_move_to_market(client, user):
    from pathlib import Path

    from cc_smith.db import engine
    from cc_smith.knowledge import offers

    with engine().begin() as c:
        offers.load(c, Path(__file__).resolve().parents[1] / "fixtures" / "offers" / "fees1.json")
    client.put("/me/holdings", json=[{"card_id": "hsbc_live_plus", "credit_limit_paise": 100_000 * R, "balance_paise": 40_000 * R}], headers=user)
    client.put("/me/spends", json={"swiggy": 8_000 * R, "online": 6_000 * R}, headers=user)
    notices = client.get("/me/notices", headers=user).json()
    # Notices are only about your own cards; offers on other cards are discovery (Market).
    assert "credit" in {n["kind"] for n in notices}
    assert "fee_offer" not in {n["kind"] for n in notices}
    assert {n["kind"] for n in client.get("/me/market/offers", headers=user).json()} == {"fee_offer"}


def test_utilisation_notice_is_general_guidance_without_source(client, user):
    client.put("/me/holdings", json=[{"card_id": "hdfc_millennia", "credit_limit_paise": 100_000 * R, "balance_paise": 50_000 * R}], headers=user)
    util = next(n for n in client.get("/me/notices", headers=user).json() if n["kind"] == "credit")
    assert util["tier"] == "guidance" and util["refs"] == []
    assert "General guidance, not a card term" in util["reason"]


def test_prime_answer_changes_the_reward_and_unanswered_says_what_it_would_be(client, user):
    client.put("/me/holdings", json=[{"card_id": "icici_amazon_pay"}], headers=user)
    pay = {"merchant": "Amazon", "amount_paise": 3_000 * R}
    unanswered = client.post("/pay", json=pay, headers=user).json()["best"]
    assert unanswered["reward_paise"] == 90 * R  # 3% until you say you have Prime
    assert unanswered["if_answered"] == [{"key": "amazon_prime", "question": "Do you have Amazon Prime?", "reward_paise": 150 * R}]
    me = client.put("/me/answers", json={"amazon_prime": True}, headers=user).json()
    assert me["answers"]["amazon_prime"] is True and "amazon_prime" in me["profile"]["flags"]
    yes = client.post("/pay", json=pay, headers=user).json()["best"]
    assert yes["reward_paise"] == 150 * R and yes["if_answered"] == []
    client.put("/me/answers", json={"amazon_prime": False}, headers=user)
    no = client.post("/pay", json=pay, headers=user).json()["best"]
    assert no["reward_paise"] == 90 * R and no["if_answered"] == []  # answered: no more nudging


def test_offer_condition_eligibility_moves_from_unknown_to_not_for_you(client, user):
    from pathlib import Path

    from cc_smith.db import engine
    from cc_smith.knowledge import offers

    with engine().begin() as c:
        offers.load(c, Path(__file__).resolve().parents[1] / "fixtures" / "offers" / "fees1.json")
    client.put("/me/spends", json={"swiggy": 8_000 * R, "online": 6_000 * R}, headers=user)
    client.put("/me/holdings", json=[{"card_id": "hdfc_regalia_gold"}], headers=user)

    def ornge():
        return next(n for n in client.get("/me/market/offers", headers=user).json() if n["id"] == "feeoffer:hdfc_swiggy_ornge_ltf_corporate")

    first = ornge()
    assert first["eligibility"] == "unknown" and first["requires"][0]["key"] == "select_corporate_employee"
    client.put("/me/answers", json={"select_corporate_employee": False}, headers=user)
    offers = client.get("/me/market/offers", headers=user).json()
    assert offers[-1]["id"] == "feeoffer:hdfc_swiggy_ornge_ltf_corporate" and offers[-1]["eligibility"] == "no"
    client.put("/me/answers", json={"select_corporate_employee": True}, headers=user)
    assert ornge()["eligibility"] == "yes"


def test_saving_preferences_keeps_answers_and_unknown_conditions_are_rejected(client, user):
    client.put("/me/answers", json={"kiwi_neon": True}, headers=user)
    me = client.put("/me/profile", json={"reward_preference": "cashback"}, headers=user).json()
    assert me["answers"] == {"kiwi_neon": True}
    assert "kiwi_neon" in me["profile"]["flags"]  # the engine still applies Kiwi Neon
    assert client.put("/me/answers", json={"has_a_yacht": True}, headers=user).status_code == 422
