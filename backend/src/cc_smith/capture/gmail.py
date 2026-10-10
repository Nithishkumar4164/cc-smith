"""Gmail capture: read card transaction alert emails from issuer senders only.

- OAuth installed-app flow with PKCE, client JSON at settings.google_oauth_client_path,
  scope gmail.readonly only (restricted scope: Google verification + CASA, DR-9).
- Tokens are Fernet-encrypted at rest with settings.capture_token_key. M1 replaces this
  with a per-user data key under KMS so `user.erased` can crypto-shred it (DR-9).
- sync(): the first run lists alert-sender messages from the last `gmail_initial_days`;
  later runs read Gmail history since the stored historyId. Each new message's From
  header is checked against the allow-list before its body is fetched; bodies are parsed
  with alerts.py and only the parsed fields reach the ledger (source="gmail").

Sender allow-list: a sender is accepted only if its domain is an issuer's official domain
(docs/research/official-domains.yaml, canonical + legacy hosts) or one of the issuer mail
domains below. The exact addresses used in the Gmail query come from public open-source
Gmail parsers (Rrishik/dus-aane-bot Constants.js, read 2026-10-10) and are UNVERIFIED
until seen in a real inbox: every entry carries verified=False.
"""

import base64
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parseaddr
from functools import lru_cache
from html.parser import HTMLParser
from typing import ClassVar

import yaml
from sqlalchemy import Connection, insert, select, update

from cc_smith.capture import alerts, ingest
from cc_smith.capture.state import get_state, set_state
from cc_smith.config import settings
from cc_smith.db import capture_event, gmail_account, now

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


@dataclass(frozen=True)
class Sender:
    address: str
    issuer: str
    verified: bool = False
    seen_in: str = "Rrishik/dus-aane-bot Constants.js (secondary)"


KNOWN_SENDERS: list[Sender] = [
    Sender("alerts@hdfcbank.net", "hdfc_bank"),
    Sender("alert@hdfcbank.net", "hdfc_bank"),
    Sender("alerts@hdfcbank.bank.in", "hdfc_bank"),
    Sender("credit_cards@icicibank.com", "icici_bank"),
    Sender("credit_cards@icici.bank.in", "icici_bank"),
    Sender("customernotification@icici.bank.in", "icici_bank"),
    Sender("alerts@icicibank.com", "icici_bank"),
    Sender("onlinesbicard@sbicard.com", "sbi_card"),
    Sender("alerts@sbicard.com", "sbi_card"),
    Sender("alerts@axisbank.com", "axis_bank", seen_in="guess: Axis alert sender on the legacy domain"),
    Sender("alerts@axis.bank.in", "axis_bank"),
    Sender("credit_cards@axisbank.com", "axis_bank"),
    Sender("hsbc@mail.hsbc.co.in", "hsbc_india"),
    Sender("alerts@kotak.com", "kotak_mahindra_bank"),
    Sender("donotreply@kotak.com", "kotak_mahindra_bank"),
    Sender("transaction-alerts@idfcfirstbank.com", "idfc_first_bank"),
    Sender("transaction.alerts@idfcfirstbank.com", "idfc_first_bank"),
    Sender("noreply@idfcfirstbank.com", "idfc_first_bank"),
    Sender("alerts@yes.bank.in", "yes_bank"),
    Sender("aucreditcard.alerts@aubank.in", "au_small_finance_bank"),
    Sender("aucreditcards.alerts@aubank.in", "au_small_finance_bank"),
]
# Bank-owned mail domains that are not web hosts in official-domains.yaml (UNVERIFIED).
EXTRA_MAIL_DOMAINS = {"hdfcbank.net": "hdfc_bank", "hdfcbank.bank.in": "hdfc_bank"}
ISSUERS = {"hdfc_bank", "icici_bank", "sbi_card", "axis_bank", "hsbc_india", "kotak_mahindra_bank", "idfc_first_bank", "yes_bank",
           "au_small_finance_bank"}


class GmailError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code  # not_configured | not_connected | bad_state | wrong_scope | exchange_failed


@lru_cache
def official_domains() -> dict[str, str]:
    """domain -> issuer id, from the official-source allow-list (www. dropped)."""
    doc = yaml.safe_load(settings.allowlist_path.read_text())
    out = {}
    for issuer, spec in (doc.get("issuers") or {}).items():
        if issuer not in ISSUERS:
            continue
        for host in [spec.get("canonical"), *(spec.get("legacy") or [])]:
            if host:
                out[host.lower().removeprefix("www.")] = issuer
    out.update(EXTRA_MAIL_DOMAINS)
    return out


def sender_issuer(from_header: str) -> str | None:
    """Issuer id if the From address is on an allowed issuer domain, else None."""
    addr = parseaddr(from_header or "")[1].lower()
    if "@" not in addr:
        return None
    domain = addr.rsplit("@", 1)[1]
    for d, issuer in official_domains().items():
        if domain == d or domain.endswith("." + d):
            return issuer
    return None


def gmail_query(days: int | None = None) -> str:
    q = "from:(" + " OR ".join(s.address for s in KNOWN_SENDERS) + ")"
    return f"{q} newer_than:{days}d" if days else q


# ---------- secrets ----------
def _fernet():
    from cryptography.fernet import Fernet

    if not settings.capture_token_key:
        raise GmailError("not_configured", "CAPTURE_TOKEN_KEY is not set")
    return Fernet(settings.capture_token_key.encode())


def _enc(s: str) -> str:
    return _fernet().encrypt(s.encode()).decode()


def _dec(s: str) -> str:
    return _fernet().decrypt(s.encode()).decode()


def client_config() -> dict:
    path = settings.google_oauth_client_path
    if not path.exists():
        raise GmailError("not_configured", "Google OAuth client JSON not found; set GOOGLE_OAUTH_CLIENT_PATH")
    return json.loads(path.read_text())


def _redirect_uri(cfg: dict) -> str:
    if settings.google_oauth_redirect_uri:
        return settings.google_oauth_redirect_uri
    inner = cfg.get("installed") or cfg.get("web") or {}
    uris = inner.get("redirect_uris") or ["http://localhost"]
    return uris[0]


def _flow(state: str | None = None, code_verifier: str | None = None):
    from google_auth_oauthlib.flow import Flow

    cfg = client_config()
    return Flow.from_client_config(cfg, scopes=SCOPES, redirect_uri=_redirect_uri(cfg), state=state,
                                   code_verifier=code_verifier, autogenerate_code_verifier=code_verifier is None)


# ---------- OAuth ----------
def _row(conn: Connection, uid: str):
    return conn.execute(select(gmail_account).where(gmail_account.c.user_id == uid)).first()


def _upsert(conn: Connection, uid: str, **values) -> None:
    values["updated_at"] = now()
    if _row(conn, uid):
        conn.execute(update(gmail_account).where(gmail_account.c.user_id == uid).values(**values))
    else:
        conn.execute(insert(gmail_account).values(user_id=uid, **values))


def auth_url(conn: Connection, uid: str) -> dict:
    _fernet()  # fail before sending the user to Google if tokens could not be stored
    flow = _flow()
    url, state = flow.authorization_url(access_type="offline", prompt="consent", include_granted_scopes="false")
    _upsert(conn, uid, pending_state=state, pending_verifier_enc=_enc(flow.code_verifier or ""))
    return {"url": url, "state": state, "redirect_uri": flow.redirect_uri, "scopes": SCOPES}


def finish(conn: Connection, uid: str, code: str, state: str | None = None, flow_factory=None) -> dict:
    row = _row(conn, uid)
    if row is None or not row.pending_state:
        raise GmailError("bad_state", "call GET /me/capture/gmail/auth-url first")
    if state and state != row.pending_state:
        raise GmailError("bad_state", "state does not match the pending authorisation")
    verifier = _dec(row.pending_verifier_enc) if row.pending_verifier_enc else None
    flow = (flow_factory or _flow)(state=row.pending_state, code_verifier=verifier or None)
    try:
        flow.fetch_token(code=code)
    except Exception as e:  # noqa: BLE001  oauthlib raises many types; none should leak the code
        raise GmailError("exchange_failed", f"token exchange failed: {type(e).__name__}") from None
    creds = flow.credentials
    granted = set(getattr(creds, "granted_scopes", None) or creds.scopes or SCOPES)
    if not granted <= set(SCOPES) | {"openid"}:
        raise GmailError("wrong_scope", f"unexpected scopes granted: {sorted(granted - set(SCOPES))}")
    _upsert(conn, uid, token_enc=_enc(creds.to_json()), pending_state=None, pending_verifier_enc=None, connected_at=now())
    return {"connected": True, "scopes": SCOPES}


def disconnect(conn: Connection, uid: str) -> None:
    conn.execute(update(gmail_account).where(gmail_account.c.user_id == uid).values(
        token_enc=None, pending_state=None, pending_verifier_enc=None, updated_at=now()))
    set_state(conn, uid, "gmail", cursor=None, synced=False)


def connected(conn: Connection, uid: str) -> bool:
    row = _row(conn, uid)
    return bool(row and row.token_enc)


def _credentials(conn: Connection, uid: str):
    from google.oauth2.credentials import Credentials

    row = _row(conn, uid)
    if row is None or not row.token_enc:
        raise GmailError("not_connected", "Gmail is not connected")
    return Credentials.from_authorized_user_info(json.loads(_dec(row.token_enc)), SCOPES)


# ---------- message bodies ----------
class _Text(HTMLParser):
    BLOCK: ClassVar[set[str]] = {"p", "div", "br", "tr", "li", "table", "h1", "h2", "h3", "h4", "td"}

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "head"):
            self.skip += 1
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("style", "script", "head") and self.skip:
            self.skip -= 1
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    p = _Text()
    p.feed(html)
    text = "".join(p.parts)
    return re.sub(r"\n\s*\n+", "\n", text)


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace")


def body_text(payload: dict) -> str:
    plain, html = [], []

    def walk(part):
        mime = part.get("mimeType", "")
        data = (part.get("body") or {}).get("data")
        if data and mime == "text/plain":
            plain.append(_decode(data))
        elif data and mime == "text/html":
            html.append(_decode(data))
        for p in part.get("parts") or []:
            walk(p)

    walk(payload)
    if plain:
        return "\n".join(plain)
    return "\n".join(html_to_text(h) for h in html)


def _header(msg: dict, name: str) -> str:
    for h in (msg.get("payload") or {}).get("headers") or []:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


# ---------- sync ----------
def _list_ids(svc, query: str) -> list[str]:
    ids, token = [], None
    while True:
        resp = svc.users().messages().list(userId="me", q=query, pageToken=token, maxResults=500).execute()
        ids += [m["id"] for m in resp.get("messages") or []]
        token = resp.get("nextPageToken")
        if not token or len(ids) >= 5000:
            return ids


def _history_ids(svc, start: str) -> list[str] | None:
    """None when the historyId is too old (Gmail answers 404) and a full list is needed."""
    from googleapiclient.errors import HttpError

    ids, token = [], None
    try:
        while True:
            resp = svc.users().history().list(userId="me", startHistoryId=start, historyTypes=["messageAdded"], pageToken=token).execute()
            for h in resp.get("history") or []:
                for added in h.get("messagesAdded") or []:
                    ids.append(added["message"]["id"])
            token = resp.get("nextPageToken")
            if not token:
                return list(dict.fromkeys(ids))
    except HttpError as e:
        if getattr(e, "status_code", None) == 404 or getattr(getattr(e, "resp", None), "status", None) == 404:
            return None
        raise


def _seen(conn: Connection, msg_id: str) -> bool:
    key = ingest.idem_key("gmail", msg_id)
    return conn.execute(select(capture_event.c.id).where(capture_event.c.idempotency_key == key)).first() is not None


def sync(conn: Connection, uid: str, service=None) -> dict:
    creds = None
    if service is None:
        from googleapiclient.discovery import build

        creds = _credentials(conn, uid)
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    elif not connected(conn, uid):
        raise GmailError("not_connected", "Gmail is not connected")
    state = get_state(conn, uid, "gmail")
    cursor = state.get("cursor") or {}
    profile_history = str(service.users().getProfile(userId="me").execute().get("historyId"))
    ids = _history_ids(service, cursor["history_id"]) if cursor.get("history_id") else None
    mode = "history"
    if ids is None:
        mode = "query"
        if state.get("last_sync_at"):
            last = state["last_sync_at"]
            last = last if last.tzinfo else last.replace(tzinfo=UTC)
            days = max(1, (datetime.now(UTC) - last + timedelta(days=1)).days)
        else:
            days = settings.gmail_initial_days
        ids = _list_ids(service, gmail_query(days))
    stats = {"mode": mode, "messages": len(ids), "from_allowed_senders": 0, "parsed": 0, "not_alerts": 0}
    events = []
    for mid in ids:
        if _seen(conn, mid):
            continue
        meta = service.users().messages().get(userId="me", id=mid, format="metadata", metadataHeaders=["From"]).execute()
        sender = _header(meta, "From")
        if sender_issuer(sender) is None:
            continue
        stats["from_allowed_senders"] += 1
        full = service.users().messages().get(userId="me", id=mid, format="full").execute()
        received = datetime.fromtimestamp(int(full.get("internalDate", "0")) / 1000, UTC) if full.get("internalDate") else None
        a = alerts.parse(body_text(full.get("payload") or {}), sender=sender, received_at=received)
        if a is None:
            stats["not_alerts"] += 1
            ingest.log_ignored(conn, uid, "gmail", mid, "not_a_transaction")
            continue
        stats["parsed"] += 1
        ev = a.to_dict()
        ev["id"] = mid
        ev["ts"] = ev["ts"] or (received.isoformat() if received else None)
        events.append(ev)
    outcomes = ingest.ingest_events(conn, uid, events, "gmail")
    for o in outcomes:
        stats[o.outcome] = stats.get(o.outcome, 0) + 1
    set_state(conn, uid, "gmail", cursor={"history_id": profile_history}, detail=stats)
    if creds is not None and creds.token:
        _upsert(conn, uid, token_enc=_enc(creds.to_json()))  # keep a refreshed access token
    return stats
