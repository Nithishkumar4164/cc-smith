"""Statement upload end to end: a synthetic password-protected statement PDF through
POST /me/capture/statement."""
# ruff: noqa: F811  (pytest fixtures imported from capture_app are redefined as test arguments)

from datetime import UTC, datetime

from capture_app import capture_client, capture_user, hold  # noqa: F401  fixtures used as test arguments
from capture_docs import statement_pdf
from sqlalchemy import select

from cc_smith.capture.alerts import IST
from cc_smith.capture.statements import parse_statement
from cc_smith.db import card_payment, holding, txn
from cc_smith.ledger import credit as credit_mod
from cc_smith.ledger import service as ledger

R = 100
PW = "TEST1234"


def _upload(client, user, data, password=PW, card_id=None):
    form = {k: v for k, v in {"password": password, "card_id": card_id}.items() if v is not None}
    return client.post("/me/capture/statement", files={"file": ("statement.pdf", data, "application/pdf")}, data=form, headers=user)


def test_parse_summary_box_and_inline_layouts():
    for style in ("box", "inline"):
        st = parse_statement(statement_pdf(style=style), PW)
        assert st.issuer_hint == "hdfc_bank" and st.last4 == "4321"
        assert (st.statement_date, st.due_date) == ("2026-09-15", "2026-10-05")
        assert st.total_due_paise == st.closing_balance_paise == 36_786 * R
        assert st.min_due_paise == 1_840 * R
        assert st.credit_limit_paise == 200_000 * R and st.available_credit_paise == 163_214 * R
        assert [(x.kind, x.amount_paise) for x in st.lines] == [
            ("debit", 1_250 * R), ("debit", 4_000 * R), ("payment_received", 10_000 * R), ("refund", 500 * R),
            ("debit", 2_000 * R), ("fee", 36 * R)]
        assert st.warnings == []


def test_password_required_and_wrong_password(capture_client, capture_user, db):
    hold(db, capture_user, [{"card_id": "hdfc_millennia"}])
    data = statement_pdf()
    r = _upload(capture_client, capture_user, data, password=None)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "password_required"
    r = _upload(capture_client, capture_user, data, password="nope")
    assert r.status_code == 422 and r.json()["detail"]["code"] == "wrong_password"
    r = capture_client.post("/me/capture/statement", files={"file": ("x.pdf", b"hello", "application/pdf")}, headers=capture_user)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "not_a_pdf"


def test_statement_resets_balance_and_reconciles_manual_entries(capture_client, capture_user, db):
    uid = capture_user["X-User-Id"]
    # The user holds one HDFC card and has not entered its last4 yet.
    hold(db, capture_user, [{"card_id": "hdfc_millennia", "balance_paise": 5_000 * R}, {"card_id": "sbi_cashback", "last4": "4321"}])
    # A checkout entry for the Swiggy order the statement also lists.
    with db.begin() as c:
        manual = ledger.record(c, uid, card_id="hdfc_millennia", amount_paise=1_250 * R, merchant_key="swiggy", merchant_name="Swiggy",
                               category="dining", channel="online", reward_paise=0, cap_use={},
                               ts=datetime(2026, 8, 18, 20, 0, tzinfo=IST).astimezone(UTC))
    r = _upload(capture_client, capture_user, statement_pdf())
    assert r.status_code == 200, r.text
    out = r.json()
    # last4 4321 is held on an SBI card; the issuer (HDFC) picks the HDFC card without a last4.
    assert out["card_id"] == "hdfc_millennia"
    assert out["read"]["total_due_paise"] == 36_786 * R
    assert out["updated"]["balance_paise"] == 36_786 * R and out["updated"]["credit_limit_paise"] == 200_000 * R
    assert out["updated"]["statement_day"] == 15 and out["updated"]["last4"] == "4321"
    assert out["lines"] == {"duplicate": 1, "recorded": 5}
    with db.begin() as c:
        h = c.execute(select(holding).where((holding.c.user_id == uid) & (holding.c.card_id == "hdfc_millennia"))).one()
        rows = c.execute(select(txn).where(txn.c.source == "statement")).all()
        pays = c.execute(select(card_payment)).all()
        owed = credit_mod.credit(c, uid)["hdfc_millennia"]
    assert h.balance_paise == 36_786 * R and h.statement_day == 15
    assert manual not in {x.id for x in rows}
    assert sorted(x.amount_paise for x in rows) == [-500 * R, 36 * R, 2_000 * R, 4_000 * R]
    assert next(x for x in rows if x.amount_paise == 36 * R).reward_paise == 0  # GST earns nothing
    assert [p.amount_paise for p in pays] == [10_000 * R]
    # Everything on the statement is inside the closing balance, so nothing is counted twice.
    assert owed.outstanding_paise == 36_786 * R and owed.available_paise == (200_000 - 36_786) * R

    again = _upload(capture_client, capture_user, statement_pdf()).json()
    assert again["lines"] == {"duplicate": 6}


def test_no_password_name_or_file_is_stored(capture_client, capture_user, db, tmp_path):
    hold(db, capture_user, [{"card_id": "hdfc_millennia"}])
    assert _upload(capture_client, capture_user, statement_pdf()).status_code == 200
    db.dispose()
    raw = b"".join(p.read_bytes() for p in tmp_path.glob("test.db*"))
    for secret in (PW.encode(), b"TEST CARDHOLDER", b"SAMPLE STREET", b"5522"):
        assert secret not in raw


def test_unmatched_card_leaves_holdings_alone(capture_client, capture_user, db):
    hold(db, capture_user, [{"card_id": "sbi_cashback", "last4": "1111"}])
    out = _upload(capture_client, capture_user, statement_pdf()).json()
    assert out["matched"] is False and out["unmatched_reason"] == "no_card_with_last4"
    assert out["read"]["last4"] == "4321"  # still shown so the app can ask which card
    # The user picks the card explicitly.
    hold(db, capture_user, [{"card_id": "sbi_cashback", "last4": "1111"}, {"card_id": "hdfc_millennia"}])
    out = _upload(capture_client, capture_user, statement_pdf(), card_id="hdfc_millennia").json()
    assert out["card_id"] == "hdfc_millennia" and out["lines"]["recorded"] == 6
