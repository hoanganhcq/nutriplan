import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, settings
from app.dependencies import get_current_session, get_db
from app.main import app
from app.repositories import event_repository
from app.services import demo_service


@pytest.fixture
def client():
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: object()
    app.dependency_overrides[get_current_session] = lambda: {"session_id": 17}
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)


def batch(events=None):
    return {
        "sessionId": "ses_u03",
        "participantId": "P03",
        "events": events
        if events is not None
        else [
            {"type": "task_start", "task": "log_meal", "at": "2026-11-25T09:00:00Z"},
            {
                "type": "dish_corrected",
                "at": "2026-11-25T09:01:10Z",
                "meta": {"itemId": "item_2"},
            },
            {
                "type": "task_end",
                "task": "log_meal",
                "at": "2026-11-25T09:02:30Z",
                "meta": {"success": True},
            },
        ],
    }


def test_events_require_token(client):
    app.dependency_overrides.pop(get_current_session)
    assert client.post("/events", json=batch()).status_code == 401


def test_events_without_consent_are_dropped_without_writes(client, monkeypatch):
    monkeypatch.setattr(event_repository, "analytics_allowed", lambda *args: False)
    monkeypatch.setattr(
        event_repository, "save", lambda *args: pytest.fail("No consent")
    )
    response = client.post("/events", json=batch())
    assert response.status_code == 202
    assert response.json() == {"data": {"accepted": 0, "dropped": 3}}


def test_events_are_bound_to_authenticated_session_and_normalized_to_utc(
    client,
    monkeypatch,
):
    monkeypatch.setattr(event_repository, "analytics_allowed", lambda *args: True)
    saved = []
    monkeypatch.setattr(event_repository, "save", lambda *args: saved.append(args))
    payload = batch()
    payload["events"][1]["at"] = "2026-11-25T16:01:10+07:00"
    response = client.post("/events", json=payload)
    assert response.status_code == 202
    assert response.json() == {"data": {"accepted": 3, "dropped": 0}}
    assert all(args[1:4] == (17, "ses_u03", "P03") for args in saved)
    assert saved[1][-1] == datetime(2026, 11, 25, 9, 1, 10)
    assert json.loads(saved[1][-2]) == {"itemId": "item_2"}


@pytest.mark.parametrize(
    "meta",
    [
        {"health_conditions": ["T2D"]},
        {"image": "data:image/png;base64,secret"},
        {"itemId": {"condition": "CKD"}},
        {"itemId": "item_diabetes"},
        {"success": "has HTN"},
        {"errorCode": "PATIENT_HAS_CKD"},
        {"weightKg": 60},
        {"note": "patient name"},
    ],
)
def test_sensitive_metadata_is_dropped_per_event(client, monkeypatch, meta):
    monkeypatch.setattr(event_repository, "analytics_allowed", lambda *args: True)
    saved = []
    monkeypatch.setattr(event_repository, "save", lambda *args: saved.append(args))
    payload = batch()
    payload["events"][1]["meta"] = meta
    response = client.post("/events", json=payload)
    assert response.json() == {"data": {"accepted": 2, "dropped": 1}}
    assert len(saved) == 2


@pytest.mark.parametrize(
    "event",
    [
        {"type": "unknown", "at": "2026-11-25T09:00:00Z"},
        {"type": "task_start", "at": "2026-11-25T09:00:00Z"},
        {"type": "undo_used", "at": "2026-11-25T09:00:00"},
    ],
)
def test_invalid_event_contract_is_rejected(client, event):
    assert client.post("/events", json=batch([event])).status_code == 422


def test_oversized_batch_is_rejected(client):
    events = [{"type": "undo_used", "at": "2026-11-25T09:00:00Z"}] * 101
    assert client.post("/events", json=batch(events)).status_code == 422


@pytest.mark.parametrize("environment", ["production", "staging", "test"])
def test_demo_is_hidden_before_opening_database(client, monkeypatch, environment):
    monkeypatch.setattr(settings, "environment", environment)
    app.dependency_overrides[get_db] = lambda: pytest.fail("Must not open database")
    response = client.post("/dev/seed-demo", json={"reset": True})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("environment", ["dev", "development", "demo"])
def test_demo_endpoint_contract(client, monkeypatch, environment):
    monkeypatch.setattr(settings, "environment", environment)
    received = []

    def seed(db, reset):
        received.append(reset)
        return {
            "data": {
                "householdId": 5,
                "token": "demo-token",
                "members": 2,
                "dishes": 28,
                "rules": 12,
            }
        }

    monkeypatch.setattr(demo_service, "seed", seed)
    response = client.post("/dev/seed-demo", json={"reset": True})
    assert response.status_code == 201
    assert response.json()["data"]["householdId"] == 5
    assert received == [True]


def test_env_alias_supports_specification(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("ENV", "dev")
    config = Settings(_env_file=None, database_url="mysql://u:p@localhost/nutrition_ai")
    assert config.environment == "dev"


def test_openapi_documents_support_endpoints_and_security():
    paths = app.openapi()["paths"]
    assert "503" in paths["/health"]["get"]["responses"]
    assert not paths["/health"]["get"].get("security")
    assert not paths["/dev/seed-demo"]["post"].get("security")
    assert "201" in paths["/dev/seed-demo"]["post"]["responses"]
    assert "202" in paths["/events"]["post"]["responses"]
    assert paths["/events"]["post"]["security"]
