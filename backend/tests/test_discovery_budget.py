"""Demo bureau fetch, budget that fills and adapts itself, and launch notices (10 Oct 2026)."""

from datetime import UTC, date, datetime

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
    return {"X-User-Id": client.post("/users").json()["user_id"]}


def test_demo_bureau_fetch_needs_consent_and_the_code(client, user):
    assert client.post("/me/discovery/bureau/start", json={"phone": "9876543210", "consent": False}, headers=user).status_code == 422
    start = client.post("/me/discovery/bureau/start", json={"phone": "+91 98765 43210", "consent": True}, headers=user).json()
    assert start["mock"] is True and len(start["demo_otp"]) == 6
    wrong = "000000" if start["demo_otp"] != "000000" else "111111"
    assert client.post("/me/discovery/bureau/verify", json={"request_id": start["request_id"], "otp": wrong}, headers=user).status_code == 422
    out = client.post("/me/discovery/bureau/verify", json={"request_id": start["request_id"], "otp": start["demo_otp"]}, headers=user).json()
    assert out["mock"] is True and out["stored"]["source"] == "demo_bureau"
    report = out["report"]
    assert 2 <= len(report["accounts"]) <= 3 and all(a["credit_limit_paise"] > 0 for a in report["accounts"])
    # Same phone, same simulated file: the demo repeats exactly.
    again = client.post("/me/discovery/bureau/start", json={"phone": "9876543210", "consent": True}, headers=user).json()
    out2 = client.post("/me/discovery/bureau/verify", json={"request_id": again["request_id"], "otp": again["demo_otp"]}, headers=user).json()
    assert [a["lender"] for a in out2["report"]["accounts"]] == [a["lender"] for a in report["accounts"]]


def test_bureau_names_the_exact_card_with_open_date_and_marks_it_held_once_added(client, user):
    start = client.post("/me/discovery/bureau/start", json={"phone": "9876543210", "consent": True}, headers=user).json()
    out = client.post("/me/discovery/bureau/verify", json={"request_id": start["request_id"], "otp": start["demo_otp"]}, headers=user).json()
    accts = out["report"]["accounts"]
    names = {c["id"]: c for c in client.get("/cards").json()}
    assert all(a["card_id"] in names and a["card_name"] == names[a["card_id"]]["name"] for a in accts)
    assert all(a["opened"] < out["report"]["report_date"] for a in accts)
    assert len({a["lender"] for a in accts}) == len(accts)  # one card per bank
    assert all(a["held_card_id"] is None for a in accts)
    # Added with the bureau's limit: a second fetch recognises them as held by product, not by guess.
    client.put("/me/holdings", json=[{"card_id": a["card_id"], "credit_limit_paise": a["credit_limit_paise"], "balance_paise": 0}
                                     for a in accts], headers=user)
    again = client.post("/me/discovery/bureau/start", json={"phone": "9876543210", "consent": True}, headers=user).json()
    out2 = client.post("/me/discovery/bureau/verify", json={"request_id": again["request_id"], "otp": again["demo_otp"]}, headers=user).json()
    assert [a["held_card_id"] for a in out2["report"]["accounts"]] == [a["card_id"] for a in accts]


def test_demo_import_fills_the_budget_and_is_not_money_owed(client, user):
    client.put("/me/holdings", json=[{"card_id": "hdfc_millennia", "credit_limit_paise": 100_000 * R, "balance_paise": 0}], headers=user)
    out = client.post("/me/budget/import-demo", json={"sources": ["sms", "email"]}, headers=user).json()
    assert out["mock"] is True and out["transactions"] > 30
    lines = {line["key"]: line for line in out["budget"]["lines"]}
    assert lines["dining"]["budget_paise"] == lines["dining"]["last_month_paise"] > 0
    assert lines["swiggy"]["kind"] == "merchant" and not lines["swiggy"]["pinned"]
    assert out["budget"]["adapted_from"] == out["month"]
    # Importing again adds nothing (idempotent), and demo spends are not outstanding.
    assert client.post("/me/budget/import-demo", json={}, headers=user).json()["budget"]["lines"] == out["budget"]["lines"]
    credit = client.get("/me/credit", headers=user).json()[0]
    assert credit["outstanding_paise"] == 0
    # Finder works off the imported budget.
    assert client.post("/finder", json={"max_new": 1}, headers=user).status_code == 200


def test_budget_edit_pins_and_reset_returns_to_last_month(client, user):
    client.post("/me/budget/import-demo", json={}, headers=user)
    b = client.put("/me/budget", json={"dining": 5_000 * R}, headers=user).json()
    dining = next(line for line in b["lines"] if line["key"] == "dining")
    assert dining["budget_paise"] == 5_000 * R and dining["pinned"]
    b = client.put("/me/budget", json={"dining": None}, headers=user).json()
    dining = next(line for line in b["lines"] if line["key"] == "dining")
    assert not dining["pinned"] and dining["budget_paise"] == dining["last_month_paise"]
    assert client.put("/me/budget", json={"spaceships": 1}, headers=user).status_code == 422


def test_new_month_adapts_unpinned_lines_but_keeps_edits(db, client, user):
    from cc_smith.ledger import service as ledger
    from cc_smith.users import budget

    uid = user["X-User-Id"]
    with db.begin() as c:
        ledger.record(c, uid, card_id="hdfc_millennia", amount_paise=3_000 * R, merchant_key="dmart", merchant_name="DMart",
                      category="grocery", channel="offline", reward_paise=0, cap_use={}, source="checkout",
                      ts=datetime(2026, 9, 12, 12, tzinfo=UTC))
        ledger.record(c, uid, card_id="hdfc_millennia", amount_paise=1_000 * R, merchant_key="swiggy", merchant_name="Swiggy",
                      category="dining", channel="online", reward_paise=0, cap_use={}, source="checkout",
                      ts=datetime(2026, 9, 20, 12, tzinfo=UTC))
        budget.edit(c, uid, {"dining": 8_000 * R}, today=date(2026, 9, 25))   # pinned in September
        view = budget.view(c, uid, today=date(2026, 10, 2))                      # first look in October
    lines = {line["key"]: line for line in view["lines"]}
    assert view["adapted_from"] == "2026-09"
    assert lines["grocery"]["budget_paise"] == 3_000 * R      # adapted to September's actual
    assert lines["dining"]["budget_paise"] == 8_000 * R       # edited, so kept


def test_launch_notice_only_above_the_threshold(db, client, user, cards):
    from cc_smith.db import launch_candidate

    with db.begin() as c:
        c.execute(launch_candidate.insert().values(dedupe_key="hsbc_india:live", name="HSBC Live+ Credit Card", issuer="HSBC India",
                                                   card_id="hsbc_live_plus", status="profiled", refs=[], summary="Profiled."))
    client.put("/me/holdings", json=[{"card_id": "hdfc_millennia"}], headers=user)
    client.put("/me/spends", json={"other": 1_000 * R}, headers=user)
    assert not [n for n in client.get("/me/notices", headers=user).json() if n["kind"] == "launch"]
    client.put("/me/spends", json={"dining": 12_000 * R, "grocery": 8_000 * R, "online": 6_000 * R}, headers=user)
    launch = [n for n in client.get("/me/notices", headers=user).json() if n["kind"] == "launch"]
    assert len(launch) == 1 and launch[0]["card_id"] == "hsbc_live_plus" and launch[0]["rupees_paise"] >= 2_000 * R


def test_custom_annual_fee_replaces_the_catalogue_fee_in_finder(client, user):
    client.put("/me/spends", json={"dining": 2_000 * R}, headers=user)
    hold = {"card_id": "hdfc_regalia_gold", "credit_limit_paise": 100_000 * R, "balance_paise": 0}

    def card(**fee):
        client.put("/me/holdings", json=[{**hold, **fee}], headers=user)
        return next(x for x in client.post("/finder", json={"max_new": 1}, headers=user).json()["base_cards"] if x["card_id"] == "hdfc_regalia_gold")

    standard = card()
    assert standard["fee_paise"] > 0  # the bank's fee incl. GST, not waived on ₹24,000 a year
    custom = card(fee_status="custom", annual_fee_paise=500 * R)
    assert custom["fee_paise"] == 500 * R
    assert client.get("/me", headers=user).json()["holdings"][0]["annual_fee_paise"] == 500 * R
    # The amount is ignored unless the status is custom.
    assert card(fee_status="ltf", annual_fee_paise=500 * R)["fee_paise"] == 0
    assert client.get("/me", headers=user).json()["holdings"][0]["annual_fee_paise"] is None
