"""Gmail capture with a fake Gmail service and a fake OAuth flow: no network."""
# ruff: noqa: F811  (pytest fixtures imported from capture_app are redefined as test arguments)

import base64
import json

import pytest
from capture_app import capture_client, capture_user, hold  # noqa: F401  fixtures used as test arguments
from cryptography.fernet import Fernet
from google.oauth2.credentials import Credentials
from sqlalchemy import select

from cc_smith.capture import gmail
from cc_smith.config import settings
from cc_smith.db import gmail_account, txn

R = 100


@pytest.fixture
def gmail_cfg(tmp_path, monkeypatch):
    client = tmp_path / "client.json"
    client.write_text(json.dumps({"installed": {
        "client_id": "test-client.apps.googleusercontent.com", "client_secret": "test-secret", "project_id": "cc-smith-test",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"]}}))
    monkeypatch.setattr(settings, "google_oauth_client_path", client)
    monkeypatch.setattr(settings, "capture_token_key", Fernet.generate_key().decode())
    return client


class _Req:
    def __init__(self, value):
        self.value = value

    def execute(self):
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


def _b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode()


class FakeGmail:
    """Just enough of googleapiclient's Gmail resource."""

    def __init__(self, messages: dict[str, tuple[str, str, str]], history: list[str] | None = None, history_id="900"):
        self.store = messages  # id -> (from, mime, body)
        self.added = history or []
        self.history_id = history_id
        self.full_fetched: list[str] = []
        self.queries: list[str] = []

    def users(self):
        return self

    def getProfile(self, userId):
        return _Req({"historyId": self.history_id})

    def history(self):
        outer = self

        class H:
            def list(self, **kw):
                return _Req({"history": [{"messagesAdded": [{"message": {"id": i}} for i in outer.added]}]})

        return H()

    def messages(self):
        outer = self

        class M:
            def list(self, userId, q, pageToken=None, maxResults=None):
                outer.queries.append(q)
                return _Req({"messages": [{"id": i} for i in outer.store]})

            def get(self, userId, id, format, metadataHeaders=None):
                sender, mime, body = outer.store[id]
                headers = [{"name": "From", "value": sender}]
                if format == "metadata":
                    return _Req({"id": id, "payload": {"headers": headers}})
                outer.full_fetched.append(id)
                return _Req({"id": id, "internalDate": "1791000000000", "payload": {
                    "mimeType": "multipart/alternative", "headers": headers,
                    "parts": [{"mimeType": mime, "body": {"data": _b64(body)}}]}})

        return M()


class FakeFlow:
    def __init__(self, scopes=gmail.SCOPES):
        self.credentials = Credentials(token="access-token-value", refresh_token="refresh-token-value",
                                       token_uri="https://oauth2.googleapis.com/token", client_id="c", client_secret="s", scopes=scopes)
        self.codes = []

    def fetch_token(self, code):
        self.codes.append(code)


def _connect(db, uid, scopes=gmail.SCOPES):
    with db.begin() as c:
        gmail.auth_url(c, uid)
        state = c.execute(select(gmail_account.c.pending_state).where(gmail_account.c.user_id == uid)).scalar_one()
        return gmail.finish(c, uid, "auth-code", state, flow_factory=lambda **kw: FakeFlow(scopes))


def test_auth_url_asks_only_for_gmail_readonly_with_pkce(capture_client, capture_user, gmail_cfg):
    r = capture_client.get("/me/capture/gmail/auth-url", headers=capture_user)
    assert r.status_code == 200, r.text
    url = r.json()["url"]
    assert "gmail.readonly" in url and "code_challenge=" in url and "access_type=offline" in url
    assert "gmail.modify" not in url and "mail.google.com" not in url


def test_not_configured_without_client_json(capture_client, capture_user, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "google_oauth_client_path", tmp_path / "missing.json")
    monkeypatch.setattr(settings, "capture_token_key", Fernet.generate_key().decode())
    r = capture_client.get("/me/capture/gmail/auth-url", headers=capture_user)
    assert r.status_code == 503 and r.json()["detail"]["code"] == "not_configured"


def test_callback_needs_a_pending_auth(capture_client, capture_user, gmail_cfg):
    r = capture_client.post("/me/capture/gmail/callback", json={"code": "x"}, headers=capture_user)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "bad_state"


def test_token_is_encrypted_at_rest(capture_client, capture_user, db, gmail_cfg):
    uid = capture_user["X-User-Id"]
    assert _connect(db, uid)["connected"]
    with db.begin() as c:
        enc = c.execute(select(gmail_account.c.token_enc).where(gmail_account.c.user_id == uid)).scalar_one()
    assert "refresh-token-value" not in enc and "access-token-value" not in enc
    assert "refresh-token-value" in Fernet(settings.capture_token_key.encode()).decrypt(enc.encode()).decode()
    assert capture_client.get("/me/capture/status", headers=capture_user).json()["gmail"]["connected"] is True


def test_broader_scope_grant_is_refused(capture_client, capture_user, db, gmail_cfg):
    with pytest.raises(gmail.GmailError) as e:
        _connect(db, capture_user["X-User-Id"], scopes=["https://mail.google.com/"])
    assert e.value.code == "wrong_scope"


def test_sync_reads_only_issuer_alerts_and_records_them(capture_client, capture_user, db, gmail_cfg):
    uid = capture_user["X-User-Id"]
    hold(db, capture_user, [{"card_id": "hdfc_millennia", "last4": "1234"}])
    _connect(db, uid)
    fake = FakeGmail({
        "m1": ("HDFC Bank InstaAlerts <alerts@hdfcbank.net>", "text/html",
               ("<html><body><p>Dear Customer,</p><p>Rs.1,499.00 is debited from your HDFC Bank Credit Card ending 1234 towards "
                "AMAZON on 15 Sep, 2026 at 21:14:05.</p><p>Explore offers on your card.</p></body></html>")),
        "m2": ("HDFC Bank <alerts@hdfcbank.net.phish.example>", "text/plain",
               "Rs.9,999.00 is debited from your HDFC Bank Credit Card ending 1234 towards EVIL on 15 Sep, 2026"),
        "m3": ("HDFC Bank <alerts@hdfcbank.net>", "text/plain", "Your OTP for the transaction is 123456. Do not share it."),
        "m4": ("Friend <friend@gmail.com>", "text/plain", "lunch?"),
    })
    with db.begin() as c:
        stats = gmail.sync(c, uid, service=fake)
    assert stats["mode"] == "query" and "alerts@hdfcbank.net" in fake.queries[0] and "newer_than:90d" in fake.queries[0]
    assert fake.full_fetched == ["m1", "m3"]  # a look-alike or non-issuer sender's body is never fetched
    assert stats["recorded"] == 1 and stats["not_alerts"] == 1
    with db.begin() as c:
        rows = c.execute(select(txn)).all()
    assert [(r.source, r.amount_paise, r.merchant_key, r.card_id) for r in rows] == [("gmail", 1_499 * R, "amazon", "hdfc_millennia")]

    # Next sync reads history from the stored historyId; already-seen messages are skipped.
    fake.added = ["m1", "m5"]
    fake.store["m5"] = ("alerts@hdfcbank.net", "text/plain",
                           "Rs.250.00 is debited from your HDFC Bank Credit Card ending 1234 towards SWIGGY on 16 Sep, 2026 at 10:00:00.")
    with db.begin() as c:
        stats = gmail.sync(c, uid, service=fake)
    assert stats["mode"] == "history" and stats["recorded"] == 1 and fake.full_fetched[-1] == "m5"
    st = capture_client.get("/me/capture/status", headers=capture_user).json()["gmail"]
    assert st["counts"] == {"recorded": 2, "ignored": 1} and st["last_sync_at"]


def test_sender_allow_list_comes_from_official_domains():
    assert gmail.sender_issuer("alerts@hdfcbank.net") == "hdfc_bank"
    assert gmail.sender_issuer("Axis <alerts@axis.bank.in>") == "axis_bank"
    assert gmail.sender_issuer("x@mail.hsbc.co.in") == "hsbc_india"
    assert gmail.sender_issuer("alerts@hdfcbank.net.evil.com") is None
    assert gmail.sender_issuer("alerts@nothdfcbank.net") is None
    for s in gmail.KNOWN_SENDERS:
        assert gmail.sender_issuer(s.address) == s.issuer, s.address


def test_disconnect_forgets_the_token(capture_client, capture_user, db, gmail_cfg):
    uid = capture_user["X-User-Id"]
    _connect(db, uid)
    assert capture_client.delete("/me/capture/gmail", headers=capture_user).json() == {"connected": False}
    r = capture_client.post("/me/capture/gmail/sync", headers=capture_user)
    assert r.status_code == 409
