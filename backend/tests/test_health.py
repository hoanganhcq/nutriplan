from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_ok_when_database_is_available(monkeypatch):
    monkeypatch.setattr(
        "app.services.health_service.check_database_connection", lambda: True
    )
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_endpoint_reports_unavailable_database(monkeypatch):
    monkeypatch.setattr(
        "app.services.health_service.check_database_connection", lambda: False
    )
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "degraded", "database": "unavailable"}
