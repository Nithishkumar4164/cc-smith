"""Rewards engine: pure functions over a CardProfile. No I/O, no LLM.

Units: a pct rule earns "face paise" (₹1 face = one currency unit for cashback and for
points worth ₹1 face, e.g. Amazon Pay balance); a per_spend rule earns points.
Value in paise = face_paise * currency.value_paise / 100, or points * currency.value_paise.
"""

from dataclasses import dataclass, field

from cc_smith.knowledge.schema import CardProfile, EarnRule, Match


@dataclass(frozen=True)
class Purchase:
    amount_paise: int
    category: str
    merchant: str | None = None
    channel: str = "offline"
    flags: frozenset[str] = frozenset()


@dataclass
class RuleLine:
    rule_id: str
    units: int
    value_paise: int
    spend_paise: int
    capped: bool = False


@dataclass
class Reward:
    card_id: str
    value_paise: int = 0
    lines: list[RuleLine] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    cap_use: dict[str, int] = field(default_factory=dict)

    @property
    def eligible(self) -> bool:
        return not any(r in self.reason_codes for r in ("not_assessable", "no_upi"))


def _matches(m: Match, p: Purchase) -> bool:
    if m.merchants and p.merchant not in m.merchants:
        return False
    if m.categories and p.category not in m.categories and (p.merchant or "") not in m.categories:
        return False
    return not (m.channels and p.channel not in m.channels)


def _excluded(card: CardProfile, p: Purchase, rule_id: str | None) -> str | None:
    for x in card.exclusions:
        if x.rule_ids and rule_id not in x.rule_ids:
            continue
        if not x.rule_ids and rule_id is not None:
            continue
        if p.merchant and p.merchant in x.except_merchants:
            continue
        hit = (
            (x.categories and p.category in x.categories)
            or (x.merchants and p.merchant in x.merchants)
            or (x.channels and p.channel in x.channels)
        )
        if hit:
            return p.category if x.categories and p.category in x.categories else (p.merchant or p.channel)
    return None


# Profiles are immutable once loaded, so per-object lookups can be memoised by id().
_CAPS: dict[int, tuple[CardProfile, dict]] = {}
_CANDIDATES: dict[tuple, tuple[list[EarnRule], list[EarnRule]]] = {}


def _caps(card: CardProfile) -> dict:
    hit = _CAPS.get(id(card))
    if hit is None or hit[0] is not card:
        hit = (card, {c.id: c for c in card.caps})
        _CAPS[id(card)] = hit
    return hit[1]


def earned_key(rule_id: str) -> str:
    """Counter, kept alongside cap usage, of what a base rule earned in the period."""
    return f"earned:{rule_id}"


def _limit(cap, used: dict[str, int]) -> int:
    if cap.unit == "base_multiple":
        return cap.amount * used.get(earned_key(cap.of_rule), 0) // 100
    return cap.amount


def _base_rules(card: CardProfile) -> set[str]:
    return {c.of_rule for c in _caps(card).values() if c.unit == "base_multiple" and c.of_rule}


def _cap_left(card: CardProfile, rule: EarnRule, unit: str, used: dict[str, int]) -> int | None:
    caps = _caps(card)
    # A base-multiple cap limits earned units like a paise cap does.
    units = {unit, "base_multiple"} if unit == "paise" else {unit}
    lefts = [
        _limit(caps[cid], used) - used.get(cid, 0)
        for cid in rule.cap_ids
        if caps[cid].unit in units
    ]
    return max(0, min(lefts)) if lefts else None


def _earn_units(rule: EarnRule, spend: int) -> int:
    if rule.rate.kind == "pct":
        return spend * (rule.rate.bp or 0) // 10_000
    return (spend // (rule.rate.per_paise or 1)) * (rule.rate.points or 0)


def _value(card: CardProfile, rule: EarnRule, units: int) -> int:
    assert card.currency
    if rule.rate.kind == "pct":
        return units * card.currency.value_paise // 100
    return units * card.currency.value_paise


def _unit_cap_kind(rule: EarnRule) -> str:
    return "paise" if rule.rate.kind == "pct" else "points"


def _apply_rule(card: CardProfile, rule: EarnRule, spend: int, used: dict[str, int], out: Reward) -> int:
    """Earns on up to `spend`; returns the spend left over by a spend cap."""
    eligible = spend
    spend_left = _cap_left(card, rule, "spend_paise", used)
    if spend_left is not None:
        eligible = min(spend, spend_left)
    units = _earn_units(rule, eligible)
    capped = eligible < spend
    unit_left = _cap_left(card, rule, _unit_cap_kind(rule), used)
    if unit_left is not None and units > unit_left:
        units, capped = unit_left, True
    caps = _caps(card)
    for cid in rule.cap_ids:
        cap = caps[cid]
        delta = eligible if cap.unit == "spend_paise" else units
        used[cid] = used.get(cid, 0) + delta
        out.cap_use[cid] = out.cap_use.get(cid, 0) + delta
    if rule.id in _base_rules(card):
        k = earned_key(rule.id)
        used[k] = used.get(k, 0) + units
        out.cap_use[k] = out.cap_use.get(k, 0) + units
    out.lines.append(RuleLine(rule.id, units, _value(card, rule, units), eligible, capped))
    if capped:
        out.reason_codes.append(f"capped:{rule.id}")
    spills = all(caps[cid].spill for cid in rule.cap_ids if caps[cid].unit == "spend_paise")
    return spend - eligible if spills else 0


def _ordered_rules(card: CardProfile, p: Purchase) -> tuple[list[EarnRule], list[EarnRule]]:
    key = (id(card), p.category, p.merchant, p.channel, p.flags)
    hit = _CANDIDATES.get(key)
    if hit is not None and _CAPS.get(id(card), (None,))[0] is card:
        return hit
    _caps(card)
    matching = [
        r for r in card.earn_rules
        if _matches(r.match, p) and _excluded(card, p, r.id) is None and set(r.requires) <= p.flags
    ]
    base = sorted(
        (r for r in matching if not r.stacks),
        key=lambda r: (-r.match.specificity(), -r.priority, -_value(card, r, _earn_units(r, 1_000_000))),
    )
    hit = (base, [r for r in matching if r.stacks])
    _CANDIDATES[key] = hit
    return hit


def narrowness(card: CardProfile, r: "Reward") -> int:
    """How specific the rules that paid are: 2 for named merchants, 1 for a category, 0 for
    a catch-all or channel rule. On equal rewards, spend the narrower rule and keep the
    broader one free for spends only it covers."""
    rules = {x.id: x for x in card.earn_rules}
    return max((rules[line.rule_id].match.specificity() for line in r.lines if line.rule_id in rules), default=0)


def reward(card: CardProfile, p: Purchase, cap_used: dict[str, int] | None = None) -> Reward:
    """Reward for one purchase given cap usage so far in the current periods.

    `cap_used` is not mutated; the consumption is returned in Reward.cap_use.
    """
    out = Reward(card.id)
    if not card.assessable():
        out.reason_codes.append("not_assessable")
        return out
    if p.channel == "upi" and not (card.identity and card.identity.upi_rupay):
        out.reason_codes.append("no_upi")
        return out
    if (why := _excluded(card, p, None)) is not None:
        out.reason_codes.append(f"excluded:{why}")
        return out
    if card.min_txn_paise and p.amount_paise < card.min_txn_paise:
        out.reason_codes.append("below_min_txn")
        return out

    used = dict(cap_used or {})
    base_all, stacked_all = _ordered_rules(card, p)
    base = [r for r in base_all if not (r.min_txn_paise and p.amount_paise < r.min_txn_paise)]
    stacked = [r for r in stacked_all if not (r.min_txn_paise and p.amount_paise < r.min_txn_paise)]
    remaining = p.amount_paise
    for rule in base:
        remaining = _apply_rule(card, rule, remaining, used, out)
        if remaining == 0:
            break
    for rule in stacked:
        _apply_rule(card, rule, p.amount_paise, used, out)

    if not out.lines:
        out.reason_codes.append("no_matching_rule")
    out.value_paise = sum(line.value_paise for line in out.lines)
    if out.lines and out.value_paise == 0 and p.amount_paise > 0:
        out.reason_codes.append("rounds_to_zero" if not any(l.capped for l in out.lines) else "cap_exhausted")
    return out
