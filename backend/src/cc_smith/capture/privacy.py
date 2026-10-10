"""DR-9: no card numbers anywhere. Runs of 12–19 digits (optionally grouped by single
spaces or hyphens, as card numbers are printed) are stripped from every inbound payload."""

import re

# 12–19 contiguous digits, or a card number printed in groups ("4111 1111 1111 1111",
# "4111-1111-1111-1111", Amex "3782 822463 10005"). Mixed separators are not matched, so
# "x1234 21-03-2026 05:49" (last4 then a date) is left alone.
PAN_RUN = re.compile(
    r"(?<![\d])(?:\d{12,19}|\d{4}([ \-])\d{4}\1\d{4}\1\d{1,7}|\d{4}([ \-])\d{6}\2\d{4,5})(?![\d])"
)
# Contiguous run only: the strict check for structured fields the phone sends.
DIGIT_RUN = re.compile(r"\d{12,}")


def has_long_digit_run(value: str) -> bool:
    return bool(DIGIT_RUN.search(value) or PAN_RUN.search(value))


def strip_long_digit_runs(text: str, repl: str = "") -> str:
    return PAN_RUN.sub(repl, text)


def last4_of_long_runs(text: str) -> list[str]:
    """Last four digits of every card-number-like run, so a statement that prints a full
    PAN still yields last4 without the number ever being kept."""
    return [re.sub(r"\D", "", m.group())[-4:] for m in PAN_RUN.finditer(text)]
