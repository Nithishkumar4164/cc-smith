"""Parse Indian card/bank transaction alert text (SMS, app notification or email body)
into a small structured event. The phone runs a Dart port of this parser on
notifications and uploads only the parsed fields (DR-2); the server runs it on Gmail
alert bodies. `fixtures/alerts/vectors.json` is the shared test-vector file both
implementations must pass.

Output: {amount_paise, currency, last4, merchant_text, ts, kind, issuer_hint, instrument}
- amount_paise: amount x 100 in `currency` (INR for almost every alert; a foreign-currency
  alert keeps its own currency and the ledger ignores it until the statement shows INR).
- kind: debit | credit | refund | payment_received
- instrument: credit_card | debit_card | account | card (a card the text does not type)
- ts: ISO 8601 in IST (+05:30); None when the text carries no date.

The parser is generic (amount / card / merchant / date / kind extracted independently)
rather than one regex per template, so small wording changes do not break it. Formats
it is tested against, and where each came from (all read 2026-10-10):

[A] akhilnarang/bank-sms-parser, tests/fixtures/sms/<bank>/*.txt — scrubbed real SMS
    (digits zeroed) for HDFC, ICICI, SBI Card, Axis, HSBC, IDFC FIRST, Kotak:
    https://github.com/akhilnarang/bank-sms-parser/tree/main/tests/fixtures/sms
[P] sarim2000/pennywiseai-tracker, parser-core/src/test/kotlin/Test<Bank>Parser.kt —
    test cases built from user-reported SMS for AU, YES, Kotak CC, SBI Card, HDFC:
    https://github.com/sarim2000/pennywiseai-tracker/tree/main/parser-core/src/test/kotlin
[D] Rrishik/dus-aane-bot BankTemplates.js — "approximated public formats" (secondary):
    https://github.com/Rrishik/dus-aane-bot/blob/main/BankTemplates.js
[G] GUESS — written from memory of issuer email alerts / app notifications, not checked
    against a published sample. Marked `"source": "guess"` in the vectors; verify with
    real alerts before relying on them.
"""

import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta, timezone

from cc_smith.capture.privacy import strip_long_digit_runs

IST = timezone(timedelta(hours=5, minutes=30))

KINDS = ("debit", "credit", "refund", "payment_received")


@dataclass
class Alert:
    amount_paise: int
    currency: str
    last4: str | None
    merchant_text: str | None
    ts: str | None
    kind: str
    issuer_hint: str | None
    instrument: str

    def to_dict(self) -> dict:
        return asdict(self)


# ---------- issuer ----------
# Issuer ids match docs/research/official-domains.yaml.
ISSUER_WORDS: list[tuple[str, str]] = [
    (r"\bhdfc\s*bank\b|\bhdfcbank\b|\bhdfc\b", "hdfc_bank"),
    (r"\bicici\b", "icici_bank"),
    (r"\bsbi\s*cards?\b|\bsbi\s+credit\s+card\b|\bsbicard\b|\bsbi\s+cardholder\b", "sbi_card"),
    (r"\baxis\s*bank\b|\baxis\b", "axis_bank"),
    (r"\bhsbc\b|hongkong\s+and\s+shanghai", "hsbc_india"),
    (r"\bkotak\b", "kotak_mahindra_bank"),
    (r"\bidfc\b|\bfirst\s+(?:wealth|millennia|classic|select|wow)\b", "idfc_first_bank"),
    (r"\bkiwi\b", "yes_bank"),  # Kiwi credit-on-UPI cards are issued by YES Bank
    (r"\byes\s*bank\b|\byesbank\b", "yes_bank"),
    (r"\bau\s+(?:small\s+finance\s+)?bank\b|\baubank\b", "au_small_finance_bank"),
]
# DLT sender headers ("AX-HDFCBK-S"): the 6-letter entity code after the operator prefix.
SENDER_CODES = {
    "HDFCBK": "hdfc_bank", "HDFCCC": "hdfc_bank", "ICICIB": "icici_bank", "ICICIT": "icici_bank",
    "SBICRD": "sbi_card", "SBIPSG": "sbi_card", "SBICAR": "sbi_card", "AXISBK": "axis_bank", "AXISCC": "axis_bank",
    "HSBCIN": "hsbc_india", "HSBCBK": "hsbc_india", "KOTAKB": "kotak_mahindra_bank", "KOTAKD": "kotak_mahindra_bank",
    "IDFCFB": "idfc_first_bank", "IDFCBK": "idfc_first_bank", "YESBNK": "yes_bank", "YESBCC": "yes_bank",
    "AUBANK": "au_small_finance_bank", "AUBKCC": "au_small_finance_bank", "GOKIWI": "yes_bank",
}
SENDER_DOMAINS = {
    "hdfcbank.net": "hdfc_bank", "hdfcbank.com": "hdfc_bank", "hdfc.bank.in": "hdfc_bank", "hdfcbank.bank.in": "hdfc_bank",
    "icicibank.com": "icici_bank", "icici.bank.in": "icici_bank", "sbicard.com": "sbi_card",
    "axisbank.com": "axis_bank", "axis.bank.in": "axis_bank", "hsbc.co.in": "hsbc_india", "hsbc.bank.in": "hsbc_india",
    "kotak.com": "kotak_mahindra_bank", "kotak.bank.in": "kotak_mahindra_bank",
    "idfcfirstbank.com": "idfc_first_bank", "idfcfirst.bank.in": "idfc_first_bank",
    "yesbank.in": "yes_bank", "yes.bank.in": "yes_bank", "aubank.in": "au_small_finance_bank", "au.bank.in": "au_small_finance_bank",
}


def issuer_from_sender(sender: str | None) -> str | None:
    if not sender:
        return None
    s = sender.strip()
    if "@" in s:
        domain = s.rsplit("@", 1)[1].strip(" >").lower()
        for d, issuer in SENDER_DOMAINS.items():
            if domain == d or domain.endswith("." + d):
                return issuer
        return None
    for part in re.split(r"[-_ ]", s.upper()):
        if part in SENDER_CODES:
            return SENDER_CODES[part]
    return None


def issuer_from_text(text: str) -> str | None:
    best: tuple[int, str] | None = None
    for pattern, issuer in ISSUER_WORDS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), issuer)
    return best[1] if best else None


# ---------- normalise ----------
def normalise(text: str) -> str:
    """NFKC folds styled Unicode (SBI Card sends 𝗌𝗉𝖾𝗇𝗍 in Mathematical Sans-Serif) to ASCII.
    Spaces collapse within a line; line breaks are kept because Axis and HDFC put fields
    on separate lines."""
    t = unicodedata.normalize("NFKC", text).replace("\r", "\n").replace(" ", " ")
    t = strip_long_digit_runs(t)
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in t.split("\n")]
    return "\n".join(ln for ln in lines if ln)


# ---------- skip ----------
NOT_A_TRANSACTION = re.compile(
    r"\bOTP\b|one[- ]time password|verification code|\bis due\b|\bdue (?:by|on)\b|payment due date"
    r"|statement (?:for|of) .{0,40}(?:generated|is ready)|\bdeclined\b|\bfailed\b|\bunsuccessful\b|has been blocked"
    r"|will be (?:debited|charged)|\bmandate\b|requested (?:money|payment)|collect request|\bbill alert\b",
    re.IGNORECASE,
)
# Promotional words only disqualify a message that has no transaction verb (email footers carry offers).
PROMO = re.compile(r"\boffers?\b|\bapply now\b|\bpre-?approved\b|\bcashback offer\b|limit (?:has been )?(?:increased|enhanced)", re.IGNORECASE)


# ---------- amount ----------
CUR = r"(?P<cur>INR|Rs|₹|USD|EUR|GBP|SGD|AED|AUD|CAD|JPY|CHF|THB|MYR|HKD)"
AMOUNT = re.compile(CUR + r"\s*\.?\s*:?\s*(?P<num>\d[\d,]*(?:\.\d{1,2})?|\.\d{1,2})(?![\d])", re.IGNORECASE)
# Amounts that are a balance/limit, not the transaction.
NOT_TXN_AMOUNT = re.compile(r"(?:limit|lmt|bal|balance|outstanding|due|available|avl|avbl)\W{0,3}(?:is\s+|of\s+)?\W{0,3}$", re.IGNORECASE)


def _amount(t: str) -> tuple[int, str] | None:
    for m in AMOUNT.finditer(t):
        before = t[max(0, m.start() - 25):m.start()]
        if NOT_TXN_AMOUNT.search(before):
            continue
        num = m.group("num").replace(",", "")
        rupees, _, frac = num.partition(".")
        paise = int(rupees or 0) * 100 + int((frac + "00")[:2])
        if paise <= 0:
            continue
        cur = m.group("cur").upper()
        return paise, "INR" if cur in ("RS", "₹", "INR") else cur
    # SBI UPI: "debited by 120.0 on date" (no currency word)
    m = re.search(r"debited by (\d[\d,]*(?:\.\d{1,2})?) on date", t, re.IGNORECASE)
    if m:
        num = m.group(1).replace(",", "")
        rupees, _, frac = num.partition(".")
        return int(rupees) * 100 + int((frac + "00")[:2]), "INR"
    return None


# ---------- card / account ----------
CARD_LAST4 = re.compile(
    r"(?:credit\s*card|creditcard|debit\s*card|card)(?:\s+account)?\s*(?:no\.?|number|num)?\s*"
    r"(?:ending\s*(?:with|in)?)?\s*[:#\-]?\s*[0-9xX*•.]*?(?P<l4>\d{4})(?!\d)",
    re.IGNORECASE,
)
ENDING_LAST4 = re.compile(r"\bending\s*(?:with|in)?\s*[xX*•.]*(?P<l4>\d{4})(?!\d)", re.IGNORECASE)
BLOCK_LAST4 = re.compile(r"\bBLOCK\s*(?:CC|PCC|DC|CARD)?\s*(?:XX)?(?P<l4>\d{4})(?!\d)", re.IGNORECASE)
ACCOUNT_LAST4 = re.compile(r"(?:a/c|acct|account|\bac)\s*(?:no\.?)?\s*[xX*]*(?P<l4>\d{3,4})(?!\d)", re.IGNORECASE)

CARD_WORD = re.compile(r"credit\s*card|creditcard|\bcard\b|\bcardmember\b|\bcardholder\b", re.IGNORECASE)
CREDIT_CARD = re.compile(r"credit\s*card|creditcard|\bcardmember\b|\bcardholder\b|BLOCK\s*P?CC\b|CCBLOCK|BLKCC|\bAvl\.?\s*(?:Limit|Lmt)\b|\bAvbl\.?\s*Limit\b|available limit", re.IGNORECASE)
DEBIT_CARD = re.compile(r"debit\s*card|BLOCK\s*DC\b|from\s+HDFC\s+Bank\s+Card", re.IGNORECASE)
ACCOUNT = re.compile(r"\ba/c\b|\bacct\b|\baccount\b|\bAC\s+X|\bupi user\b", re.IGNORECASE)


def _instrument(t: str) -> str:
    if DEBIT_CARD.search(t):
        return "debit_card"
    if CREDIT_CARD.search(t):
        return "credit_card"
    if CARD_WORD.search(t) and not ACCOUNT.search(t):
        return "card"
    if ACCOUNT.search(t):
        return "account"
    return "card" if CARD_WORD.search(t) else "account"


def _last4(t: str, instrument: str) -> str | None:
    if instrument == "account":
        m = ACCOUNT_LAST4.search(t)
        return m.group("l4") if m else None
    for rx in (CARD_LAST4, ENDING_LAST4, BLOCK_LAST4):
        m = rx.search(t)
        if m:
            return m.group("l4")
    return None


# ---------- kind ----------
REFUND = re.compile(r"\brefund|\brevers(?:ed|al)\b", re.IGNORECASE)
PAYMENT_RECEIVED = re.compile(
    r"payment\s+of\b.{0,80}?\b(?:received|credited|processed)|thank you for (?:your )?payment|received (?:a |your )?payment"
    r"|payment\s+(?:has been\s+)?(?:received|credited)|we have received a payment",
    re.IGNORECASE | re.DOTALL,
)
DEBIT_VERB = re.compile(r"\bspent\b|\bdebited\b|\bused\b|\btxn\b(?! reversal)|\bpurchase\b|\bpaid\b|\bsent\b|\bdeducted\b|\btransaction of\b|\bwithdrawn\b|\bcharged\b"
    r"|\bfor using\b|\btransaction (?:amount|alert)\b", re.IGNORECASE)
CREDIT_VERB = re.compile(r"\bcredited\b|\breceived\b|\bdeposited\b|\bsent to your\b", re.IGNORECASE)


def _kind(t: str, instrument: str) -> str | None:
    if REFUND.search(t):
        return "refund"
    if instrument != "account" and PAYMENT_RECEIVED.search(t) and not re.search(r"\bfrom\s+(?:your\s+)?a/c\b", t, re.IGNORECASE):
        return "payment_received"
    d, c = DEBIT_VERB.search(t), CREDIT_VERB.search(t)
    if c and re.match(r"sent to your", c.group(), re.IGNORECASE):
        return "credit"
    if d and (not c or d.start() <= c.start()):
        return "debit"
    if c:
        return "credit"
    return None


# ---------- date ----------
MON = r"(?P<mon>jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"
DATES = [
    re.compile(r"(?P<y>\d{4})-(?P<m>\d{1,2})-(?P<d>\d{1,2})(?:[:T ](?P<H>\d{1,2}):(?P<M>\d{2})(?::(?P<S>\d{2}))?)?"),
    re.compile(r"(?<![\d/])(?P<d>\d{1,2})[-/ ]" + MON + r"[-/ ,]+(?P<y>\d{4}|\d{2})(?![\d])", re.IGNORECASE),
    re.compile(r"(?<![\d])(?P<d>\d{1,2})" + MON + r"(?P<y>\d{2,4})(?![\d])", re.IGNORECASE),
    re.compile(r"\b" + MON + r"\s+(?P<d>\d{1,2}),?\s+(?P<y>\d{4})", re.IGNORECASE),
    re.compile(r"(?<![\d/:.,])(?P<d>\d{1,2})[-/.](?P<m>\d{1,2})[-/.](?P<y>\d{4}|\d{2})(?![\d/])"),
    re.compile(r"(?<![\d/:.,])(?P<d>\d{1,2})-(?P<m>\d{1,2})(?![\d/\-:.])"),  # HDFC UPI "On 23-05": no year
]
TIME = re.compile(r"^(?:[ ,]+(?:at\s+)?|_?)(?P<H>\d{1,2}):(?P<M>\d{2})(?::(?P<S>\d{2}))?(?:\s*(?P<ap>[ap]\.?m\.?))?", re.IGNORECASE)
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _ts(t: str, received_at: datetime | None) -> str | None:
    ref = (received_at or datetime.now(UTC)).astimezone(IST)
    found: list[tuple[int, re.Match]] = []
    for rx in DATES:
        m = rx.search(t)
        if m:
            found.append((m.start(), m))
    for _, m in sorted(found, key=lambda x: x[0]):
        g = m.groupdict()
        try:
            month = MONTHS[g["mon"].lower()[:3]] if g.get("mon") else int(g["m"])
            day = int(g["d"])
            if g.get("y"):
                year = int(g["y"])
                year += 2000 if year < 100 else 0
            else:
                year = ref.year
                if date(year, month, day) > ref.date() + timedelta(days=1):
                    year -= 1
            d = date(year, month, day)
        except (ValueError, KeyError, TypeError):
            continue
        hh = mm = ss = 0
        if g.get("H"):
            hh, mm, ss = int(g["H"]), int(g["M"]), int(g.get("S") or 0)
        else:
            tm = TIME.match(t[m.end():])
            if tm:
                hh, mm, ss = int(tm["H"]), int(tm["M"]), int(tm["S"] or 0)
                ap = (tm["ap"] or "").lower().replace(".", "")
                if ap == "pm" and hh < 12:
                    hh += 12
                elif ap == "am" and hh == 12:
                    hh = 0
        if hh > 23 or mm > 59 or ss > 59:
            hh = mm = ss = 0
        return datetime(d.year, d.month, d.day, hh, mm, ss, tzinfo=IST).isoformat()
    return None


# ---------- merchant ----------
_END = r"(?=\s+(?:on|for|was|by|via|ref|avl|avbl|info|using|with|txn|if|not|card|dated?|at\s+\d)\b|\s*[.;](?:\s|$)|\n|$|\s+\d{1,2}[-/]\d{1,2}[-/]\d{2,4})"
MERCHANT_PATTERNS = [
    re.compile(r"Merchant Name\s*:?\s*(?P<m>[^\n]+)", re.IGNORECASE),  # [G] Axis-style email table
    re.compile(r"\bInfo\s*:\s*(?P<m>[^\n.]+)", re.IGNORECASE),  # [G] ICICI email "Info: AMAZON"
    re.compile(r"\brefunded by (?P<m>.+?)" + _END, re.IGNORECASE),
    re.compile(r"\bfrom (?P<m>.+?) refunded\b", re.IGNORECASE),
    re.compile(r"^(?P<m>[A-Za-z][^\n]{1,60}?) refund of\b", re.IGNORECASE),
    re.compile(r"\b(?:used|spent|purchase|paid|transaction|txn|reversal)\b[^\n]*?\bat\s+(?P<m>.+?)" + _END, re.IGNORECASE),
    re.compile(r"(?:^|\n|\s)at\s+(?P<m>.+?)" + _END, re.IGNORECASE),
    re.compile(r"@\s*(?:UPI_)?(?P<m>[^@\n]+?)(?=\s+\d{1,2}-\d{1,2}-\d{2,4}|\s+on\b|\.\s|\n|$)", re.IGNORECASE),
    re.compile(r"\btowards (?!your\b)(?P<m>.+?)" + _END, re.IGNORECASE),
    re.compile(r"\bon \d{1,2}-[A-Za-z]{3}-\d{2,4} on (?P<m>.+?)" + _END, re.IGNORECASE),  # ICICI "on 01-May-26 on ONYX BAR."
    re.compile(r"\bBy (?P<m>.+?)\s+On\s+\d", re.IGNORECASE),  # HDFC reversal "By AMAZON 000 On 2026-..."
    re.compile(r";\s*(?P<m>[^;\n]+?) credited\b", re.IGNORECASE),  # ICICI/IDFC UPI "; Pune Metro credited."
    re.compile(r"\btrf to (?P<m>.+?) Ref", re.IGNORECASE),  # SBI UPI
    re.compile(r"\bto (?!your\b|a/c\b)(?P<m>[^\n]+?)(?=\s+(?:using|via|from)\b|\s+on\s+\d)", re.IGNORECASE),  # Kotak/HDFC UPI "Sent Rs.X from .. to NAME on 10-09-26"
    re.compile(r"\nTo (?P<m>[^\n]+)\nOn\b", re.IGNORECASE),  # HDFC multi-line UPI
    # Axis multi-line card SMS: the merchant is the line after the date/time line.
    re.compile(r"\n\d{2}-\d{2}-\d{2,4},?\s+\d{2}:\d{2}:\d{2}(?:\s*IST)?\n(?P<m>[^\n]+)", re.IGNORECASE),
]
BAD_MERCHANT = re.compile(r"^(?:https?:|www\.|\d{1,2}:\d{2}|your\b|the\b|card\b|a/c\b|\d+$|rs\b|inr\b)", re.IGNORECASE)


def _clean_merchant(raw: str) -> str | None:
    m = raw.strip(" .,:;-*")
    if "@" in m and " " not in m:  # a VPA: keep its handle
        m = re.sub(r"[._\-]+", " ", m.split("@", 1)[0])
    m = re.sub(r"^(?:UPI[-_/ ]+(?:P2[AM][-_/ ]+)?)+", "", m, flags=re.IGNORECASE)
    m = re.sub(r"(?:\s+\d{1,6})+$", "", m)  # trailing terminal ids "AMAZON 000"
    m = re.sub(r"[-_/]{2,}", "-", m)
    m = re.sub(r"\s{2,}", " ", m).strip(" .,:;-*")
    if len(m) < 2 or BAD_MERCHANT.search(m):
        return None
    return m[:80]


def _merchant(t: str) -> str | None:
    for rx in MERCHANT_PATTERNS:
        for m in rx.finditer(t):
            cleaned = _clean_merchant(m.group("m"))
            if cleaned:
                return cleaned
    return None


# ---------- entry point ----------
def parse(text: str, sender: str | None = None, received_at: datetime | None = None) -> Alert | None:
    """None when the text is not a completed transaction (OTP, reminder, promo, decline)
    or has no amount."""
    if not text or not text.strip():
        return None
    t = normalise(text)
    if NOT_A_TRANSACTION.search(t) and not REFUND.search(t) and not PAYMENT_RECEIVED.search(t):
        return None
    if PROMO.search(t) and not (DEBIT_VERB.search(t) or CREDIT_VERB.search(t)):
        return None
    amt = _amount(t)
    if not amt:
        return None
    instrument = _instrument(t)
    kind = _kind(t, instrument)
    if kind is None:
        return None
    merchant = None if kind == "payment_received" else _merchant(t)
    return Alert(
        amount_paise=amt[0], currency=amt[1], last4=_last4(t, instrument), merchant_text=merchant,
        ts=_ts(t, received_at), kind=kind, issuer_hint=issuer_from_sender(sender) or issuer_from_text(t), instrument=instrument,
    )
