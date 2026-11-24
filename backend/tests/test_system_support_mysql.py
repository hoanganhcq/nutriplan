"""Opt-in MySQL tests; create/drop only a UUID-named isolated database."""

import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.database import get_connection
from app.dependencies import get_db
from app.main import app

pytestmark = pytest.mark.mysql_support


@pytest.fixture(scope="module")
def isolated_database():
    if os.getenv("RUN_MYSQL_SUPPORT_TESTS") != "1":
        pytest.skip("Set RUN_MYSQL_SUPPORT_TESTS=1 for isolated MySQL validation")
    name = "nutriplan_validation_" + uuid4().hex
    assert re.fullmatch(r"nutriplan_validation_[0-9a-f]{32}", name)
    original_url = settings.database_url
    original_environment = settings.environment
    with get_connection() as admin:
        admin.execute(f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4")
    try:
        settings.database_url = (
            urlsplit(original_url)._replace(path=f"/{name}").geturl()
        )
        schema = Path(__file__).parents[1] / "app" / "db" / "schema.sql"
        with get_connection() as db:
            for statement in schema.read_text(encoding="utf-8").split(";"):
                if statement.strip():
                    db.execute(statement)
        yield
    finally:
        settings.database_url = original_url
        settings.environment = original_environment
        # The name is generated above, never supplied by configuration or a user.
        assert re.fullmatch(r"nutriplan_validation_[0-9a-f]{32}", name)
        with get_connection() as admin:
            admin.execute(f"DROP DATABASE `{name}`")


@pytest.fixture
def mysql_client(isolated_database, monkeypatch):
    monkeypatch.setattr(settings, "environment", "demo")
    db = get_connection()
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            yield client, db
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        db._connection.rollback()
        db._connection.close()


def seed(client, reset=False):
    response = client.post("/dev/seed-demo", json={"reset": reset})
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    return data, {"Authorization": f"Bearer {data['token']}"}


def events():
    return {
        "sessionId": "ses_u03",
        "participantId": "P03",
        "events": [
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


def consent(client, headers, household_id, granted):
    response = client.put(
        "/consents",
        headers=headers,
        json={
            "householdId": household_id,
            "policyVersion": "0.1",
            "consents": {"usage_analytics": granted},
        },
    )
    assert response.status_code == 200, response.text


def test_demo_seed_is_idempotent_and_returns_real_token(mysql_client):
    client, db = mysql_client
    first, headers = seed(client)
    assert (first["members"], first["dishes"], first["rules"]) == (2, 28, 12)
    profiles = client.get(
        "/members", headers=headers, params={"householdId": first["householdId"]}
    )
    assert profiles.status_code == 200, profiles.text
    members = profiles.json()["data"]
    assert {(m["name"], m["age"]) for m in members} == {
        ("Bà Trung", 66),
        ("Ông Thanh", 70),
    }
    assert all(m["isSimulated"] for m in members)
    assert members[0]["conditions"] == ["diabetes", "hypertension"]
    assert members[1]["conditions"] == ["kidney_disease"]
    assert (
        db.execute(
            "SELECT COUNT(*) AS n FROM HEALTH_RULE WHERE enabled = TRUE"
        ).fetchone()["n"]
        == 0
    )
    second, headers = seed(client)
    assert second["householdId"] == first["householdId"]
    assert second["token"] != first["token"]
    assert (
        client.get(
            "/members",
            params={"householdId": first["householdId"]},
            headers={"Authorization": f"Bearer {first['token']}"},
        ).status_code
        == 401
    )
    assert db.execute("SELECT COUNT(*) AS n FROM FOOD_ITEM").fetchone()["n"] == 28
    assert db.execute("SELECT COUNT(*) AS n FROM HEALTH_RULE").fetchone()["n"] == 12


def test_events_persist_only_with_current_consent_and_safe_metadata(mysql_client):
    client, db = mysql_client
    data, headers = seed(client)
    payload = events()
    response = client.post("/events", headers=headers, json=payload)
    assert response.status_code == 202
    assert response.json()["data"] == {"accepted": 0, "dropped": 3}
    consent(client, headers, data["householdId"], True)
    payload["events"].append(
        {
            "type": "error_shown",
            "at": "2026-11-25T09:02:40Z",
            "meta": {"health_conditions": ["T2D"], "image": "private-image"},
        }
    )
    response = client.post("/events", headers=headers, json=payload)
    assert response.json()["data"] == {"accepted": 3, "dropped": 1}
    rows = db.execute("SELECT meta_json FROM USAGE_EVENT").fetchall()
    assert len(rows) == 3
    assert {key for row in rows for key in json.loads(row["meta_json"])} == {
        "itemId",
        "success",
    }
    consent(client, headers, data["householdId"], False)
    assert (
        client.post("/events", headers=headers, json=events()).json()["data"][
            "accepted"
        ]
        == 0
    )
    assert db.execute("SELECT COUNT(*) AS n FROM USAGE_EVENT").fetchone()["n"] == 3


def test_another_session_cannot_use_demo_household_consent(mysql_client):
    client, db = mysql_client
    data, headers = seed(client)
    consent(client, headers, data["householdId"], True)
    other = client.post("/sessions").json()
    response = client.post(
        "/events", headers={"Authorization": f"Bearer {other['token']}"}, json=events()
    )
    assert response.json()["data"] == {"accepted": 0, "dropped": 3}
    assert db.execute("SELECT COUNT(*) AS n FROM USAGE_EVENT").fetchone()["n"] == 0


def test_events_require_consent_for_all_households_in_a_session(mysql_client):
    client, db = mysql_client
    data, headers = seed(client)
    consent(client, headers, data["householdId"], True)
    other_id = client.post(
        "/households", headers=headers, json={"name": "Another owned household"}
    ).json()["household_id"]
    response = client.post("/events", headers=headers, json=events())
    assert response.json()["data"] == {"accepted": 0, "dropped": 3}
    consent(client, headers, other_id, True)
    response = client.post("/events", headers=headers, json=events())
    assert response.json()["data"] == {"accepted": 3, "dropped": 0}


def test_health_can_probe_real_mysql_without_authorization(mysql_client):
    client, db = mysql_client
    # Health uses its own connection and only reads committed data.
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["services"] == {
        "db": "ok",
        "vision": "degraded",
        "llm": "disabled",
    }
    assert response.json()["rulesetVersion"] is None


def test_reset_cleans_demo_meals_and_menus_but_preserves_other_households(mysql_client):
    client, db = mysql_client
    data, headers = seed(client)
    other = client.post("/sessions").json()
    other_household = client.post(
        "/households",
        headers={"Authorization": f"Bearer {other['token']}"},
        json={"name": "Unrelated household"},
    ).json()["household_id"]
    member_id = db.execute("SELECT member_id FROM MEMBER LIMIT 1").fetchone()[
        "member_id"
    ]
    food_id = db.execute("SELECT food_id FROM FOOD_ITEM LIMIT 1").fetchone()["food_id"]
    meal_id = db.execute(
        "INSERT INTO MEAL (household_id, eaten_at) VALUES (%s, CURRENT_TIMESTAMP)",
        (data["householdId"],),
    ).lastrowid
    db.execute(
        "INSERT INTO MEAL_ITEM (meal_id, food_id) VALUES (%s, %s)", (meal_id, food_id)
    )
    db.execute(
        "INSERT INTO MEAL_MEMBER (meal_id, member_id) VALUES (%s, %s)",
        (meal_id, member_id),
    )
    db.execute(
        """INSERT INTO ASSESSMENT
           (meal_id, member_id, suitability_level, created_at)
           VALUES (%s, %s, 'INSUFFICIENT_DATA', CURRENT_TIMESTAMP)""",
        (meal_id, member_id),
    )
    db.execute(
        """INSERT INTO MEAL_REVISION_HISTORY
           (meal_id, revision_no, action, snapshot_json)
           VALUES (%s, 1, 'analyze', '[]')""",
        (meal_id,),
    )
    plan_id = db.execute(
        "INSERT INTO MENU_PLAN (member_id, start_date) VALUES (%s, CURRENT_DATE)",
        (member_id,),
    ).lastrowid
    db.execute(
        "INSERT INTO MENU_ITEM (menu_plan_id, food_id, meal_type) "
        "VALUES (%s, %s, 'lunch')",
        (plan_id, food_id),
    )
    db.execute(
        "INSERT INTO MENU_PLAN_REVISION_HISTORY "
        "(menu_plan_id, revision, snapshot_json) VALUES (%s, 1, '{}')",
        (plan_id,),
    )
    consent(client, headers, data["householdId"], True)
    assert (
        client.post("/events", headers=headers, json=events()).json()["data"][
            "accepted"
        ]
        == 3
    )
    new, _ = seed(client, reset=True)
    assert new["householdId"] != data["householdId"]
    assert db.execute(
        "SELECT 1 FROM HOUSEHOLD WHERE household_id = %s", (other_household,)
    ).fetchone()
    for table in (
        "MEAL",
        "MEAL_ITEM",
        "MEAL_MEMBER",
        "ASSESSMENT",
        "MEAL_REVISION_HISTORY",
        "MENU_PLAN",
        "MENU_ITEM",
        "MENU_PLAN_REVISION_HISTORY",
        "USAGE_EVENT",
    ):
        assert db.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"] == 0
    assert db.execute("SELECT COUNT(*) AS n FROM MEMBER").fetchone()["n"] == 2
    assert db.execute("SELECT COUNT(*) AS n FROM FOOD_ITEM").fetchone()["n"] == 28


def test_reset_refuses_household_with_real_profile(mysql_client):
    client, db = mysql_client
    data, _ = seed(client)
    db.execute(
        "UPDATE MEMBER SET is_simulated = FALSE WHERE household_id = %s",
        (data["householdId"],),
    )
    response = client.post("/dev/seed-demo", json={"reset": True})
    assert response.status_code == 409
    assert db.execute("SELECT COUNT(*) AS n FROM MEMBER").fetchone()["n"] == 2
