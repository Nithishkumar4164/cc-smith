"""The alert parser against the shared vectors the phone's Dart port also runs."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from cc_smith.capture.alerts import parse
from cc_smith.capture.privacy import has_long_digit_run, last4_of_long_runs, strip_long_digit_runs

VECTORS = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "alerts" / "vectors.json").read_text())
RECEIVED = datetime.fromisoformat(VECTORS["received_at"])


@pytest.mark.parametrize("case", VECTORS["cases"], ids=[c["id"] for c in VECTORS["cases"]])
def test_vector(case):
    got = parse(case["text"], sender=case["sender"], received_at=RECEIVED)
    assert (got.to_dict() if got else None) == case["expected"]


def test_vectors_cover_every_target_issuer_and_kind():
    issuers = {c["expected"]["issuer_hint"] for c in VECTORS["cases"] if c["expected"]}
    assert issuers >= {"hdfc_bank", "icici_bank", "sbi_card", "axis_bank", "hsbc_india", "kotak_mahindra_bank", "idfc_first_bank",
                       "yes_bank", "au_small_finance_bank"}
    kinds = {c["expected"]["kind"] for c in VECTORS["cases"] if c["expected"]}
    assert kinds >= {"debit", "refund", "payment_received"}
    assert any(c["expected"] is None for c in VECTORS["cases"])


def test_parsed_output_never_carries_a_card_number():
    for case in VECTORS["cases"]:
        got = parse(case["text"], sender=case["sender"], received_at=RECEIVED)
        if got:
            assert not any(isinstance(v, str) and has_long_digit_run(v) for v in got.to_dict().values()), case["id"]


def test_card_number_runs_are_stripped_but_dates_and_last4_survive():
    assert strip_long_digit_runs("card 4111111111111111 ok") == "card  ok"
    assert strip_long_digit_runs("card 4111 1111 1111 1111 ok") == "card  ok"
    assert strip_long_digit_runs("card 3782-822463-10005 ok") == "card  ok"
    kept = "Card x1234 21-03-2026 05:49:40 PM, Avl Limit: INR 1,23,456.00, call 1800 2662"
    assert strip_long_digit_runs(kept) == kept
    assert last4_of_long_runs("5522 6012 3456 4321") == ["4321"]
    assert has_long_digit_run("UPI-638903921672-CORN")
    assert not has_long_digit_run("XX1234")
