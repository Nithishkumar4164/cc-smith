"""D10: a quick model chooses the card at checkout; the engine does every calculation."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from cc_smith.api.main import app
from cc_smith.knowledge.pipeline import profile_card
from cc_smith.rewards import advisor

R = 100


class FakeModel:
    """Stands in for the Anthropic client: records the request, returns a canned tool call."""

    def __init__(self, card_id=None, reason="", fail=None, tool="choose_card"):
        self.card_id, self.reason, self.fail, self.tool, self.requests = card_id, reason, fail, tool, []
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **kw):
        self.requests.append(kw)
        if self.fail:
            raise self.fail
        block = SimpleNamespace(type="tool_use", name=self.tool, input={"card_id": self.card_id, "reason": self.reason})
        return SimpleNamespace(content=[block], stop_reason="tool_use")


@pytest.fixture
def client(db, cards):
    for c in cards.values():
        profile_card(c)
    return TestClient(app)


@pytest.fixture
def user(client):
    u = {"X-User-Id": client.post("/users").json()["user_id"]}
    client.put("/me/holdings", json=[{"card_id": "hsbc_live_plus"}, {"card_id": "sbi_cashback"}], headers=u)
    client.put("/me/spends", json={k: v * R for k, v in {"dining": 20000, "bigbasket": 3000, "other": 10000}.items()}, headers=u)
    return u


def _with_model(monkeypatch, fake):
    real = advisor.decide
    monkeypatch.setattr(advisor, "decide", lambda *a, **k: real(*a, client=fake))


def _pay(client, user):
    return client.post("/pay", json={"merchant": "BigBasket", "amount_paise": 1_000 * R, "channel": "online"}, headers=user).json()


def test_without_a_model_the_rules_decide(client, user):
    r = _pay(client, user)
    assert r["decided_by"] == "rules" and r["best"]["card_id"] == "sbi_cashback"


def test_model_choice_is_used_with_its_reason(client, user, monkeypatch):
    fake = FakeModel("hsbc_live_plus", "Live+ earns ₹100 now, the most on this payment.")
    _with_model(monkeypatch, fake)
    r = _pay(client, user)
    assert r["decided_by"] == "model"
    assert r["best"]["card_id"] == "hsbc_live_plus"
    assert r["ranked"][0]["card_id"] == "hsbc_live_plus"
    assert r["text"].startswith("Live+ earns ₹100 now")
    # Engine figures are unchanged by the model's choice.
    assert r["best"]["reward_paise"] == 100 * R


def test_model_gets_engine_figures_and_no_user_id(client, user, monkeypatch):
    fake = FakeModel("sbi_cashback", "SBI Cashback is better over the month.")
    _with_model(monkeypatch, fake)
    _pay(client, user)
    req = fake.requests[0]
    prompt = req["messages"][0]["content"]
    assert user["X-User-Id"] not in prompt
    assert "<merchant>BigBasket</merchant>" in prompt
    assert '"now": "₹100"' in prompt and '"month_difference"' in prompt
    assert req["tools"][0]["input_schema"]["properties"]["card_id"]["enum"] == ["sbi_cashback", "hsbc_live_plus"]
    assert "Do not calculate" in req["system"]


def test_invented_rupee_figure_falls_back_to_engine_text(client, user, monkeypatch):
    _with_model(monkeypatch, FakeModel("hsbc_live_plus", "Live+ saves you ₹137 this month."))
    r = _pay(client, user)
    assert r["decided_by"] == "model" and r["best"]["card_id"] == "hsbc_live_plus"
    assert "₹137" not in r["text"]
    assert r["text"].startswith("Pay with HSBC Live+ Credit Card: earns ₹100")


@pytest.mark.parametrize("fake", [
    FakeModel("hdfc_infinia_metal", "Use Infinia."),             # not a card the user holds
    FakeModel(fail=TimeoutError("took longer than 2s")),          # slow or down
    FakeModel("hsbc_live_plus", "x", tool="something_else"),      # no choose_card call
])
def test_invalid_or_failed_model_answers_fall_back_to_rules(client, user, monkeypatch, fake):
    _with_model(monkeypatch, fake)
    r = _pay(client, user)
    assert r["decided_by"] == "rules" and r["best"]["card_id"] == "sbi_cashback"


def test_reason_check_accepts_only_supplied_figures():
    allowed = {"₹100", "₹50", "₹20.68"}
    assert advisor.reason_ok("Earns ₹100 now and ₹20.68 more this month.", allowed)
    assert not advisor.reason_ok("Earns ₹100 now and ₹21 more this month.", allowed)
    assert advisor.reason_ok("No rupee amounts here.", allowed)
