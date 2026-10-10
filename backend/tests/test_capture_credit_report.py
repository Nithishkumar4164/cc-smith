"""Credit report upload end to end with a synthetic CIBIL-like PDF."""
# ruff: noqa: F811  (pytest fixtures imported from capture_app are redefined as test arguments)

import json

from capture_app import capture_client, capture_user, hold  # noqa: F401  fixtures used as test arguments
from capture_docs import credit_report_pdf

from cc_smith.users import service as users

R = 100


def _upload(client, user, data, consent="true", password=None):
    form = {"consent": consent} if consent is not None else {}
    if password:
        form["password"] = password
    return client.post("/me/capture/credit-report", files={"file": ("report.pdf", data, "application/pdf")}, data=form, headers=user)


def test_consent_is_required(capture_client, capture_user):
    for consent in (None, "false"):
        r = _upload(capture_client, capture_user, credit_report_pdf(), consent=consent)
        assert r.status_code == 422 and r.json()["detail"]["code"] == "consent_required"


def test_report_gives_score_cards_limits_and_enquiries_without_personal_data(capture_client, capture_user, db):
    uid = capture_user["X-User-Id"]
    hold(db, capture_user, [{"card_id": "hdfc_millennia", "last4": "4321"}])
    r = _upload(capture_client, capture_user, credit_report_pdf(password="dob0101"), password="dob0101")
    assert r.status_code == 200, r.text
    out = r.json()
    rep = out["report"]
    assert (rep["bureau"], rep["score"], rep["report_date"]) == ("cibil", 782, "2026-10-01")
    cards = {a["lender"]: a for a in rep["accounts"]}
    assert set(cards) == {"HDFC BANK", "ICICI BANK", "SBI CARDS AND PAYMENT SERVICES"}  # the loan is not a card
    assert rep["other_accounts"] == 1
    hdfc = cards["HDFC BANK"]
    assert hdfc["credit_limit_paise"] == 200_000 * R and hdfc["current_balance_paise"] == 36_786 * R
    assert hdfc["last4"] == "4321" and hdfc["opened"] == "2019-03-15" and hdfc["status"] == "Active"
    assert hdfc["held_card_id"] == "hdfc_millennia"
    assert cards["ICICI BANK"]["max_dpd_days"] == 30 and cards["ICICI BANK"]["held_card_id"] is None
    assert cards["SBI CARDS AND PAYMENT SERVICES"]["issuer_hint"] == "sbi_card"
    assert [(e["lender"], e["date"], e["purpose"]) for e in rep["enquiries"]] == [
        ("AXIS BANK", "2026-08-12", "Credit Card"), ("KOTAK MAHINDRA BANK", "2026-06-02", "Personal Loan")]
    with db.begin() as c:
        stored = users.get_profile(c, uid)["credit"]
    assert stored["score"] == 782 and stored["bureau"] == "cibil" and stored["consent"]["purpose"] == "credit_report_analysis"
    assert stored["enquiries_6m"] == 2 and stored["credit_card_accounts"] == 3
    blob = json.dumps(out)
    for pii in ("ABCDE1234F", "TEST PERSON", "9876543210", "example.com", "SAMPLE STREET", "1990", "XXXXXXXXXXXX"):
        assert pii not in blob
    st = capture_client.get("/me/capture/status", headers=capture_user).json()
    assert st["credit_report"]["stored"]["score"] == 782
