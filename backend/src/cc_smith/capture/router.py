"""HTTP API for capture: statement and credit-report upload, phone notification events,
Gmail connect/sync, and per-source status. Mounted by api/main.py with
`app.include_router(capture_router)`."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, ValidationError

from cc_smith.capture import credit_report, gmail, ingest, statements
from cc_smith.capture.pdftext import PdfError
from cc_smith.capture.privacy import has_long_digit_run
from cc_smith.capture.state import counts, get_state, set_state
from cc_smith.config import settings
from cc_smith.db import engine
from cc_smith.users import service as users

router = APIRouter(prefix="/me/capture", tags=["capture"])

MAX_EVENTS = 500


# Same pattern as api/main.py; kept local so main.py can import this router without a cycle.
def conn():
    with engine().begin() as c:
        yield c


def user_id(x_user_id: str = Header(...), c=Depends(conn)) -> str:
    if not users.exists(c, x_user_id):
        raise HTTPException(401, "unknown user; call POST /users")
    return x_user_id


async def _read_pdf(file: UploadFile) -> bytes:
    data = await file.read(settings.capture_max_upload_bytes + 1)
    await file.close()
    if len(data) > settings.capture_max_upload_bytes:
        raise HTTPException(413, "file too large")
    if not data.startswith(b"%PDF"):
        raise HTTPException(422, {"code": "not_a_pdf", "message": "upload a PDF"})
    return data


def _pdf_error(e: PdfError) -> HTTPException:
    return HTTPException(422, {"code": e.code, "message": str(e)})


@router.post("/statement")
async def upload_statement(
    file: Annotated[UploadFile, File()],
    password: Annotated[str | None, Form()] = None,
    card_id: Annotated[str | None, Form()] = None,
    uid: str = Depends(user_id), c=Depends(conn),
):
    """Parse a card statement in memory. The file and password are dropped after parsing;
    the response is the 'confirm what we read' summary."""
    data = await _read_pdf(file)
    try:
        st = statements.parse_statement(data, password)
    except PdfError as e:
        raise _pdf_error(e) from None
    finally:
        del data, password
    return statements.apply(c, uid, st, card_id)


@router.post("/credit-report")
async def upload_credit_report(
    file: Annotated[UploadFile, File()],
    consent: Annotated[bool, Form()] = False,
    password: Annotated[str | None, Form()] = None,
    uid: str = Depends(user_id), c=Depends(conn),
):
    if consent is not True:
        raise HTTPException(422, {"code": "consent_required", "message": "consent=true is required to analyse a credit report"})
    data = await _read_pdf(file)
    try:
        report = credit_report.parse_report(data, password)
    except PdfError as e:
        raise _pdf_error(e) from None
    finally:
        del data, password
    return credit_report.apply(c, uid, report)


def _scan(value, path: str = "") -> str | None:
    """Path of the first field holding a 12-19 digit run (DR-9), or None."""
    if isinstance(value, dict):
        for k, v in value.items():
            hit = _scan(k, f"{path}.{k}#key") or _scan(v, f"{path}.{k}")
            if hit:
                return hit
    elif isinstance(value, list):
        for i, v in enumerate(value):
            hit = _scan(v, f"{path}[{i}]")
            if hit:
                return hit
    elif isinstance(value, (str, int, float)) and not isinstance(value, bool) and has_long_digit_run(str(value)):
        return path or "."
    return None


@router.post("/events")
def post_events(body: Annotated[list, Body()], uid: str = Depends(user_id), c=Depends(conn)):
    """Parsed notification events from the phone. Raw notification text is never sent (DR-2)."""
    if len(body) > MAX_EVENTS:
        raise HTTPException(413, f"at most {MAX_EVENTS} events per request")
    hit = _scan(body)
    if hit:
        raise HTTPException(422, {"code": "card_number_like_value", "message": "a field holds a 12-19 digit run", "field": hit})
    try:
        events = [ingest.CaptureEvent.model_validate(e) for e in body]
    except ValidationError as e:
        raise HTTPException(422, e.errors(include_input=False, include_url=False)) from None
    outcomes = ingest.ingest_events(c, uid, events, "notification")
    set_state(c, uid, "notification")
    return {"outcomes": [o.__dict__ for o in outcomes]}


def _gmail_error(e: gmail.GmailError) -> HTTPException:
    status = {"not_configured": 503, "not_connected": 409}.get(e.code, 400)
    return HTTPException(status, {"code": e.code, "message": str(e)})


@router.get("/gmail/auth-url")
def gmail_auth_url(uid: str = Depends(user_id), c=Depends(conn)):
    try:
        return gmail.auth_url(c, uid)
    except gmail.GmailError as e:
        raise _gmail_error(e) from None


class GmailCallbackIn(BaseModel):
    code: str
    state: str | None = None


@router.post("/gmail/callback")
def gmail_callback(body: GmailCallbackIn, uid: str = Depends(user_id), c=Depends(conn)):
    try:
        return gmail.finish(c, uid, body.code, body.state)
    except gmail.GmailError as e:
        raise _gmail_error(e) from None


@router.post("/gmail/sync")
def gmail_sync(uid: str = Depends(user_id), c=Depends(conn)):
    try:
        return gmail.sync(c, uid)
    except gmail.GmailError as e:
        raise _gmail_error(e) from None


@router.delete("/gmail")
def gmail_disconnect(uid: str = Depends(user_id), c=Depends(conn)):
    gmail.disconnect(c, uid)
    return {"connected": False}


@router.get("/status")
def status(uid: str = Depends(user_id), c=Depends(conn)):
    per = counts(c, uid)
    out = {}
    for source in ingest.SOURCES:
        st = get_state(c, uid, source)
        last = st.get("last_sync_at")
        out[source] = {"last_sync_at": last.isoformat() if last else None, "counts": per.get(source, {}), "detail": st.get("detail")}
    out["gmail"]["connected"] = gmail.connected(c, uid)
    prof = users.get_profile(c, uid).get("credit")
    out["credit_report"] = {"stored": prof}
    return out
