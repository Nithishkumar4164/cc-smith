"""Card Profile workflow (DR-4, DR-12): extraction → allow-list → quote check →
range checks → publish as fact, or store as speculation. No human step."""

import json
from dataclasses import dataclass, field

from sqlalchemy import Connection

from cc_smith.db import engine
from cc_smith.knowledge import allowlist, store
from cc_smith.knowledge.fetcher import Evidence, FetchError, fetch
from cc_smith.knowledge.quotes import match_kind
from cc_smith.knowledge.schema import FIELDS, CardProfile

MAX_EARN_BP = 2_500
MAX_FEE_PAISE = 100_000 * 100
LARGE_CHANGE = 0.5


@dataclass
class FieldResult:
    field: str
    outcome: str  # first | published | unchanged | speculation | empty
    reasons: list[str] = field(default_factory=list)


@dataclass
class ProfileResult:
    card_id: str
    fields: list[FieldResult]

    def summary(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for f in self.fields:
            out[f.outcome] = out.get(f.outcome, 0) + 1
        return out


def _field_value(p: CardProfile, name: str):
    if name == "min_txn":
        if p.min_txn_paise is None:
            return None
        return {"min_txn_paise": p.min_txn_paise, "min_txn_src": [s.model_dump() for s in p.min_txn_src]}
    v = getattr(p, name)
    if v is None or v == []:
        return None
    if isinstance(v, list):
        return [x.model_dump(exclude_none=True) for x in v]
    return v.model_dump(exclude_none=True)


def _sources(value) -> list[dict]:
    out: list[dict] = []
    if isinstance(value, dict):
        for key in ("src", "min_txn_src"):
            out.extend(value.get(key, []))
    elif isinstance(value, list):
        for item in value:
            out.extend(_sources(item))
    return out


def _range_problems(name: str, value, p: CardProfile) -> list[str]:
    problems = []
    if name == "earn_rules":
        unit = p.currency.value_paise if p.currency else 100
        for r in value:
            rate = r["rate"]
            if rate["kind"] == "pct":
                bp = rate.get("bp") or 0
            else:
                bp = (rate.get("points") or 0) * unit * 10_000 // max(rate.get("per_paise") or 1, 1)
            if bp > MAX_EARN_BP:
                problems.append(f"rule {r['id']} earns {bp / 100:.1f}% (> 25%)")
    if name == "fees":
        for k in ("joining_paise", "annual_paise"):
            if (value.get(k) or 0) > MAX_FEE_PAISE:
                problems.append(f"{k} above ₹1 lakh")
    return problems


def _indian(n: int) -> str:
    s = str(n)
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    return ",".join([head, *groups, tail]) if head else ",".join([*groups, tail])


def _amount_forms(rupees: int) -> set[str]:
    forms = {str(rupees), f"{rupees:,}", _indian(rupees)}
    if rupees % 100_000 == 0 or rupees % 10_000 == 0:
        lakh = rupees / 100_000
        txt = f"{lakh:g}"
        forms |= {f"{txt} lakh", f"{txt} lac", f"{txt}lakh"}
    return forms


def _pct_forms(bp: int) -> set[str]:
    v = bp / 100
    return {f"{v:g}%", f"{v:g} %", f"{v:.2f}%", f"{v:g} per cent", f"{v:g}x"}


def _quotes_text(item) -> str:
    from cc_smith.knowledge.quotes import normalise

    return normalise(" ".join(s["quote"].replace(" | ", " ") for s in _sources(item)))


def _value_problems(name: str, value) -> list[str]:
    """Each number we publish must be written in its own quote, so a misread value
    cannot pass on the strength of a quote that says something else."""
    problems = []

    def need(forms: set[str], text: str, what: str) -> None:
        if not any(f.lower() in text for f in forms):
            problems.append(f"{what} not stated in its quote")

    if name == "fees":
        text = _quotes_text(value)
        for k in ("joining_paise", "annual_paise", "waiver_spend_paise"):
            v = value.get(k)
            if v:
                need(_amount_forms(v // 100), text, k)
    elif name == "caps":
        for c in value:
            amount = c["amount"] // 100 if c["unit"] in ("paise", "spend_paise") else c["amount"]
            need(_amount_forms(amount), _quotes_text(c), f"cap {c['id']}")
    elif name == "earn_rules":
        for r in value:
            rate = r["rate"]
            if rate["kind"] == "pct":
                need(_pct_forms(rate["bp"]), _quotes_text(r), f"rule {r['id']} rate")
    return problems


def _numbers(value, prefix="") -> dict[str, float]:
    out: dict[str, float] = {}
    if isinstance(value, dict):
        for k, v in value.items():
            if k in ("src", "min_txn_src", "note", "description"):
                continue
            out.update(_numbers(v, f"{prefix}.{k}"))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            key = v.get("id", str(i)) if isinstance(v, dict) else str(i)
            out.update(_numbers(v, f"{prefix}[{key}]"))
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        out[prefix] = value
    return out


def _large_change(old, new) -> bool:
    if old is None:
        return False
    a, b = _numbers(old), _numbers(new)
    for k in a.keys() & b.keys():
        if a[k] and abs(b[k] - a[k]) / abs(a[k]) > LARGE_CHANGE:
            return True
    return False


def _verify(name: str, value, issuer: str, evidence_cache: dict[str, Evidence | str], refresh: bool) -> tuple[list[dict], list[str]]:
    refs, problems = [], []
    for s in _sources(value):
        verdict = allowlist.check(s["url"], issuer, name)
        if not verdict.official:
            problems.append(f"not official ({verdict.reason}): {s['url']}")
            refs.append({**s, "official": False})
            continue
        ev = evidence_cache.get(s["url"])
        if ev is None:
            try:
                ev = fetch(s["url"], refresh=refresh)
            except FetchError as e:
                ev = str(e)
            evidence_cache[s["url"]] = ev
        if isinstance(ev, str):
            problems.append(f"fetch failed: {ev}")
            refs.append({**s, "official": True})
            continue
        kind = match_kind(s["quote"], ev.text)
        ref = {**s, "official": True, "evidence_id": ev.id, "fetched_at": ev.fetched_at.isoformat(), "match": kind}
        refs.append(ref)
        if kind is None:
            problems.append(f"quote not found in {s['url']}: {s['quote'][:80]}")
    return refs, problems


def profile_card(extraction: CardProfile, origin: str = "seed", refresh: bool = False, conn: Connection | None = None) -> ProfileResult:
    evidence_cache: dict[str, Evidence | str] = {}
    results: list[FieldResult] = []

    def run(c: Connection) -> None:
        store.ensure_card(c, extraction.id, extraction.name, extraction.issuer, origin=origin)
        for name in FIELDS:
            value = _field_value(extraction, name)
            if value is None:
                results.append(FieldResult(name, "empty"))
                continue
            refs, problems = _verify(name, value, extraction.issuer, evidence_cache, refresh)
            problems += _range_problems(name, value, extraction)
            problems += _value_problems(name, value)
            if problems:
                origin_tag = "range_check_failed" if any("%" in p or "lakh" in p or "not stated" in p for p in problems) else (
                    "not_official" if any(p.startswith("not official") for p in problems) else "quote_check_failed")
                store.add_speculation(c, extraction.id, name, value, refs, origin_tag, "; ".join(problems)[:2000])
                results.append(FieldResult(name, "speculation", problems))
                continue
            cur = store.current(c, extraction.id, name)
            outcome = store.publish_fact(c, extraction.id, name, value, refs, _large_change(cur.value if cur else None, value))
            results.append(FieldResult(name, outcome))

    if conn is not None:
        run(conn)
    else:
        with engine().begin() as c:
            run(c)
    return ProfileResult(extraction.id, results)


def load_extraction(path) -> CardProfile:
    return CardProfile.model_validate(json.loads(open(path).read()))
