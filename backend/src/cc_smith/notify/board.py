"""Notice board: the few things a user must know about their cards right now, each with
the reason, the rupees at stake, what to do, and the sources behind it."""

from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import Connection

from cc_smith.knowledge import offers as offers_mod
from cc_smith.knowledge import store
from cc_smith.knowledge.schema import PERIOD_MONTHS, CardProfile
from cc_smith.ledger import credit as credit_mod
from cc_smith.ledger import service as ledger
from cc_smith.merchants import by_key, categories
from cc_smith.rewards.explain import rupees
from cc_smith.rewards.finder import GST_BP, refine

SEVERITY = {"act": 0, "watch": 1, "info": 2}
PERIOD_WORD = {"statement_cycle": "statement cycle", "calendar_month": "month", "calendar_quarter": "quarter",
               "statement_quarter": "statement quarter", "anniversary_year": "card year", "calendar_year": "year", "half_year": "six months"}
FIELD_WORD = {"fees": "fees", "earn_rules": "how you earn", "caps": "caps", "exclusions": "exclusions",
              "currency": "reward value", "milestones": "milestones", "identity": "network", "min_txn": "minimum amount"}


def today_ist() -> date:
    return datetime.now(ZoneInfo("Asia/Kolkata")).date()


@dataclass
class Notice:
    id: str
    kind: str
    severity: str  # act | watch | info
    title: str
    reason: str
    action: str
    card_id: str | None = None
    rupees_paise: int | None = None
    due: str | None = None
    tier: str = "fact"  # fact | speculation
    refs: list[dict] = field(default_factory=list)


def _refs(meta: dict, name: str) -> list[dict]:
    return [{k: r.get(k) for k in ("url", "quote", "official")} for r in (meta.get(name) or {}).get("refs", [])][:2]


def _fee_with_gst(p: CardProfile) -> int:
    return p.fees.annual_paise * (10_000 + GST_BP) // 10_000 if p.fees else 0


def held_fees(holds: list[dict], cat: dict, today: date) -> dict[str, int]:
    """Annual fee to use for each held card: 0 when LTF or inside its free first year."""
    out = {}
    for h in holds:
        if h["card_id"] not in cat:
            continue
        if h.get("fee_status") == "ltf" or (h.get("fee_status") == "fyf" and h.get("fyf_until") and date.fromisoformat(h["fyf_until"]) >= today):
            out[h["card_id"]] = 0
    return out


def build(conn: Connection, uid: str, cat: dict, holds: list[dict], profile: dict, spend_items: dict[str, int], lines, today: date | None = None) -> list[dict]:
    today = today or datetime.now(ZoneInfo("Asia/Kolkata")).date()
    notes: list[Notice] = []
    held = [cat[h["card_id"]][0] for h in holds if h["card_id"] in cat and cat[h["card_id"]][0].assessable()]
    held_ids = {h["card_id"] for h in holds}
    fees = held_fees(holds, cat, today)
    sim = refine(held, lines, fees=fees)[0] if held and lines else None

    # Fees and waivers
    for h in holds:
        if h["card_id"] not in cat:
            continue
        p, meta, _ = cat[h["card_id"]]
        if not p.fees or p.fees.annual_paise == 0:
            continue
        due = None
        if h.get("renewal_month"):
            y = today.year + (1 if h["renewal_month"] < today.month else 0)
            due = date(y, h["renewal_month"], 1).isoformat()
        fee = _fee_with_gst(p)
        if h.get("fee_status") == "ltf":
            continue
        if h.get("fee_status") == "fyf" and h.get("fyf_until"):
            end = date.fromisoformat(h["fyf_until"])
            if today <= end <= today + timedelta(days=60):
                notes.append(Notice(f"fyf:{p.id}", "fee", "watch", f"Free year on {p.name} ends {end:%d %b %Y}",
                                    f"After that the renewal fee is {rupees(fee)} a year including GST.",
                                    "Check whether your spend will reach the waiver, or ask the bank for another fee waiver before it renews.",
                                    p.id, fee, end.isoformat(), refs=_refs(meta, "fees")))
            if end >= today:
                continue
        r = sim.cards.get(p.id) if sim else None
        spend = r.spend_paise if r else 0
        net = r.net_paise if r else None
        waiver = p.fees.waiver_spend_paise
        if waiver and spend >= waiver:
            notes.append(Notice(f"fee:{p.id}", "fee", "info", f"{p.name}: renewal fee waived on your spend",
                                f"Your spends route about {rupees(spend)} a year to this card, above the {rupees(waiver)} waiver.",
                                "Keep using it for the categories shown in Finder.", p.id, fee, due, refs=_refs(meta, "fees")))
        elif waiver:
            gap = waiver - spend
            worth = gap <= waiver // 3
            notes.append(Notice(f"fee:{p.id}", "fee", "watch" if worth else "info",
                                f"{rupees(gap)} more a year on {p.name} waives its {rupees(fee)} fee",
                                f"The waiver needs {rupees(waiver)} a year; your spends put about {rupees(spend)} on this card.",
                                "Move some everyday spend to this card before the renewal date." if worth else
                                "The gap is large; compare the fee with what the card earns you in Finder.",
                                p.id, fee, due, refs=_refs(meta, "fees")))
        if net is not None and net < 0:
            notes.append(Notice(f"close:{p.id}", "fee", "act", f"{p.name} costs you {rupees(-net)} a year",
                                f"On your spends it earns less than its {rupees(fee)} fee.",
                                "Ask the bank to waive the fee or move you to a lifetime-free variant; close it only after redeeming rewards.",
                                p.id, -net, due, refs=_refs(meta, "fees")))

    # Caps: this period (logged payments) and structurally (every month on your spends)
    for h in holds:
        if h["card_id"] not in cat:
            continue
        p, meta, _ = cat[h["card_id"]]
        used = ledger.cap_used(conn, uid, p, h.get("statement_day"), today)
        for cap in p.caps:
            if cap.amount and used.get(cap.id, 0) * 100 >= cap.amount * 70:
                pct = used[cap.id] * 100 // cap.amount
                amount = rupees(cap.amount) if cap.unit != "points" else f"{cap.amount:,} points"
                notes.append(Notice(f"cap:{p.id}:{cap.id}", "cap", "act" if pct >= 100 else "watch",
                                    f"{p.name}: {min(pct, 100)}% of the {amount} cap used this {PERIOD_WORD[cap.period]}",
                                    "Payments you logged have used most of this cap; beyond it the card earns less or nothing on those spends.",
                                    "Check Pay before your next payment in this category; it counts what is left of the cap and picks your next-best card.", p.id, refs=_refs(meta, "caps")))
    if sim:
        for r in sim.cards.values():
            p, meta, _ = cat[r.card_id]
            capped = [cl for cl in r.lines.values() if cl.capped]
            if capped:
                keys = ", ".join(categories().get(cl.spend_key) or (by_key(cl.spend_key) or {}).get("name", cl.spend_key) for cl in capped)
                notes.append(Notice(f"capfill:{p.id}", "cap", "info", f"{p.name}'s cap fills every month on your spends",
                                    f"{keys}: part of this spend earns at a lower rate once the cap is used.",
                                    "Card Finder shows whether another card would pay more on the overflow.", p.id, refs=_refs(meta, "caps")))

    # Milestones within reach
    if sim:
        for r in sim.cards.values():
            p, meta, _ = cat[r.card_id]
            for m in p.milestones:
                per_year = 12 // PERIOD_MONTHS[m.period]
                per_period = r.spend_paise // per_year
                gap = m.spend_paise - per_period
                if 0 < gap <= m.spend_paise * 30 // 100:
                    notes.append(Notice(f"ms:{p.id}:{m.spend_paise}", "milestone", "watch",
                                        f"{rupees(gap)} more per {PERIOD_WORD[m.period]} on {p.name} earns {m.description}",
                                        f"Your spends put about {rupees(per_period)} per {PERIOD_WORD[m.period]} on this card; the milestone needs {rupees(m.spend_paise)}.",
                                        "Route a little more spend to this card to reach it.", p.id, m.value_paise * per_year, refs=_refs(meta, "milestones")))

    # Credit limit and utilisation
    for cid, c in credit_mod.credit(conn, uid).items():
        if cid not in cat or c.utilisation_bp is None:
            continue
        name = cat[cid][0].name
        scope = f"the {c.pool_name} limit" if c.pool_name else "its limit"
        if c.utilisation_bp >= 3_000:
            notes.append(Notice(f"util:{c.pool_id or cid}", "credit", "act" if c.utilisation_bp >= 7_000 else "watch",
                                f"{name}: {c.utilisation_bp // 100}% of {scope} in use",
                                f"{rupees(c.available_paise or 0)} available. Bureaus treat using more than about 30% of a limit as a risk signal when the statement is reported.",
                                "Pay part of the balance before the statement date, or spread spends across cards.", cid))

    # LTF / FYF / fee-waiver offers on cards that would pay off for you
    fee_offers = offers_mod.fee_offers(conn, today)
    if lines:
        base_net = sim.net_paise if sim else 0
        for cid, offs in fee_offers.items():
            if cid in held_ids or cid not in cat or not cat[cid][0].assessable():
                continue
            p, meta, status = cat[cid]
            if status != "active":
                continue
            with_card = refine(held + [p], lines, held_ids, fees)[0].net_paise - base_net
            for o in offs:
                # with_card already pays the yearly fee; each of these offers makes year one fee-free,
                # and an LTF keeps every later year fee-free too.
                annual = _fee_with_gst(p)
                year_one = with_card + annual
                gain = with_card + (annual if o.kind in ("ltf", "annual_waiver") else 0)
                if year_one <= 0:
                    continue
                # The offer's own title carries its conditions (e.g. "for select corporates").
                notes.append(Notice(f"feeoffer:{o.id}", "fee_offer", "watch" if o.tier == "fact" else "info",
                                    f"{p.name}: {o.title}",
                                    f"{o.title}. On your spends it adds about {rupees(year_one)} in the first year"
                                    + (f" and {rupees(gain)} a year after" if o.kind in ("ltf", "annual_waiver") else "") + ".",
                                    "Apply through the source below if the card suits you; cc-smith takes no referral money.",
                                    cid, year_one, o.valid_to, o.tier, [{"url": r["url"], "quote": r["quote"], "official": r.get("official")} for r in o.refs]))

    # Bank offers at merchants you spend at, ending within 10 days
    spend_merchants = {k for k in spend_items if by_key(k)}
    for o in offers_mod.live_merchant_offers(conn, today):
        if o.merchant_key not in spend_merchants or not o.valid_to:
            continue
        end = date.fromisoformat(o.valid_to)
        if end > today + timedelta(days=10):
            continue
        mine = [h["card_id"] for h in holds if h["card_id"] in cat and offers_mod.allowlist.issuer_key(cat[h["card_id"]][0].issuer) == offers_mod.allowlist.issuer_key(o.issuer)
                and ("*" in o.card_ids or h["card_id"] in o.card_ids)]
        if not mine:
            continue
        notes.append(Notice(f"offer:{o.id}", "offer", "info", f"{o.merchant_name or o.merchant_key} offer ends {end:%d %b}",
                            f"{o.title}, with your {cat[mine[0]][0].name}.", "Use Pay at checkout to compare it with your best card.",
                            mine[0], o.max_paise, o.valid_to, o.tier, [{"url": r["url"], "quote": r["quote"]} for r in o.refs]))

    # Changes to your cards: published facts and unconfirmed reports
    since = datetime.now(UTC) - timedelta(days=45)
    for cid in held_ids:
        if cid not in cat:
            continue
        p = cat[cid][0]
        for e in store.events(conn, cid, 50):
            at = e.created_at if e.created_at.tzinfo else e.created_at.replace(tzinfo=UTC)
            if e.event_type == "published" and e.old is not None and at >= since:
                notes.append(Notice(f"change:{e.id}", "card_change", "act" if e.large_change else "watch",
                                    f"{p.name}: {FIELD_WORD.get(e.field, e.field)} changed on {at:%d %b %Y}",
                                    "The bank published new terms; cc-smith's numbers already use them.",
                                    "Check Finder: if this card earns less now, it may suggest a better one.",
                                    cid, refs=[{k: r.get(k) for k in ("url", "quote", "official")} for r in (e.refs or [])][:2]))
        for s in store.open_speculation(conn, cid):
            notes.append(Notice(f"spec:{s.id}", "card_change", "info", f"{p.name}: change reported, not confirmed by the bank",
                                (s.reason or "")[:240], "Nothing changes in your numbers until the bank's own page confirms it.",
                                cid, tier="speculation", refs=[{k: r.get(k) for k in ("url", "quote")} for r in (s.refs or [])][:2]))

    # Your own cards' issues come before offers on cards you don't hold.
    notes.sort(key=lambda n: (SEVERITY[n.severity], n.kind in ("fee_offer", "offer"), -(n.rupees_paise or 0)))
    return [asdict(n) for n in notes]


