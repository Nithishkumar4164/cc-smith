"""Launch triage and dedupe (architecture §4 Launch Radar step 2).

Rules run first and are the whole of triage in replay mode, so the demo and tests are
deterministic. In live mode the headlines that pass the rules go to Haiku
(signals.llm.triage_headlines) to name the card; the rules' reading is the fallback.

The dedupe key is the issuer plus the card name with issuer and generic words removed,
sorted, so "Scapia and Axis Bank launch travel credit card" and the seed entry
"Scapia Axis Bank Credit Card" collide."""

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache

from cc_smith.config import REPO
from cc_smith.knowledge import allowlist
from cc_smith.knowledge.discover import issuer_tokens

_LAUNCH = re.compile(
    r"\b(launch(es|ed|ing)?|unveil(s|ed)?|introduc(es|ed|ing)|roll(s|ed)? out|enters?|forays? into|debuts?|goes live)\b", re.IGNORECASE)
_CARD = re.compile(r"\bcards?\b", re.IGNORECASE)
# Card-adjacent launches that are not a new credit card (live run R17: ~9 Apple Pay stories).
_NOISE = re.compile(
    r"\b(apple pay|google wallet|samsung wallet|tap to pay|debit cards?|prepaid|forex cards?|gift cards?|upi lite|"
    r"credit line on upi|fd[- ]backed loan|insurance|mutual fund|stocks?|shares?|ipo)\b", re.IGNORECASE)
_NETWORKS = {"visa", "mastercard", "rupay", "amex", "american", "express", "diners", "club"}
_GENERIC = {
    "credit", "card", "cards", "bank", "the", "and", "with", "new", "launch", "launches", "launched", "india", "indian",
    "co-branded", "cobranded", "co-brand", "travel", "variant", "variants", "metal", "edition", "incl", "a", "an", "of",
    "for", "in", "on", "its", "first", "four", "two", "three", "business", "enters", "forays", "into", "unveils",
}
_WORD = re.compile(r"[a-z0-9+]+")
_CAP_RUN = re.compile(r"((?:[A-Z][\w+&'-]*\s+){1,6}?(?:Credit\s+)?Card)\b")

# Issuers that write credit-card news but are not on the allow-list yet. They can be
# detected and listed; nothing they say can become a fact until the owner adds them.
EXTRA_ISSUERS = {
    "bandhan": "Bandhan Bank", "union bank": "Union Bank of India", "canara": "Canara Bank", "pnb": "Punjab National Bank",
    "punjab national": "Punjab National Bank", "bank of india": "Bank of India", "dbs": "DBS Bank India",
    "standard chartered": "Standard Chartered", "south indian bank": "South Indian Bank", "onecard": "OneCard",
}
ISSUER_NAMES = {
    "hdfc": "HDFC Bank", "sbi": "SBI Card", "icici": "ICICI Bank", "axis": "Axis Bank", "kotak": "Kotak Mahindra Bank",
    "idfc": "IDFC FIRST Bank", "au small": "AU Small Finance Bank", "au bank": "AU Small Finance Bank", "hsbc": "HSBC India",
    "yes bank": "YES Bank", "federal": "Federal Bank", "bobcard": "BOBCARD", "bank of baroda": "BOBCARD",
    "indusind": "IndusInd Bank", "rbl": "RBL Bank", **EXTRA_ISSUERS,
}

# Seed cards whose names in seed-cards.md cover more than one product (row 15: Scapia
# runs on Federal, BOBCARD and, since 3 Sep 2026, Axis). They are known, not launches.
SEED_ALIASES: list[tuple[str, str, str]] = [
    ("scapia_federal", "Scapia Axis Bank Credit Card", "Axis Bank"),
    ("scapia_federal", "Scapia BOBCARD Credit Card", "BOBCARD"),
]


@dataclass
class Verdict:
    is_launch: bool
    issuer: str | None = None
    card_name: str | None = None
    reasons: list[str] = field(default_factory=list)


def _slug(text: str) -> str:
    return "_".join(_WORD.findall(text.lower()))


def find_issuer(text: str) -> str | None:
    low = text.lower()
    hits = [(m.start(), name) for hint, name in ISSUER_NAMES.items() if (m := re.search(rf"\b{re.escape(hint)}", low))]
    return min(hits)[1] if hits else None


def issuer_slug(issuer: str) -> str:
    return allowlist.issuer_key(issuer) or _slug(issuer)


def _issuer_words(issuer: str) -> set[str]:
    return issuer_tokens(issuer) | set(_WORD.findall(issuer_slug(issuer).replace("_", " ")))


def name_tokens(name: str, issuer: str) -> list[str]:
    name = re.sub(r"\([^)]*\)", " ", name)
    drop = _GENERIC | _NETWORKS | _issuer_words(issuer)
    return sorted({w for w in _WORD.findall(name.lower()) if w not in drop})


def dedupe_key(issuer: str, name: str) -> str:
    return f"{issuer_slug(issuer)}:{'-'.join(name_tokens(name, issuer)) or '*'}"


def card_id_for(issuer: str, name: str) -> str:
    prefix = issuer_slug(issuer).split("_")[0]
    return f"{prefix}_{'_'.join(name_tokens(name, issuer)) or 'card'}"


def _card_name(title: str, issuer: str) -> str:
    """Best-effort card name from a headline. Prefers a capitalised run ending in
    'Card' ("Google Pay Flex SBI Card"); else partner brand + issuer ("Scapia and Axis
    Bank launch ..." → "Scapia Axis Bank Credit Card"); else the issuer's new cards."""
    issuer_words = _issuer_words(issuer)
    for m in _CAP_RUN.finditer(title):
        run = m.group(1).strip()
        words = [w for w in _WORD.findall(run.lower()) if w not in _GENERIC and w not in _NETWORKS]
        if any(w not in issuer_words for w in words):
            return run
    brands = [w for w in re.findall(r"\b[A-Z][\w+&'-]*", title)
              if w.lower() not in _GENERIC and w.lower() not in _NETWORKS and w.lower() not in issuer_words]
    if brands:
        return f"{' '.join(dict.fromkeys(brands))} {issuer} Credit Card"
    return f"{issuer} credit cards"


def rules(title: str, snippet: str = "") -> Verdict:
    text = f"{title} {snippet}".strip()
    if _NOISE.search(text):
        return Verdict(False, reasons=[f"noise: {_NOISE.search(text).group(0)}"])
    if not (_LAUNCH.search(title) and _CARD.search(title)):
        return Verdict(False, reasons=["no launch verb + card in headline"])
    issuer = find_issuer(title) or find_issuer(snippet)
    if issuer is None:
        return Verdict(False, reasons=["no known issuer named"])
    return Verdict(True, issuer, _card_name(title, issuer), ["rules"])


@lru_cache
def seed_cards() -> tuple[tuple[str, str, str], ...]:
    """(card_id, name, issuer) for the seed list, which counts as catalogue even before
    every seed has been profiled (DR-4 catalogue growth)."""
    out = []
    for fname in ("verified-card-facts.json", "seed-card-facts-batch2.json"):
        path = REPO / "docs" / "research" / fname
        if path.exists():
            out += [(c["id"], c["name"], c["issuer"]) for c in json.loads(path.read_text())["cards"]]
    return tuple(out + SEED_ALIASES)
