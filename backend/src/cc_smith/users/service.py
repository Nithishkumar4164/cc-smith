"""users module: anonymous accounts, profile, holdings and the monthly spend profile."""

import uuid

from sqlalchemy import Connection, delete, insert, select

from cc_smith.db import app_user, holding, profile, spend
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
    conn.execute(delete(holding).where(holding.c.user_id == uid))
    for h in items:
        conn.execute(insert(holding).values(user_id=uid, card_id=h["card_id"], last4=h.get("last4"),
                                            statement_day=h.get("statement_day"), renewal_month=h.get("renewal_month")))


def spends(conn: Connection, uid: str) -> dict[str, int]:
    return {r.key: r.monthly_paise for r in conn.execute(select(spend).where(spend.c.user_id == uid)).all()}


def set_spends(conn: Connection, uid: str, items: dict[str, int]) -> None:
    conn.execute(delete(spend).where(spend.c.user_id == uid))
    for key, paise in items.items():
        if paise > 0:
            conn.execute(insert(spend).values(user_id=uid, key=key, monthly_paise=paise))


def spend_lines(items: dict[str, int], flags: frozenset[str] = frozenset()) -> list[SpendLine]:
    lines = []
    for key, paise in items.items():
        m = by_key(key)
        if m:
            lines.append(SpendLine(key, m["category"], key, m["channel"], paise, flags))
        elif key in categories():
            lines.append(SpendLine(key, key, None, DEFAULT_CHANNEL.get(key, "offline"), paise, flags))
        else:
            raise ValueError(f"unknown spend key {key}")
    return lines
