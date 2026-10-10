"""Merchant registry and resolver: free text (typed, QR payee name, share URL) → merchant."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

import yaml
from rapidfuzz import fuzz, process

DATA = Path(__file__).resolve().parents[2] / "data" / "merchants.yaml"

# MCC → category for QR codes whose payee is not in the registry.
MCC_CATEGORY = {
    "5411": "grocery", "5412": "grocery", "5499": "grocery",
    "5812": "dining", "5813": "dining", "5814": "dining",
    "5541": "fuel", "5542": "fuel", "5983": "fuel",
    "4121": "travel", "4111": "travel", "4112": "travel", "4722": "travel", "7011": "travel", "4511": "travel",
    "4814": "utilities", "4899": "entertainment", "4900": "utilities",
    "6513": "rent", "6300": "insurance", "9311": "government", "9399": "government",
    "6540": "wallet", "5944": "jewellery", "8220": "education", "8299": "education", "4784": "tolls", "7832": "entertainment",
}


@dataclass(frozen=True)
class Merchant:
    key: str | None
    name: str
    category: str
    channel: str
    mcc: str | None
    confidence: str  # high | medium | low


@lru_cache
def registry() -> dict:
    return yaml.safe_load(DATA.read_text())


@lru_cache
def conditions() -> dict[str, dict]:
    return yaml.safe_load((DATA.parent / "conditions.yaml").read_text())


@lru_cache
def offer_conditions() -> dict[str, list[str]]:
    return yaml.safe_load((DATA.parent / "offer_conditions.yaml").read_text()) or {}


def eligibility(requires: list[str], answers: dict[str, bool]) -> str:
    """'yes' when every condition is answered yes, 'no' when any is answered no,
    otherwise 'unknown'. Unanswered never hides anything."""
    if any(answers.get(k) is False for k in requires):
        return "no"
    if all(answers.get(k) is True for k in requires):
        return "yes"
    return "unknown"


@lru_cache
def memberships() -> dict[str, dict]:
    return yaml.safe_load((DATA.parent / "memberships.yaml").read_text())


def categories() -> dict[str, str]:
    return registry()["categories"]


def by_key(key: str) -> dict | None:
    return next((m for m in registry()["merchants"] if m["key"] == key), None)


def _choices() -> dict[str, str]:
    out = {}
    for m in registry()["merchants"]:
        for label in [m["key"].replace("_", " "), m["name"], *m.get("aliases", [])]:
            out[label.lower()] = m["key"]
    return out


def _as_merchant(m: dict, confidence: str) -> Merchant:
    return Merchant(m["key"], m["name"], m["category"], m["channel"], m.get("mcc"), confidence)


def resolve(text: str, mcc: str | None = None) -> Merchant:
    raw = text.strip()
    if raw.startswith(("http://", "https://")):
        host = urlparse(raw).hostname or ""
        raw = host.removeprefix("www.").removeprefix("m.").split(".")[0]
    query = raw.lower()
    choices = _choices()
    if query in choices:
        return _as_merchant(by_key(choices[query]), "high")
    hit = process.extractOne(query, list(choices), scorer=fuzz.WRatio, score_cutoff=86)
    if hit:
        return _as_merchant(by_key(choices[hit[0]]), "medium")
    if mcc and mcc in MCC_CATEGORY:
        return Merchant(None, text.strip(), MCC_CATEGORY[mcc], "offline", mcc, "medium")
    return Merchant(None, text.strip(), "other", "offline", mcc, "low")
