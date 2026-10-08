"""Fetch an official page or PDF and keep its text as evidence.

Evidence text is stored under fixtures/evidence so the demo and tests replay without
the network. In replay mode a missing URL is an error rather than a live fetch."""

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

_BLOCKED = re.compile(r"think that you are a bot|verify you are human|access denied|attention required|enable javascript and cookies", re.IGNORECASE)
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


def _html_text(html: str) -> str:
    main = trafilatura.extract(html, include_tables=True, favor_recall=True) or ""
    import html as htmllib

    flat = htmllib.unescape(_TAG.sub(" ", html))
    # Some issuers (SBI Card offers) ship their content as JSON inside inline scripts;
    # it is still the bank's own page, so keep the data blocks, not the code.
    data = [m.group(1) for m in _INLINE_SCRIPT.finditer(html) if '{"' in m.group(1)[:2000]]
    return main + "\n\n" + flat + ("\n\n" + "\n".join(data) if data else "")


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


def fetch(url: str, refresh: bool = False, client: httpx.Client | None = None) -> Evidence:
    if not refresh and (ev := cached(url)):
        return ev
    if settings.mode == "replay" and not refresh:
        raise FetchError(f"no recorded evidence for {url} (mode=replay)")
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
    text = _compact(_pdf_text(resp.content) if is_pdf else _html_text(resp.text))
    if len(text) < 5_000 and _BLOCKED.search(text):
        raise FetchError(f"{url}: bot-check page, not the document")
    if len(text.strip()) < 200:
        raise FetchError(f"{url}: too little text ({len(text.strip())} chars); JS-rendered or blocked")
    digest = hashlib.sha256(text.encode()).hexdigest()
    key = _url_key(url)
    text_path = _dir() / f"{key}.txt"
    text_path.write_text(text)
    fetched_at = datetime.now(UTC)
    meta = {
        "id": digest, "url": url, "final_url": str(resp.url), "http_status": resp.status_code,
        "content_type": "application/pdf" if is_pdf else ctype, "text_file": text_path.name,
        "fetched_at": fetched_at.isoformat(),
    }
    (_dir() / f"{key}.json").write_text(json.dumps(meta, indent=2) + "\n")
    return Evidence(digest, url, str(resp.url), resp.status_code, meta["content_type"], text, fetched_at, text_path)
