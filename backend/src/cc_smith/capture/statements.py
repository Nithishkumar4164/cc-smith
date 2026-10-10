"""Credit-card statement PDF upload. The PDF is opened in memory with the user's password
(most Indian issuers protect statements); neither the file nor the password is stored.
Only derived fields are kept: last4, dates, dues, limits and line items.

Extraction is generic first: summary fields are found by label (same line, or the value
printed under the label in a two-row summary box), and line items are any line that
starts with a date and ends with an amount. Per-issuer hints add label wordings and
debit/credit markers. The hints are from general knowledge of issuer statement layouts,
not from real samples yet; `tests/test_capture_real_samples.py` runs on the owner's real
statements when they are in private_samples/.
"""

import hashlib
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, time

from sqlalchemy import Connection, update

from cc_smith.capture import ingest
from cc_smith.capture.alerts import IST, MONTHS, issuer_from_text
from cc_smith.capture.pdftext import MONEY, Line, find_labeled, money_paise, read_lines
from cc_smith.capture.privacy import last4_of_long_runs, strip_long_digit_runs
from cc_smith.capture.state import get_state, set_state
from cc_smith.db import holding
from cc_smith.users import service as users

_MON = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"
DATE_RX = re.compile(
    r"(?<![\d])(?:\d{1,2}[/-]\d{1,2}[/-](?:\d{4}|\d{2})|\d{1,2}[ -/]?" + _MON + r"[ ,-/]*(?:\d{4}|\d{2})|" + _MON + r" \d{1,2},? \d{4}|\d{4}-\d{2}-\d{2})(?![\d])",
    re.IGNORECASE,
)


def parse_date(s: str) -> date | None:
    s = s.strip()
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        y, mo, d = int(m[1]), int(m[2]), int(m[3])
    elif m := re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4}|\d{2})", s):
        d, mo, y = int(m[1]), int(m[2]), int(m[3])
    elif m := re.fullmatch(r"(\d{1,2})[ -/]?([a-z]+)[ ,-/]*(\d{4}|\d{2})", s, re.IGNORECASE):
        d, mo, y = int(m[1]), MONTHS.get(m[2].lower()[:3], 0), int(m[3])
    elif m := re.fullmatch(r"([a-z]+) (\d{1,2}),? (\d{4})", s, re.IGNORECASE):
        mo, d, y = MONTHS.get(m[1].lower()[:3], 0), int(m[2]), int(m[3])
    else:
        return None
    y += 2000 if y < 100 else 0
    try:
        return date(y, mo, d)
    except ValueError:
        return None


# ---------- summary labels (generic; issuer wordings folded in) ----------
LABELS: dict[str, list[str]] = {
    "statement_date": [r"statement\s+date", r"statement\s+generation\s+date", r"date\s+of\s+statement", r"bill(?:ing)?\s+date"],
    "statement_period": [r"statement\s+period", r"billing\s+period", r"billing\s+cycle"],
    "due_date": [r"payment\s+due\s+date", r"due\s+date", r"pay\s+by"],
    "total_due": [r"total\s+amount\s+due", r"total\s+payment\s+due", r"total\s+dues", r"total\s+due", r"total\s+amount\s+payable",
                  r"total\s+outstanding"],
    "min_due": [r"minimum\s+amount\s+due", r"minimum\s+payment\s+due", r"minimum\s+due", r"min\.?\s*amt\.?\s*due", r"minimum\s+amount\s+payable"],
    "closing_balance": [r"closing\s+balance", r"current\s+outstanding", r"new\s+balance", r"current\s+balance", r"total\s+outstanding"],
    "opening_balance": [r"opening\s+balance", r"previous\s+(?:statement\s+)?balance", r"previous\s+dues"],
    "credit_limit": [r"(?<!available\s)(?<!avl\.\s)(?<!available\scash\s)(?:total\s+|sanctioned\s+)?credit\s+limit"],
    "available_credit": [r"available\s+credit\s+limit", r"available\s+credit", r"available\s+limit"],
    "payments": [r"payments?\s*(?:/|&|and)\s*credits?", r"payments?\s+received", r"total\s+payments?"],
}

# Line-item credit markers: "Cr"/"CR" suffix (HDFC, ICICI, Axis), "C" vs "D" column (SBI Card).
ISSUER_HINTS: dict[str, dict] = {
    "sbi_card": {"single_letter_marker": True},
    "hdfc_bank": {}, "icici_bank": {}, "axis_bank": {}, "hsbc_india": {}, "kotak_mahindra_bank": {},
    "idfc_first_bank": {}, "yes_bank": {}, "au_small_finance_bank": {},
}

PAYMENT_DESC = re.compile(r"payment|thank\s*you|\bbbps\b|\bneft\b|\bimps\b|auto\s*debit|autopay|\bach\b|\bnach\b|received", re.IGNORECASE)
CREDIT_DESC = re.compile(r"refund|revers|cashback|cash\s*back|credit\s+adjust", re.IGNORECASE)
FEE_DESC = re.compile(
    r"\b(?:[ics]?gst|finance\s+charges?|interest|late\s+(?:payment\s+)?(?:fee|charge)|annual\s+fee|joining\s+fee|membership\s+fee|renewal\s+fee"
    r"|over\s*limit|cash\s+advance\s+fee|fuel\s+surcharge|surcharge|mark-?up|forex\s+fee|cross\s+currency)\b",
    re.IGNORECASE,
)
ROW_DATE = re.compile(
    r"^(?P<d>\d{1,2}[/-]\d{1,2}[/-](?:\d{4}|\d{2})|\d{1,2}[ -]?" + _MON + r"[ ,-]*(?:\d{4}|\d{2})|\d{4}-\d{2}-\d{2})(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?\s+",
    re.IGNORECASE,
)
ROW_AMOUNT = re.compile(
    r"\s(?P<sign>[+-])?\s?(?:Rs\.?|INR|₹|`)?\s?(?P<num>\d{1,3}(?:,\d{2,3})*\.\d{2}|\d+\.\d{2})\s*(?P<mk>Cr|CR|Dr|DR|C|D|\+)?\s*$"
)
MASKED_PAN = re.compile(r"(?<![\w])(?=[0-9Xx*•]*[Xx*•])[0-9Xx*•]{4}[ -]?[0-9Xx*•]{2,6}[ -]?[0-9Xx*•]{2,6}[ -]?[Xx*•]{0,4}(?P<l4>\d{4})(?!\d)")


@dataclass
class StatementLine:
    date: str
    description: str
    amount_paise: int
    direction: str  # debit | credit
    kind: str  # debit | refund | credit | payment_received | fee


@dataclass
class Statement:
    issuer_hint: str | None = None
    last4: str | None = None
    statement_date: str | None = None
    period_from: str | None = None
    due_date: str | None = None
    total_due_paise: int | None = None
    min_due_paise: int | None = None
    closing_balance_paise: int | None = None
    opening_balance_paise: int | None = None
    credit_limit_paise: int | None = None
    available_credit_paise: int | None = None
    payments_paise: int | None = None
    lines: list[StatementLine] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _is_row(text: str) -> bool:
    """A transaction row (date first, amount last): never a summary label."""
    return bool(ROW_DATE.match(text) and ROW_AMOUNT.search(text))


def _first(lines: list[Line], name: str, rx: re.Pattern) -> str | None:
    for label in LABELS[name]:
        hit = find_labeled(lines, label, rx, skip=_is_row)
        if hit:
            return hit[0]
    return None


def _money(lines, name) -> int | None:
    v = _first(lines, name, MONEY)
    return money_paise(v) if v else None


def _date(lines, name) -> date | None:
    v = _first(lines, name, DATE_RX)
    return parse_date(v) if v else None


def _last4(text: str) -> str | None:
    near = re.search(r"card\s*(?:no|number|num)\.?\s*:?\s*(?P<v>[^\n]{0,40})", text, re.IGNORECASE)
    for chunk in ([near.group("v")] if near else []) + [text]:
        m = MASKED_PAN.search(chunk)
        if m:
            return m.group("l4")
        full = last4_of_long_runs(chunk)
        if full and chunk is not text:
            return full[0]
    m = re.search(r"card\s+ending\s*(?:with|in)?\s*[Xx*]*(\d{4})\b", text, re.IGNORECASE)
    return m.group(1) if m else None


def _rows(lines: list[Line], single_letter: bool) -> list[StatementLine]:
    out = []
    for ln in lines:
        text = strip_long_digit_runs(ln.text)
        dm = ROW_DATE.match(text)
        if not dm:
            continue
        am = ROW_AMOUNT.search(text)
        if not am or am.start() < dm.end():
            continue
        d = parse_date(dm.group("d"))
        if d is None:
            continue
        mk = (am.group("mk") or "").upper()
        desc = text[dm.end():am.start()].strip()
        # Drop reward-point columns and reference numbers around the description.
        desc = re.sub(r"(?:\s+[+-]?\d{1,6})+$", "", desc)
        desc = re.sub(r"^(?:\d{6,}\s+)+", "", desc).strip(" -|")
        if not desc or re.fullmatch(r"(?i)(?:opening|closing|previous|total)\b.*", desc):
            continue
        if DATE_RX.search(desc) or MONEY.search(desc):
            continue  # a summary value row ("15/09/2026 05/10/2026 36,786.00 1,840.00"), not a purchase
        num = am.group("num").replace(",", "")
        rupees, _, frac = num.partition(".")
        paise = int(rupees) * 100 + int((frac + "00")[:2])
        if paise == 0:
            continue
        credit = mk in ("CR", "C", "+") or am.group("sign") == "-"
        if not credit and not mk and CREDIT_DESC.search(desc) and not FEE_DESC.search(desc):
            credit = True
        if credit:
            kind = "payment_received" if PAYMENT_DESC.search(desc) and not CREDIT_DESC.search(desc) else (
                "refund" if re.search(r"refund|revers", desc, re.IGNORECASE) else "credit")
        else:
            kind = "fee" if FEE_DESC.search(desc) else "debit"
        out.append(StatementLine(d.isoformat(), desc[:120], paise, "credit" if credit else "debit", kind))
    return out


def parse_statement(data: bytes, password: str | None = None) -> Statement:
    lines = read_lines(data, password)
    full = "\n".join(ln.text for ln in lines)
    st = Statement(issuer_hint=issuer_from_text(full))
    st.last4 = _last4(full)
    sd = _date(lines, "statement_date")
    period = _first(lines, "statement_period", re.compile(DATE_RX.pattern + r".{0,6}?(?:to|-)\s*" + DATE_RX.pattern, re.IGNORECASE))
    if period:
        ds = [parse_date(x.group(0)) for x in DATE_RX.finditer(period)]
        ds = [x for x in ds if x]
        if len(ds) >= 2:
            st.period_from = ds[0].isoformat()
            sd = sd or ds[-1]
    st.statement_date = sd.isoformat() if sd else None
    dd = _date(lines, "due_date")
    st.due_date = dd.isoformat() if dd else None
    st.total_due_paise = _money(lines, "total_due")
    st.min_due_paise = _money(lines, "min_due")
    st.closing_balance_paise = _money(lines, "closing_balance")
    if st.closing_balance_paise is None:
        st.closing_balance_paise = st.total_due_paise
    st.opening_balance_paise = _money(lines, "opening_balance")
    st.credit_limit_paise = _money(lines, "credit_limit")
    st.available_credit_paise = _money(lines, "available_credit")
    st.payments_paise = _money(lines, "payments")
    hints = ISSUER_HINTS.get(st.issuer_hint or "", {})
    st.lines = _rows(lines, hints.get("single_letter_marker", False))
    if st.statement_date is None:
        st.warnings.append("statement_date_not_found")
    if st.closing_balance_paise is None:
        st.warnings.append("closing_balance_not_found")
    if st.last4 is None:
        st.warnings.append("card_last4_not_found")
    if not st.lines:
        st.warnings.append("no_line_items_found")
    if st.opening_balance_paise is not None and st.closing_balance_paise is not None and st.lines:
        net = sum(x.amount_paise if x.direction == "debit" else -x.amount_paise for x in st.lines)
        if st.opening_balance_paise + net != st.closing_balance_paise:
            st.warnings.append("line_items_do_not_reconcile_with_balances")
    return st


def _line_events(st: Statement, card_id: str) -> list[ingest.CaptureEvent]:
    out = []
    for i, x in enumerate(st.lines):
        eid = hashlib.sha256(f"{st.last4}|{st.statement_date}|{i}|{x.date}|{x.amount_paise}|{x.description}".encode()).hexdigest()[:32]
        ts = datetime.combine(date.fromisoformat(x.date), time(12, 0), IST)
        out.append(ingest.CaptureEvent(
            id=eid, amount_paise=x.amount_paise, last4=st.last4, merchant_text=x.description or None, ts=ts,
            kind=x.kind, issuer_hint=st.issuer_hint, instrument="credit_card", card_id=card_id,
        ))
    return out


def apply(conn: Connection, uid: str, st: Statement, card_id: str | None = None) -> dict:
    """Reset the card's balance to the statement's closing balance as of the statement date,
    set its limit and statement day, and ingest the line items so manual entries reconcile."""
    holds = users.holdings(conn, uid)
    if card_id is None:
        probe = ingest.CaptureEvent(id="probe", amount_paise=1, last4=st.last4, kind="debit", issuer_hint=st.issuer_hint)
        card_id, why = ingest.match_card(conn, holds, probe)
    else:
        why = None if any(h["card_id"] == card_id for h in holds) else "card_not_held"
        card_id = card_id if why is None else None
    summary = {"read": st.to_dict(), "card_id": card_id, "matched": card_id is not None, "unmatched_reason": why, "updated": {}, "lines": {}}
    if card_id is None:
        return summary
    state = get_state(conn, uid, "statement")
    per_card = (state.get("detail") or {}).get(card_id, {})
    newer_applied = bool(st.statement_date and per_card.get("statement_date") and per_card["statement_date"] > st.statement_date)
    values: dict = {}
    if st.closing_balance_paise is not None and st.statement_date and not newer_applied:
        as_of = datetime.combine(date.fromisoformat(st.statement_date), time(23, 59, 59), IST).astimezone(UTC)
        values.update(balance_paise=max(0, st.closing_balance_paise), balance_as_of=as_of)
    if st.credit_limit_paise:
        values["credit_limit_paise"] = st.credit_limit_paise
    if st.statement_date:
        values["statement_day"] = date.fromisoformat(st.statement_date).day
    if st.last4:
        values["last4"] = st.last4
    if values:
        conn.execute(update(holding).where((holding.c.user_id == uid) & (holding.c.card_id == card_id)).values(**values))
    summary["updated"] = {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in values.items()}
    if newer_applied:
        summary["updated"]["skipped_balance"] = "a newer statement was already applied"
    outcomes = ingest.ingest_events(conn, uid, _line_events(st, card_id), "statement")
    counts: dict[str, int] = {}
    for o in outcomes:
        counts[o.outcome] = counts.get(o.outcome, 0) + 1
    summary["lines"] = counts
    detail = dict(state.get("detail") or {})
    if not newer_applied:
        detail[card_id] = {"statement_date": st.statement_date, "due_date": st.due_date, "total_due_paise": st.total_due_paise,
                           "min_due_paise": st.min_due_paise}
    set_state(conn, uid, "statement", detail=detail)
    return summary
