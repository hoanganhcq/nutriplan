"""Exercise the browser's meal flow against MySQL with rollback per test."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.dependencies import get_db
from app.main import app

pytestmark = pytest.mark.integration


def test_upload_review_assess_and_keep_unverified_meal_as_draft(monkeypatch):
    monkeypatch.setattr(settings, "vision_mock_detections", "[]")
    # The integration fixture supplies one transaction for all API calls.
    db = next(app.dependency_overrides[get_db]())
    dish_id = db.execute(
        """INSERT INTO FOOD_ITEM
           (name, category, kcal_per_100g, protein_per_100g,
            carb_per_100g, fat_per_100g, source_name, source_url)
           VALUES (%s, 'dish', 100, 4, 20, 1, 'Test source', 'https://example.test')""",
        ("PR meal flow test dish",),
    ).lastrowid

    with TestClient(app) as client:
        session = client.post("/sessions")
        assert session.status_code == 201
        headers = {"Authorization": f"Bearer {session.json()['token']}"}
        household = client.post(
            "/households", headers=headers, json={"name": "PR test household"}
        )
        assert household.status_code == 201
        household_id = household.json()["household_id"]
        consent = client.put(
            "/consents",
            headers=headers,
            json={
                "householdId": household_id,
                "policyVersion": "0.1",
                "consents": {"store_health_profile": True},
            },
        )
        assert consent.status_code == 200
        member = client.post(
            "/members",
            headers=headers,
            json={"householdId": household_id, "name": "PR test member", "age": 30},
        )
        assert member.status_code == 201
        member_id = member.json()["data"]["memberId"]

        uploaded = client.post(
            "/meals/analyze",
            headers=headers,
            data={"householdId": str(household_id), "memberIds": f"[{member_id}]"},
            files={"images": ("meal.png", b"\x89PNG\r\n\x1a\nmock", "image/png")},
        )
        assert uploaded.status_code == 201, uploaded.text
        meal_id = uploaded.json()["data"]["mealId"]
        assert uploaded.json()["data"]["status"] == "draft"

        added = client.post(
            f"/meals/{meal_id}/items",
            headers=headers,
            json={"dishId": dish_id, "grams": 125, "confirmWeight": True},
        )
        assert added.status_code == 201, added.text
        assert added.json()["data"]["items"][0]["isEstimate"] is False
        assessed = client.post(
            f"/meals/{meal_id}/assessments",
            headers=headers,
            json={"memberIds": [member_id]},
        )
        assert assessed.status_code == 200, assessed.text
        assert assessed.json()["data"]["assessments"][0]["level"] == "INSUFFICIENT_DATA"
        confirmed = client.post(
            f"/meals/{meal_id}/confirm",
            headers=headers,
            json={"eatenBy": [member_id]},
        )
        assert confirmed.status_code == 409
        journal = client.get("/meals?status=all", headers=headers)
        assert journal.status_code == 200
        assert any(
            row["mealId"] == meal_id and row["status"] == "draft"
            for row in journal.json()["data"]
        )
