"""Monthly budget that fills and adapts itself (owner decision, 10 Oct 2026).

The budget is the user's spend profile (`spend` table: category totals and merchants
inside them). Each new month, every line the user hasn't edited (unpinned) is reset to
last month's actual spend from the ledger. Edited lines are pinned until reset."""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Connection, and_, select

from cc_smith.db import txn
from cc_smith.merchants import by_key, categories
from cc_smith.users import service as users

MERCHANT_LINE_MIN = 500 * 100  # a merchant gets its own line from ₹500 a month


def _month_bounds(today: date) -> tuple[date, date, date]:
    first_this = today.replace(day=1)
    last_end = first_this - timedelta(days=1)
    return last_end.replace(day=1), last_end, first_this


def last_month_actuals(conn: Connection, uid: str, today: date | None = None) -> tuple[str, dict[str, int]]:
    """Category totals plus merchant lines (merchants are part of their category total)."""
    today = today or datetime.now(UTC).date()
    start, _, first_this = _month_bounds(today)
    rows = conn.execute(select(txn.c.amount_paise, txn.c.merchant_key, txn.c.category).where(and_(
        txn.c.user_id == uid, txn.c.superseded_by.is_(None),
        txn.c.ts >= datetime.combine(start, datetime.min.time(), UTC),
        txn.c.ts < datetime.combine(first_this, datetime.min.time(), UTC),
    ))).all()
    cats: dict[str, int] = {}
    merch: dict[str, int] = {}
    for r in rows:
        cat = r.category if r.category in categories() else "other"
        cats[cat] = cats.get(cat, 0) + r.amount_paise
        if r.merchant_key and by_key(r.merchant_key):
            merch[r.merchant_key] = merch.get(r.merchant_key, 0) + r.amount_paise
    out = dict(cats)
    out.update({k: v for k, v in merch.items() if v >= MERCHANT_LINE_MIN})
    return start.strftime("%Y-%m"), out


def adapt(conn: Connection, uid: str, today: date | None = None, force: bool = False) -> str | None:
    """Reset unpinned lines to last month's actuals once per month (or now, when forced)."""
    today = today or datetime.now(UTC).date()
    prof = users.get_profile(conn, uid)
    this_month = today.strftime("%Y-%m")
    if not force and prof.get("budget_month") == this_month:
        return prof.get("budget_adapted_from")
    month, actuals = last_month_actuals(conn, uid, today)
    if not actuals:
        return None
    pins = set(prof.get("budget_pins", []))
    spends = users.spends(conn, uid)
    new = {k: v for k, v in spends.items() if k in pins}
    new.update({k: v for k, v in actuals.items() if k not in pins})
    users.set_spends(conn, uid, new)
    prof = users.get_profile(conn, uid)
    prof["budget_month"], prof["budget_adapted_from"] = this_month, month
    users.set_profile(conn, uid, prof)
    return month


def view(conn: Connection, uid: str, today: date | None = None) -> dict:
    today = today or datetime.now(UTC).date()
    adapted = adapt(conn, uid, today)
    _, actuals = last_month_actuals(conn, uid, today)
    spends = users.spends(conn, uid)
    pins = set(users.get_profile(conn, uid).get("budget_pins", []))
    names = categories()
    lines = []
    for key in sorted(set(spends) | set(actuals), key=lambda k: (by_key(k) is not None, k)):
        m = by_key(key)
        lines.append({
            "key": key, "label": m["name"] if m else names.get(key, key), "kind": "merchant" if m else "category",
            "category": m["category"] if m else key, "budget_paise": spends.get(key, 0),
            "last_month_paise": actuals.get(key, 0), "pinned": key in pins,
        })
    total = sum(users.category_totals(spends).values())
    return {"month": today.strftime("%Y-%m"), "adapted_from": adapted, "lines": lines, "total_paise": total}


def edit(conn: Connection, uid: str, changes: dict[str, int | None], today: date | None = None) -> dict:
    """Set lines (pinned) or reset them to auto (None: back to last month's actual)."""
    _, actuals = last_month_actuals(conn, uid, today)
    spends = users.spends(conn, uid)
    prof = users.get_profile(conn, uid)
    pins = set(prof.get("budget_pins", []))
    for key, value in changes.items():
        if value is None:
            pins.discard(key)
            if key in actuals:
                spends[key] = actuals[key]
            else:
                spends.pop(key, None)
        else:
            pins.add(key)
            spends[key] = value
    users.spend_lines(spends)  # validates keys
    users.set_spends(conn, uid, spends)
    prof = users.get_profile(conn, uid)
    prof["budget_pins"] = sorted(pins)
    users.set_profile(conn, uid, prof)
    return view(conn, uid, today)
