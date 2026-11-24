from contextlib import contextmanager
from urllib.error import URLError

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services import health_service
from app.services.health_service import vision_status as probe_vision

client = TestClient(app)


@pytest.fixture(autouse=True)
def health_dependencies(monkeypatch):
    @contextmanager
    def connection():
        yield object()

    monkeypatch.setattr(health_service, "get_connection", connection)
    monkeypatch.setattr(
        health_service.health_repository, "probe", lambda db: ["2026.11.1"]
    )
    monkeypatch.setattr(health_service, "vision_status", lambda: "ok")


def test_health_endpoint_returns_ok_when_database_is_available():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "0.1.0",
        "rulesetVersion": "2026.11.1",
        "services": {"db": "ok", "vision": "ok", "llm": "disabled"},
    }


def test_health_endpoint_reports_unavailable_database(monkeypatch):
    def unavailable(db):
        raise OSError("database down")

    monkeypatch.setattr(health_service.health_repository, "probe", unavailable)
    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["services"]["db"] == "down"
    assert response.json()["rulesetVersion"] is None


@pytest.mark.parametrize("vision", ["degraded", "down"])
def test_vision_failure_keeps_health_available_for_manual_entry(monkeypatch, vision):
    monkeypatch.setattr(health_service, "vision_status", lambda: vision)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["services"]["vision"] == vision


@pytest.mark.parametrize("versions", [[], ["v1", "v2"]])
def test_health_does_not_invent_a_ruleset_version(monkeypatch, versions):
    monkeypatch.setattr(health_service.health_repository, "probe", lambda db: versions)
    assert client.get("/health").json()["rulesetVersion"] is None


def test_vision_probe_uses_a_bounded_timeout_and_reports_down(monkeypatch):
    monkeypatch.setattr(settings, "vision_provider", "http")
    monkeypatch.setattr(settings, "vision_url", "https://example.invalid/analyze")
    monkeypatch.setattr(settings, "vision_health_url", "https://example.invalid/health")

    def unavailable(request, timeout):
        assert timeout == 1.0
        raise URLError("offline")

    monkeypatch.setattr(health_service, "urlopen", unavailable)
    assert probe_vision() == "down"


@pytest.mark.parametrize("status, expected", [(200, "ok"), (503, "down")])
def test_vision_probe_reports_actual_http_status(monkeypatch, status, expected):
    from types import SimpleNamespace

    monkeypatch.setattr(settings, "vision_provider", "http")
    monkeypatch.setattr(settings, "vision_url", "https://example.invalid/analyze")
    monkeypatch.setattr(settings, "vision_health_url", "https://example.invalid/health")

    @contextmanager
    def readiness(request, timeout):
        yield SimpleNamespace(status=status)

    monkeypatch.setattr(health_service, "urlopen", readiness)
    assert probe_vision() == expected


def test_mock_provider_does_not_claim_real_vision_is_healthy(monkeypatch):
    monkeypatch.setattr(settings, "vision_provider", "mock")
    monkeypatch.setattr(
        health_service, "urlopen", lambda *args, **kw: pytest.fail("No network probe")
    )
    assert probe_vision() == "degraded"
