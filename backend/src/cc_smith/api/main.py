"""FastAPI BFF. All money is integer paise. The hackathon identifies a user by the
X-User-Id header returned from POST /users (JWT auth comes in M1)."""

import calendar
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import func, select

import cc_smith.notify.alerts  # noqa: F401  registers outbox consumers
from cc_smith import merchants
from cc_smith.api.discovery import router as discovery_router
from cc_smith.capture.router import router as capture_router
from cc_smith.config import settings
from cc_smith.db import card as card_t
from cc_smith.db import credit_ledger, engine, knowledge_event, launch_candidate, owner_alert
from cc_smith.knowledge import offers, store
from cc_smith.knowledge.schema import CardProfile
from cc_smith.ledger import credit as credit_mod
from cc_smith.ledger import service as ledger
from cc_smith.notify import board
from cc_smith.ops.outbox import drain
from cc_smith.rewards import advisor, opportunity
from cc_smith.rewards.engine import Purchase, narrowness, reward
from cc_smith.rewards.explain import offer_hint, option_notes, pay_text
from cc_smith.rewards.finder import (
    CardResult,
    Simulation,
    find_portfolios,
    keep_or_close,
    refine,
)
from cc_smith.users import service as users


@asynccontextmanager
async def lifespan(_app: FastAPI):
    sched = None
    if settings.scheduler_enabled:
        from cc_smith.signals.scheduler import build_scheduler

        sched = build_scheduler()
        sched.start()
    yield
    if sched is not None:
        sched.shutdown(wait=False)


app = FastAPI(title="cc-smith", version="0.1.0", lifespan=lifespan)
app.include_router(capture_router)  # statements, credit reports, phone notifications, Gmail
app.include_router(discovery_router)  # demo bureau fetch, budget that fills and adapts itself
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
    # Memberships that change what this card earns (from its rules), e.g. Amazon Prime, Kiwi Neon.
    memberships: list[dict] = []
    # Live LTF / FYF / fee-waiver offers for this card; tier "speculation" = reported, not confirmed by the bank.
    fee_offers: list[dict] = []


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
    pools: list[dict] = []
    # Condition answers: key -> true/false; absent = not answered (see /meta conditions).
    answers: dict[str, bool] = {}
    spends: dict[str, int]
    # Per category: the monthly total as the user means it (category amount, or its merchants' sum if larger).
    category_totals: dict[str, int] = {}


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
    fee_status: Literal["standard", "ltf", "fyf", "custom"] = "standard"
    fyf_until: str | None = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    annual_fee_paise: int | None = Field(None, ge=0)  # with fee_status "custom", GST included
    credit_limit_paise: int | None = Field(None, ge=0)
    pool_id: str | None = None
    balance_paise: int | None = Field(None, ge=0)


class PoolIn(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=80)
    limit_paise: int = Field(gt=0)


class BillPaidIn(BaseModel):
    # None = the whole outstanding was paid.
    amount_paise: int | None = Field(None, gt=0)


class CreditView(BaseModel):
    card_id: str
    limit_paise: int | None
    pool_id: str | None
    pool_name: str | None
    outstanding_paise: int
    available_paise: int | None
    utilisation_bp: int | None


class NoticeView(BaseModel):
    id: str
    kind: Literal["fee", "cap", "milestone", "credit", "fee_offer", "offer", "card_change", "launch"]
    severity: Literal["act", "watch", "info"]
    title: str
    reason: str
    action: str
    card_id: str | None
    rupees_paise: int | None
    due: str | None
    # guidance = general practice, not a card term; it has no source to show.
    tier: Literal["fact", "speculation", "guidance"]
    refs: list[dict]
    # Offers with conditions: yes | no (collapse as "Not for you") | unknown (ask inline).
    eligibility: Literal["yes", "no", "unknown"] | None = None
    requires: list[dict] = []


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
    # Joining fees for the new cards (first-year cost, not in gain_paise), and their live fee offers.
    joining_fee_paise: int = 0
    fee_offers: dict[str, list[dict]] = {}


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
    # Rest-of-month rewards (from the monthly spends, prorated) if this card is used now, and
    # reward_paise + later_paise. Pay ranks usable cards by month_paise. Null when unusable.
    later_paise: int | None = None
    month_paise: int | None = None
    # What this card would earn if an unanswered membership were yes ("₹150 with Amazon Prime").
    if_answered: list[dict] = []


class OfferView(BaseModel):
    id: str
    issuer: str
    title: str
    card_ids: list[str]
    # fact: quoted from the bank's own offer page; speculation: reported, not confirmed.
    tier: Literal["fact", "speculation"]
    valid_to: str | None
    min_txn_paise: int | None
    # Rough value of the offer on this amount; not used in the card ranking. None for
    # "up to N%" offers, whose real value is unknown (see up_to_paise).
    est_saving_paise: int | None
    # For "up to N%" offers: the most it can give on this amount. Never added to rewards.
    up_to_paise: int | None = None
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
    # Who chose the card: "model" (quick model choosing among engine figures) or "rules"
    # (the engine's month-best pick; also the fallback on timeout, error or an invalid answer).
    decided_by: Literal["model", "rules"] = "rules"


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
def _memberships(prof: CardProfile) -> list[dict]:
    known = merchants.memberships()
    keys = sorted({k for r in prof.earn_rules for k in r.requires})
    return [{"key": k, **known.get(k, {"name": k})} for k in keys]


def _fee_offer_views(rows, answers: dict[str, bool] | None = None) -> list[dict]:
    conds, need = merchants.conditions(), merchants.offer_conditions()
    out = []
    for o in rows:
        req = need.get(o.id, [])
        out.append({
            "id": o.id, "kind": o.kind, "title": o.title, "tier": o.tier, "valid_to": o.valid_to,
            "spend_condition_paise": o.spend_condition_paise, "spend_window_days": o.spend_window_days,
            "url": o.refs[0]["url"], "quote": o.refs[0]["quote"],
            # Conditions the offer needs, with the user's eligibility when known.
            "requires": [{"key": k, "question": conds[k]["question"], "why": conds[k]["why"]} for k in req if k in conds],
            "eligibility": merchants.eligibility(req, answers or {}) if req else "yes",
        })
    return out


def _summary(cid: str, prof: CardProfile, meta: dict, status: str, spec_count: int, fee_offers: list | None = None) -> CardSummary:
    as_of = max((m["as_of"] for m in meta.values() if "as_of" in m), default=None)
    return CardSummary(memberships=_memberships(prof), fee_offers=_fee_offer_views(fee_offers or []),
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
    ms = [{k: m[k] for k in ("key", "name", "category", "channel")} for m in reg["merchants"]]
    groups = [{"category": k, "label": label, "merchants": [m for m in ms if m["category"] == k]} for k, label in reg["categories"].items()]
    return {"categories": reg["categories"], "merchants": ms, "groups": groups,
            "memberships": [{"key": k, **v} for k, v in merchants.memberships().items()],
            "conditions": [{"key": k, **v} for k, v in merchants.conditions().items()]}


@app.get("/cards", response_model=list[CardSummary])
def list_cards(c=Depends(conn)):
    spec = {}
    for s in store.open_speculation(c):
        spec[s.card_id] = spec.get(s.card_id, 0) + 1
    fo = offers.fee_offers(c)
    return [_summary(cid, p, m, st, spec.get(cid, 0), fo.get(cid)) for cid, (p, m, st) in catalogue(c).items()]


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
    sp = users.spends(c, uid)
    holds = [{**h, "balance_as_of": h["balance_as_of"].isoformat() if h.get("balance_as_of") else None} for h in users.holdings(c, uid)]
    return MeView(user_id=uid, profile=users.get_profile(c, uid), holdings=holds, pools=users.pools(c, uid), spends=sp,
                  answers=users.answers(c, uid),
                  category_totals=users.category_totals(sp))


@app.put("/me/pools", response_model=MeView)
def put_pools(body: list[PoolIn], uid: str = Depends(user_id), c=Depends(conn)):
    users.set_pools(c, uid, [p.model_dump() for p in body])
    return me(uid, c)


@app.get("/me/credit", response_model=list[CreditView])
def get_credit(uid: str = Depends(user_id), c=Depends(conn)):
    return [CreditView(**vars(v)) for v in credit_mod.credit(c, uid).values()]


@app.post("/me/cards/{card_id}/bill-paid", response_model=list[CreditView])
def bill_paid(card_id: str, body: BillPaidIn, uid: str = Depends(user_id), c=Depends(conn)):
    try:
        credit_mod.record_bill_payment(c, uid, card_id, body.amount_paise)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return get_credit(uid, c)


@app.get("/me/market/offers", response_model=list[NoticeView])
def market_offers(uid: str = Depends(user_id), c=Depends(conn)):
    """Fee offers (LTF, FYF, joining waivers) on cards you don't hold that suit your spends."""
    prof, _, lines = _user_inputs(c, uid)
    return board.fee_offer_items(c, uid, catalogue(c), users.holdings(c, uid), prof, lines)


@app.get("/me/notices", response_model=list[NoticeView])
def notices(uid: str = Depends(user_id), c=Depends(conn)):
    prof, _, lines = _user_inputs(c, uid)
    return board.build(c, uid, catalogue(c), users.holdings(c, uid), prof, users.spends(c, uid), lines)


@app.put("/me/profile", response_model=MeView)
def put_profile(body: ProfileIn, uid: str = Depends(user_id), c=Depends(conn)):
    # Merge: the profile also holds answers and credit-report data that this form doesn't send.
    data = dict(users.get_profile(c, uid))
    data.update(body.model_dump())
    # Memberships answered yes stay on as engine flags; the form's own flags add to them.
    yes = {k for k, v in (data.get("answers") or {}).items() if v}
    data["flags"] = sorted(set(body.flags) | yes)
    users.set_profile(c, uid, data)
    return me(uid, c)


@app.put("/me/answers", response_model=MeView)
def put_answers(body: dict[str, bool | None], uid: str = Depends(user_id), c=Depends(conn)):
    """Yes / No to a condition (true / false), or null to clear it. Keys from /meta conditions."""
    unknown = sorted(set(body) - set(merchants.conditions()))
    if unknown:
        raise HTTPException(422, f"unknown conditions: {unknown}")
    users.set_answers(c, uid, body)
    return me(uid, c)


@app.put("/me/holdings", response_model=MeView)
def put_holdings(body: list[HoldingIn], uid: str = Depends(user_id), c=Depends(conn)):
    known = {r.id for r in store.all_cards(c)}
    missing = [h.card_id for h in body if h.card_id not in known]
    if missing:
        raise HTTPException(422, f"unknown cards: {missing}")
    pools = {p["id"] for p in users.pools(c, uid)}
    unknown = [h.pool_id for h in body if h.pool_id and h.pool_id not in pools]
    if unknown:
        raise HTTPException(422, f"unknown credit pools: {unknown}; create them with PUT /me/pools")
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
    fees = board.held_fees(users.holdings(c, uid), cat, board.today_ist())
    base, portfolios = find_portfolios(held, candidates, lines, max_new=body.max_new, fees=fees)
    fo = offers.fee_offers(c)
    return FinderOut(
        base_net_paise=base.net_paise,
        base_cards=_sim_cards(base, names),
        portfolios=[PortfolioView(
            new_cards=p.new_cards, gain_paise=p.gain_paise, cards=_sim_cards(p.simulation, names),
            joining_fee_paise=sum(cat[i][0].fees.joining_paise for i in p.new_cards if cat[i][0].fees),
            fee_offers={i: _fee_offer_views(fo[i], users.answers(c, uid)) for i in p.new_cards if i in fo},
        ) for p in portfolios],
        keep_or_close=keep_or_close(held, lines, fees) if held else {},
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
    fees = board.held_fees(users.holdings(c, uid), cat, board.today_ist())
    base, _ = refine(held, lines, fees=fees)
    with_card, _ = refine(held + [target], lines, {p.id for p in held}, fees)
    return AssessOut(card_id=body.card_id, gain_paise=with_card.net_paise - base.net_paise, cards=_sim_cards(with_card, names), assessable=True)


def _if_answered(c, uid: str, cp, p: Purchase, r) -> list[dict]:
    """Unanswered memberships that would raise this card's reward on this payment."""
    answered = users.answers(c, uid)
    conds = merchants.conditions()
    out = []
    for key in sorted({k for rule in cp.earn_rules for k in rule.requires} - set(answered)):
        alt = reward(cp, Purchase(p.amount_paise, p.category, p.merchant, p.channel, p.flags | {key}))
        if alt.value_paise > r.value_paise and key in conds:
            out.append({"key": key, "question": conds[key]["question"], "reward_paise": alt.value_paise})
    return out


def _usable(codes: list[str]) -> bool:
    return not any(c in ("not_assessable", "no_upi") or c.startswith("insufficient_credit") for c in codes)


def _pay(c, uid: str, body: PayIn | ConfirmIn):
    m = merchants.resolve(body.merchant, body.mcc)
    channel = body.channel or m.channel
    prof = users.get_profile(c, uid)
    flags = frozenset(prof.get("flags", []))
    p = Purchase(body.amount_paise, m.category, m.key, channel, flags)
    cat = catalogue(c)
    options = []
    avail = credit_mod.credit(c, uid)
    for h in users.holdings(c, uid):
        if h["card_id"] not in cat:
            continue
        cardp = cat[h["card_id"]][0]
        used = ledger.cap_used(c, uid, cardp, h.get("statement_day"))
        r = reward(cardp, p, used)
        a = avail.get(cardp.id)
        if a and a.available_paise is not None and a.available_paise < p.amount_paise:
            r.reason_codes.append(f"insufficient_credit:{a.available_paise}")
        options.append((cardp, r, used))
    later = _later(c, uid, cat, options, avail, p.amount_paise)
    # Best for the month: this payment plus what the rest of the month still earns after it.
    # When the month can't tell cards apart, spend the narrower rule (a few named merchants)
    # and keep the broader one (all online, all dining) free for spends only it covers.
    options.sort(key=lambda o: (not _usable(o[1].reason_codes), -(o[1].value_paise + later.get(o[0].id, 0)),
                                -o[1].value_paise, -narrowness(o[0], o[1]), sum(o[1].cap_use.values())))
    return m, channel, p, [(cp, r) for cp, r, _ in options], later


def _later(c, uid: str, cat, options, avail, amount_paise: int) -> dict[str, int]:
    _, _, lines = _user_inputs(c, uid)
    usable = [(cp, r, used) for cp, r, used in options if _usable(r.reason_codes)]
    if not lines or len(usable) < 2:
        return {}
    today = board.today_ist()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_left = max(1, days_in_month - today.day)
    cards = [cp for cp, _, _ in options if _usable_card(cp)]
    cap_used = {cp.id: used for cp, _, used in options}
    available = {cid: a.available_paise for cid, a in avail.items()}
    return opportunity.outlooks(cards, {cp.id: (r.value_paise, r.cap_use) for cp, r, _ in usable}, lines, cap_used,
                                available, amount_paise, days_left)


def _usable_card(cp) -> bool:
    return cp.assessable()


@app.post("/pay", response_model=PayOut)
def pay(body: PayIn, uid: str = Depends(user_id), c=Depends(conn)):
    m, channel, p, options, later = _pay(c, uid, body)
    ranked = [PayOption(card_id=cp.id, name=cp.name, reward_paise=r.value_paise, reason_codes=r.reason_codes,
                        rules=[line.rule_id for line in r.lines], notes=option_notes(cp, r),
                        if_answered=_if_answered(c, uid, cp, p, r),
                        later_paise=later.get(cp.id), month_paise=r.value_paise + later[cp.id] if cp.id in later else None)
              for cp, r in options]
    eligible = [o for o in ranked if _usable(o.reason_codes)]
    mv = MerchantView(key=m.key, name=m.name, category=m.category, channel=channel, confidence=m.confidence)
    held = [(cp.id, cp.issuer) for cp, _ in options]
    found = offers.for_checkout(c, m.key, channel, held)
    offer_views = [OfferView(
        id=f["offer"].id, issuer=f["offer"].issuer, title=f["offer"].title, card_ids=f["card_ids"], tier=f["offer"].tier,
        valid_to=f["offer"].valid_to, min_txn_paise=f["offer"].min_txn_paise,
        est_saving_paise=offers.estimate(f["offer"], p.amount_paise),
        up_to_paise=offers.up_to_ceiling(f["offer"], p.amount_paise) if offers.is_up_to(f["offer"]) else None,
        url=f["offer"].refs[0]["url"], quote=f["offer"].refs[0]["quote"],
    ) for f in found]
    offer_views.sort(key=lambda o: (o.tier != "fact", -(o.est_saving_paise or 0)))

    # D10: a quick model chooses among the engine's options; it never calculates.
    choice = advisor.decide(
        {"name": m.name, "category": m.category, "channel": channel}, p.amount_paise,
        [{"card_id": o.card_id, "name": o.name, "notes": o.notes, "now": o.reward_paise, "later": o.later_paise,
          "month": o.month_paise,
          "offers": [{"title": ov.title, "saving": ov.est_saving_paise} for ov in offer_views
                     if ov.tier == "fact" and o.card_id in ov.card_ids and ov.est_saving_paise]}
         for o in eligible],
    )
    decided_by = "rules"
    if choice:
        eligible.sort(key=lambda o: o.card_id != choice.card_id)
        decided_by = "model"
    best = eligible[0] if eligible else None
    if best and len(eligible) > 1 and best.month_paise is not None:
        margin = best.month_paise - eligible[1].month_paise
    else:
        margin = best.reward_paise - eligible[1].reward_paise if len(eligible) > 1 else (best.reward_paise if best else 0)
    if choice and choice.reason:
        text = choice.reason
    else:
        text = pay_text(mv, best, eligible, p.amount_paise, held_any=bool(options), ranked=ranked, channel=channel)
    text += offer_hint(best, eligible, offer_views)
    if choice:
        ranked.sort(key=lambda o: o.card_id != choice.card_id)
    return PayOut(merchant=mv, channel=channel, best=best, margin_paise=margin, text=text, ranked=ranked,
                  offers=offer_views, decided_by=decided_by)


@app.post("/pay/confirm")
def confirm(body: ConfirmIn, uid: str = Depends(user_id), c=Depends(conn)):
    m, channel, _, options, _ = _pay(c, uid, body)
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
            fees = board.held_fees(users.holdings(c, x_user_id), cat, board.today_ist())
            base_sim, _ = refine(held, lines, fees=fees)
            ids = {p.id for p in held}
            for r in rows:
                if r.card_id in cat and cat[r.card_id][0].assessable() and r.card_id not in ids:
                    gains[r.card_id] = refine(held + [cat[r.card_id][0]], lines, ids, fees)[0].net_paise - base_sim.net_paise
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
