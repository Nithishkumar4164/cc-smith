"""Opportunity cost at checkout. Paying with a card uses part of its caps and credit,
which the rest of the month's spends might have earned more with. Each option is
valued as: earned on this payment + what the rest of the month still earns afterwards
(the user's monthly spends prorated to the days left, routed to the best card chunk by
chunk under the caps and credit that remain)."""

from dataclasses import dataclass

from cc_smith.knowledge.schema import CardProfile
from cc_smith.rewards.engine import Purchase, narrowness, reward
from cc_smith.rewards.finder import CHUNKS_PER_LINE, SpendLine


@dataclass
class Outlook:
    later_paise: int  # rest-of-month rewards if this card is used now
    cap_after: dict[str, dict[str, int]]


def rest_of_month(
    cards: list[CardProfile], lines: list[SpendLine], cap_used: dict[str, dict[str, int]],
    available: dict[str, int | None], days_left: int, days_in_month: int = 30,
) -> int:
    used = {cid: dict(v) for cid, v in cap_used.items()}
    avail = dict(available)
    total = 0
    for line in lines:
        amount = line.monthly_paise * days_left // days_in_month
        chunk = amount // CHUNKS_PER_LINE
        for i in range(CHUNKS_PER_LINE):
            part = amount - chunk * (CHUNKS_PER_LINE - 1) if i == CHUNKS_PER_LINE - 1 else chunk
            if part <= 0:
                continue
            p = Purchase(part, line.category, line.merchant, line.channel, line.flags)
            best = None
            for c in cards:
                a = avail.get(c.id)
                if a is not None and a < part:
                    continue
                r = reward(c, p, used.get(c.id, {}))
                if r.eligible and (best is None or (r.value_paise, narrowness(c, r)) > (best[1].value_paise, narrowness(*best))):
                    best = (c, r)
            if best is None:
                continue
            c, r = best
            total += r.value_paise
            for cid, d in r.cap_use.items():
                used.setdefault(c.id, {})[cid] = used.get(c.id, {}).get(cid, 0) + d
            if avail.get(c.id) is not None:
                avail[c.id] -= part
    return total


def outlooks(
    cards: list[CardProfile], options: dict[str, tuple[int, dict[str, int]]], lines: list[SpendLine],
    cap_used: dict[str, dict[str, int]], available: dict[str, int | None], amount_paise: int, days_left: int,
) -> dict[str, int]:
    """options: card_id -> (reward now, cap use of this payment). Returns card_id -> later rewards."""
    out = {}
    for cid, (_, use) in options.items():
        used = {k: dict(v) for k, v in cap_used.items()}
        for cap, d in use.items():
            used.setdefault(cid, {})[cap] = used.get(cid, {}).get(cap, 0) + d
        avail = dict(available)
        if avail.get(cid) is not None:
            avail[cid] -= amount_paise
        out[cid] = rest_of_month(cards, lines, used, avail, days_left)
    return out
