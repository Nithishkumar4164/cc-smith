"""Shared fixtures for the capture tests: an app with only the capture router mounted,
seed cards profiled, and a user created through the users service."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cc_smith.capture.router import router
from cc_smith.knowledge.pipeline import profile_card
from cc_smith.users import service as users


@pytest.fixture
def capture_client(db, cards):
    for c in cards.values():
        profile_card(c)
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def capture_user(capture_client, db):
    with db.begin() as c:
        uid = users.create(c)
    return {"X-User-Id": uid}


def hold(db, headers, items):
    with db.begin() as c:
        users.set_holdings(c, headers["X-User-Id"], items)
