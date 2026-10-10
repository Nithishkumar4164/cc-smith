"""Fetch an official page or PDF and keep its text as evidence.

Evidence text is stored under fixtures/evidence so the demo and tests replay without
the network. In replay mode a missing URL is an error rather than a live fetch.

Pages that are JavaScript-rendered or behind a bot wall fall back to a headless
browser (Playwright, imported only when needed). Rendered evidence is stored in the
same format, so replay never needs a browser."""

import hashlib
import io
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pdfplumber
import pypdfium2
import trafilatura

from cc_smith.config import settings

_BLOCKED = re.compile(r"think that you are a bot|verify you are human|access denied|attention required|enable javascript and cookies|verifying your browser|just a moment\.\.\.", re.IGNORECASE)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}
_INLINE_SCRIPT = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.DOTALL | re.IGNORECASE)
_TAG = re.compile(r"<(script|style)[^>]*>.*?</\1>|<[^>]+>", re.DOTALL | re.IGNORECASE)


@dataclass
class Evidence:
    id: str
    url: str
    final_url: str
    http_status: int
    content_type: str
    text: str
    fetched_at: datetime
    text_path: Path


class FetchError(Exception):
    pass


def _dir() -> Path:
    d = settings.fixtures_dir / "evidence"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _url_key(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:24]


def _flat_and_data(html: str) -> str:
    import html as htmllib

    flat = htmllib.unescape(_TAG.sub(" ", html))
    # Some issuers (SBI Card offers) ship their content as JSON inside inline scripts;
    # it is still the bank's own page, so keep the data blocks, not the code.
    data = [m.group(1) for m in _INLINE_SCRIPT.finditer(html) if '{"' in m.group(1)[:2000]]
    return flat + ("\n\n" + "\n".join(data) if data else "")


def _html_text(html: str) -> str:
    main = trafilatura.extract(html, include_tables=True, favor_recall=True) or ""
    return main + "\n\n" + _flat_and_data(html)


# Document-classification stamps that PDF text extraction splices into sentences.
_WATERMARK = re.compile(r"\s*classification\s*-\s*(internal|public|confidential)\s*", re.IGNORECASE)


def _pdf_text(data: bytes) -> str:
    # pdfium is fast on any size; pdfplumber keeps table cells in reading order better
    # but is far too slow on very large documents.
    doc = pypdfium2.PdfDocument(data)
    try:
        fast = "\n".join(doc[i].get_textpage().get_text_range() for i in range(len(doc)))
    finally:
        doc.close()
    if len(fast) > 300_000:
        return _WATERMARK.sub(" ", fast)
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        # Bold text is often drawn twice; dedupe_chars drops the overlapping copy. It is
        # quadratic in characters, so dense pages are read as they are.
        text = "\n".join(
            ((page.dedupe_chars() if len(page.chars) < 8_000 else page).extract_text() or "") for page in pdf.pages
        )
    # Each extractor drops some table cells the other keeps; evidence holds both readings.
    return _WATERMARK.sub(" ", text + "\n\n" + fast)


def _compact(text: str) -> str:
    # The quote check ignores whitespace runs, so storing them buys nothing.
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n", text).strip()


def cached(url: str) -> Evidence | None:
    meta_path = _dir() / f"{_url_key(url)}.json"
    if not meta_path.exists():
        return None
    meta = json.loads(meta_path.read_text())
    text_path = _dir() / meta["text_file"]
    return Evidence(
        meta["id"], meta["url"], meta["final_url"], meta["http_status"], meta["content_type"],
        text_path.read_text(), datetime.fromisoformat(meta["fetched_at"]), text_path,
    )


# Worth retrying in a browser: bot walls and pages whose content is drawn by scripts.
_RENDERABLE = ("HTTP 403", "HTTP 429", "HTTP 503", "bot-check page", "too little text")
# Pages whose static HTML is a long site shell without the card content, so the text
# check cannot tell they need a browser (official-domains.yaml notes): (host, path prefix).
_JS_RENDERED = (("www.sbicard.com", "/en/personal/credit-cards/"),)


def needs_render(url: str) -> bool:
    from urllib.parse import urlparse

    u = urlparse(url)
    return not u.path.lower().endswith(".pdf") and any(
        u.hostname == host and u.path.startswith(prefix) for host, prefix in _JS_RENDERED
    )


def _checked(url: str, text: str) -> str:
    text = _compact(text)
    if len(text) < 5_000 and _BLOCKED.search(text):
        raise FetchError(f"{url}: bot-check page, not the document")
    if len(text.strip()) < 200:
        raise FetchError(f"{url}: too little text ({len(text.strip())} chars); JS-rendered or blocked")
    return text


def _store(url: str, text: str, final_url: str, status: int, ctype: str) -> Evidence:
    digest = hashlib.sha256(text.encode()).hexdigest()
    key = _url_key(url)
    text_path = _dir() / f"{key}.txt"
    text_path.write_text(text)
    fetched_at = datetime.now(UTC)
    meta = {
        "id": digest, "url": url, "final_url": final_url, "http_status": status,
        "content_type": ctype, "text_file": text_path.name,
        "fetched_at": fetched_at.isoformat(),
    }
    (_dir() / f"{key}.json").write_text(json.dumps(meta, indent=2) + "\n")
    return Evidence(digest, url, final_url, status, ctype, text, fetched_at, text_path)


def _http(url: str, client: httpx.Client | None) -> Evidence:
    own = client is None
    client = client or httpx.Client(follow_redirects=True, timeout=30, headers=HEADERS)
    try:
        resp = client.get(url)
    except httpx.HTTPError as e:
        raise FetchError(f"{url}: {e}") from e
    finally:
        if own:
            client.close()
    if resp.status_code >= 400:
        raise FetchError(f"{url}: HTTP {resp.status_code}")
    ctype = resp.headers.get("content-type", "").split(";")[0]
    is_pdf = ctype == "application/pdf" or resp.content[:5] == b"%PDF-"
    text = _checked(url, _pdf_text(resp.content) if is_pdf else _html_text(resp.text))
    return _store(url, text, str(resp.url), resp.status_code, "application/pdf" if is_pdf else ctype)


RENDER_TIMEOUT_MS = 45_000
_CHALLENGE_WAIT_MS = 15_000


def render(url: str) -> Evidence:
    """Load the page in headless Chromium and keep what a reader sees (innerText), the
    rendered markup flattened the way the HTML path does (so collapsed accordions still
    count) and inline JSON data blocks. Live only: replay serves the stored text."""
    if settings.mode == "replay":
        raise FetchError(f"no recorded evidence for {url} (mode=replay; rendering is live only)")
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as e:  # pragma: no cover - depends on the install
        raise FetchError(f"{url}: needs a browser render but playwright is not installed") from e
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
            try:
                ctx = browser.new_context(user_agent=UA, locale="en-IN", viewport={"width": 1366, "height": 900},
                                          extra_http_headers={"Accept-Language": HEADERS["Accept-Language"]})
                page = ctx.new_page()
                try:
                    resp = page.goto(url, wait_until="domcontentloaded", timeout=RENDER_TIMEOUT_MS)
                    ctype = ((resp.headers.get("content-type") if resp else "") or "").split(";")[0]
                except PlaywrightError as e:
                    # A PDF served as an attachment starts a download instead of a page.
                    if "Download is starting" not in str(e):
                        raise
                    resp, ctype = None, "application/pdf"
                if ctype == "application/pdf":
                    # Same browser session (cookies from any bot check), read the bytes directly.
                    body = ctx.request.get(url, timeout=RENDER_TIMEOUT_MS)
                    if body.status >= 400:
                        raise FetchError(f"{url}: HTTP {body.status} (browser)")
                    data = body.body()
                    if data[:5] != b"%PDF-":
                        raise FetchError(f"{url}: expected a PDF, got {body.headers.get('content-type')}")
                    return _store(url, _checked(url, _pdf_text(data)), body.url, body.status, "application/pdf")
                # A bot wall (Cloudflare "Just a moment...") may clear itself after a few seconds.
                waited = 0
                while waited < _CHALLENGE_WAIT_MS and _BLOCKED.search(page.title() + " " + page.inner_text("body")[:2000]):
                    page.wait_for_timeout(1_000)
                    waited += 1_000
                try:
                    page.wait_for_load_state("networkidle", timeout=RENDER_TIMEOUT_MS // 2)
                except PlaywrightError:
                    pass  # pages that poll forever: take what is drawn so far
                # Lazy sections load as they scroll into view.
                page.evaluate("async () => { for (let y = 0; y < document.body.scrollHeight; y += 800) {"
                              " window.scrollTo(0, y); await new Promise(r => setTimeout(r, 100)); } }")
                try:
                    page.wait_for_load_state("networkidle", timeout=5_000)
                except PlaywrightError:
                    pass
                seen = page.evaluate("() => document.body.innerText")
                text = _checked(url, seen + "\n\n" + _flat_and_data(page.content()))
                status = resp.status if resp else 200
                if status >= 400 and waited == 0:
                    raise FetchError(f"{url}: HTTP {status} (browser)")
                return _store(url, text, page.url, status, "text/html")
            finally:
                browser.close()
    except PlaywrightError as e:
        raise FetchError(f"{url}: browser render failed: {e}") from e


def fetch(url: str, refresh: bool = False, client: httpx.Client | None = None, render: bool = False) -> Evidence:
    if not refresh and (ev := cached(url)):
        return ev
    if settings.mode == "replay" and not refresh:
        raise FetchError(f"no recorded evidence for {url} (mode=replay)")
    if render or needs_render(url):
        return _render(url)
    try:
        return _http(url, client)
    except FetchError as e:
        if not any(k in str(e) for k in _RENDERABLE):
            raise
        try:
            return _render(url)
        except FetchError as e2:
            raise FetchError(f"{e}; browser fallback: {e2}") from e


_render = render
