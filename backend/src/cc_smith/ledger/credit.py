"""Available credit per held card. Outstanding = the balance the user entered (as of a
time) + checkout payments logged since − bill payments since. Cards in a pool share the
pool's limit. Only as accurate as the payments captured: manual now, notifications and
statements later."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Connection, and_, func, select

from cc_smith.db import card_payment, txn
from cc_smith.users import service as users


@dataclass
class Credit:
    card_id: str
    limit_paise: int | None
    pool_id: str | None
    pool_name: str | None
    outstanding_paise: int
    available_paise: int | None
    utilisation_bp: int | None  # of the card's limit, or of the pool's limit when shared


def _since(ts: datetime | None) -> datetime:
    if ts is None:
        return datetime(1970, 1, 1, tzinfo=UTC)
    return ts if ts.tzinfo else ts.replace(tzinfo=UTC)


def outstanding(conn: Connection, uid: str, h: dict) -> int:
    since = _since(h.get("balance_as_of"))
    spent = conn.execute(select(func.coalesce(func.sum(txn.c.amount_paise), 0)).where(and_(
        txn.c.user_id == uid, txn.c.card_id == h["card_id"], txn.c.superseded_by.is_(None), txn.c.ts >= since,
    ))).scalar_one()
    paid = conn.execute(select(func.coalesce(func.sum(card_payment.c.amount_paise), 0)).where(and_(
        card_payment.c.user_id == uid, card_payment.c.card_id == h["card_id"], card_payment.c.ts >= since,
    ))).scalar_one()
    return max(0, (h.get("balance_paise") or 0) + spent - paid)


def credit(conn: Connection, uid: str) -> dict[str, Credit]:
    holds = users.holdings(conn, uid)
    pools = {p["id"]: p for p in users.pools(conn, uid)}
    owed = {h["card_id"]: outstanding(conn, uid, h) for h in holds}
    pool_owed: dict[str, int] = {}
    for h in holds:
        if h.get("pool_id") in pools:
            pool_owed[h["pool_id"]] = pool_owed.get(h["pool_id"], 0) + owed[h["card_id"]]
    out = {}
    for h in holds:
        pid = h.get("pool_id") if h.get("pool_id") in pools else None
        if pid:
            limit, used = pools[pid]["limit_paise"], pool_owed[pid]
        else:
            limit, used = h.get("credit_limit_paise"), owed[h["card_id"]]
        available = max(0, limit - used) if limit else None
        util = used * 10_000 // limit if limit else None
        out[h["card_id"]] = Credit(h["card_id"], limit, pid, pools[pid]["name"] if pid else None, owed[h["card_id"]], available, util)
    return out


def record_bill_payment(conn: Connection, uid: str, card_id: str, amount_paise: int | None) -> int:
    """Amount None = paid the full outstanding."""
    h = next((x for x in users.holdings(conn, uid) if x["card_id"] == card_id), None)
    if h is None:
        raise ValueError("card not held")
    amount = outstanding(conn, uid, h) if amount_paise is None else amount_paise
    if amount > 0:
        conn.execute(card_payment.insert().values(user_id=uid, card_id=card_id, amount_paise=amount))
    return amount
