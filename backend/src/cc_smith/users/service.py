"""users module: anonymous accounts, profile, holdings and the monthly spend profile."""

import uuid

from sqlalchemy import Connection, delete, insert, select

from cc_smith.db import app_user, credit_pool, holding, now, profile, spend
from cc_smith.merchants import by_key, categories
from cc_smith.rewards.finder import SpendLine

DEFAULT_CHANNEL = {"online": "online", "travel": "online", "entertainment": "online", "utilities": "online"}


def create(conn: Connection) -> str:
    uid = uuid.uuid4().hex
    conn.execute(insert(app_user).values(id=uid))
    conn.execute(insert(profile).values(user_id=uid, data={}))
    return uid


def exists(conn: Connection, uid: str) -> bool:
    return conn.execute(select(app_user.c.id).where(app_user.c.id == uid)).first() is not None


def get_profile(conn: Connection, uid: str) -> dict:
    row = conn.execute(select(profile.c.data).where(profile.c.user_id == uid)).first()
    return row.data if row else {}


def set_profile(conn: Connection, uid: str, data: dict) -> None:
    conn.execute(delete(profile).where(profile.c.user_id == uid))
    conn.execute(insert(profile).values(user_id=uid, data=data))


def holdings(conn: Connection, uid: str) -> list[dict]:
    return [dict(r._mapping) for r in conn.execute(select(holding).where(holding.c.user_id == uid)).all()]


def set_holdings(conn: Connection, uid: str, items: list[dict]) -> None:
    old = {h["card_id"]: h for h in holdings(conn, uid)}
    conn.execute(delete(holding).where(holding.c.user_id == uid))
    for h in items:
        prev = old.get(h["card_id"], {})
        balance = h.get("balance_paise")
        # Keep the as-of time unless the user typed a new balance, so logged payments since then still count.
        as_of = prev.get("balance_as_of") if balance is not None and balance == prev.get("balance_paise") else (now() if balance is not None else None)
        conn.execute(insert(holding).values(
            user_id=uid, card_id=h["card_id"], last4=h.get("last4"), statement_day=h.get("statement_day"),
            renewal_month=h.get("renewal_month"), fee_status=h.get("fee_status") or "standard", fyf_until=h.get("fyf_until"),
            credit_limit_paise=h.get("credit_limit_paise"), pool_id=h.get("pool_id"), balance_paise=balance, balance_as_of=as_of,
        ))


def pools(conn: Connection, uid: str) -> list[dict]:
    return [dict(r._mapping) for r in conn.execute(select(credit_pool).where(credit_pool.c.user_id == uid)).all()]


def set_pools(conn: Connection, uid: str, items: list[dict]) -> None:
    conn.execute(delete(credit_pool).where(credit_pool.c.user_id == uid))
    for p in items:
        conn.execute(insert(credit_pool).values(user_id=uid, id=p["id"], name=p["name"], limit_paise=p["limit_paise"]))


def spends(conn: Connection, uid: str) -> dict[str, int]:
    return {r.key: r.monthly_paise for r in conn.execute(select(spend).where(spend.c.user_id == uid)).all()}


def set_spends(conn: Connection, uid: str, items: dict[str, int]) -> None:
    conn.execute(delete(spend).where(spend.c.user_id == uid))
    for key, paise in items.items():
        if paise > 0:
            conn.execute(insert(spend).values(user_id=uid, key=key, monthly_paise=paise))


def spend_lines(items: dict[str, int], flags: frozenset[str] = frozenset()) -> list[SpendLine]:
    """A category amount is the category's total; merchants listed under it are part of
    that total. The engine scores each merchant on its own and the remainder as the
    category. If the merchants add up to more than the category, the category is their sum."""
    lines = []
    by_category: dict[str, int] = {}
    for key, paise in items.items():
        m = by_key(key)
        if m:
            lines.append(SpendLine(key, m["category"], key, m["channel"], paise, flags))
            by_category[m["category"]] = by_category.get(m["category"], 0) + paise
        elif key not in categories():
            raise ValueError(f"unknown spend key {key}")
    for key, paise in items.items():
        if key in categories():
            rest = paise - by_category.get(key, 0)
            if rest > 0:
                lines.append(SpendLine(key, key, None, DEFAULT_CHANNEL.get(key, "offline"), rest, flags))
    return lines


def category_totals(items: dict[str, int]) -> dict[str, int]:
    """Monthly total per category as the user means it: the category amount, or the sum
    of its merchants if that is larger."""
    merchants: dict[str, int] = {}
    for key, paise in items.items():
        if m := by_key(key):
            merchants[m["category"]] = merchants.get(m["category"], 0) + paise
    totals = dict(merchants)
    for key, paise in items.items():
        if key in categories():
            totals[key] = max(paise, merchants.get(key, 0))
    return totals
