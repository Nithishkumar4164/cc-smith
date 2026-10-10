import json
from types import SimpleNamespace

import pytest

from cc_smith.config import settings
from cc_smith.knowledge.extract import (
    TOOL_NAME,
    ExtractionError,
    extract_terms,
    strict_schema,
)
from cc_smith.knowledge.schema import CardProfile


class FakeMessages:
    def __init__(self, reply):
        self.reply, self.kwargs = reply, None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return self.reply


def _client(tool_input, stop="tool_use"):
    block = SimpleNamespace(type="tool_use", name=TOOL_NAME, input=tool_input)
    return SimpleNamespace(messages=FakeMessages(SimpleNamespace(stop_reason=stop, content=[block])))


def _objects(node):
    if isinstance(node, dict):
        if node.get("type") == "object":
            yield node
        for v in node.values():
            yield from _objects(v)
    elif isinstance(node, list):
        for v in node:
            yield from _objects(v)


def test_strict_schema_closes_every_object_and_drops_unsupported_constraints():
    s = strict_schema(CardProfile)
    assert all(o.get("additionalProperties") is False for o in _objects(s))
    assert "minItems" not in json.dumps(s)


def test_replay_reads_launch_fixture(db):
    p = extract_terms("axis_ace", "Axis Bank ACE Credit Card", "Axis Bank", [])
    assert p.fees.annual_paise == 49_900 and p.caps[0].amount == 50_000


def test_live_extraction_offers_only_the_schema_tool_and_validates(monkeypatch):
    monkeypatch.setattr(settings, "mode", "live")
    body = json.loads((settings.fixtures_dir / "extractions_launch" / "axis_ace.json").read_text())
    client = _client({**body, "id": "ignored", "name": "ignored"})
    p = extract_terms("axis_ace", "Axis Bank ACE Credit Card", "Axis Bank", [("https://www.axis.bank.in/x", "page text")], client=client)
    kw = client.messages.kwargs
    assert [t["name"] for t in kw["tools"]] == [TOOL_NAME] and "strict" not in kw["tools"][0]  # grammar too large for strict (400)
    assert kw["tool_choice"]["type"] == "auto"  # Sonnet 5.5 rejects forced tool_choice
    assert kw["model"] == settings.extract_model and '<document url="https://www.axis.bank.in/x">' in kw["messages"][0]["content"]
    assert p.id == "axis_ace" and p.name == "Axis Bank ACE Credit Card"

    bad = _client({"fees": {"src": [], "joining_paise": 0, "annual_paise": 0}})
    with pytest.raises(ExtractionError, match="schema validation"):
        extract_terms("x", "X", "Axis Bank", [("https://www.axis.bank.in/x", "t")], client=bad)
