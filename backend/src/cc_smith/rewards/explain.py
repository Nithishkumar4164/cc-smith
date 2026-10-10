"""Templated "why this card" text for /pay (DR-8: no LLM on the pay path)."""


def _indian(n: int) -> str:
    s = str(abs(n))
    head, tail = s[:-3], s[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    return ("-" if n < 0 else "") + ",".join([g for g in [head, *groups] if g] + [tail])


def rupees(paise: int) -> str:
    """Indian digit grouping (₹4,00,000); paise only below ₹100 and only when non-zero."""
    if paise % 100 and abs(paise) < 10_000:
        whole, frac = divmod(abs(paise), 100)
        return f"{'-' if paise < 0 else ''}₹{_indian(whole)}.{frac:02d}"
    return f"₹{_indian(round(paise / 100))}" if paise >= 0 else f"-₹{_indian(round(-paise / 100))}"


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
        if c.startswith("insufficient_credit:"):
            return f"only {rupees(int(c.split(':')[1]))} of credit available"
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
        multiple = next((c for c in card.caps if c.id in rule.cap_ids and c.unit == "base_multiple"), None)
        if line.capped and multiple:
            times = {100: "the", 200: "twice the", 300: "three times the"}.get(multiple.amount, f"{multiple.amount / 100:g}x the")
            note += f" — capped at {times} base cashback earned this month; spend more on other things to unlock more"
        elif line.capped:
            note += " — cap reached"
        notes.append(note)
    for code in reward.reason_codes:
        if code.startswith("capped:"):
            continue
        why = _why([code])
        if why:
            notes.append(why[0].upper() + why[1:])
    return notes


def pay_text(merchant, best, eligible, amount_paise: int, held_any: bool = False, ranked=None, channel: str = "") -> str:
    if best is None:
        if not held_any:
            return "Add a card you hold to get a recommendation."
        codes = [c for o in (ranked or []) for c in o.reason_codes]
        if codes and all(any(c.startswith("insufficient_credit") for c in o.reason_codes) or "not_assessable" in o.reason_codes for o in ranked):
            return f"None of your cards has {rupees(amount_paise)} of credit available. Pay part now, or pay a bill first."
        if channel == "upi":
            return "None of your cards can be used on UPI (that needs a RuPay credit card). Pay another way."
        return "None of your cards can be used for this payment."
    if best.reward_paise == 0:
        why = _why(best.reason_codes)
        return f"No card earns on this {merchant.category} payment" + (f" ({why})." if why else ".") + " Pay with any card."
    text = f"Pay with {best.name}: earns {rupees(best.reward_paise)} on {rupees(amount_paise)} at {merchant.name}."
    top_now = max(eligible, key=lambda o: o.reward_paise)
    month = best.month_paise is not None
    if month and top_now.card_id != best.card_id:
        loss = top_now.reward_paise - best.reward_paise
        cost = top_now.later_paise is not None and best.later_paise - top_now.later_paise
        text += (f" That is {rupees(loss)} less than {top_now.name} now, but paying with {top_now.name} would use up its"
                 f" capped rewards and cost about {rupees(cost)} on your other spends later this month,"
                 f" so this pays about {rupees(best.month_paise - top_now.month_paise)} more over the month.")
    elif len(eligible) > 1:
        nxt = eligible[1]
        gap = best.reward_paise - nxt.reward_paise
        if gap == 0 and month and nxt.month_paise is not None and best.month_paise > nxt.month_paise:
            text += (f" {nxt.name} earns the same now, but would use up about {rupees(best.later_paise - nxt.later_paise)}"
                     f" of rewards your other spends earn with it later this month.")
        elif gap == 0 and nxt.notes:
            text += f" {nxt.name} earns the same now; its {nxt.notes[0]} covers more of your spending, so keep it free for later."
        elif gap == 0:
            text += f" {nxt.name} earns the same."
        elif gap < 0:
            text += f" {nxt.name} would earn {rupees(-gap)} more on this payment."
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
    up_to = next((ov for ov in offer_views if ov.tier == "fact" and ov.up_to_paise and best.card_id in ov.card_ids), None)
    # "Up to" offers never join a combined figure: their real value is unknown.
    tail = f" Bank offer on this card: up to {rupees(up_to.up_to_paise)} ({up_to.title}); check the offer terms." if up_to else ""
    if top is None:
        return tail
    total, card, ov = top
    if card.card_id == best.card_id:
        return f" Bank offer on this card too: {ov.title} (about {rupees(ov.est_saving_paise)})."
    return (f" But {card.name} has a bank offer here — {ov.title} — worth about {rupees(ov.est_saving_paise)}, "
            f"{rupees(total)} in all; check the offer terms before you pay.")
