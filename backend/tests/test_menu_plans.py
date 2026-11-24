import json
from datetime import date

import pytest

from app.main import app
from app.schemas.e2e import MenuGenerateInput, MenuRegenerateInput
from app.services import menu_plan_service


def test_menu_generate_accepts_one_to_three_days_and_explicit_meals():
    payload = MenuGenerateInput(
        memberId=3,
        days=3,
        startDate="2026-11-19",
        mealsPerDay=["breakfast", "lunch", "dinner"],
        seed=17,
    )
    assert payload.days == 3
    assert payload.meal_types == ["breakfast", "lunch", "dinner"]
    assert payload.seed == 17


def test_regenerate_requires_scope_arguments():
    with pytest.raises(ValueError):
        MenuRegenerateInput(scope="meal")
    payload = MenuRegenerateInput(scope="meal", date="2026-11-19", mealType="dinner")
    assert payload.date == date(2026, 11, 19)


def test_day_validation_enforces_enabled_sourced_health_rules(monkeypatch):
    monkeypatch.setattr(
        "app.services.menu_plan_service.rule_engine.evaluate",
        lambda *_args: {
            "hardConstraintsPassed": True,
            "reasons": [],
            "rulesetVersion": "legacy-v1",
        },
    )
    profile = {"health_conditions": json.dumps(["hypertension"]), "allergies": "[]"}
    dish = {
        "menu_item_id": 1,
        "food_id": 9,
        "meal_type": "dinner",
        "portion_g": 100,
        "kcal_per_100g": 120,
        "protein_per_100g": 5,
        "carb_per_100g": 15,
        "fat_per_100g": 4,
        "sodium_mg_per_100g": 1465,
    }
    rules = [
        {
            "rule_id": "rule_htn_sodium_meal",
            "condition_name": "HTN",
            "nutrient": "sodium_mg",
            "scope": "meal",
            "operator": "lte",
            "threshold": 800,
            "unit": "mg",
            "version": "2026.11.1",
            "source_org": "Health organization",
            "source_title": "Sourced guidance",
            "source_year": 2026,
            "source_applicability": "Adults",
            "source_updated_at": date(2026, 11, 1),
        }
    ]

    violations, version = menu_plan_service._validate_day(
        None, profile, [dish], date(2026, 11, 19), rules
    )
    assert version == "2026.11.1"
    assert violations[0]["ruleId"] == "rule_htn_sodium_meal"
    assert violations[0]["type"] == "health_rule"


def test_menu_pdf_export_is_a_pdf():
    content = menu_plan_service._pdf_export(
        ["NutriPlan", "Menu for 2026-11-19"], "large"
    )
    assert content.startswith(b"%PDF-1.4")
    assert content.endswith(b"%%EOF\n")


def test_openapi_exposes_menu_plan_workflow():
    paths = app.openapi()["paths"]
    expected = {
        "/menu-plans": {"get"},
        "/menu-plans/generate": {"post"},
        "/menu-plans/{planId}": {"get", "delete"},
        "/menu-plans/{planId}/items/{itemId}/alternatives": {"get"},
        "/menu-plans/{planId}/items/{itemId}": {"patch"},
        "/menu-plans/{planId}/items/{itemId}/lock": {"put"},
        "/menu-plans/{planId}/regenerate": {"post"},
        "/menu-plans/{planId}/undo": {"post"},
        "/menu-plans/{planId}/validate": {"post"},
        "/menu-plans/{planId}/export": {"get"},
    }
    for path, methods in expected.items():
        assert methods <= paths[path].keys()
