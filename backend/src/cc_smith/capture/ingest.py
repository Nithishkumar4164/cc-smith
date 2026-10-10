"""Turn parsed transaction events (phone notifications, Gmail alerts, statement lines)
into ledger rows. The phone sends parsed fields only, never the notification text (DR-2).

Per event:
1. Idempotency: sha256(source:event id). The same event twice is a duplicate.
2. Card: a held card with the same last4 (narrowed by issuer when the alert names one);
   an alert without last4 matches only if the user holds exactly one card from that issuer.
3. Dedupe across sources: a ledger row on the same card, same amount, same merchant, within
   48 h, recorded by a different source and not already matched by this source, is the same
   purchase (a checkout entry later seen in a notification, then on the statement).
4. Record: purchases via ledger.service.record(source=...) with the reward the engine gives
   under current cap usage; refunds as a negative row that gives the reward back;
   repayments ("payment received") as card_payment rows.
"""

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from rapidfuzz import fuzz
from sqlalchemy import Connection, and_, insert, select

from cc_smith import merchants
from cc_smith.capture.alerts import IST
from cc_smith.capture.privacy import has_long_digit_run
from cc_smith.db import capture_event, card, card_payment, now, txn
from cc_smith.knowledge import store
from cc_smith.ledger import service as ledger
from cc_smith.rewards.engine import Purchase, reward
from cc_smith.users import service as users

SOURCES = ("notification", "gmail", "statement")
WINDOW = timedelta(hours=48)

# alerts.py issuer ids -> a word in card.issuer ("HDFC Bank", "SBI Card", "YES Bank (fintech partner: Kiwi …)").
ISSUER_WORD = {
    "hdfc_bank": "hdfc", "icici_bank": "icici", "sbi_card": "sbi card", "axis_bank": "axis", "hsbc_india": "hsbc",
    "kotak_mahindra_bank": "kotak", "idfc_first_bank": "idfc", "yes_bank": "yes bank", "au_small_finance_bank": "au small",
    "federal_bank": "federal",
}


class CaptureEvent(BaseModel):
    """One parsed transaction. `id` is the source's own id (notification key, Gmail message
    id, statement line hash) and makes re-sends idempotent."""

    model_config = ConfigDict(extra="forbid")  # no raw notification text or other fields (DR-2)

    id: str = Field(min_length=1, max_length=200)
    amount_paise: int = Field(gt=0)
    currency: str = "INR"
    last4: str | None = Field(None, pattern=r"^\d{4}$")
    merchant_text: str | None = Field(None, max_length=200)
    ts: datetime | None = None
    kind: Literal["debit", "credit", "refund", "payment_received", "fee"]  # fee: statement-only (GST, interest, late fee)
    issuer_hint: str | None = Field(None, max_length=64)
    instrument: str | None = Field(None, max_length=32)
    card_id: str | None = Field(None, max_length=128)  # set when the user (or a statement) already chose the card

    @field_validator("id", "merchant_text", "issuer_hint", "instrument", "card_id", "currency")
    @classmethod
    def _no_card_numbers(cls, v):
        if isinstance(v, str) and has_long_digit_run(v):
            raise ValueError("contains a 12-19 digit run (card numbers are never accepted)")
        return v


@dataclass
class Outcome:
    id: str
    outcome: str  # recorded | duplicate | unmatched_card | ignored
    reason: str | None = None
    card_id: str | None = None
    txn_id: int | None = None
    payment_id: int | None = None
    reward_paise: int | None = None


def idem_key(source: str, event_id: str) -> str:
    return hashlib.sha256(f"{source}:{event_id}".encode()).hexdigest()


def _utc(ts: datetime | None) -> datetime:
    if ts is None:
        return now()
    return (ts if ts.tzinfo else ts.replace(tzinfo=IST)).astimezone(UTC)


def _aware(ts: datetime) -> datetime:
    # SQLite hands back naive datetimes; everything is stored as UTC.
    return ts if ts.tzinfo else ts.replace(tzinfo=UTC)


def _issuers(conn: Connection, card_ids: list[str]) -> dict[str, str]:
    if not card_ids:
        return {}
    return {r.id: r.issuer.lower() for r in conn.execute(select(card.c.id, card.c.issuer).where(card.c.id.in_(card_ids))).all()}


def match_card(conn: Connection, holds: list[dict], ev: CaptureEvent) -> tuple[str | None, str | None]:
    """(card_id, reason when unmatched)."""
    if ev.card_id:
        return (ev.card_id, None) if any(h["card_id"] == ev.card_id for h in holds) else (None, "card_not_held")
    issuers = _issuers(conn, [h["card_id"] for h in holds])
    word = ISSUER_WORD.get(ev.issuer_hint or "")

    def same_issuer(h: dict) -> bool:
        return word is None or word in issuers.get(h["card_id"], "")

    if ev.last4:
        hits = [h for h in holds if h.get("last4") == ev.last4]
        if len(hits) > 1:
            hits = [h for h in hits if same_issuer(h)]
        if len(hits) == 1 and same_issuer(hits[0]):
            return hits[0]["card_id"], None
        if len(hits) > 1:
            return None, "ambiguous_last4"
        # A held card without last4 from the named issuer: only if it is the only one.
        if word:
            open_ = [h for h in holds if not h.get("last4") and same_issuer(h)]
            if len(open_) == 1:
                return open_[0]["card_id"], None
        return None, "no_card_with_last4"
    if word:
        hits = [h for h in holds if same_issuer(h)]
        if len(hits) == 1:
            return hits[0]["card_id"], None
        return None, "ambiguous_issuer" if hits else "no_card_from_issuer"
    return None, "no_last4"


def _claimed(conn: Connection, source: str, col, ids: list[int]) -> set[int]:
    if not ids:
        return set()
    rows = conn.execute(select(col).where(and_(capture_event.c.source == source, col.in_(ids)))).all()
    return {r[0] for r in rows}


def _same_merchant(key: str | None, name: str | None, row) -> bool:
    if key and row.merchant_key:
        return key == row.merchant_key
    if not name or not row.merchant_name:
        return True
    return fuzz.token_set_ratio(name.lower(), row.merchant_name.lower()) >= 80


def _find_txn_duplicate(conn, uid, card_id, amount, key, name, ts, source) -> int | None:
    rows = conn.execute(select(txn).where(and_(
        txn.c.user_id == uid, txn.c.card_id == card_id, txn.c.amount_paise == amount,
        txn.c.superseded_by.is_(None), txn.c.source != source,
    ))).all()
    rows = [r for r in rows if abs(_aware(r.ts) - ts) <= WINDOW and _same_merchant(key, name, r)]
    taken = _claimed(conn, source, capture_event.c.txn_id, [r.id for r in rows])
    rows = [r for r in rows if r.id not in taken]
    rows.sort(key=lambda r: abs(_aware(r.ts) - ts))
    return rows[0].id if rows else None


def _find_payment_duplicate(conn, uid, card_id, amount, ts, source) -> int | None:
    rows = conn.execute(select(card_payment).where(and_(
        card_payment.c.user_id == uid, card_payment.c.card_id == card_id, card_payment.c.amount_paise == amount,
    ))).all()
    rows = [r for r in rows if abs(_aware(r.ts) - ts) <= WINDOW]
    mine = _claimed(conn, source, capture_event.c.payment_id, [r.id for r in rows])
    rows = [r for r in rows if r.id not in mine]
    rows.sort(key=lambda r: abs(_aware(r.ts) - ts))
    return rows[0].id if rows else None


def _reward(conn, uid, card_id: str, statement_day, flags, amount: int, m: merchants.Merchant, ts: datetime):
    prof = store.profile(conn, card_id)
    if prof is None or not prof[0].assessable():
        return 0, {}
    cp = prof[0]
    used = ledger.cap_used(conn, uid, cp, statement_day, today=ts.astimezone(IST).date())
    r = reward(cp, Purchase(amount, m.category, m.key, m.channel, flags), used)
    return r.value_paise, r.cap_use


def _log(conn, uid, source, key, o: Outcome) -> None:
    conn.execute(insert(capture_event).values(
        user_id=uid, source=source, idempotency_key=key, outcome=o.outcome, reason=o.reason, card_id=o.card_id,
        txn_id=o.txn_id, payment_id=o.payment_id,
    ))


def ingest_events(conn: Connection, uid: str, events: list[CaptureEvent | dict], source: str) -> list[Outcome]:
    if source not in SOURCES:
        raise ValueError(f"unknown source {source}")
    holds = users.holdings(conn, uid)
    by_card = {h["card_id"]: h for h in holds}
    flags = frozenset(users.get_profile(conn, uid).get("flags", []))
    out: list[Outcome] = []
    for raw in events:
        ev = raw if isinstance(raw, CaptureEvent) else CaptureEvent.model_validate(raw)
        key = idem_key(source, ev.id)
        prior = conn.execute(select(capture_event).where(capture_event.c.idempotency_key == key)).first()
        if prior:
            out.append(Outcome(ev.id, "duplicate", "already_ingested", prior.card_id, prior.txn_id, prior.payment_id))
            continue
        o = _one(conn, uid, ev, source, holds, by_card, flags)
        _log(conn, uid, source, key, o)
        out.append(o)
    return out


def _one(conn, uid, ev: CaptureEvent, source: str, holds, by_card, flags) -> Outcome:
    if ev.currency.upper() != "INR":
        return Outcome(ev.id, "ignored", "foreign_currency")  # the statement brings the INR amount
    if ev.instrument in ("account", "debit_card"):
        return Outcome(ev.id, "ignored", "not_a_credit_card")
    card_id, why = match_card(conn, holds, ev)
    if card_id is None:
        return Outcome(ev.id, "unmatched_card", why)
    ts = _utc(ev.ts)
    if ev.kind == "payment_received":
        dup = _find_payment_duplicate(conn, uid, card_id, ev.amount_paise, ts, source)
        if dup:
            return Outcome(ev.id, "duplicate", "matches_existing_payment", card_id, payment_id=dup)
        pid = conn.execute(insert(card_payment).values(user_id=uid, card_id=card_id, amount_paise=ev.amount_paise, ts=ts)).inserted_primary_key[0]
        return Outcome(ev.id, "recorded", None, card_id, payment_id=pid)

    if ev.kind == "fee":
        m = merchants.Merchant(None, ev.merchant_text or "fee", "fees", "offline", None, "high")
    elif ev.merchant_text:
        m = merchants.resolve(ev.merchant_text)
    else:
        m = merchants.Merchant(None, "", "other", "offline", None, "low")
    sign = 1 if ev.kind in ("debit", "fee") else -1
    amount = sign * ev.amount_paise
    dup = _find_txn_duplicate(conn, uid, card_id, amount, m.key, m.name or None, ts, source)
    if dup:
        return Outcome(ev.id, "duplicate", "matches_existing_txn", card_id, txn_id=dup)
    h = by_card[card_id]
    if ev.kind in ("credit", "fee"):
        value, cap_use = 0, {}  # fees earn nothing; a cashback or other credit lowers what is owed and earns nothing
    else:
        value, cap_use = _reward(conn, uid, card_id, h.get("statement_day"), flags, ev.amount_paise, m, ts)
        if sign < 0:  # a refund gives back what the purchase earned and frees its cap
            value, cap_use = -value, {k: -v for k, v in cap_use.items()}
    tid = ledger.record(
        conn, uid, card_id=card_id, amount_paise=amount, merchant_key=m.key, merchant_name=m.name or None,
        category=m.category, channel=m.channel, reward_paise=value, cap_use=cap_use, source=source,
        idempotency_key=f"{source}:{idem_key(source, ev.id)[:32]}", ts=ts,
    )
    return Outcome(ev.id, "recorded", None if ev.kind == "debit" else ev.kind, card_id, txn_id=tid, reward_paise=value)


def log_ignored(conn: Connection, uid: str, source: str, event_id: str, reason: str) -> None:
    """Remember a source item that was not a transaction so a re-sync does not fetch it again."""
    key = idem_key(source, event_id)
    if conn.execute(select(capture_event.c.id).where(capture_event.c.idempotency_key == key)).first() is None:
        _log(conn, uid, source, key, Outcome(event_id, "ignored", reason))
