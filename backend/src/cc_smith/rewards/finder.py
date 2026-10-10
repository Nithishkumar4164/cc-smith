"""Card Finder: simulate a year of monthly spends over a set of cards, routing each
chunk of spend to the card that earns most for it at that moment (caps included)."""

from dataclasses import dataclass, field
from itertools import combinations

from cc_smith.knowledge.schema import PERIOD_MONTHS, CardProfile
from cc_smith.rewards.engine import Purchase, narrowness, reward

GST_BP = 1_800
CHUNKS_PER_LINE = 5


@dataclass(frozen=True)
class SpendLine:
    key: str
    category: str
    merchant: str | None
    channel: str
    monthly_paise: int
    flags: frozenset[str] = frozenset()


@dataclass
class CardLine:
    spend_key: str
    spend_paise: int = 0
    reward_paise: int = 0
    capped: bool = False


@dataclass
class CardResult:
    card_id: str
    spend_paise: int = 0
    reward_paise: int = 0
    milestone_paise: int = 0
    fee_paise: int = 0
    fee_waived: bool = False
    milestones_hit: list[str] = field(default_factory=list)
    lines: dict[str, CardLine] = field(default_factory=dict)

    @property
    def net_paise(self) -> int:
        return self.reward_paise + self.milestone_paise - self.fee_paise


@dataclass
class Simulation:
    cards: dict[str, CardResult]
    unearned: dict[str, int]

    @property
    def net_paise(self) -> int:
        return sum(c.net_paise for c in self.cards.values())


def _reset_due(period: str, month: int) -> bool:
    return month % PERIOD_MONTHS[period] == 0


def simulate(
    cards: list[CardProfile], spends: list[SpendLine], months: int | None = None, pins: dict[str, str] | None = None,
    exclude: frozenset[str] = frozenset(), fees: dict[str, int] | None = None,
) -> Simulation:
    """`pins` routes a whole spend line to one card; unpinned lines go chunk by chunk to the
    best card not in `exclude`."""
    if months is None:
        yearly = any(PERIOD_MONTHS[cap.period] == 12 for c in cards for cap in c.caps)
        months = 12 if yearly else 3
    results = {c.id: CardResult(c.id) for c in cards}
    caps: dict[str, dict[str, int]] = {c.id: {} for c in cards}
    unearned: dict[str, int] = {}
    for month in range(months):
        for c in cards:
            for cap in c.caps:
                if _reset_due(cap.period, month):
                    caps[c.id].pop(cap.id, None)
                    if cap.unit == "base_multiple" and cap.of_rule:
                        caps[c.id].pop(f"earned:{cap.of_rule}", None)
        for line in spends:
            chunk = line.monthly_paise // CHUNKS_PER_LINE
            last = line.monthly_paise - chunk * (CHUNKS_PER_LINE - 1)
            for i in range(CHUNKS_PER_LINE):
                amount = last if i == CHUNKS_PER_LINE - 1 else chunk
                if amount <= 0:
                    continue
                p = Purchase(amount, line.category, line.merchant, line.channel, line.flags)
                best = None
                pinned = (pins or {}).get(line.key)
                for c in cards:
                    if (pinned and c.id != pinned) or (not pinned and c.id in exclude):
                        continue
                    r = reward(c, p, caps[c.id])
                    if r.eligible and (best is None or (r.value_paise, narrowness(c, r)) > (best[1].value_paise, narrowness(*best))):
                        best = (c, r)
                if best is None:
                    unearned[line.key] = unearned.get(line.key, 0) + amount
                    continue
                c, r = best
                for cid, delta in r.cap_use.items():
                    caps[c.id][cid] = caps[c.id].get(cid, 0) + delta
                res = results[c.id]
                cl = res.lines.setdefault(line.key, CardLine(line.key))
                cl.spend_paise += amount
                cl.reward_paise += r.value_paise
                cl.capped = cl.capped or any(x.capped for x in r.lines)
                res.spend_paise += amount
                res.reward_paise += r.value_paise
                if r.value_paise == 0:
                    unearned[line.key] = unearned.get(line.key, 0) + amount
    scale = 12 // months
    for res in results.values():
        res.spend_paise *= scale
        res.reward_paise *= scale
        for cl in res.lines.values():
            cl.spend_paise *= scale
            cl.reward_paise *= scale
    unearned = {k: v * scale for k, v in unearned.items()}
    for c in cards:
        res = results[c.id]
        if fees is not None and c.id in fees:
            # The user's own card is LTF, or still inside its free first year.
            res.fee_paise, res.fee_waived = fees[c.id], fees[c.id] == 0
        elif c.fees:
            waived = c.fees.waiver_spend_paise is not None and res.spend_paise >= c.fees.waiver_spend_paise
            res.fee_waived = waived
            res.fee_paise = 0 if waived else c.fees.annual_paise * (10_000 + GST_BP) // 10_000
        yearly_spend = res.spend_paise
        for m in c.milestones:
            per_year = 12 // PERIOD_MONTHS[m.period]
            per_period = yearly_spend // per_year
            if per_period >= m.spend_paise:
                res.milestone_paise += m.value_paise * per_year
                res.milestones_hit.append(m.description)
    return Simulation(results, unearned)


def _dominant(sim: Simulation) -> dict[str, str]:
    by_line: dict[str, tuple[int, str]] = {}
    for r in sim.cards.values():
        for key, cl in r.lines.items():
            if cl.spend_paise > by_line.get(key, (0, ""))[0]:
                by_line[key] = (cl.spend_paise, r.card_id)
    return {k: v[1] for k, v in by_line.items()}


def refine(
    cards: list[CardProfile], spends: list[SpendLine], base_ids: set[str] | None = None, fees: dict[str, int] | None = None,
) -> tuple[Simulation, dict[str, str]]:
    """Greedy routing ignores fee waivers and milestones, which depend on a card's total
    spend. Hill-climb over whole-line moves (pin a line to a card, or unpin it). When
    `base_ids` is given, a second start routes exactly as those cards alone would, so the
    result is never worse than the base plus the new cards' fees."""
    ids = {c.id for c in cards}
    starts = [frozenset()]
    if base_ids is not None and ids - base_ids:
        starts.append(frozenset(ids - base_ids))
    best_sim, best_pins = None, {}
    for exclude in starts:
        pins: dict[str, str] = {}
        sim = simulate(cards, spends, pins=pins, exclude=exclude, fees=fees)
        improved = True
        while improved:
            improved = False
            for line in spends:
                for target in [None, *(c.id for c in cards)]:
                    if pins.get(line.key) == target:
                        continue
                    trial = {k: v for k, v in pins.items() if k != line.key}
                    if target:
                        trial[line.key] = target
                    t = simulate(cards, spends, pins=trial, exclude=exclude, fees=fees)
                    if t.net_paise > sim.net_paise:
                        sim, pins, improved = t, trial, True
        if best_sim is None or sim.net_paise > best_sim.net_paise:
            best_sim, best_pins = sim, pins
    return best_sim, best_pins


@dataclass
class Portfolio:
    new_cards: list[str]
    gain_paise: int
    simulation: Simulation


def find_portfolios(
    held: list[CardProfile],
    candidates: list[CardProfile],
    spends: list[SpendLine],
    max_new: int = 3,
    top: int = 3,
    prune_k: int = 4,
    max_pool: int = 10,
    refine_top: int = 5,
    fees: dict[str, int] | None = None,
) -> tuple[Simulation, list[Portfolio]]:
    """Best sets of up to `max_new` new cards, by net annual gain over the held stack."""
    held_ids = {c.id for c in held}
    pool = [c for c in candidates if c.id not in held_ids and c.assessable()]
    base, _ = refine(held, spends, fees=fees) if held else (simulate(held, spends), {})

    # Prune: keep cards that are in the top-k for some spend line on their own.
    keep: set[str] = set()
    for line in spends:
        solo = sorted(pool, key=lambda c: -simulate([c], [line]).cards[c.id].reward_paise)
        keep.update(c.id for c in solo[:prune_k])
    pool = [c for c in pool if c.id in keep]
    pool.sort(key=lambda c: -simulate([c], spends).net_paise)
    pool = pool[:max_pool]

    results: list[Portfolio] = []
    for n in range(1, max_new + 1):
        for combo in combinations(pool, n):
            sim = simulate(held + list(combo), spends, fees=fees)
            # Keep non-positive greedy gains too: greedy routing can break a held card's
            # milestone or waiver, which refine() below repairs.
            results.append(Portfolio([c.id for c in combo], sim.net_paise - base.net_paise, sim))
    results.sort(key=lambda p: (-p.gain_paise, len(p.new_cards)))
    # A bigger set only counts if it beats every subset of it by ₹500 a year.
    distinct = [
        p for p in results
        if not any(set(q.new_cards) < set(p.new_cards) and p.gain_paise - q.gain_paise < 50_000 for q in results)
    ]
    # Re-score the strongest with fee- and milestone-aware routing; the held stack's own
    # routing is one start, so a portfolio never scores below the base.
    refined = []
    for p in distinct[:refine_top]:
        sim, _ = refine(held + [c for c in pool if c.id in p.new_cards], spends, held_ids, fees)
        refined.append(Portfolio(p.new_cards, sim.net_paise - base.net_paise, sim))
    refined.sort(key=lambda p: (-p.gain_paise, len(p.new_cards)))
    chosen = [p for p in refined if p.gain_paise > 0][:top]
    return base, chosen


def keep_or_close(held: list[CardProfile], spends: list[SpendLine], fees: dict[str, int] | None = None) -> dict[str, int]:
    """Per held card: net annual loss if it were closed (negative = closing saves money)."""
    full, _ = refine(held, spends, fees=fees)
    return {c.id: full.net_paise - refine([h for h in held if h.id != c.id], spends, fees=fees)[0].net_paise for c in held}
