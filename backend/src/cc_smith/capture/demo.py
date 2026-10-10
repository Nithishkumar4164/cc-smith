"""DEMO data sources (owner decision, 10 Oct 2026). Everything here is simulated and every
response carries mock: true so the app can label it:

- a credit-bureau fetch by phone number and one-time code (the real version needs a
  bureau partnership; see docs/decisions.md D11), returning the same shape as an uploaded
  credit report;
- a "read my SMS and email" import that writes last month's transactions into the ledger
  (sources demo_sms / demo_email) so the budget can be derived from them.

Results are deterministic per phone number / user, so a demo repeats exactly."""

import hashlib
import random
import secrets
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Connection, select

from cc_smith.capture import credit_report
from cc_smith.capture.credit_report import Account, CreditReport, Enquiry
from cc_smith.capture.ingest import ISSUER_WORD
from cc_smith.db import card
from cc_smith.ledger import service as ledger
from cc_smith.merchants import by_key
from cc_smith.users import service as users

R = 100
DEMO_SOURCES = ("demo_sms", "demo_email")

# Banks the bureau feed covers; each simulated account is a real catalogue card from one of them.
_ENQUIRY_LENDERS = ["HDFC Bank", "SBI Card", "Axis Bank", "ICICI Bank", "HSBC", "IDFC FIRST Bank"]


_pending: dict[str, dict] = {}


def _rng(seed: str) -> random.Random:
    return random.Random(int(hashlib.sha256(seed.encode()).hexdigest()[:16], 16))


def bureau_start(phone: str) -> dict:
    request_id = secrets.token_hex(8)
    otp = f"{_rng('otp' + phone).randint(0, 999_999):06d}"
    _pending[request_id] = {"phone": phone, "otp": otp, "at": datetime.now(UTC)}
    return {"request_id": request_id, "demo_otp": otp, "mock": True,
            "message": "Code sent by SMS."}


def _issuer_hint(issuer: str) -> str | None:
    low = issuer.lower()
    return next((k for k, w in ISSUER_WORD.items() if w in low), None)


def bureau_report(phone: str, cards: list[tuple[str, str, str]], today: date | None = None) -> CreditReport:
    """`cards` is (id, name, issuer) for the scored catalogue. Picks 2-3 cards from different
    banks, so the feed names the exact product, its open date and limit."""
    rng = _rng("bureau" + phone)
    today = today or datetime.now(UTC).date()
    by_bank: dict[str, list[tuple[str, str, str]]] = {}
    for c in sorted(cards):
        by_bank.setdefault(c[2].split(" (")[0], []).append(c)
    banks = sorted(by_bank)
    accounts = []
    for bank in rng.sample(banks, k=min(len(banks), rng.randint(2, 3))):
        cid, name, issuer = rng.choice(by_bank[bank])
        limit = rng.randrange(75_000, 4_00_000, 5_000)
        balance = rng.randrange(0, limit // 3, 100)
        opened = today - timedelta(days=rng.randint(200, 2_500))
        accounts.append(Account(
            lender=bank, issuer_hint=_issuer_hint(issuer), account_type="Credit Card", last4=f"{rng.randint(0, 9999):04d}",
            credit_limit_paise=limit * R, current_balance_paise=balance * R, overdue_paise=0,
            dpd="000 000 000 000 000 000", max_dpd_days=0, opened=opened.isoformat(), status="Active",
            card_id=cid, card_name=name,
        ))
    enquiries = [Enquiry((today - timedelta(days=rng.randint(10, 170))).isoformat(), rng.choice(_ENQUIRY_LENDERS), "Credit Card")
                 for _ in range(rng.randint(0, 2))]
    return CreditReport(bureau="CIBIL", score=rng.randint(720, 812), report_date=today.isoformat(),
                        accounts=accounts, enquiries=enquiries, warnings=[])


def bureau_verify(conn: Connection, uid: str, request_id: str, otp: str, card_ids: set[str]) -> dict | None:
    req = _pending.get(request_id)
    if req is None or req["otp"] != otp:
        return None
    _pending.pop(request_id, None)
    rows = conn.execute(select(card.c.id, card.c.name, card.c.issuer).where(card.c.id.in_(card_ids))).all()
    out = credit_report.apply(conn, uid, bureau_report(req["phone"], [tuple(r) for r in rows]))
    out["stored"]["source"] = "demo_bureau"
    return {"mock": True, **out}


# A typical month for the demo import: (merchant key, visits, rupees per visit range).
_MONTH = [
    ("swiggy", 9, (250, 650)), ("zomato", 4, (300, 700)), ("restaurant", 3, (900, 2_200)),
    ("bigbasket", 4, (900, 2_400)), ("dmart", 2, (1_200, 3_000)), ("amazon", 3, (600, 4_000)),
    ("flipkart", 1, (800, 3_500)), ("myntra", 1, (1_000, 2_800)), ("uber", 8, (180, 450)),
    ("bpcl", 3, (1_000, 1_800)), ("airtel", 1, (599, 999)), ("bescom", 1, (1_200, 2_600)),
    ("netflix", 1, (199, 649)), ("indigo", 1, (4_500, 9_000)),
]


def _last_month(today: date) -> tuple[date, date]:
    first_this = today.replace(day=1)
    end = first_this - timedelta(days=1)
    return end.replace(day=1), end


def import_last_month(conn: Connection, uid: str, sources: list[str], today: date | None = None) -> dict:
    """Write a simulated last month of SMS/email alerts into the ledger (idempotent)."""
    today = today or datetime.now(UTC).date()
    start, end = _last_month(today)
    rng = _rng(f"ledger:{uid}:{start.isoformat()}")
    held = [h["card_id"] for h in users.holdings(conn, uid)] or ["unassigned"]
    srcs = [f"demo_{s}" for s in sources if f"demo_{s}" in DEMO_SOURCES] or ["demo_sms"]
    n = 0
    for key, visits, (lo, hi) in _MONTH:
        m = by_key(key)
        if m is None:
            continue
        for i in range(visits):
            day = start + timedelta(days=rng.randint(0, (end - start).days))
            amount = rng.randint(lo, hi) * R
            ledger.record(
                conn, uid, card_id=rng.choice(held), amount_paise=amount, merchant_key=key, merchant_name=m["name"],
                category=m["category"], channel=m["channel"], reward_paise=0, cap_use={},
                source=rng.choice(srcs), idempotency_key=f"demo:{uid}:{start.isoformat()}:{key}:{i}",
                ts=datetime(day.year, day.month, day.day, 12, tzinfo=UTC),
            )
            n += 1
    return {"mock": True, "transactions": n, "month": start.strftime("%Y-%m")}
