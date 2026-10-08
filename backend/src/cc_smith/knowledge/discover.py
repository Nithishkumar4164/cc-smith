"""URL discovery for a card's official pages (DR-4 step 1) through the SerpApi gateway.

`site:` is a hint, not a filter: live runs R12-R15 and R20 returned off-site results
for site: queries, so every link is checked against the allow-list in code and must
name the card in its title, URL or snippet."""

import re
from dataclasses import dataclass

from cc_smith.knowledge import allowlist
from cc_smith.ops import serp

_GENERIC = {"credit", "card", "cards", "bank", "the", "and", "&", "of", "new", "co-branded"}
_WORD = re.compile(r"[a-z0-9+]+")


@dataclass(frozen=True)
class DiscoveredUrl:
    url: str
    title: str
    snippet: str
    query: str
    search_id: str | None


def issuer_tokens(issuer: str) -> set[str]:
    # "Federal Bank (fintech partner: Scapia)": the partner is part of the card name.
    issuer = re.sub(r"\([^)]*\)", " ", issuer)
    key = allowlist.issuer_key(issuer)
    toks = set(_WORD.findall(issuer.lower()))
    if key:
        toks |= set(_WORD.findall(key.replace("_", " ")))
        name = (allowlist.load()["issuers"].get(key) or {}).get("name", "")
        toks |= set(_WORD.findall(name.lower()))
    return toks


def core_name(name: str, issuer: str) -> str:
    """The distinctive part of a card name: 'Axis Bank ACE Credit Card' → 'ACE'."""
    drop = _GENERIC | issuer_tokens(issuer)
    words = [w for w in re.split(r"\s+", name.strip()) if w.lower().strip("()") not in drop]
    return " ".join(words) or name


def official_domain(issuer: str) -> str | None:
    key = allowlist.issuer_key(issuer)
    if key is None:
        return None
    canonical = (allowlist.load()["issuers"].get(key) or {}).get("canonical")
    return canonical.removeprefix("www.") if canonical else None


def queries(name: str, issuer: str, page: bool = True, pdf: bool = False) -> list[str]:
    domain = official_domain(issuer)
    if domain is None:
        return []
    core = core_name(name, issuer)
    # Same shapes as the live runs: R20 (page) and R1 (terms PDF).
    out = []
    if page:
        out.append(f'site:{domain} "{core}"')
    if pdf:
        out.append(f'site:{domain} "{core}" terms filetype:pdf')
    return out


def _mentions(core: str, *texts: str) -> bool:
    need = set(_WORD.findall(core.lower()))
    hay = " ".join(texts).lower()
    squashed = re.sub(r"[^a-z0-9+]", "", hay)
    return all(w in hay or w in squashed for w in need)


def discover(name: str, issuer: str, *, flow: str = "card_profile", page: bool = True, pdf: bool = False) -> list[DiscoveredUrl]:
    """Official URLs for the card, best first. Empty when the issuer is not on the
    allow-list (nothing to search) or no result passes the domain check."""
    core = core_name(name, issuer)
    seen: set[str] = set()
    out: list[DiscoveredUrl] = []
    for q in queries(name, issuer, page, pdf):
        res = serp.search(flow, "google", {"q": q, "google_domain": "google.co.in", "gl": "in", "hl": "en"})
        for r in res.data.get("organic_results", []):
            url = r.get("link") or ""
            if url in seen or not allowlist.check(url, issuer, "fees").official:
                continue
            title, snippet = r.get("title", ""), r.get("snippet", "")
            if not _mentions(core, title, url, snippet):
                continue
            seen.add(url)
            out.append(DiscoveredUrl(url, title, snippet, q, res.search_id))
    return out
