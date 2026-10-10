"""Card discovery and budget routes (owner decisions, 10 Oct 2026). The bureau fetch and
the SMS/email import are DEMO data sources: every response carries mock: true."""

import re

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from cc_smith.capture import demo
from cc_smith.db import engine
from cc_smith.users import budget
from cc_smith.users import service as users

router = APIRouter(tags=["discovery"])


def conn():
    with engine().begin() as c:
        yield c


def user_id(x_user_id: str = Header(...), c=Depends(conn)) -> str:
    if not users.exists(c, x_user_id):
        raise HTTPException(401, "unknown user; call POST /users")
    return x_user_id


class BureauStartIn(BaseModel):
    phone: str = Field(min_length=10, max_length=20)  # "+91 98765 43210" is fine; digits are checked below
    consent: bool


class BureauVerifyIn(BaseModel):
    request_id: str
    otp: str = Field(pattern=r"^\d{6}$")


class CardCheckIn(BaseModel):
    lender: str = Field(min_length=1, max_length=80)
    last4: str = Field(pattern=r"^\d{4}$")
    bin: str = Field(pattern=r"^\d{6}$")  # first 6 digits; the full number stays on the phone


class ImportIn(BaseModel):
    sources: list[str] = ["sms", "email"]


@router.post("/me/discovery/bureau/start")
def bureau_start(body: BureauStartIn, uid: str = Depends(user_id)):
    if not body.consent:
        raise HTTPException(422, "consent=true is required to fetch a credit report")
    digits = re.sub(r"\D", "", body.phone)[-10:]
    if len(digits) != 10:
        raise HTTPException(422, "enter a 10-digit Indian mobile number")
    return demo.bureau_start(digits)


@router.post("/me/discovery/bureau/verify")
def bureau_verify(body: BureauVerifyIn, uid: str = Depends(user_id), c=Depends(conn)):
    from cc_smith.api.main import catalogue  # late import: main includes this router

    scored = {cid for cid, (_p, _m, st) in catalogue(c).items() if st == "active"}
    out = demo.bureau_verify(c, uid, body.request_id, body.otp, scored)
    if out is None:
        raise HTTPException(422, "wrong or expired code")
    return out


@router.post("/me/budget/import-demo")
def import_demo(body: ImportIn, uid: str = Depends(user_id), c=Depends(conn)):
    res = demo.import_last_month(c, uid, body.sources)
    budget.adapt(c, uid, force=True)
    return {**res, "budget": budget.view(c, uid)}


@router.get("/me/budget")
def get_budget(uid: str = Depends(user_id), c=Depends(conn)):
    return budget.view(c, uid)


@router.put("/me/budget")
def put_budget(body: dict[str, int | None], uid: str = Depends(user_id), c=Depends(conn)):
    try:
        return budget.edit(c, uid, body)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


@router.post("/me/discovery/card")
def card_check(body: CardCheckIn, uid: str = Depends(user_id), c=Depends(conn)):
    from cc_smith.api.main import catalogue  # late import: main includes this router

    scored = {cid for cid, (_p, _m, st) in catalogue(c).items() if st == "active"}
    out = demo.card_check(c, body.lender, body.last4, body.bin, scored)
    if out is None:
        raise HTTPException(422, "this card number doesn't match a card from that bank")
    return out

