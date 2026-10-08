"""Official-source allow-list (docs/research/official-domains.yaml, DR-4 §6).

A URL is official for a field only if its host belongs to the card's issuer, or to a
partner that owns that field (co-brand partners own the reward currency; fintech
operators such as Scapia and Kiwi also own the earn programme)."""

from dataclasses import dataclass
from fnmatch import fnmatch
from functools import lru_cache
from urllib.parse import urlparse

import yaml

from cc_smith.config import settings

PARTNER_FIELDS = {"currency"}
FINTECH_FIELDS = {"currency", "earn_rules", "caps"}

ISSUER_HINTS = {
    "hdfc": "hdfc_bank", "sbi": "sbi_card", "icici": "icici_bank", "axis": "axis_bank",
    "kotak": "kotak_mahindra_bank", "idfc": "idfc_first_bank", "au small": "au_small_finance_bank",
    "au bank": "au_small_finance_bank", "hsbc": "hsbc_india", "yes bank": "yes_bank",
    "federal": "federal_bank", "bobcard": "bobcard", "bank of baroda": "bobcard",
    "indusind": "indusind_bank", "rbl": "rbl_bank",
}


@dataclass(frozen=True)
class Verdict:
    official: bool
    owner: str | None  # issuer key or partner key
    reason: str


@lru_cache
def load() -> dict:
    return yaml.safe_load(settings.allowlist_path.read_text())


def issuer_key(issuer_name: str) -> str | None:
    low = issuer_name.lower()
    if low in ("au", "au lit"):
        return "au_small_finance_bank"
    return next((k for hint, k in ISSUER_HINTS.items() if hint in low), None)


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _same(host: str, allowed: str) -> bool:
    allowed = allowed.lower()
    return host == allowed or host == "www." + allowed or "www." + host == allowed


def issuer_hosts(key: str) -> list[str]:
    i = load()["issuers"].get(key) or {}
    return [h for h in [i.get("canonical"), *i.get("legacy", []), *i.get("asset_hosts", []), *i.get("legacy_asset_hosts", [])] if h]


def check(url: str, issuer_name: str, field: str) -> Verdict:
    if urlparse(url).scheme != "https":
        return Verdict(False, None, "not https")
    host = _host(url)
    key = issuer_key(issuer_name)
    if key and any(_same(host, h) for h in issuer_hosts(key)):
        return Verdict(True, key, "issuer")
    for pkey, p in (load().get("partner_sources") or {}).items():
        if not any(_same(host, h) for h in p.get("hosts", [])):
            continue
        prefix = (p.get("path_prefix") or {}).get(host)
        path = urlparse(url).path
        if prefix and not path.startswith(prefix):
            return Verdict(False, pkey, "partner host outside allowed path")
        if any(fnmatch(path, pat) for pat in p.get("exclude_paths", [])):
            return Verdict(False, pkey, "partner path excluded")
        if key and p.get("issuers") and key not in p["issuers"]:
            return Verdict(False, pkey, "partner not linked to this issuer")
        owned = FINTECH_FIELDS if p.get("operator") == "fintech" else PARTNER_FIELDS
        if field in owned:
            return Verdict(True, pkey, "partner-owned field")
        return Verdict(False, pkey, f"partner source is not official for {field}")
    return Verdict(False, None, "host not on allow-list")
