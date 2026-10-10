"""Open a (usually password-protected) PDF in memory and return its text as positioned
lines. Nothing is written to disk; the caller drops the bytes and the password after
parsing (DR-9)."""

import io
import re
from dataclasses import dataclass, field

import pdfplumber
from pdfminer.pdfexceptions import PDFException
from pdfminer.psexceptions import PSException
from pdfplumber.utils.exceptions import PdfminerException

_PDF_ERRORS = (PdfminerException, PDFException, PSException, ValueError, KeyError, TypeError, AssertionError)


class PdfError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code  # password_required | wrong_password | unreadable | no_text


@dataclass
class Word:
    text: str
    x0: float
    x1: float


@dataclass
class Line:
    page: int
    top: float
    words: list[Word] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    def span_words(self, start: int, end: int) -> list[Word]:
        """Words overlapping character span [start, end) of `text`."""
        out, pos = [], 0
        for w in self.words:
            a, b = pos, pos + len(w.text)
            if a < end and b > start:
                out.append(w)
            pos = b + 1
        return out


def _is_password_error(e: Exception) -> bool:
    seen, cur = 0, e
    while cur is not None and seen < 5:
        name = type(cur).__name__
        if "Password" in name or "password" in str(cur).lower():
            return True
        cur = cur.__cause__ or cur.__context__ or (cur.args[0] if cur.args and isinstance(cur.args[0], Exception) else None)
        seen += 1
    return False


def read_lines(data: bytes, password: str | None = None, y_tolerance: float = 3.0) -> list[Line]:
    try:
        pdf = pdfplumber.open(io.BytesIO(data), password=password or "")
    except _PDF_ERRORS as e:
        if _is_password_error(e):
            raise PdfError("wrong_password" if password else "password_required",
                           "wrong password" if password else "this PDF is password-protected; send the password") from None
        raise PdfError("unreadable", "not a readable PDF") from None
    lines: list[Line] = []
    try:
        for pno, page in enumerate(pdf.pages):
            words = page.extract_words(keep_blank_chars=False, x_tolerance=2, y_tolerance=2)
            words.sort(key=lambda w: (round(w["top"]), w["x0"]))
            cur: Line | None = None
            for w in words:
                if cur is None or abs(w["top"] - cur.top) > y_tolerance:
                    cur = Line(pno, w["top"])
                    lines.append(cur)
                cur.words.append(Word(w["text"], w["x0"], w["x1"]))
        for ln in lines:
            ln.words.sort(key=lambda w: w.x0)
    except _PDF_ERRORS as e:
        if _is_password_error(e):
            raise PdfError("wrong_password" if password else "password_required", "wrong password") from None
        raise PdfError("unreadable", "could not read the PDF text") from None
    finally:
        pdf.close()
    if not any(ln.words for ln in lines):
        raise PdfError("no_text", "the PDF has no text layer (scanned image); OCR is not supported")
    return lines


MONEY = re.compile(r"(?<![\w.])-?(?:Rs\.?|INR|₹|`)?\s*(?P<num>-?\d{1,3}(?:,\d{2,3})+(?:\.\d{1,2})?|-?\d+\.\d{2})(?:\s*(?P<sfx>Cr|CR|Dr|DR)\b)?")


def money_paise(s: str) -> int | None:
    m = MONEY.search(s)
    if not m:
        return None
    num = m.group("num").replace(",", "")
    neg = num.startswith("-") or (m.group("sfx") or "").lower() == "cr"
    num = num.lstrip("-")
    rupees, _, frac = num.partition(".")
    v = int(rupees) * 100 + int((frac + "00")[:2])
    return -v if neg else v


def find_labeled(lines: list[Line], label: str, value_rx: re.Pattern, lookahead: int = 3, start: int = 0,
                 skip=None) -> tuple[str, int] | None:
    """Value printed after `label` on the same line, or below it in the same column (the
    common two-row summary box). Returns (matched value text, line index)."""
    lab = re.compile(label, re.IGNORECASE)
    for i in range(start, len(lines)):
        ln = lines[i]
        text = ln.text
        m = lab.search(text)
        if not m or (skip and skip(text)):
            continue
        rest = text[m.end():]
        # Same line, before the next label-looking word run.
        v = value_rx.search(rest[:60])
        if v:
            return v.group(0), i
        lw = ln.span_words(m.start(), m.end())
        if not lw:
            continue
        x0, x1 = lw[0].x0 - 20, lw[-1].x1 + 20
        for j in range(i + 1, min(len(lines), i + 1 + lookahead)):
            below = lines[j]
            if below.page != ln.page:
                break
            col = " ".join(w.text for w in below.words if w.x1 >= x0 and w.x0 <= x1)
            v = value_rx.search(col)
            if v:
                return v.group(0), j
    return None
