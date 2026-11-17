from fastapi.testclient import TestClient

from app.db.database import get_connection
from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_status():

    response = client.get("/health")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] in ["ok", "degraded"]

    assert body["database"] in ["ok", "unavailable"]


def test_startup_creates_erd_tables():
    with TestClient(app):
        with get_connection() as connection:
            table_names = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }

    assert {
        "HOUSEHOLD",
        "MEMBER",
        "FOOD_ITEM",
        "MEAL",
        "MEAL_ITEM",
        "ASSESSMENT",
        "MENU_PLAN",
        "MENU_ITEM",
    } <= table_names


def test_foreign_keys_are_enabled():
    with get_connection() as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
