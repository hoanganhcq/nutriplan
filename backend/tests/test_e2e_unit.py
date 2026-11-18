import asyncio
from io import BytesIO

import pytest
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import AppException
from app.schemas.e2e import MenuGenerateInput
from app.services import (
    meal_service,
    menu_plan_service,
    nutrition_service,
    ownership,
    rule_engine,
    vision_service,
)


def test_nutrition_propagates_unknown_values():
    food = {
        "kcal_per_100g": 120,
        "protein_per_100g": None,
        "carb_per_100g": 10,
        "fat_per_100g": 2,
    }
    item = {"nutrition": nutrition_service.portion(food, 50)}
    assert item["nutrition"]["kcal"] == 60
    assert nutrition_service.totals([item])["proteinG"] is None


def test_rule_engine_does_not_claim_safe_without_rules(monkeypatch):
    monkeypatch.setattr(
        "app.services.rule_engine.rule_repository.active_verified", lambda db: []
    )
    result = rule_engine.evaluate(
        None,
        {"allergies": "[]", "health_conditions": "[]"},
        [{"name": "Dish", "source_name": "Source", "kcal_per_100g": 100}],
    )
    assert result["level"] == "INSUFFICIENT_DATA"
    assert not result["hardConstraintsPassed"]


def test_rule_engine_rejects_verified_allergen(monkeypatch):
    monkeypatch.setattr(
        "app.services.rule_engine.rule_repository.active_verified",
        lambda db: [
            {"rule_type": "general", "subject": "nutrition", "ruleset_version": "v1"},
            {"rule_type": "allergy", "subject": "peanut", "ruleset_version": "v1"},
        ],
    )
    result = rule_engine.evaluate(
        None,
        {"allergies": '["peanut"]', "health_conditions": "[]"},
        [
            {
                "name": "Dish",
                "source_name": "Test source",
                "source_url": "https://example.test",
                "kcal_per_100g": 100,
                "protein_per_100g": 5,
                "carb_per_100g": 10,
                "fat_per_100g": 2,
                "allergen_verified": True,
                "allergen_codes": '["peanut"]',
            }
        ],
    )
    assert result["level"] == "RED"
    assert not result["hardConstraintsPassed"]


def test_rule_engine_never_clears_condition_without_evaluator(monkeypatch):
    monkeypatch.setattr(
        "app.services.rule_engine.rule_repository.active_verified",
        lambda db: [
            {"rule_type": "general", "subject": "nutrition", "ruleset_version": "v1"},
            {"rule_type": "condition", "subject": "diabetes", "ruleset_version": "v1"},
        ],
    )
    result = rule_engine.evaluate(
        None,
        {"allergies": "[]", "health_conditions": '["diabetes"]'},
        [
            {
                "name": "Dish",
                "source_name": "Test source",
                "source_url": "https://example.test",
                "kcal_per_100g": 100,
            }
        ],
    )
    assert result["level"] == "INSUFFICIENT_DATA"


def test_invalid_image_signature_rejected():
    image = UploadFile(
        file=BytesIO(b"not a png"),
        filename="bad.png",
        headers={"content-type": "image/png"},
    )
    with pytest.raises(AppException) as error:
        asyncio.run(meal_service.validate_images([image]))
    assert error.value.status_code == 415


def test_mock_vision_is_explicitly_labeled(monkeypatch):
    monkeypatch.setattr(settings, "environment", "test")
    monkeypatch.setattr(settings, "vision_provider", "mock")
    monkeypatch.setattr(
        settings, "vision_mock_detections", '[{"name":"Test dish","grams":100}]'
    )
    detections, warnings = vision_service.recognize([("image/png", b"bytes")])
    assert detections[0]["name"] == "Test dish"
    assert "mocked" in warnings[0]


def test_menu_with_no_verified_dishes_is_not_saved(monkeypatch):
    monkeypatch.setattr(
        "app.services.menu_plan_service.member",
        lambda *args: {
            "household_id": 1,
            "energy_target_kcal": 2000,
        },
    )
    monkeypatch.setattr(
        "app.services.menu_plan_service.consent_service.require", lambda *args: None
    )
    monkeypatch.setattr(
        "app.services.menu_plan_service.dish_repository.list_candidates", lambda db: []
    )
    writes = []
    monkeypatch.setattr(
        "app.services.menu_plan_service.menu_plan_repository.create",
        lambda *args: writes.append(args),
    )
    payload = MenuGenerateInput(memberId=2, startDate="2026-11-19")
    with pytest.raises(AppException) as error:
        menu_plan_service.generate(None, 1, payload)
    assert error.value.code == "CONSTRAINT_UNSATISFIABLE"
    assert writes == []


def test_external_vision_requires_consent_before_provider_call(monkeypatch):
    monkeypatch.setattr(settings, "vision_provider", "http")
    monkeypatch.setattr(
        "app.services.meal_service.consent_service.get", lambda *args: {}
    )

    def deny(*args):
        raise AppException("CONSENT_REQUIRED", "No image consent", 403)

    monkeypatch.setattr("app.services.meal_service.consent_service.require", deny)
    calls = []
    monkeypatch.setattr(
        "app.services.meal_service.vision_service.recognize",
        lambda images: calls.append(images),
    )
    with pytest.raises(AppException) as error:
        meal_service.analyze(
            None, 1, 2, [("image/png", b"bytes")], None, None, [], True
        )
    assert error.value.code == "CONSENT_REQUIRED"
    assert calls == []


def test_household_ownership_hides_other_sessions(monkeypatch):
    monkeypatch.setattr(
        "app.services.ownership.household_repository.find_owned",
        lambda db, household_id, session_id: None,
    )
    with pytest.raises(AppException) as error:
        ownership.household(None, 9, 3)
    assert error.value.status_code == 404
