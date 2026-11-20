import json
from itertools import combinations

from app.core.exceptions import AppException
from app.repositories import dish_repository, menu_plan_repository
from app.services import consent_service, nutrition_service, rule_engine
from app.services.ownership import member

MEAL_TYPES = ("breakfast", "lunch", "dinner", "snack", "snack2", "snack3")
EFFORT = {"easy": 0, "medium": 1, "hard": 2}


def detail(db, session_id, plan_id):
    plan = menu_plan_repository.find_owned(db, plan_id, session_id)
    if not plan:
        raise AppException("NOT_FOUND", "Menu plan not found", 404)
    items = [
        {
            "mealType": row["meal_type"],
            "dishId": row["food_id"],
            "name": row["name"],
            "grams": float(row["portion_g"]),
            "nutrition": nutrition_service.portion(row, row["portion_g"]),
        }
        for row in menu_plan_repository.items(db, plan_id)
    ]
    return {
        "planId": plan_id,
        "memberId": plan["member_id"],
        "startDate": plan["start_date"],
        "days": plan["duration_days"],
        "status": plan["status"],
        "revision": plan["revision"],
        "meals": items,
        "dayTotals": nutrition_service.totals(items),
        "validation": json.loads(plan["validation_json"] or "{}"),
        "softScore": float(plan["soft_score"])
        if plan["soft_score"] is not None
        else None,
    }


def generate(db, session_id, payload):
    profile = member(db, session_id, payload.member_id)
    consent_service.require(
        db, session_id, profile["household_id"], "store_health_profile"
    )
    goal = profile.get("energy_target_kcal")
    if not goal:
        raise AppException("PROFILE_INCOMPLETE", "Energy goal is required", 422)
    candidates = [
        row
        for row in dish_repository.list_candidates(db)
        if row["food_id"] not in payload.exclude_dish_ids
        and row.get("default_portion_g") is not None
        and row.get("kcal_per_100g") is not None
        and (
            not payload.max_cooking_effort
            or (
                row.get("cooking_effort") in EFFORT
                and EFFORT[row["cooking_effort"]] <= EFFORT[payload.max_cooking_effort]
            )
        )
    ]
    safe = []
    reasons = []
    for row in candidates:
        result = rule_engine.evaluate(db, profile, [row])
        if result["hardConstraintsPassed"]:
            safe.append(row)
        else:
            reasons.extend(result["reasons"])
    if len(safe) < payload.meals_per_day:
        raise AppException(
            "CONSTRAINT_UNSATISFIABLE",
            "; ".join(sorted(set(reasons))[:5]) or "Too few verified dishes",
            409,
        )
    preferred = set(payload.prefer_dish_ids)
    safe.sort(key=lambda row: (row["food_id"] not in preferred, row["food_id"]))

    def score_choice(choice):
        energy = sum(
            float(row["kcal_per_100g"]) * float(row["default_portion_g"]) / 100
            for row in choice
        )
        energy_score = max(0.0, 1.0 - abs(energy - goal) / goal)
        preference_score = sum(row["food_id"] in preferred for row in choice) / len(
            choice
        )
        return round(0.8 * energy_score + 0.2 * preference_score, 3)

    selected = max(combinations(safe[:20], payload.meals_per_day), key=score_choice)
    # Recheck the complete plan before any write. Missing evidence fails closed.
    validation = rule_engine.evaluate(db, profile, selected)
    if not validation["hardConstraintsPassed"]:
        raise AppException(
            "HARD_CONSTRAINT_VIOLATION", "; ".join(validation["reasons"]), 409
        )
    score = score_choice(selected)
    plan_id = menu_plan_repository.create(
        db, payload.member_id, payload.start_date, json.dumps(validation), score
    )
    for index, row in enumerate(selected):
        menu_plan_repository.add_item(
            db, plan_id, row["food_id"], MEAL_TYPES[index], row["default_portion_g"]
        )
    return detail(db, session_id, plan_id)
