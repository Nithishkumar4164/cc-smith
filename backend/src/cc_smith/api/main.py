"""FastAPI BFF. All money is integer paise. The hackathon identifies a user by the
X-User-Id header returned from POST /users (JWT auth comes in M1)."""

from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import func, select

import cc_smith.notify.alerts  # noqa: F401  registers outbox consumers
from cc_smith import merchants
from cc_smith.db import card as card_t
from cc_smith.db import credit_ledger, engine, knowledge_event, launch_candidate, owner_alert
from cc_smith.knowledge import offers, store
from cc_smith.knowledge.schema import CardProfile
from cc_smith.ledger import service as ledger
from cc_smith.ops.outbox import drain
from cc_smith.rewards.engine import Purchase, reward
from cc_smith.rewards.explain import offer_hint, option_notes, pay_text
from cc_smith.rewards.finder import (
    CardResult,
    Simulation,
    find_portfolios,
    keep_or_close,
    refine,
)
from cc_smith.users import service as users

app = FastAPI(title="cc-smith", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def conn():
    with engine().begin() as c:
        yield c


def user_id(x_user_id: str = Header(...), c=Depends(conn)) -> str:
    if not users.exists(c, x_user_id):
        raise HTTPException(401, "unknown user; call POST /users")
    return x_user_id


_catalogue: tuple[int, dict] = (-1, {})


def catalogue(c) -> dict[str, tuple[CardProfile, dict, str]]:
    """Profiles are rebuilt only when the knowledge base changes, so the engine's
    per-profile caches stay valid and bounded."""
    global _catalogue
    version = c.execute(select(func.coalesce(func.max(knowledge_event.c.id), 0))).scalar_one()
    if _catalogue[0] == version:
        return _catalogue[1]
    out = {}
    for row in store.all_cards(c):
        prof = store.profile(c, row.id)
        if prof:
            out[row.id] = (prof[0], prof[1], row.status)
    _catalogue = (version, out)
    return out


# ---------- models ----------
class Ref(BaseModel):
    url: str
    quote: str | None = None
    official: bool | None = None
    evidence_id: str | None = None
    fetched_at: str | None = None
    match: str | None = None


class CardSummary(BaseModel):
    id: str
    name: str
    issuer: str
    status: str
    assessable: bool
    annual_fee_paise: int | None
    currency_kind: str | None
    currency_name: str | None
    as_of: str | None
    speculation_count: int


class FieldView(BaseModel):
    value: object
    refs: list[Ref]
    as_of: str
    version: int


class SpeculationView(BaseModel):
    id: int
    field: str
    value: object
    origin: str
    reason: str | None
    refs: list[dict]
    opened_at: str
    expires_at: str


class EventView(BaseModel):
    id: int
    card_id: str
    field: str | None
    event_type: str
    tier: str | None
    old: object = None
    new: object = None
    large_change: bool
    at: str


class CardDetail(CardSummary):
    fields: dict[str, FieldView]
    speculation: list[SpeculationView]
    changelog: list[EventView]


class MeView(BaseModel):
    user_id: str
    profile: dict
    holdings: list[dict]
    spends: dict[str, int]


class ProfileIn(BaseModel):
    flags: list[str] = []
    score_band: str | None = None
    income_band: str | None = None
    reward_preference: Literal["any", "cashback", "points"] = "any"
    max_annual_fee_paise: int | None = None


class HoldingIn(BaseModel):
    card_id: str
    last4: str | None = Field(None, pattern=r"^\d{4}$")
    statement_day: int | None = Field(None, ge=1, le=31)
    renewal_month: int | None = Field(None, ge=1, le=12)


class CardLineView(BaseModel):
    spend_key: str
    spend_paise: int
    reward_paise: int
    capped: bool


class CardResultView(BaseModel):
    card_id: str
    name: str
    spend_paise: int
    reward_paise: int
    milestone_paise: int
    fee_paise: int
    fee_waived: bool
    # Annual fee as charged, including 18% GST.
    fee_includes_gst: bool = True
    milestones_hit: list[str]
    net_paise: int
    lines: list[CardLineView]


class PortfolioView(BaseModel):
    new_cards: list[str]
    gain_paise: int
    cards: list[CardResultView]


class FinderOut(BaseModel):
    base_net_paise: int
    base_cards: list[CardResultView]
    portfolios: list[PortfolioView]
    keep_or_close: dict[str, int]
    unearned: dict[str, int]
    not_assessable: list[str]


class FinderIn(BaseModel):
    max_new: int = Field(3, ge=1, le=3)


class AssessIn(BaseModel):
    card_id: str


class AssessOut(BaseModel):
    card_id: str
    gain_paise: int
    cards: list[CardResultView]
    assessable: bool


class PayIn(BaseModel):
    merchant: str = Field(min_length=1, max_length=200)
    amount_paise: int = Field(gt=0)
    channel: Literal["online", "offline", "upi"] | None = None
    mcc: str | None = Field(None, pattern=r"^\d{4}$")


class MerchantView(BaseModel):
    key: str | None
    name: str
    category: str
    channel: str
    confidence: str


class PayOption(BaseModel):
    card_id: str
    name: str
    reward_paise: int
    reason_codes: list[str]
    rules: list[str]
    # Plain-language version of the rules and reason codes, for display.
    notes: list[str]


class OfferView(BaseModel):
    id: str
    issuer: str
    title: str
    card_ids: list[str]
    # fact: quoted from the bank's own offer page; speculation: reported, not confirmed.
    tier: Literal["fact", "speculation"]
    valid_to: str | None
    min_txn_paise: int | None
    # Rough value of the offer on this amount; not used in the card ranking.
    est_saving_paise: int | None
    url: str
    quote: str


class PayOut(BaseModel):
    merchant: MerchantView
    channel: str
    best: PayOption | None
    margin_paise: int
    text: str
    ranked: list[PayOption]
    offers: list[OfferView] = []


class ConfirmIn(BaseModel):
    card_id: str
    merchant: str
    amount_paise: int = Field(gt=0)
    channel: Literal["online", "offline", "upi"] | None = None
    mcc: str | None = None
    idempotency_key: str | None = None


class ReportIn(BaseModel):
    field: str
    message: str = Field(min_length=3, max_length=2000)
    evidence_url: str | None = None


class LaunchView(BaseModel):
    id: int
    name: str
    issuer: str | None
    # profiled: terms published from the bank's own pages. speculative: reported, not
    # confirmed by the bank (listed, not scored). known: already in the catalogue.
    status: Literal["profiled", "speculative", "known", "rejected"]
    card_id: str | None
    summary: str | None
    refs: list[dict]
    first_seen: str
    gain_paise: int | None = None


# ---------- helpers ----------
def _summary(cid: str, prof: CardProfile, meta: dict, status: str, spec_count: int) -> CardSummary:
    as_of = max((m["as_of"] for m in meta.values() if "as_of" in m), default=None)
    return CardSummary(
        id=cid, name=prof.name, issuer=prof.issuer, status=status, assessable=prof.assessable(),
        annual_fee_paise=prof.fees.annual_paise if prof.fees else None,
        currency_kind=prof.currency.kind if prof.currency else None,
        currency_name=prof.currency.name if prof.currency else None,
        as_of=as_of, speculation_count=spec_count,
    )


def _result_view(r: CardResult, names: dict[str, str]) -> CardResultView:
    return CardResultView(
        card_id=r.card_id, name=names.get(r.card_id, r.card_id), spend_paise=r.spend_paise, reward_paise=r.reward_paise,
        milestone_paise=r.milestone_paise, fee_paise=r.fee_paise, fee_waived=r.fee_waived, milestones_hit=r.milestones_hit,
        net_paise=r.net_paise,
        lines=[CardLineView(**vars(line)) for line in r.lines.values()],
    )


def _sim_cards(sim: Simulation, names: dict[str, str]) -> list[CardResultView]:
    return sorted((_result_view(r, names) for r in sim.cards.values()), key=lambda v: -v.net_paise)


def _user_inputs(c, uid: str):
    prof = users.get_profile(c, uid)
    flags = frozenset(prof.get("flags", []))
    lines = users.spend_lines(users.spends(c, uid), flags)
    return prof, flags, lines


def _candidate_ok(p: CardProfile, prof: dict) -> bool:
    pref = prof.get("reward_preference", "any")
    if pref != "any" and p.currency and p.currency.kind != pref:
        return False
    cap = prof.get("max_annual_fee_paise")
    return not (cap is not None and p.fees and p.fees.annual_paise > cap)


# ---------- routes ----------
@app.get("/health")
def health():
    return {"ok": True}


@app.get("/meta")
def meta():
    reg = merchants.registry()
    return {"categories": reg["categories"], "merchants": [{k: m[k] for k in ("key", "name", "category", "channel")} for m in reg["merchants"]]}


@app.get("/cards", response_model=list[CardSummary])
def list_cards(c=Depends(conn)):
    spec = {}
    for s in store.open_speculation(c):
        spec[s.card_id] = spec.get(s.card_id, 0) + 1
    return [_summary(cid, p, m, st, spec.get(cid, 0)) for cid, (p, m, st) in catalogue(c).items()]


@app.get("/cards/{card_id}", response_model=CardDetail)
def card_detail(card_id: str, c=Depends(conn)):
    row = c.execute(select(card_t).where(card_t.c.id == card_id)).first()
    if row is None:
        raise HTTPException(404, "no such card")
    prof, meta_ = store.profile(c, card_id)
    spec = store.open_speculation(c, card_id)
    fields = {}
    for name, m in meta_.items():
        if "as_of" not in m:
            continue
        value = getattr(prof, name, None) if name != "min_txn" else {"min_txn_paise": prof.min_txn_paise}
        if isinstance(value, list):
            value = [v.model_dump(exclude_none=True) for v in value]
        elif hasattr(value, "model_dump"):
            value = value.model_dump(exclude_none=True)
        fields[name] = FieldView(value=value, refs=[Ref(**r) for r in m["refs"]], as_of=m["as_of"], version=m["version"])
    s = _summary(card_id, prof, meta_, row.status, len(spec))
    return CardDetail(
        **s.model_dump(), fields=fields,
        speculation=[SpeculationView(id=x.id, field=x.field, value=x.value, origin=x.origin, reason=x.reason, refs=x.refs,
                                     opened_at=x.opened_at.isoformat(), expires_at=x.expires_at.isoformat()) for x in spec],
        changelog=[_event_view(e) for e in store.events(c, card_id, 50)],
    )


def _event_view(e) -> EventView:
    return EventView(id=e.id, card_id=e.card_id, field=e.field, event_type=e.event_type, tier=e.tier, old=e.old, new=e.new,
                     large_change=bool(e.large_change), at=e.created_at.isoformat())


@app.post("/cards/{card_id}/report", status_code=202)
def report(card_id: str, body: ReportIn, uid: str = Depends(user_id), c=Depends(conn)):
    if c.execute(select(card_t.c.id).where(card_t.c.id == card_id)).first() is None:
        raise HTTPException(404, "no such card")
    refs = [{"url": body.evidence_url or "", "quote": body.message, "official": False, "reporter": "user"}]
    sid = store.add_speculation(c, card_id, body.field, None, refs, "user_report", body.message)
    return {"speculation_id": sid, "status": "open", "note": "Shown as 'reported, not confirmed by the bank'; the official page is re-fetched."}


@app.post("/users")
def create_user(c=Depends(conn)):
    return {"user_id": users.create(c)}


@app.get("/me", response_model=MeView)
def me(uid: str = Depends(user_id), c=Depends(conn)):
    return MeView(user_id=uid, profile=users.get_profile(c, uid), holdings=users.holdings(c, uid), spends=users.spends(c, uid))


@app.put("/me/profile", response_model=MeView)
def put_profile(body: ProfileIn, uid: str = Depends(user_id), c=Depends(conn)):
    users.set_profile(c, uid, body.model_dump())
    return me(uid, c)


@app.put("/me/holdings", response_model=MeView)
def put_holdings(body: list[HoldingIn], uid: str = Depends(user_id), c=Depends(conn)):
    known = {r.id for r in store.all_cards(c)}
    missing = [h.card_id for h in body if h.card_id not in known]
    if missing:
        raise HTTPException(422, f"unknown cards: {missing}")
    users.set_holdings(c, uid, [h.model_dump() for h in body])
    return me(uid, c)


@app.put("/me/spends", response_model=MeView)
def put_spends(body: dict[str, int], uid: str = Depends(user_id), c=Depends(conn)):
    try:
        users.spend_lines(body)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    users.set_spends(c, uid, body)
    return me(uid, c)


@app.post("/finder", response_model=FinderOut)
def finder(body: FinderIn, uid: str = Depends(user_id), c=Depends(conn)):
    prof, _, lines = _user_inputs(c, uid)
    if not lines:
        raise HTTPException(422, "add monthly spends first (PUT /me/spends)")
    cat = catalogue(c)
    names = {cid: p.name for cid, (p, _, _) in cat.items()}
    held_ids = [h["card_id"] for h in users.holdings(c, uid)]
    held = [cat[i][0] for i in held_ids if i in cat and cat[i][0].assessable()]
    candidates = [p for cid, (p, _, st) in cat.items() if st == "active" and cid not in held_ids and _candidate_ok(p, prof)]
    base, portfolios = find_portfolios(held, candidates, lines, max_new=body.max_new)
    return FinderOut(
        base_net_paise=base.net_paise,
        base_cards=_sim_cards(base, names),
        portfolios=[PortfolioView(new_cards=p.new_cards, gain_paise=p.gain_paise, cards=_sim_cards(p.simulation, names)) for p in portfolios],
        keep_or_close=keep_or_close(held, lines) if held else {},
        unearned=base.unearned,
        not_assessable=[i for i in held_ids if i in cat and not cat[i][0].assessable()],
    )


@app.post("/finder/assess", response_model=AssessOut)
def assess(body: AssessIn, uid: str = Depends(user_id), c=Depends(conn)):
    _, _, lines = _user_inputs(c, uid)
    cat = catalogue(c)
    if body.card_id not in cat:
        raise HTTPException(404, "no such card")
    target = cat[body.card_id][0]
    names = {cid: p.name for cid, (p, _, _) in cat.items()}
    held = [cat[h["card_id"]][0] for h in users.holdings(c, uid) if h["card_id"] in cat and h["card_id"] != body.card_id]
    held = [p for p in held if p.assessable()]
    if not target.assessable() or not lines:
        return AssessOut(card_id=body.card_id, gain_paise=0, cards=[], assessable=False)
    base, _ = refine(held, lines)
    with_card, _ = refine(held + [target], lines, {p.id for p in held})
    return AssessOut(card_id=body.card_id, gain_paise=with_card.net_paise - base.net_paise, cards=_sim_cards(with_card, names), assessable=True)


def _pay(c, uid: str, body: PayIn | ConfirmIn):
    m = merchants.resolve(body.merchant, body.mcc)
    channel = body.channel or m.channel
    prof = users.get_profile(c, uid)
    flags = frozenset(prof.get("flags", []))
    p = Purchase(body.amount_paise, m.category, m.key, channel, flags)
    cat = catalogue(c)
    options = []
    for h in users.holdings(c, uid):
        if h["card_id"] not in cat:
            continue
        cardp = cat[h["card_id"]][0]
        used = ledger.cap_used(c, uid, cardp, h.get("statement_day"))
        r = reward(cardp, p, used)
        options.append((cardp, r))
    # On a tie, keep capped headroom for later: prefer the card that consumes less of its caps.
    options.sort(key=lambda o: (not o[1].eligible, -o[1].value_paise, sum(o[1].cap_use.values())))
    return m, channel, p, options


@app.post("/pay", response_model=PayOut)
def pay(body: PayIn, uid: str = Depends(user_id), c=Depends(conn)):
    m, channel, p, options = _pay(c, uid, body)
    ranked = [PayOption(card_id=cp.id, name=cp.name, reward_paise=r.value_paise, reason_codes=r.reason_codes,
                        rules=[line.rule_id for line in r.lines], notes=option_notes(cp, r)) for cp, r in options]
    eligible = [o for o in ranked if "not_assessable" not in o.reason_codes and "no_upi" not in o.reason_codes]
    best = eligible[0] if eligible else None
    margin = best.reward_paise - eligible[1].reward_paise if len(eligible) > 1 else (best.reward_paise if best else 0)
    mv = MerchantView(key=m.key, name=m.name, category=m.category, channel=channel, confidence=m.confidence)
    held = [(cp.id, cp.issuer) for cp, _ in options]
    found = offers.for_checkout(c, m.key, channel, held)
    offer_views = [OfferView(
        id=f["offer"].id, issuer=f["offer"].issuer, title=f["offer"].title, card_ids=f["card_ids"], tier=f["offer"].tier,
        valid_to=f["offer"].valid_to, min_txn_paise=f["offer"].min_txn_paise,
        est_saving_paise=offers.estimate(f["offer"], p.amount_paise), url=f["offer"].refs[0]["url"], quote=f["offer"].refs[0]["quote"],
    ) for f in found]
    offer_views.sort(key=lambda o: (o.tier != "fact", -(o.est_saving_paise or 0)))
    text = pay_text(mv, best, eligible, p.amount_paise, held_any=bool(options))
    text += offer_hint(best, eligible, offer_views)
    return PayOut(merchant=mv, channel=channel, best=best, margin_paise=margin, text=text, ranked=ranked, offers=offer_views)


@app.post("/pay/confirm")
def confirm(body: ConfirmIn, uid: str = Depends(user_id), c=Depends(conn)):
    m, channel, _, options = _pay(c, uid, body)
    chosen = next(((cp, r) for cp, r in options if cp.id == body.card_id), None)
    if chosen is None:
        raise HTTPException(422, "card not held")
    _, r = chosen
    tid = ledger.record(c, uid, card_id=body.card_id, amount_paise=body.amount_paise, merchant_key=m.key, merchant_name=m.name,
                        category=m.category, channel=channel, reward_paise=r.value_paise, cap_use=r.cap_use,
                        idempotency_key=body.idempotency_key)
    return {"txn_id": tid, "reward_paise": r.value_paise}


@app.get("/me/transactions")
def transactions(uid: str = Depends(user_id), c=Depends(conn)):
    return [{**t, "ts": t["ts"].isoformat()} for t in ledger.recent(c, uid)]


@app.get("/launches", response_model=list[LaunchView])
def launches(x_user_id: str | None = Header(None), c=Depends(conn)):
    rows = c.execute(select(launch_candidate).order_by(launch_candidate.c.first_seen.desc())).all()
    gains: dict[str, int] = {}
    if x_user_id and users.exists(c, x_user_id):
        _, _, lines = _user_inputs(c, x_user_id)
        cat = catalogue(c)
        held = [cat[h["card_id"]][0] for h in users.holdings(c, x_user_id) if h["card_id"] in cat]
        held = [p for p in held if p.assessable()]
        if lines:
            base_sim, _ = refine(held, lines)
            ids = {p.id for p in held}
            for r in rows:
                if r.card_id in cat and cat[r.card_id][0].assessable() and r.card_id not in ids:
                    gains[r.card_id] = refine(held + [cat[r.card_id][0]], lines, ids)[0].net_paise - base_sim.net_paise
    return [LaunchView(id=r.id, name=r.name, issuer=r.issuer, status=r.status, card_id=r.card_id, summary=r.summary, refs=r.refs,
                       first_seen=r.first_seen.isoformat(), gain_paise=gains.get(r.card_id)) for r in rows]


# ---------- owner console (read-only; DR-12) ----------
@app.get("/ops/changes", response_model=list[EventView])
def ops_changes(limit: int = 100, c=Depends(conn)):
    return [_event_view(e) for e in store.events(c, None, limit)]


@app.get("/ops/speculation", response_model=list[SpeculationView])
def ops_speculation(c=Depends(conn)):
    return [SpeculationView(id=x.id, field=x.field, value=x.value, origin=x.origin, reason=x.reason, refs=x.refs,
                            opened_at=x.opened_at.isoformat(), expires_at=x.expires_at.isoformat()) for x in store.open_speculation(c)]


@app.get("/ops/alerts")
def ops_alerts(limit: int = 100, c=Depends(conn)):
    drain()
    return [a.payload for a in c.execute(select(owner_alert).order_by(owner_alert.c.id.desc()).limit(limit)).all()]


@app.get("/ops/credits")
def ops_credits(c=Depends(conn)):
    rows = c.execute(select(credit_ledger)).all()
    by_flow: dict[str, dict[str, int]] = {}
    for r in rows:
        f = by_flow.setdefault(r.flow, {"live": 0, "cached": 0})
        f["cached" if r.cached else "live"] += 1
    return by_flow
