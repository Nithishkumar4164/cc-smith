"""Bank offers at a merchant (B11). Same rule as card facts: an offer is a fact only when
its quote is on the issuer's own page and states its numbers and end date; otherwise it is
speculation. Offers are shown at checkout as hints and never change the reward ranking,
because offer terms are free text (cards eligible, per-user limits, coupon codes)."""

import json
import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import Connection, delete, insert, select

from cc_smith.db import offer
from cc_smith.knowledge import allowlist
from cc_smith.knowledge.fetcher import FetchError, fetch
from cc_smith.knowledge.pipeline import _amount_forms, _pct_forms
from cc_smith.knowledge.quotes import match_kind, normalise

FEE_KINDS = ("ltf", "fyf", "joining_waiver", "annual_waiver")
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]


def _date_stated(iso: str, quote: str) -> bool:
    d = date.fromisoformat(iso)
    q = normalise(quote)
    month_ok = MONTHS[d.month - 1][:3] in q or re.search(rf"\b0?{d.month}[/.-]", q) is not None
    day_ok = re.search(rf"\b0?{d.day}(st|nd|rd|th)?\b", q) is not None
    year_ok = str(d.year) in q or f"'{d.year % 100}" in q or re.search(rf"[/.-]{d.year % 100}\b", q) is not None
    return month_ok and day_ok and year_ok


def check(o: dict, refresh: bool = False) -> tuple[str, list[str], dict]:
    problems = []
    verdict = allowlist.check(o["url"], o["issuer"], "offers")
    if not verdict.official:
        problems.append(f"not official ({verdict.reason})")
    ref = {"url": o["url"], "quote": o["quote"], "official": verdict.official}
    try:
        ev = fetch(o["url"], refresh=refresh)
        kind = match_kind(o["quote"], ev.text)
        ref.update(evidence_id=ev.id, fetched_at=ev.fetched_at.isoformat(), match=kind)
        if kind is None:
            problems.append("quote not found on the page")
    except FetchError as e:
        problems.append(f"fetch failed: {e}")
    q = normalise(o["quote"].replace(" | ", " "))
    if o.get("pct_bp") and not any(f in q for f in _pct_forms(o["pct_bp"])):
        problems.append("percentage not stated in its quote")
    for k in ("max_paise", "min_txn_paise", "flat_paise", "spend_condition_paise"):
        if o.get(k) and not any(f.lower() in q for f in _amount_forms(o[k] // 100)):
            problems.append(f"{k} not stated in its quote")
    if o.get("valid_to") and not _date_stated(o["valid_to"], o["quote"]):
        problems.append("end date not stated in its quote")
    return ("speculation" if problems else "fact"), problems, ref


def load(conn: Connection, path: Path, refresh: bool = False) -> dict[str, int]:
    counts = {"fact": 0, "speculation": 0}
    for o in json.loads(path.read_text())["offers"]:
        tier, problems, ref = check(o, refresh)
        conn.execute(delete(offer).where(offer.c.id == o["id"]))
        conn.execute(insert(offer).values(
            id=o["id"], issuer=o["issuer"], card_ids=o.get("card_ids") or ["*"], merchant_key=o.get("merchant_key"),
            merchant_name=o.get("merchant_name"), title=o["title"], kind=o.get("kind", "other"), pct_bp=o.get("pct_bp"),
            max_paise=o.get("max_paise"), min_txn_paise=o.get("min_txn_paise"), flat_paise=o.get("flat_paise"),
            spend_condition_paise=o.get("spend_condition_paise"), spend_window_days=o.get("spend_window_days"),
            channel=o.get("channel") or "any", valid_from=o.get("valid_from"), valid_to=o.get("valid_to"),
            refs=[ref], tier=tier, reason="; ".join(problems) or None,
        ))
        counts[tier] += 1
    return counts


_UP_TO_PCT = re.compile(r"\bup\s?to\s+\d+(?:\.\d+)?\s?%", re.IGNORECASE)


def is_up_to(o) -> bool:
    """'Up to 25% … max ₹11,300' leaves the actual percentage open; '10% up to ₹1,000' is a
    fixed 10% with a cap and is not an 'up to' offer."""
    text = f"{o.title} {o.refs[0].get('quote', '') if o.refs else ''}"
    return bool(_UP_TO_PCT.search(text))


def up_to_ceiling(o, amount_paise: int) -> int | None:
    """The most an 'up to' offer can give on this amount: the offer's own maximum, or the
    top percentage when no maximum is stated."""
    if o.min_txn_paise and amount_paise < o.min_txn_paise:
        return 0
    top = amount_paise * o.pct_bp // 10_000 if o.pct_bp else None
    if o.max_paise and top is not None:
        return min(top, o.max_paise)
    return o.max_paise or top


def estimate(o, amount_paise: int) -> int | None:
    """Expected value for offers with a fixed rate. 'Up to' offers return None: their real
    value is unknown, so they are shown with up_to_ceiling and kept out of combined figures."""
    if is_up_to(o):
        return None
    if o.min_txn_paise and amount_paise < o.min_txn_paise:
        return 0
    if o.flat_paise:
        return o.flat_paise
    if o.pct_bp:
        v = amount_paise * o.pct_bp // 10_000
        return min(v, o.max_paise) if o.max_paise else v
    return None


def for_checkout(conn: Connection, merchant_key: str | None, channel: str, held: list[tuple[str, str]], today: date | None = None) -> list[dict]:
    """Offers at this merchant for cards the user holds. `held` is [(card_id, issuer)]."""
    if not merchant_key or not held:
        return []
    # Offer validity is stated in Indian dates.
    today = today or datetime.now(ZoneInfo("Asia/Kolkata")).date()
    rows = conn.execute(select(offer).where(offer.c.merchant_key == merchant_key, offer.c.kind.not_in(FEE_KINDS))).all()
    out = []
    for o in rows:
        if o.valid_to and date.fromisoformat(o.valid_to) < today:
            continue
        if o.valid_from and date.fromisoformat(o.valid_from) > today:
            continue
        if o.channel not in ("any", channel):
            continue
        issuer = allowlist.issuer_key(o.issuer)
        cards = [cid for cid, iss in held if allowlist.issuer_key(iss) == issuer and ("*" in o.card_ids or cid in o.card_ids)]
        if cards:
            out.append({"offer": o, "card_ids": cards})
    return out


def fee_offers(conn: Connection, today: date | None = None) -> dict[str, list]:
    """Live LTF / FYF / fee-waiver offers by card id."""
    today = today or datetime.now(ZoneInfo("Asia/Kolkata")).date()
    out: dict[str, list] = {}
    for o in conn.execute(select(offer).where(offer.c.kind.in_(FEE_KINDS))).all():
        if o.valid_to and date.fromisoformat(o.valid_to) < today:
            continue
        for cid in o.card_ids:
            out.setdefault(cid, []).append(o)
    return out


def live_merchant_offers(conn: Connection, today: date | None = None) -> list:
    today = today or datetime.now(ZoneInfo("Asia/Kolkata")).date()
    rows = conn.execute(select(offer).where(offer.c.kind.not_in(FEE_KINDS), offer.c.merchant_key.is_not(None))).all()
    return [o for o in rows if not (o.valid_to and date.fromisoformat(o.valid_to) < today)]
