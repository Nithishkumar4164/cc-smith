"""ledger module: confirmed checkout transactions and cap usage per current period."""

from datetime import UTC, date, datetime

from sqlalchemy import Connection, and_, insert, select

from cc_smith.db import txn
from cc_smith.knowledge.schema import CardProfile
from cc_smith.ops import outbox


def _period_start(period: str, today: date, statement_day: int | None) -> date:
    if period in ("statement_cycle", "statement_quarter") and statement_day:
        months = 1 if period == "statement_cycle" else 3
        y, m = today.year, today.month
        if today.day <= statement_day:
            m -= 1
        m -= months - 1
        while m <= 0:
            m += 12
            y -= 1
        day = min(statement_day + 1, 28)
        return date(y, m, day)
    if period in ("calendar_month", "statement_cycle"):
        return today.replace(day=1)
    if period in ("calendar_quarter", "statement_quarter"):
        return date(today.year, 3 * ((today.month - 1) // 3) + 1, 1)
    return date(today.year, 1, 1)


def cap_used(conn: Connection, uid: str, card: CardProfile, statement_day: int | None, today: date | None = None) -> dict[str, int]:
    today = today or datetime.now(UTC).date()
    used: dict[str, int] = {}
    starts = {c.id: _period_start(c.period, today, statement_day) for c in card.caps}
    if not starts:
        return used
    earliest = min(starts.values())
    rows = conn.execute(select(txn.c.cap_use, txn.c.ts).where(and_(
        txn.c.user_id == uid, txn.c.card_id == card.id, txn.c.superseded_by.is_(None),
        txn.c.ts >= datetime.combine(earliest, datetime.min.time(), UTC),
    ))).all()
    for r in rows:
        ts = r.ts.date()
        for cid, delta in (r.cap_use or {}).items():
            if cid in starts and ts >= starts[cid]:
                used[cid] = used.get(cid, 0) + delta
    return used


def record(conn: Connection, uid: str, **values) -> int:
    key = values.get("idempotency_key")
    if key:
        existing = conn.execute(select(txn.c.id).where(txn.c.idempotency_key == key)).first()
        if existing:
            return existing.id
    tid = conn.execute(insert(txn).values(user_id=uid, **values)).inserted_primary_key[0]
    outbox.publish(conn, "txn.recorded", f"txn:{tid}", {"txn_id": tid, "user_id": uid, "card_id": values["card_id"]})
    return tid


def recent(conn: Connection, uid: str, limit: int = 20) -> list[dict]:
    rows = conn.execute(select(txn).where(txn.c.user_id == uid).order_by(txn.c.ts.desc()).limit(limit)).all()
    return [dict(r._mapping) for r in rows]
