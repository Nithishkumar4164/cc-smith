"""Bureau credit report upload (CIBIL, Experian, Equifax, CRIF High Mark). Parsed in
memory; only derived fields are kept: score, bureau, report date, and per credit-card
account the lender, limit, balance, DPD string, dates and status, plus recent enquiries.
PAN, name, address, phone, email, DOB and account numbers are never extracted (account
numbers are reduced to their last 4).

Report layouts differ by bureau and are not public in full. The extractor reads
"KEY: value" pairs inside each account block (a block starts at a lender label such as
"MEMBER NAME" / "Lender" / "Subscriber Name") and an enquiry table after an "ENQUIR…"
heading. The key aliases are from general knowledge of the bureau consumer reports and
need checking against real reports (private_samples/ test).
"""

import re
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta

from sqlalchemy import Connection

from cc_smith.capture.alerts import issuer_from_text
from cc_smith.capture.pdftext import read_lines
from cc_smith.capture.privacy import strip_long_digit_runs
from cc_smith.capture.statements import DATE_RX, parse_date
from cc_smith.db import now
from cc_smith.users import service as users

BUREAUS = [
    (r"transunion|cibil", "cibil"),
    (r"experian", "experian"),
    (r"equifax", "equifax"),
    (r"crif|high\s*mark", "crif_highmark"),
]

# Longest aliases first so "account type" wins over "type", "credit limit" over "limit".
KEYS: dict[str, list[str]] = {
    "lender": ["member name", "lender name", "lender", "subscriber name", "institution", "bank name", "credit grantor"],
    "account_type": ["account type", "type of account", "type"],
    "account_number": ["account number", "account no", "acct no", "a/c no"],
    "opened": ["date opened", "account open date", "date of opening", "open date", "opened on", "opened"],
    "closed": ["date closed", "closed on", "closed date"],
    "reported": ["date reported", "last reported", "reported on"],
    "credit_limit": ["credit limit amount", "credit limit", "card limit"],
    "sanctioned": ["high credit/sanctioned amount", "sanctioned/high credit", "sanctioned amount", "high credit", "sanctioned"],
    "current_balance": ["current balance", "outstanding balance", "balance"],
    "overdue": ["amount overdue", "overdue amount", "overdue"],
    "status": ["account status", "status"],
    "dpd": ["days past due/asset classification", "days past due", "payment history", "dpd"],
    "ownership": ["ownership"],
}
_ALIASES = sorted(((a, k) for k, al in KEYS.items() for a in al), key=lambda x: -len(x[0]))
KEY_RX = re.compile(r"(?<![A-Za-z])(?P<key>" + "|".join(re.escape(a).replace(r"\ ", r"\s+") for a, _ in _ALIASES) + r")\s*:\s*", re.IGNORECASE)
ALIAS_TO_KEY = {a: k for a, k in _ALIASES}
BLOCK_START = re.compile(r"^\s*(?:member\s+name|lender(?:\s+name)?|subscriber\s+name|institution|bank\s+name|credit\s+grantor)\s*:", re.IGNORECASE)
SECTION_END = re.compile(r"^\s*(?:enquir|inquir|end of report|employment information|contact information|personal information)", re.IGNORECASE)
CREDIT_CARD_TYPE = re.compile(r"credit\s*card|charge\s*card|corporate\s+credit", re.IGNORECASE)
DPD_TOKEN = re.compile(r"\b(?:\d{3}|STD|SMA|SUB|DBT|LSS|XXX)\b")
AMOUNT = re.compile(r"-?\d{1,3}(?:,\d{2,3})+(?:\.\d{1,2})?|-?\d+(?:\.\d{1,2})?")


@dataclass
class Account:
    lender: str | None = None
    issuer_hint: str | None = None
    account_type: str | None = None
    last4: str | None = None
    credit_limit_paise: int | None = None
    sanctioned_paise: int | None = None
    current_balance_paise: int | None = None
    overdue_paise: int | None = None
    dpd: str | None = None
    max_dpd_days: int | None = None
    opened: str | None = None
    closed: str | None = None
    status: str | None = None
    held_card_id: str | None = None
    # The exact product, when the source names it (the bureau feed does; PDF reports don't).
    card_id: str | None = None
    card_name: str | None = None


@dataclass
class Enquiry:
    date: str
    lender: str | None
    purpose: str | None


@dataclass
class CreditReport:
    bureau: str | None = None
    score: int | None = None
    report_date: str | None = None
    accounts: list[Account] = field(default_factory=list)
    other_accounts: int = 0
    enquiries: list[Enquiry] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _paise(v: str | None) -> int | None:
    if not v:
        return None
    m = AMOUNT.search(v.replace("Rs.", "").replace("₹", ""))
    if not m:
        return None
    num = m.group(0).replace(",", "")
    rupees, _, frac = num.partition(".")
    sign = -1 if rupees.startswith("-") else 1
    return sign * (abs(int(rupees)) * 100 + int((frac + "00")[:2]))


def _date(v: str | None) -> str | None:
    if not v:
        return None
    m = DATE_RX.search(v)
    d = parse_date(m.group(0)) if m else None
    return d.isoformat() if d else None


def _kv(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    ms = list(KEY_RX.finditer(text))
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        key = ALIAS_TO_KEY[re.sub(r"\s+", " ", m.group("key").lower())]
        val = text[m.end():end].strip(" |;,\n")
        out.setdefault(key, val)
    return out


def _account(block: str) -> Account:
    kv = _kv(block)
    a = Account()
    a.lender = re.sub(r"\d{5,}", "", kv.get("lender", "")).strip() or None
    a.issuer_hint = issuer_from_text(a.lender or "")
    a.account_type = (kv.get("account_type") or "").strip() or None
    digits = re.findall(r"\d", kv.get("account_number", ""))
    a.last4 = "".join(digits[-4:]) if len(digits) >= 4 else None
    a.credit_limit_paise = _paise(kv.get("credit_limit"))
    a.sanctioned_paise = _paise(kv.get("sanctioned"))
    a.current_balance_paise = _paise(kv.get("current_balance"))
    a.overdue_paise = _paise(kv.get("overdue"))
    tokens = DPD_TOKEN.findall(kv.get("dpd", ""))
    if tokens:
        a.dpd = "|".join(tokens[:36])
        days = [int(t) for t in tokens if t.isdigit()]
        a.max_dpd_days = max(days) if days else 0
    a.opened = _date(kv.get("opened"))
    a.closed = _date(kv.get("closed"))
    a.status = (kv.get("status") or "").strip() or None
    return a


def _enquiries(lines: list[str]) -> list[Enquiry]:
    out = []
    for ln in lines:
        m = DATE_RX.search(ln)
        if not m:
            continue
        d = parse_date(m.group(0))
        if not d:
            continue
        lender = ln[:m.start()].strip(" |-") or None
        rest = AMOUNT.sub("", ln[m.end():]).strip(" |-,.") or None
        out.append(Enquiry(d.isoformat(), lender, rest))
    return out


def parse_report(data: bytes, password: str | None = None) -> CreditReport:
    lines = [strip_long_digit_runs(ln.text) for ln in read_lines(data, password)]
    full = "\n".join(lines)
    r = CreditReport()
    for pattern, name in BUREAUS:
        if re.search(pattern, full, re.IGNORECASE):
            r.bureau = name
            break
    for m in re.finditer(r"score\b[^\d\n]{0,30}(\d{3})\b", full, re.IGNORECASE):
        v = int(m.group(1))
        if 300 <= v <= 900:
            r.score = v
            break
    m = re.search(r"(?:date\s+of\s+report|report\s+date|date\s+of\s+issue|generated\s+on|report\s+generated|^date)\s*:?\s*(" + DATE_RX.pattern + ")",
                  full, re.IGNORECASE | re.MULTILINE)
    if m:
        d = parse_date(m.group(1))
        r.report_date = d.isoformat() if d else None

    blocks: list[list[str]] = []
    enquiry_lines: list[str] = []
    in_enquiries = False
    for ln in lines:
        if re.match(r"^\s*(?:enquir|inquir)", ln, re.IGNORECASE):
            in_enquiries = True
            continue
        if SECTION_END.match(ln):
            in_enquiries = False
            if blocks:
                blocks.append([])  # close the open block
            continue
        if in_enquiries:
            enquiry_lines.append(ln)
            continue
        if BLOCK_START.match(ln):
            blocks.append([ln])
        elif blocks and blocks[-1]:
            blocks[-1].append(ln)
    for b in blocks:
        if not b:
            continue
        a = _account("\n".join(b))
        if a.account_type and CREDIT_CARD_TYPE.search(a.account_type):
            r.accounts.append(a)
        else:
            r.other_accounts += 1
    r.enquiries = _enquiries(enquiry_lines)
    if r.score is None:
        r.warnings.append("score_not_found")
    if not r.accounts:
        r.warnings.append("no_credit_card_accounts_found")
    return r


def apply(conn: Connection, uid: str, r: CreditReport) -> dict:
    """Store score, bureau and date in the profile (consent already checked by the caller)
    and mark accounts the user already holds (same issuer and last4)."""
    from cc_smith.capture.ingest import ISSUER_WORD, _issuers

    holds = users.holdings(conn, uid)
    issuers = _issuers(conn, [h["card_id"] for h in holds])
    held_ids = {h["card_id"] for h in holds}
    for a in r.accounts:
        if a.card_id in held_ids:
            a.held_card_id = a.card_id
            continue
        word = ISSUER_WORD.get(a.issuer_hint or "")
        for h in holds:
            if word and word in issuers.get(h["card_id"], "") and (a.last4 is None or h.get("last4") in (None, a.last4)):
                a.held_card_id = h["card_id"]
                break
    prof = users.get_profile(conn, uid)
    stamp = now().isoformat()
    # Enquiries in the 6 months before the report (issuers look at recent hard pulls).
    asof = date.fromisoformat(r.report_date) if r.report_date else now().date()
    recent = [e for e in r.enquiries if e.date >= (asof - timedelta(days=183)).isoformat()]
    prof["credit"] = {
        "bureau": r.bureau, "score": r.score, "report_date": r.report_date, "uploaded_at": stamp,
        "consent": {"purpose": "credit_report_analysis", "at": stamp},
        "credit_card_accounts": len(r.accounts), "enquiries_6m": len(recent),
    }
    users.set_profile(conn, uid, prof)
    return {"stored": prof["credit"], "report": r.to_dict()}
