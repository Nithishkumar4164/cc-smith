import json
from pathlib import Path

import pytest

from cc_smith.knowledge.schema import CardProfile

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "extractions"


@pytest.fixture(scope="session")
def cards() -> dict[str, CardProfile]:
    return {p.stem: CardProfile.model_validate(json.loads(p.read_text())) for p in FIXTURES.glob("*.json")}


@pytest.fixture
def db(tmp_path, monkeypatch):
    from cc_smith import db as dbmod
    from cc_smith.config import settings

    monkeypatch.setattr(settings, "mode", "replay")
    monkeypatch.setattr(settings, "alerts_log", tmp_path / "alerts.log")
    eng = dbmod.make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(dbmod, "_engine", eng)
    import cc_smith.notify.alerts  # noqa: F401  registers the consumer

    return eng
