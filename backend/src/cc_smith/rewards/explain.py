"""Templated "why this card" text for /pay (DR-8: no LLM on the pay path)."""


def rupees(paise: int) -> str:
    r = paise / 100
    return f"₹{r:,.0f}" if r >= 100 or r == int(r) else f"₹{r:,.2f}"


REASONS = {
    "below_min_txn": "below the card's minimum amount",
    "no_upi": "not usable on UPI",
    "not_assessable": "rules not confirmed yet",
    "no_matching_rule": "no reward rule applies",
    "rounds_to_zero": "rounds down to zero",
    "cap_exhausted": "monthly cap already used up",
}


def _why(codes: list[str]) -> str:
    for c in codes:
        if c.startswith("excluded:"):
            return f"{c.split(':', 1)[1]} is excluded"
        if c.startswith("capped:"):
            return "partly over the cap"
        if c in REASONS:
            return REASONS[c]
    return ""


def _rate(card, rule) -> str:
    r = rule.rate
    if r.kind == "pct":
        return f"{r.bp / 100:g}%"
    unit = card.currency.name if card.currency else "points"
    return f"{r.points} {unit} per {rupees(r.per_paise)}"


def _scope(rule) -> str:
    m = rule.match
    parts = []
    if m.merchants:
        parts.append(", ".join(x.replace("_", " ").title() for x in m.merchants[:4]) + (" and more" if len(m.merchants) > 4 else ""))
    if m.categories:
        parts.append(", ".join(m.categories))
    if m.channels:
        parts.append("/".join(m.channels) + " payments")
    return " · ".join(parts) or "everything else"


def option_notes(card, reward) -> list[str]:
    rules = {r.id: r for r in card.earn_rules}
    notes = []
    for line in reward.lines:
        rule = rules.get(line.rule_id)
        if rule is None:
            continue
        note = f"{_rate(card, rule)} on {_scope(rule)}" + (" (bonus)" if rule.stacks else "")
        if line.capped:
            note += " — cap reached"
        notes.append(note)
    for code in reward.reason_codes:
        if code.startswith("capped:"):
            continue
        why = _why([code])
        if why:
            notes.append(why[0].upper() + why[1:])
    return notes


def pay_text(merchant, best, eligible, amount_paise: int, held_any: bool = False) -> str:
    if best is None:
        if held_any and merchant is not None:
            return "None of your cards can be used here (UPI needs a RuPay credit card). Pay another way."
        return "Add a card you hold to get a recommendation."
    if best.reward_paise == 0:
        why = _why(best.reason_codes)
        return f"No card earns on this {merchant.category} payment" + (f" ({why})." if why else ".") + " Pay with any card."
    text = f"Pay with {best.name}: earns {rupees(best.reward_paise)} on {rupees(amount_paise)} at {merchant.name}."
    if len(eligible) > 1:
        nxt = eligible[1]
        gap = best.reward_paise - nxt.reward_paise
        if gap == 0:
            text += f" {nxt.name} earns the same; this one keeps its capped rewards free for later."
        else:
            text += f" That is {rupees(gap)} more than {nxt.name}" + (f" ({_why(nxt.reason_codes)})." if _why(nxt.reason_codes) else ".")
    if merchant.confidence == "low":
        text += " Merchant category is a guess; correct it if wrong."
    return text


def offer_hint(best, eligible, offer_views) -> str:
    """Offers stay out of the ranking (their terms are free text), but say when a fact-tier
    offer on another held card would beat the pick on this payment."""
    if best is None:
        return ""
    by_card = {o.card_id: o for o in eligible}
    top = None
    for ov in offer_views:
        if ov.tier != "fact" or not ov.est_saving_paise:
            continue
        for cid in ov.card_ids:
            if cid in by_card:
                total = by_card[cid].reward_paise + ov.est_saving_paise
                if total > best.reward_paise and (top is None or total > top[0]):
                    top = (total, by_card[cid], ov)
    if top is None:
        return ""
    total, card, ov = top
    if card.card_id == best.card_id:
        return f" Bank offer on this card too: {ov.title} (about {rupees(ov.est_saving_paise)})."
    return (f" But {card.name} has a bank offer here — {ov.title} — worth about {rupees(ov.est_saving_paise)}, "
            f"{rupees(total)} in all; check the offer terms before you pay.")
