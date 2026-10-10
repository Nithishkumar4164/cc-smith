"""Notification events from the phone, end to end through POST /me/capture/events."""
# ruff: noqa: F811  (pytest fixtures imported from capture_app are redefined as test arguments)

from datetime import UTC, datetime, timedelta

from capture_app import capture_client, capture_user, hold  # noqa: F401  fixtures used as test arguments
from sqlalchemy import select

from cc_smith.capture.alerts import IST, parse
from cc_smith.db import card_payment, txn
from cc_smith.ledger import credit as credit_mod
from cc_smith.ledger import service as ledger

R = 100


def _ev(eid, amount_rupees, merchant="Amazon", kind="debit", last4="1234", ts=None, **kw):
    return {"id": eid, "amount_paise": amount_rupees * R, "merchant_text": merchant, "kind": kind, "last4": last4,
            "ts": (ts or datetime(2026, 10, 9, 13, 0, tzinfo=IST)).isoformat(), "issuer_hint": "hdfc_bank", **kw}


def _post(client, user, events):
    r = client.post("/me/capture/events", json=events, headers=user)
    assert r.status_code == 200, r.text
    return r.json()["outcomes"]


def test_phone_event_from_parsed_notification_is_recorded_with_reward_once(capture_client, capture_user, db):
    hold(db, capture_user, [{"card_id": "hdfc_millennia", "last4": "1234"}])
    # The phone parses the notification and sends only the fields.
    a = parse("Spent Rs.10000 On HDFC Bank Card 1234 At AMAZON On 2026-10-09:13:00:00.Not You? SMS BLOCK CC 1234 to 7308080808")
    ev = {**a.to_dict(), "id": "notif-1"}
    out = _post(capture_client, capture_user, [ev])
    assert out[0]["outcome"] == "recorded" and out[0]["card_id"] == "hdfc_millennia"
    assert out[0]["reward_paise"] == 500 * R  # Millennia 5% on Amazon
    again = _post(capture_client, capture_user, [ev])
    assert again[0]["outcome"] == "duplicate" and again[0]["reason"] == "already_ingested"
    with db.begin() as c:
        rows = c.execute(select(txn)).all()
    assert len(rows) == 1 and rows[0].source == "notification" and rows[0].merchant_key == "amazon"


def test_cap_usage_carries_into_captured_events(capture_client, capture_user, db):
    hold(db, capture_user, [{"card_id": "hdfc_millennia", "last4": "1234"}])
    ts = datetime.now(IST) - timedelta(minutes=5)
    out = _post(capture_client, capture_user, [_ev(f"n{i}", 10_000, ts=ts - timedelta(minutes=i)) for i in range(3)])
    # ₹1,000 monthly cap on the 5% rule: two ₹10,000 spends use it; the third earns the base rate only.
    assert [o["outcome"] for o in out] == ["recorded"] * 3
    assert out[0]["reward_paise"] == out[1]["reward_paise"] == 500 * R
    assert out[2]["reward_paise"] < 500 * R


def test_checkout_entry_then_notification_is_one_purchase(capture_client, capture_user, db):
    uid = capture_user["X-User-Id"]
    hold(db, capture_user, [{"card_id": "hdfc_millennia", "last4": "1234"}])
    when = datetime(2026, 10, 9, 13, 0, tzinfo=IST)
    with db.begin() as c:
        tid = ledger.record(c, uid, card_id="hdfc_millennia", amount_paise=500 * R, merchant_key="swiggy", merchant_name="Swiggy",
                            category="dining", channel="online", reward_paise=0, cap_use={}, ts=when.astimezone(UTC))
    out = _post(capture_client, capture_user, [
        _ev("n-sw-1", 500, "SWIGGY LIMITED", ts=when + timedelta(hours=20)),
        _ev("n-sw-2", 500, "SWIGGY LIMITED", ts=when + timedelta(hours=21)),  # a second order: not the same purchase
        _ev("n-sw-3", 500, "SWIGGY LIMITED", ts=when + timedelta(days=5)),
    ])
    assert out[0]["outcome"] == "duplicate" and out[0]["txn_id"] == tid
    assert out[1]["outcome"] == "recorded"
    assert out[2]["outcome"] == "recorded"


def test_unmatched_foreign_and_bank_account_events(capture_client, capture_user, db):
    hold(db, capture_user, [{"card_id": "hdfc_millennia", "last4": "1234"}, {"card_id": "sbi_cashback"}])
    out = _post(capture_client, capture_user, [
        _ev("u1", 100, last4="9999"),
        _ev("u2", 100, currency="USD"),
        _ev("u3", 100, instrument="account"),
        # SBI Card payment SMS has no last4; the user holds one SBI card, so it matches.
        {"id": "u4", "amount_paise": 2_000 * R, "kind": "payment_received", "issuer_hint": "sbi_card"},
    ])
    assert [(o["outcome"], o["reason"]) for o in out] == [
        ("unmatched_card", "no_card_with_last4"), ("ignored", "foreign_currency"), ("ignored", "not_a_credit_card"), ("recorded", None)]
    assert out[3]["card_id"] == "sbi_cashback" and out[3]["payment_id"]


def test_payment_and_refund_move_the_outstanding(capture_client, capture_user, db):
    uid = capture_user["X-User-Id"]
    hold(db, capture_user, [{"card_id": "hdfc_millennia", "last4": "1234", "balance_paise": 20_000 * R, "credit_limit_paise": 100_000 * R}])
    now = datetime.now(IST)
    out = _post(capture_client, capture_user, [
        _ev("p1", 4_000, ts=now),
        _ev("p2", 1_000, kind="refund", ts=now),
        {"id": "p3", "amount_paise": 15_000 * R, "kind": "payment_received", "last4": "1234", "issuer_hint": "hdfc_bank", "ts": now.isoformat()},
    ])
    assert [o["outcome"] for o in out] == ["recorded"] * 3
    assert out[1]["reward_paise"] == -50 * R  # the refund gives back 5% of ₹1,000
    with db.begin() as c:
        assert c.execute(select(card_payment.c.amount_paise)).scalar_one() == 15_000 * R
        owed = credit_mod.credit(c, uid)["hdfc_millennia"].outstanding_paise
    assert owed == (20_000 + 4_000 - 1_000 - 15_000) * R


def test_events_with_card_numbers_are_rejected(capture_client, capture_user, db):
    hold(db, capture_user, [{"card_id": "hdfc_millennia", "last4": "1234"}])
    for bad in ("AMAZON 4111111111111111", "AMAZON 4111 1111 1111 1111"):
        r = capture_client.post("/me/capture/events", json=[_ev("x", 100, bad)], headers=capture_user)
        assert r.status_code == 422 and r.json()["detail"]["code"] == "card_number_like_value"
    r = capture_client.post("/me/capture/events", json=[_ev("x", 100, last4="41111111")], headers=capture_user)
    assert r.status_code == 422
    r = capture_client.post("/me/capture/events", json=[{"id": "y", "amount_paise": 100, "kind": "debit", "raw_text": "spent 5522601234564321"}],
                            headers=capture_user)
    assert r.status_code == 422
    with db.begin() as c:
        assert c.execute(select(txn)).first() is None


def test_status_counts_by_source(capture_client, capture_user, db):
    hold(db, capture_user, [{"card_id": "hdfc_millennia", "last4": "1234"}])
    _post(capture_client, capture_user, [_ev("s1", 100), _ev("s2", 100, last4="0000")])
    st = capture_client.get("/me/capture/status", headers=capture_user).json()
    assert st["notification"]["counts"] == {"recorded": 1, "unmatched_card": 1}
    assert st["notification"]["last_sync_at"]
    assert st["gmail"]["connected"] is False


def test_unknown_user_is_rejected(capture_client):
    assert capture_client.get("/me/capture/status", headers={"X-User-Id": "nobody"}).status_code == 401


def test_raw_text_field_is_refused(capture_client, capture_user, db):
    hold(db, capture_user, [{"card_id": "hdfc_millennia", "last4": "1234"}])
    r = capture_client.post("/me/capture/events", json=[{**_ev("z", 100), "text": "Spent Rs.100 On HDFC Bank Card 1234"}], headers=capture_user)
    assert r.status_code == 422
