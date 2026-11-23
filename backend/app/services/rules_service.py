import json

from app.core.config import settings
from app.core.exceptions import AppException
from app.repositories import rule_repository

NUTRIENT_WIRE_NAMES = {
    "kcal": "energyKcal",
    "sodium_mg": "sodiumMg",
    "potassium_mg": "potassiumMg",
    "phosphorus_mg": "phosphorusMg",
    "sugar_g": "sugarG",
    "fiber_g": "fiberG",
}
NUTRIENT_DATABASE_NAMES = {
    wire_name: database_name
    for database_name, wire_name in NUTRIENT_WIRE_NAMES.items()
}


def _number(value):
    return float(value) if value is not None else None


def _year(value):
    return str(value) if value is not None else None


def _timestamp(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


def _serialize_rule(row, include_details=False):
    result = {
        "ruleId": row["rule_id"],
        "condition": row["condition_name"],
        "nutrient": NUTRIENT_WIRE_NAMES.get(row["nutrient"], row["nutrient"]),
        "scope": row["scope"],
        "operator": row["operator"],
        "threshold": _number(row["threshold"]),
        "unit": row["unit"],
        "severityWhenViolated": row["severity_when_violated"],
        "enabled": bool(row["enabled"]),
        "version": row["version"],
        "source": {
            "org": row["source_org"],
            "title": row["source_title"],
            "year": _year(row["source_year"]),
            "applicability": row["source_applicability"],
            "url": row["source_url"],
            "updatedAt": _timestamp(row["source_updated_at"]),
        },
        "rationale": row["rationale"],
    }
    if include_details:
        change_log = row["change_log"]
        if change_log is None:
            result["changeLog"] = []
        elif isinstance(change_log, str):
            result["changeLog"] = json.loads(change_log)
        else:
            result["changeLog"] = change_log
    return result


def list_rules(db, condition, nutrient, scope, enabled, limit, cursor):
    rows, next_cursor = rule_repository.list_rules(
        db,
        {
            "condition": condition,
            "nutrient": NUTRIENT_DATABASE_NAMES.get(nutrient, nutrient),
            "scope": scope,
            "enabled": enabled,
        },
        limit,
        cursor,
    )
    versions = [row["version"] for row in rows]
    return {
        "data": [_serialize_rule(row) for row in rows],
        "meta": {
            "rulesetVersion": max(versions) if versions else None,
            "nextCursor": next_cursor,
        },
    }


def get_rule(db, rule_id):
    row = rule_repository.find_rule(db, rule_id)
    if not row:
        raise AppException("NOT_FOUND", "Rule not found", 404)
    return {"data": _serialize_rule(row, include_details=True)}


def _violated(operator, value, threshold):
    comparisons = {
        "lt": value >= threshold,
        "lte": value > threshold,
        "gt": value <= threshold,
        "gte": value < threshold,
        "eq": value != threshold,
    }
    if operator not in comparisons:
        raise ValueError(f"Unsupported rule operator: {operator}")
    return comparisons[operator]


def evaluate(db, payload):
    if settings.environment not in {"development", "test"}:
        raise AppException("NOT_FOUND", "Not found", 404)

    rules = rule_repository.enabled_rules(db)
    conditions = set(payload.profile.conditions)
    fired_rules = []
    applicable_count = 0
    levels = {"GREEN": 0, "YELLOW": 1, "ORANGE": 2, "RED": 3}
    for rule in rules:
        condition = rule["condition_name"]
        if (
            rule["scope"] != "meal"
            or (condition and condition != "general" and condition not in conditions)
            or NUTRIENT_WIRE_NAMES.get(rule["nutrient"], rule["nutrient"])
            not in payload.nutrition
        ):
            continue
        applicable_count += 1
        nutrient = NUTRIENT_WIRE_NAMES.get(rule["nutrient"], rule["nutrient"])
        value = payload.nutrition[nutrient]
        threshold = float(rule["threshold"])
        severity = rule["severity_when_violated"]
        if severity not in levels:
            raise ValueError(f"Unsupported rule severity: {severity}")
        if _violated(rule["operator"], value, threshold):
            fired_rules.append(
                {
                    "ruleId": rule["rule_id"],
                    "severity": severity,
                    "value": value,
                    "limit": threshold,
                }
            )

    version_set = {rule["version"] for rule in rules}
    if len(version_set) > 1:
        raise ValueError("Enabled rules must use a single ruleset version")
    level = (
        max((rule["severity"] for rule in fired_rules), key=levels.get)
        if fired_rules
        else "GREEN" if applicable_count else "INSUFFICIENT_DATA"
    )
    return {
        "data": {
            "level": level,
            "firedRules": fired_rules,
            "rulesetVersion": next(iter(version_set), None),
        }
    }
