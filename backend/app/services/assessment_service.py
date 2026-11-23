import json

from app.core.exceptions import AppException
from app.repositories import assessment_repository, meal_repository, member_repository
from app.services import meal_service, rule_engine
from app.services.ownership import member


def _output(db, session_id, meal, assessment):
    profile = member(db, session_id, assessment["member_id"])
    reasons = json.loads(assessment.get("reasons") or "[]")
    return {
        "assessmentId": assessment["assessment_id"],
        "memberId": assessment["member_id"],
        "mealRevision": assessment["meal_revision"],
        "profileVersion": assessment["profile_version"],
        "level": assessment["suitability_level"],
        "reasons": reasons,
        "rulesetVersion": assessment.get("ruleset_version"),
        "hardConstraintsPassed": assessment["suitability_level"] not in {
            "RED",
            "INSUFFICIENT_DATA",
        },
        "keyMetrics": meal_service.detail(db, session_id, meal["meal_id"])["totals"],
        "alternatives": [],
        "stale": (
            assessment["meal_revision"] != meal["revision"]
            or assessment["profile_version"] != profile.get("profile_version", 1)
        ),
    }


def assess(db, session_id, meal_id, member_ids=None):
    meal = meal_service.owned(db, session_id, meal_id, lock=True)
    if meal["status"] != "draft":
        raise AppException("MEAL_LOCKED", "Confirmed meal cannot be reassessed", 409)
    selected_ids = list(dict.fromkeys(member_ids or []))
    if not selected_ids:
        selected_ids = meal_repository.member_ids(db, meal_id)
    if not selected_ids:
        selected_ids = [
            row["member_id"]
            for row in member_repository.list_by_household(db, meal["household_id"])
        ]
    if not selected_ids:
        raise AppException(
            "PROFILE_INCOMPLETE", "No household members are available", 422
        )

    foods = meal_repository.items(db, meal_id)
    results = []
    for member_id in selected_ids:
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
        saved = assessment_repository.find_for_meal_member(db, meal_id, member_id)
        results.append(_output(db, session_id, meal, saved))
    return {
        "mealId": meal_id,
        "assessments": results,
        "warnings": json.loads(meal.get("warnings") or "[]"),
    }


def get_assessments(db, session_id, meal_id, member_id=None):
    meal = meal_service.owned(db, session_id, meal_id)
    if member_id is not None:
        profile = member(db, session_id, member_id)
        if profile["household_id"] != meal["household_id"]:
            raise AppException("NOT_FOUND", "Member not found", 404)
    rows = assessment_repository.list_for_meal(db, meal_id)
    if member_id is not None:
        rows = [row for row in rows if row["member_id"] == member_id]
    return {
        "mealId": meal_id,
        "assessments": [_output(db, session_id, meal, row) for row in rows],
        "warnings": json.loads(meal.get("warnings") or "[]"),
    }


def confirm(db, session_id, meal_id, eaten_by=None, note=None):
    meal = meal_service.owned(db, session_id, meal_id, lock=True)
    if meal["status"] != "draft":
        raise AppException("MEAL_LOCKED", "Meal already confirmed", 409)
    saved = {
        row["member_id"]: row
        for row in assessment_repository.list_for_meal(db, meal_id)
    }
    member_ids = list(
        dict.fromkeys(
            eaten_by
            if eaten_by is not None
            else (
                meal_repository.member_ids(db, meal_id)
                or list(saved)
            )
        )
    )
    if not member_ids:
        raise AppException(
            "PROFILE_INCOMPLETE", "Add at least one member before confirming", 422
        )
    for member_id in member_ids:
        profile = member(db, session_id, member_id)
        if profile["household_id"] != meal["household_id"]:
            raise AppException("NOT_FOUND", "Member not found", 404)
        result = saved.get(member_id)
        current = rule_engine.evaluate(db, profile, meal_repository.items(db, meal_id))
        if (
            not result
            or result["meal_revision"] != meal["revision"]
            or result["profile_version"] != profile.get("profile_version", 1)
            or current["level"] != result["suitability_level"]
            or current["rulesetVersion"] != result["ruleset_version"]
        ):
            assessment_repository.save(
                db,
                meal_id,
                member_id,
                current,
                meal["revision"],
                profile.get("profile_version", 1),
            )
            result = assessment_repository.find_for_meal_member(db, meal_id, member_id)
            saved[member_id] = result
        if result["suitability_level"] == "INSUFFICIENT_DATA":
            raise AppException(
                "HARD_CONSTRAINT_VIOLATION", "Assessment lacks verified evidence", 409
            )
    meal_repository.set_member_ids(db, meal_id, member_ids)
    confirmed_at = meal_repository.set_confirmation(db, meal_id, note)
    return {
        "mealId": meal_id,
        "status": "confirmed",
        "confirmedAt": confirmed_at,
        "journalEntries": [
            {
                "memberId": member_id,
                "level": saved[member_id]["suitability_level"],
            }
            for member_id in member_ids
        ],
    }


def explain(db, session_id, assessment_id, max_words):
    assessment = assessment_repository.find_owned(db, assessment_id, session_id)
    if not assessment:
        raise AppException("NOT_FOUND", "Assessment not found", 404)
    level = assessment["suitability_level"]
    explanation = {
        "RED": (
            "Đánh giá ghi nhận vi phạm ràng buộc cứng đã xác minh. "
            "Hãy xem lý do chi tiết và cân nhắc món thay thế."
        ),
        "YELLOW": (
            "Bữa ăn cần lưu ý theo các quy tắc dinh dưỡng đã xác minh. "
            "Hãy xem chỉ số và lý do chi tiết."
        ),
        "GREEN": "Đánh giá hiện không ghi nhận vi phạm ràng buộc cứng đã xác minh.",
        "INSUFFICIENT_DATA": (
            "Chưa đủ dữ liệu hoặc bằng chứng đã xác minh để đưa ra "
            "đánh giá đáng tin cậy."
        ),
    }.get(level, "Chưa có nội dung giải thích cho đánh giá này.")
    explanation = " ".join(explanation.split()[:max_words])
    return {
        "assessmentId": assessment_id,
        "generatedBy": "template",
        "explanation": explanation,
        "disclaimer": "Thông tin hỗ trợ, không thay thế tư vấn của bác sĩ.",
    }
