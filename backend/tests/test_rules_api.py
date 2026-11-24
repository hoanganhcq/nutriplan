from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.core.config import settings
from app.dependencies import get_db
from app.main import app
from app.repositories import rule_repository
from app.routers.rules import get_evaluation_db
from app.schemas.rules import RuleEvaluationInput
from app.services import rules_service


class DummyDB:
    pass


def test_list_rules_returns_paginated_result(monkeypatch):
    app.dependency_overrides[get_db] = lambda: DummyDB()
    received = []

    def list_rules(*args):
        received.append(args)
        return {
            "data": [],
            "meta": {"rulesetVersion": None, "nextCursor": None},
        }

    monkeypatch.setattr(
        rules_service,
        "list_rules",
        list_rules,
    )
    try:
        with TestClient(app) as client:
            response = client.get(
                "/rules?condition=HTN&nutrient=sodiumMg&scope=meal&limit=5"
            )
        assert response.status_code == 200
        assert response.json()["meta"]["nextCursor"] is None
        assert received[0][1:] == ("HTN", "sodiumMg", "meal", True, 5, 0)
    finally:
        app.dependency_overrides.clear()


def test_rule_detail_returns_not_found(monkeypatch):
    app.dependency_overrides[get_db] = lambda: DummyDB()

    def missing_rule(*args):
        from app.core.exceptions import AppException

        raise AppException("NOT_FOUND", "Rule not found", 404)

    monkeypatch.setattr(rules_service, "get_rule", missing_rule)
    try:
        with TestClient(app) as client:
            response = client.get("/rules/missing")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


def test_rule_detail_includes_source_and_change_log(monkeypatch):
    monkeypatch.setattr(
        "app.services.rules_service.rule_repository.find_rule",
        lambda _db, _rule_id: {
            "rule_id": "rule_htn_sodium_meal",
            "condition_name": "HTN",
            "nutrient": "sodium_mg",
            "scope": "meal",
            "operator": "lte",
            "threshold": Decimal("800"),
            "unit": "mg",
            "severity_when_violated": "YELLOW",
            "enabled": True,
            "version": "2026.11.1",
            "source_org": "Test organization",
            "source_title": "Test guidance",
            "source_year": "2026",
            "source_applicability": "Adults",
            "source_url": "https://example.test/guidance",
            "source_updated_at": date(2026, 11, 1),
            "rationale": "Test rationale",
            "change_log": '[{"version":"2026.11.1","change":"Initial"}]',
        },
    )
    result = rules_service.get_rule(None, "rule_htn_sodium_meal")["data"]
    assert result["threshold"] == 800
    assert result["nutrient"] == "sodiumMg"
    assert result["source"] == {
        "org": "Test organization",
        "title": "Test guidance",
        "year": "2026",
        "applicability": "Adults",
        "url": "https://example.test/guidance",
        "updatedAt": "2026-11-01",
    }
    assert result["changeLog"][0]["change"] == "Initial"


def test_evaluate_is_not_found_outside_dev_and_test(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    with TestClient(app) as client:
        response = client.post(
            "/rules/evaluate",
            json={
                "profile": {"conditions": ["HTN"]},
                "nutrition": {"sodiumMg": 1465},
                "dishIds": ["dish_ca_kho"],
            },
        )
    assert response.status_code == 404
    assert get_evaluation_db not in app.dependency_overrides


def test_evaluate_endpoint_returns_engine_result(monkeypatch):
    monkeypatch.setattr(settings, "environment", "test")
    app.dependency_overrides[get_evaluation_db] = lambda: DummyDB()
    monkeypatch.setattr(
        rules_service,
        "evaluate",
        lambda _db, _payload: {
            "data": {
                "level": "YELLOW",
                "firedRules": [],
                "rulesetVersion": "2026.11.1",
            }
        },
    )
    try:
        with TestClient(app) as client:
            response = client.post(
                "/rules/evaluate",
                json={
                    "profile": {"conditions": ["HTN"], "energyGoalKcal": 1800},
                    "nutrition": {"energyKcal": 275, "sodiumMg": 1465},
                    "dishIds": ["dish_ca_kho"],
                },
            )
        assert response.status_code == 200
        assert response.json()["data"]["rulesetVersion"] == "2026.11.1"
    finally:
        app.dependency_overrides.clear()


def test_evaluate_fires_only_matching_meal_rules(monkeypatch):
    monkeypatch.setattr(settings, "environment", "test")
    monkeypatch.setattr(
        "app.services.rules_service.rule_repository.enabled_rules",
        lambda _db: [
            {
                "rule_id": "rule_htn_sodium_meal",
                "condition_name": "HTN",
                "nutrient": "sodium_mg",
                "scope": "meal",
                "operator": "lte",
                "threshold": 800,
                "severity_when_violated": "YELLOW",
                "version": "2026.11.1",
            },
            {
                "rule_id": "rule_diabetes_sodium_day",
                "condition_name": "diabetes",
                "nutrient": "sodiumMg",
                "scope": "day",
                "operator": "lte",
                "threshold": 800,
                "severity_when_violated": "RED",
                "version": "2026.11.1",
            },
        ],
    )
    payload = RuleEvaluationInput.model_validate(
        {
            "profile": {"conditions": ["HTN"]},
            "nutrition": {"sodiumMg": 1465},
            "dishIds": ["dish_ca_kho"],
        }
    )
    result = rules_service.evaluate(None, payload)
    assert result["data"] == {
        "level": "YELLOW",
        "firedRules": [
            {
                "ruleId": "rule_htn_sodium_meal",
                "severity": "YELLOW",
                "value": 1465,
                "limit": 800.0,
            }
        ],
        "rulesetVersion": "2026.11.1",
    }


def test_evaluate_does_not_claim_green_without_applicable_rule(monkeypatch):
    monkeypatch.setattr(settings, "environment", "test")
    monkeypatch.setattr(
        "app.services.rules_service.rule_repository.enabled_rules", lambda _db: []
    )
    payload = RuleEvaluationInput.model_validate(
        {"profile": {"conditions": ["HTN"]}, "nutrition": {"sodiumMg": 100}}
    )
    result = rules_service.evaluate(None, payload)
    assert result["data"]["level"] == "INSUFFICIENT_DATA"


def test_openapi_includes_rule_endpoints():
    paths = app.openapi()["paths"]
    assert "/rules" in paths
    assert "/rules/{ruleId}" in paths
    assert "/rules/evaluate" in paths


def test_rule_repository_reads_normalized_rule_and_source_tables():
    class QueryDB:
        query = ""
        params = ()

        def execute(self, query, params=()):
            self.query = query
            self.params = params
            return self

        def fetchall(self):
            return []

    db = QueryDB()
    rule_repository.list_rules(
        db,
        {
            "condition": "HTN",
            "nutrient": "sodium_mg",
            "scope": "meal",
            "enabled": True,
        },
        3,
        0,
    )
    assert "FROM HEALTH_RULE h" in db.query
    assert "LEFT JOIN RULE_SOURCE s" in db.query
    assert db.params == ("HTN", "sodium_mg", "meal", True, 4, 0)
