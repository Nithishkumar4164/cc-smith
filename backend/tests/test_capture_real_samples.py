"""Runs the statement and credit-report parsers on the owner's real files, if any are in
<repo>/private_samples/ (gitignored). Prints which fields were found, never the values:
no names, addresses, PAN, card numbers or amounts. Run with `pytest -s` to see it.

private_samples/passwords.txt holds one `filename: password` per line."""

from collections import Counter
from pathlib import Path

import pytest

from cc_smith.capture.credit_report import parse_report
from cc_smith.capture.pdftext import PdfError
from cc_smith.capture.statements import parse_statement
from cc_smith.config import REPO

SAMPLES = REPO / "private_samples"
REPORT_HINT = ("cibil", "experian", "equifax", "crif", "highmark", "credit_report", "credit-report", "creditreport", "bureau")


def _pdfs() -> list[Path]:
    return sorted(SAMPLES.glob("*.pdf")) if SAMPLES.is_dir() else []


def _passwords() -> dict[str, str]:
    f = SAMPLES / "passwords.txt"
    out = {}
    if f.exists():
        for line in f.read_text().splitlines():
            if ":" in line:
                name, pw = line.split(":", 1)
                out[name.strip()] = pw.strip()
    return out


@pytest.mark.skipif(not _pdfs(), reason="no real samples in private_samples/")
def test_real_samples_summary():
    pws = _passwords()
    for i, path in enumerate(_pdfs(), 1):
        pw = pws.get(path.name)
        is_report = any(h in path.name.lower() for h in REPORT_HINT)
        label = f"[{i}] {'report' if is_report else 'statement'} ({'password' if pw else 'no password'})"
        try:
            if is_report:
                r = parse_report(path.read_bytes(), pw)
                print(label, {"bureau": r.bureau, "score_found": r.score is not None, "report_date_found": bool(r.report_date),
                              "card_accounts": len(r.accounts), "other_accounts": r.other_accounts,
                              "accounts_with_limit": sum(a.credit_limit_paise is not None for a in r.accounts),
                              "accounts_with_balance": sum(a.current_balance_paise is not None for a in r.accounts),
                              "accounts_with_dpd": sum(a.dpd is not None for a in r.accounts),
                              "enquiries": len(r.enquiries), "warnings": r.warnings})
            else:
                st = parse_statement(path.read_bytes(), pw)
                found = {k: v is not None for k, v in st.to_dict().items() if k not in ("lines", "warnings", "issuer_hint")}
                print(label, {"issuer": st.issuer_hint, **found, "lines": len(st.lines),
                              "line_kinds": dict(Counter(x.kind for x in st.lines)), "warnings": st.warnings})
        except PdfError as e:
            print(label, {"error": e.code})
