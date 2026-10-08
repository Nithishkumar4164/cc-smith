"""Quote check (DR-4 step 4): every quote must appear in the fetched official text.

Quotes were recorded with whitespace collapsed, separate lines joined by " | " and
omissions marked "...". Each segment must appear, in order, in the normalised text."""

import re
import unicodedata
from functools import lru_cache

_SPACE = re.compile(r"\s+")
_TRANSLATE = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-",
    " ": " ", " ": " ", " ": " ", "\u200b": "",
})


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_TRANSLATE)
    return _SPACE.sub(" ", text).strip().lower()


def segments(quote: str) -> list[str]:
    parts = re.split(r"\s*(?:\.\.\.|…|\s\|\s)\s*", quote)
    return [s for s in (normalise(p) for p in parts) if len(s) >= 4]


def _squash(s: str) -> str:
    return s.replace(" ", "")


_WORD = re.compile(r"[\w₹%.,/&*-]+")


def _table_match(seg: str, body: str) -> bool:
    """PDF tables come out column-interleaved, so a row read across is split up.
    Accept when every word of the segment occurs, as many times as in the segment,
    inside one window no longer than 3x the segment."""
    words = _WORD.findall(seg)
    if len(words) < 3:
        return False
    need: dict[str, int] = {}
    for w in words:
        need[w] = need.get(w, 0) + 1
    anchor = max(need, key=len)
    window = max(len(seg) * 3, 200)
    start = 0
    while (i := body.find(anchor, start)) >= 0:
        lo = max(0, i - window)
        chunk_words = _WORD.findall(body[lo : i + window])
        have: dict[str, int] = {}
        for w in chunk_words:
            have[w] = have.get(w, 0) + 1
        if all(have.get(w, 0) >= n for w, n in need.items()):
            return True
        start = i + 1
    return False


@lru_cache(maxsize=64)
def _body(text: str) -> str:
    return normalise(text)


def match_kind(quote: str, text: str) -> str | None:
    """'exact' when every segment appears in order, 'table' when only the windowed
    word match passes, None when the quote is not supported by the text."""
    body = _body(text)
    segs = segments(quote)
    if not segs:
        return None
    kind = "exact"
    squashed = None
    pos = 0
    for seg in segs:
        i = body.find(seg, pos)
        if i >= 0:
            pos = i + len(seg)
            continue
        # PDF extraction often drops or adds spaces inside table cells.
        squashed = squashed or _squash(body)
        if _squash(seg) in squashed:
            continue
        if _table_match(seg, body):
            kind = "table"
            continue
        return None
    return kind


def quote_present(quote: str, text: str) -> bool:
    return match_kind(quote, text) is not None
