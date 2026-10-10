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

from rapidfuzz import fuzz

from cc_smith.config import REPO
from cc_smith.knowledge import allowlist
from cc_smith.knowledge.discover import issuer_tokens

_LAUNCH = re.compile(
    r"\b(launch(es|ed|ing)?|unveil(s|ed)?|introduc(es|ed|ing)|roll(s|ed)? out|enters?|forays? into|debuts?|goes live)\b", re.IGNORECASE)
_CARD = re.compile(r"\bcards?\b", re.IGNORECASE)
# Card-adjacent launches that are not a new credit card (live run R17: ~9 Apple Pay stories).
_NOISE = re.compile(
    r"\b(apple pay|google wallet|samsung wallet|tap to pay|debit cards?|prepaid|forex cards?|gift cards?|upi lite|"
    r"credit line on upi|fd[- ]backed loan|insurance|mutual fund|stocks?|shares?|ipo|e-debit|"
    r"savings accounts?|current accounts?|salary accounts?|home loans?|personal loans?|car loans?)\b", re.IGNORECASE)


def is_noise(text: str) -> bool:
    """Not a new credit card: wallets, debit/prepaid/forex cards, bank accounts, loans."""
    return bool(_NOISE.search(text))
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

# Seed cards listed under another name. Empty on purpose: a co-brand on a different
# issuer (Scapia on Axis vs Federal) is a separate card under DR-4's variant route,
# matched on issuer + family + variant, never on the co-brand name alone.
SEED_ALIASES: list[tuple[str, str, str]] = []
SAME_LAUNCH_RATIO = 85


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


# Indian banking shorthand seen in launch headlines ("OD CC linked card" = overdraft and
# cash-credit linked). "credit" is already generic, so "cc" maps to its other word.
_ABBREV = {"od": "overdraft", "cc": "cash"}


def name_tokens(name: str, issuer: str) -> list[str]:
    name = re.sub(r"\([^)]*\)", " ", name)
    drop = _GENERIC | _NETWORKS | _issuer_words(issuer)
    return sorted({_ABBREV.get(w, w) for w in _WORD.findall(name.lower()) if w not in drop})


def dedupe_key(issuer: str, name: str) -> str:
    return f"{issuer_slug(issuer)}:{'-'.join(name_tokens(name, issuer)) or '*'}"


def is_generic(name: str, issuer: str) -> bool:
    """Nothing left once the issuer and generic words are removed ("SBI Credit Cards")."""
    return not name_tokens(name, issuer)


def specificity(name: str, issuer: str) -> int:
    """How specific a launch name is; names that are really headlines rank lower."""
    return len(name_tokens(name, issuer)) - (2 if _LAUNCH.match(name.strip()) else 0)


def same_launch(issuer_a: str, name_a: str, text_a: str, issuer_b: str, name_b: str, text_b: str) -> bool:
    """Two leads are one launch when they share an issuer and either their names are
    near-identical (token-set similarity >= 85, which includes one name's words being a
    subset of the other's) or one name's words all appear in the other lead's headline."""
    if issuer_slug(issuer_a) != issuer_slug(issuer_b):
        return False
    ta, tb = set(name_tokens(name_a, issuer_a)), set(name_tokens(name_b, issuer_b))
    if not ta or not tb:
        return False
    if fuzz.token_set_ratio(" ".join(sorted(ta)), " ".join(sorted(tb))) >= SAME_LAUNCH_RATIO:
        return True
    return ta <= set(name_tokens(text_b, issuer_b)) or tb <= set(name_tokens(text_a, issuer_a))


def variant_family(issuer: str, name: str, catalogue: list[tuple[str, str, str]]) -> tuple[str, str] | None:
    """A catalogue card from a different issuer in the same family (Scapia on Axis vs
    Scapia on Federal): returns (card_id, family words) or None."""
    tokens = set(name_tokens(name, issuer))
    if not tokens:
        return None
    for cid, cname, cissuer in catalogue:
        if issuer_slug(cissuer) == issuer_slug(issuer):
            continue
        family = set(name_tokens(cname, cissuer))
        if family and (family <= tokens or tokens <= family):
            return cid, " ".join(sorted(family & tokens)).title()
    return None


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
