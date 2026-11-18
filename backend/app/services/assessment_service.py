from app.core.exceptions import AppException
from app.repositories import assessment_repository, meal_repository
from app.services import meal_service, rule_engine
from app.services.ownership import member


def assess(db, session_id, meal_id, member_ids):
    meal = meal_service.owned(db, session_id, meal_id, lock=True)
    if meal["status"] != "draft":
        raise AppException("MEAL_LOCKED", "Confirmed meal cannot be reassessed", 409)
    foods = meal_repository.items(db, meal_id)
    results = []
    for member_id in set(member_ids):
        profile = member(db, session_id, member_id)
        if profile["household_id"] != meal["household_id"]:
            raise AppException("NOT_FOUND", "Member not found", 404)
        result = rule_engine.evaluate(db, profile, foods)
        assessment_repository.save(
            db,
            meal_id,
            member_id,
            result,
            meal["revision"],
            profile.get("profile_version", 1),
        )
        results.append(
            {
                "memberId": member_id,
                "mealRevision": meal["revision"],
                "profileVersion": profile.get("profile_version", 1),
                **result,
                "keyMetrics": meal_service.detail(db, session_id, meal_id)["totals"],
                "alternatives": [],
            }
        )
    return results


def confirm(db, session_id, meal_id):
    meal = meal_service.owned(db, session_id, meal_id, lock=True)
    if meal["status"] != "draft":
        raise AppException("CONFLICT", "Meal already confirmed", 409)
    member_ids = meal_repository.member_ids(db, meal_id)
    if not member_ids:
        raise AppException(
            "PROFILE_INCOMPLETE", "Add at least one member before confirming", 422
        )
    saved = {
        row["member_id"]: row
        for row in assessment_repository.list_for_meal(db, meal_id)
    }
    for member_id in member_ids:
        profile = member(db, session_id, member_id)
        result = saved.get(member_id)
        if (
            not result
            or result["meal_revision"] != meal["revision"]
            or result["profile_version"] != profile.get("profile_version", 1)
        ):
            raise AppException("CONFLICT", "Assessment is missing or stale", 409)
        if result["suitability_level"] == "INSUFFICIENT_DATA":
            raise AppException(
                "HARD_CONSTRAINT_VIOLATION", "Assessment lacks verified evidence", 409
            )
        current = rule_engine.evaluate(db, profile, meal_repository.items(db, meal_id))
        if (
            current["level"] != result["suitability_level"]
            or current["rulesetVersion"] != result["ruleset_version"]
        ):
            raise AppException("CONFLICT", "Assessment rules changed", 409)
    db.execute("UPDATE MEAL SET status = 'confirmed' WHERE meal_id = %s", (meal_id,))
    return meal_service.detail(db, session_id, meal_id)
