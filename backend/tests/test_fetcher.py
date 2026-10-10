import importlib.abc
import sys

import pytest

from cc_smith.knowledge import fetcher


class _NoPlaywright(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name == "playwright" or name.startswith("playwright."):
            raise AssertionError(f"replay imported {name}")


@pytest.fixture
def no_playwright(monkeypatch):
    for name in [m for m in sys.modules if m == "playwright" or m.startswith("playwright.")]:
        monkeypatch.delitem(sys.modules, name)
    guard = _NoPlaywright()
    sys.meta_path.insert(0, guard)
    yield
    sys.meta_path.remove(guard)


def test_replay_serves_recorded_evidence_without_a_browser(no_playwright):
    # Recorded from a browser render: SBI Card product pages are JavaScript-drawn.
    ev = fetcher.fetch("https://www.sbicard.com/en/personal/credit-cards/simplyclick-sbi-card.html")
    assert "4 Reward Points = Re 1" in ev.text
    ev = fetcher.fetch("https://www.sbicard.com/en/personal/credit-cards/simplyclick-sbi-card.html", render=True)
    assert "playwright" not in sys.modules


def test_replay_never_renders_a_missing_page(no_playwright):
    with pytest.raises(fetcher.FetchError, match="mode=replay"):
        fetcher.fetch("https://www.sbicard.com/en/not-recorded.html", render=True)
    with pytest.raises(fetcher.FetchError, match="mode=replay"):
        fetcher.render("https://www.sbicard.com/en/not-recorded.html")
    assert "playwright" not in sys.modules
