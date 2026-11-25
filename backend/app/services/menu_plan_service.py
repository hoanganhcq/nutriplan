import html
import json
import random
import time
import unicodedata
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from app.core.exceptions import AppException
from app.repositories import dish_repository, menu_plan_repository, rule_repository
from app.services import consent_service, rule_engine
from app.services.ownership import member

MEAL_TYPES = ("breakfast", "lunch", "dinner", "snack", "snack2", "snack3")
EFFORT = {"easy": 1.0, "medium": 0.7, "hard": 0.4}
NUTRIENTS = {
    "energyKcal": "kcal_per_100g",
    "proteinG": "protein_per_100g",
    "carbG": "carb_per_100g",
    "fatG": "fat_per_100g",
    "sugarG": "sugar_per_100g",
    "fiberG": "fiber_per_100g",
    "sodiumMg": "sodium_mg_per_100g",
    "potassiumMg": "potassium_mg_per_100g",
    "phosphorusMg": "phosphorus_mg_per_100g",
}
RULE_NUTRIENTS = {
    "kcal": "energyKcal",
    "energyKcal": "energyKcal",
    "sodium_mg": "sodiumMg",
    "sodiumMg": "sodiumMg",
    "potassium_mg": "potassiumMg",
    "potassiumMg": "potassiumMg",
    "phosphorus_mg": "phosphorusMg",
    "phosphorusMg": "phosphorusMg",
    "protein_g": "proteinG",
    "proteinG": "proteinG",
    "carb_g": "carbG",
    "carbG": "carbG",
    "fat_g": "fatG",
    "fatG": "fatG",
    "sugar_g": "sugarG",
    "sugarG": "sugarG",
    "fiber_g": "fiberG",
    "fiberG": "fiberG",
}
CONDITION_CODES = {
    "diabetes": {"diabetes", "t2d"},
    "hypertension": {"hypertension", "htn"},
    "kidney_disease": {"kidney_disease", "ckd"},
}
MAX_SEARCH_NODES = 8000


def _json_list(value):
    if isinstance(value, str):
        try:
            value = json.loads(value or "[]")
        except ValueError:
            return None
    return value if isinstance(value, list) else None


def _as_float(value):
    return float(value) if value is not None else None


def _iso(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


def _item_nutrition(item):
    grams = _as_float(item.get("portion_g"))
    result = {}
    for output, column in NUTRIENTS.items():
        amount = item.get(column)
        result[output] = (
            round(float(amount) * grams / 100, 2)
            if amount is not None and grams is not None
            else None
        )
    return result


def _nutrition_totals(items):
    if not items:
        return {key: None for key in NUTRIENTS}
    nutrients = [_item_nutrition(item) for item in items]
    return {
        key: (
            round(sum(row[key] for row in nutrients), 2)
            if all(row[key] is not None for row in nutrients)
            else None
        )
        for key in NUTRIENTS
    }


def _violated(operator, value, threshold):
    checks = {
        "lt": value >= threshold,
        "lte": value > threshold,
        "gt": value <= threshold,
        "gte": value < threshold,
        "eq": value != threshold,
    }
    if operator not in checks:
        raise ValueError(f"Unsupported menu rule operator: {operator}")
    return checks[operator]


def _condition_codes(profile):
    conditions = _json_list(profile.get("health_conditions"))
    if conditions is None:
        return None, set()
    codes = set()
    for condition in conditions:
        if condition == "none":
            continue
        codes.update(CONDITION_CODES.get(condition, {condition.casefold()}))
    return conditions, codes


def _rule_contexts(rule, items):
    scope = rule["scope"]
    if scope == "dish":
        return [[item] for item in items]
    if scope == "day":
        return [items]
    if scope == "meal":
        groups = defaultdict(list)
        for item in items:
            groups[item["meal_type"]].append(item)
        return [groups[key] for key in sorted(groups)]
    raise ValueError(f"Unsupported menu rule scope: {scope}")


def _base_profile(profile):
    clean = dict(profile)
    clean["health_conditions"] = "[]"
    return clean


def _validate_day(db, profile, items, day_date, enabled_rules=None):
    violations = []
    if not items:
        return [
            {
                "date": day_date.isoformat(),
                "type": "coverage",
                "ruleId": None,
                "message": "The day has no meals to validate.",
            }
        ], None

    baseline = rule_engine.evaluate(db, _base_profile(profile), items)
    if not baseline["hardConstraintsPassed"]:
        violations.extend(
            {
                "date": day_date.isoformat(),
                "mealType": item.get("meal_type"),
                "itemId": item.get("menu_item_id"),
                "type": "coverage",
                "ruleId": None,
                "message": reason,
            }
            for item in items
            for reason in baseline["reasons"]
        )

    conditions, codes = _condition_codes(profile)
    if conditions is None:
        violations.append(
            {
                "date": day_date.isoformat(),
                "type": "profile",
                "ruleId": None,
                "message": "The member condition profile is invalid.",
            }
        )
        return violations, None

    rules = (
        enabled_rules
        if enabled_rules is not None
        else rule_repository.enabled_rules(db)
    )
    applicable = [
        rule
        for rule in rules
        if rule["condition_name"].casefold() == "general"
        or rule["condition_name"].casefold() in codes
    ]
    for condition in conditions:
        if condition != "none" and not any(
            rule["condition_name"].casefold()
            in CONDITION_CODES.get(condition, {condition.casefold()})
            for rule in rules
        ):
            violations.append(
                {
                    "date": day_date.isoformat(),
                    "type": "rule_coverage",
                    "ruleId": None,
                    "message": f"No enabled health rule covers condition {condition}.",
                }
            )

    versions = set()
    for rule in applicable:
        versions.add(rule["version"])
        if not all(
            rule.get(key)
            for key in (
                "source_org",
                "source_title",
                "source_year",
                "source_applicability",
                "source_updated_at",
            )
        ):
            violations.append(
                {
                    "date": day_date.isoformat(),
                    "type": "rule_source",
                    "ruleId": rule["rule_id"],
                    "message": "An enabled health rule has incomplete source details.",
                }
            )
            continue
        nutrient = RULE_NUTRIENTS.get(rule["nutrient"], rule["nutrient"])
        for context in _rule_contexts(rule, items):
            totals = _nutrition_totals(context)
            value = totals.get(nutrient)
            if value is None:
                violations.append(
                    {
                        "date": day_date.isoformat(),
                        "mealType": context[0].get("meal_type"),
                        "itemId": context[0].get("menu_item_id"),
                        "type": "nutrition_data",
                        "ruleId": rule["rule_id"],
                        "message": f"Nutrition data for {rule['nutrient']} is missing.",
                    }
                )
                continue
            threshold = float(rule["threshold"])
            if _violated(rule["operator"], value, threshold):
                violations.append(
                    {
                        "date": day_date.isoformat(),
                        "mealType": context[0].get("meal_type"),
                        "itemId": context[0].get("menu_item_id"),
                        "type": "health_rule",
                        "ruleId": rule["rule_id"],
                        "message": (
                            f"{rule['nutrient']} violates the {rule['operator']} "
                            f"limit {threshold:g} {rule['unit']}."
                        ),
                    }
                )
    if len(versions) > 1:
        violations.append(
            {
                "date": day_date.isoformat(),
                "type": "ruleset",
                "ruleId": None,
                "message": "Enabled health rules have different versions.",
            }
        )
    return violations, next(iter(versions), baseline.get("rulesetVersion"))


def _validate_plan(db, profile, items, start_date, days, enabled_rules=None):
    violations = []
    versions = set()
    for day_index in range(1, days + 1):
        day_date = start_date + timedelta(days=day_index - 1)
        day_items = [item for item in items if item["day_index"] == day_index]
        day_violations, version = _validate_day(
            db, profile, day_items, day_date, enabled_rules
        )
        violations.extend(day_violations)
        if version:
            versions.add(version)
    if len(versions) > 1:
        violations.append(
            {
                "date": start_date.isoformat(),
                "type": "ruleset",
                "ruleId": None,
                "message": "Enabled health rules have different versions.",
            }
        )
    return {
        "hardConstraintsPassed": not violations,
        "violations": violations,
        "rulesetVersion": next(iter(versions), None),
        "profileVersion": profile.get("profile_version", 1),
    }


def _item_output(item):
    return {
        "itemId": item["menu_item_id"],
        "dishId": item["food_id"],
        "name": item["name"],
        "grams": _as_float(item["portion_g"]),
        "locked": bool(item.get("locked")),
        "reason": "Selected from sourced nutrition data and passed hard constraints.",
        "nutrition": _item_nutrition(item),
    }


def _soft_score(items, goal, preferred_ids, max_effort):
    count = len(items)
    if not count:
        return {
            "total": 0.0,
            "calorieFit": 0.0,
            "variety": 0.0,
            "foodGroupBalance": 0.0,
            "preference": 0.0,
            "ease": 0.0,
        }
    totals = _nutrition_totals(items)
    energy = totals["energyKcal"]
    calorie_fit = (
        max(0.0, 1 - abs(energy - goal) / goal) if energy is not None and goal else 0.0
    )
    variety = len({item["food_id"] for item in items}) / count
    categories = [item.get("category") for item in items if item.get("category")]
    balance = min(1.0, len(set(categories)) / min(count, 4)) if categories else 0.0
    preference = (
        sum(item["food_id"] in preferred_ids for item in items) / count
        if preferred_ids
        else 1.0
    )
    effort_scores = [EFFORT.get(item.get("cooking_effort"), 0.0) for item in items]
    ease = sum(effort_scores) / count
    if max_effort:
        ease = min(ease, EFFORT[max_effort])
    total = (
        0.4 * calorie_fit
        + 0.2 * variety
        + 0.15 * balance
        + 0.15 * preference
        + 0.1 * ease
    )
    return {
        "total": round(total, 2),
        "calorieFit": round(calorie_fit, 2),
        "variety": round(variety, 2),
        "foodGroupBalance": round(balance, 2),
        "preference": round(preference, 2),
        "ease": round(ease, 2),
    }


def _day_response(plan, day_index, items, goal):
    day_date = plan["start_date"] + timedelta(days=day_index - 1)
    groups = defaultdict(list)
    for item in items:
        if item["day_index"] == day_index:
            groups[item["meal_type"]].append(_item_output(item))
    meals = [
        {"mealType": meal_type, "items": groups[meal_type]}
        for meal_type in MEAL_TYPES
        if groups[meal_type]
    ]
    totals = _nutrition_totals(
        [item for item in items if item["day_index"] == day_index]
    )
    return {
        "date": day_date.isoformat(),
        "meals": meals,
        "dayTotals": totals,
        "goalDiff": {
            "energyKcal": (
                round(totals["energyKcal"] - goal, 2)
                if totals["energyKcal"] is not None and goal
                else None
            )
        },
    }


def _can_undo(db, plan_id, revision):
    return revision > 1 and bool(
        menu_plan_repository.get_revision(db, plan_id, revision - 1)
    )


def detail(db, session_id, plan_id):
    plan = menu_plan_repository.find_owned(db, plan_id, session_id)
    if not plan:
        raise AppException("NOT_FOUND", "Menu plan not found", 404)
    items = menu_plan_repository.items(db, plan_id)
    goal = plan.get("energy_target_kcal")
    if goal is None:
        profile = member(db, session_id, plan["member_id"])
        goal = profile.get("energy_target_kcal")
    validation = json.loads(plan.get("validation_json") or "{}")
    score = (
        json.loads(plan["soft_score_json"])
        if plan.get("soft_score_json")
        else {"total": _as_float(plan.get("soft_score"))}
    )
    start_date = plan["start_date"]
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    days = plan["duration_days"]
    return {
        "planId": plan_id,
        "memberId": plan["member_id"],
        "startDate": start_date.isoformat(),
        "revision": plan["revision"],
        "canUndo": _can_undo(db, plan_id, plan["revision"]),
        "days": [
            _day_response(plan | {"start_date": start_date}, day, items, goal)
            for day in range(1, days + 1)
        ],
        "validation": validation,
        "softScore": score,
    }


def _candidate_pool(db, profile, excluded, max_effort):
    candidates = []
    rejected = []
    baseline_profile = _base_profile(profile)
    for row in dish_repository.list_candidates(db):
        if row["food_id"] in excluded:
            continue
        if row.get("entity_type", "DISH") != "DISH":
            continue
        portion = row.get("default_portion_g")
        if portion is None or any(
            row.get(key) is None
            for key in (
                "kcal_per_100g",
                "protein_per_100g",
                "carb_per_100g",
                "fat_per_100g",
            )
        ):
            rejected.append(f"{row['name']}: incomplete nutrition or portion data")
            continue
        if max_effort and (
            row.get("cooking_effort") not in EFFORT
            or EFFORT[row["cooking_effort"]] < EFFORT[max_effort]
        ):
            rejected.append(f"{row['name']}: cooking effort is not verified")
            continue
        result = rule_engine.evaluate(db, baseline_profile, [row])
        if not result["hardConstraintsPassed"]:
            rejected.extend(result["reasons"])
            continue
        candidates.append(row)
    return candidates, sorted(set(rejected))


def _search_day(
    db,
    profile,
    day_date,
    day_index,
    meal_types,
    candidates,
    fixed_items,
    used_dishes,
    preferred_ids,
    goal,
    enabled_rules,
    rng,
):
    shuffled_candidates = rng.sample(candidates, len(candidates))
    rank = {row["food_id"]: index for index, row in enumerate(shuffled_candidates)}
    chosen = []
    last_violations = []
    nodes = [0]
    meal_target = goal / max(1, len(meal_types))

    def search(slot):
        nodes[0] += 1
        if nodes[0] > MAX_SEARCH_NODES:
            return None
        if slot == len(meal_types):
            trial = fixed_items + chosen
            violations, _ = _validate_day(db, profile, trial, day_date, enabled_rules)
            if not violations:
                return list(chosen)
            last_violations.extend(violations)
            return None

        current_energy = sum(
            _as_float(row.get("kcal_per_100g")) * float(row["portion_g"]) / 100
            for row in fixed_items + chosen
        )

        def candidate_order(row):
            portion = float(row["default_portion_g"])
            kcal = float(row["kcal_per_100g"]) * portion / 100
            return (
                row["food_id"] not in preferred_ids,
                row["food_id"] in used_dishes,
                row["food_id"] in {item["food_id"] for item in chosen},
                abs(current_energy + kcal - meal_target * (slot + 1)),
                rank[row["food_id"]],
            )

        for row in sorted(candidates, key=candidate_order):
            chosen.append(
                {
                    **row,
                    "food_id": row["food_id"],
                    "portion_g": row["default_portion_g"],
                    "meal_type": meal_types[slot],
                    "day_index": day_index,
                    "locked": False,
                }
            )
            result = search(slot + 1)
            if result is not None:
                return result
            chosen.pop()
        return None

    result = search(0)
    return result, last_violations


def _validation_for_items(db, profile, items, plan):
    start_date = plan["start_date"]
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    rules = rule_repository.enabled_rules(db)
    return _validate_plan(db, profile, items, start_date, plan["duration_days"], rules)


def _generation_options(payload):
    return {
        "mealTypes": payload.meal_types,
        "preferDishIds": payload.prefer_dish_ids,
        "excludeDishIds": payload.exclude_dish_ids,
        "maxCookingEffort": payload.max_cooking_effort,
        "seed": payload.seed,
    }


def generate(db, session_id, payload):
    started = time.perf_counter()
    profile = member(db, session_id, payload.member_id)
    consent_service.require(
        db, session_id, profile["household_id"], "store_health_profile"
    )
    goal = profile.get("energy_target_kcal")
    if not goal:
        raise AppException("PROFILE_INCOMPLETE", "Energy goal is required", 422)

    candidates, rejected = _candidate_pool(
        db,
        profile,
        set(payload.exclude_dish_ids),
        payload.max_cooking_effort,
    )
    if not candidates:
        raise AppException(
            "CONSTRAINT_UNSATISFIABLE",
            "No dish satisfies the available hard constraints and data requirements.",
            422,
            details={
                "violations": rejected[:20],
                "suggestions": [
                    "Add dishes with verified nutrition and allergen data.",
                    "Add sourced enabled health rules for the member's conditions.",
                ],
            },
        )

    enabled_rules = rule_repository.enabled_rules(db)
    rng = random.Random(payload.seed)
    selected = []
    used = set()
    final_violations = []
    for day_index in range(1, payload.days + 1):
        day_date = payload.start_date + timedelta(days=day_index - 1)
        day_items, violations = _search_day(
            db,
            profile,
            day_date,
            day_index,
            payload.meal_types,
            candidates,
            [],
            used,
            set(payload.prefer_dish_ids),
            float(goal),
            enabled_rules,
            rng,
        )
        if day_items is None:
            final_violations.extend(violations)
            raise AppException(
                "CONSTRAINT_UNSATISFIABLE",
                "No menu satisfies the hard constraints for every requested meal.",
                422,
                details={
                    "violations": final_violations[:30],
                    "suggestions": [
                        "Add verified dishes or sourced health rules.",
                        "Adjust only soft preferences such as maxCookingEffort.",
                    ],
                },
            )
        selected.extend(day_items)
        used.update(row["food_id"] for row in day_items)

    validation = _validate_plan(
        db,
        profile,
        selected,
        payload.start_date,
        payload.days,
        enabled_rules,
    )
    if not validation["hardConstraintsPassed"]:
        raise AppException(
            "CONSTRAINT_UNSATISFIABLE",
            "The complete menu failed final hard-constraint validation.",
            422,
            details={"violations": validation["violations"]},
        )
    preferred = set(payload.prefer_dish_ids)
    score = _soft_score(selected, goal, preferred, payload.max_cooking_effort)
    options = _generation_options(payload)
    plan_id = menu_plan_repository.create(
        db,
        payload.member_id,
        payload.start_date,
        payload.days,
        json.dumps(validation),
        score["total"],
        json.dumps(score),
        json.dumps(options),
    )
    for item_row in selected:
        menu_plan_repository.add_item(
            db,
            plan_id,
            item_row["food_id"],
            item_row["meal_type"],
            item_row["portion_g"],
            item_row["day_index"],
        )
    return {
        "data": detail(db, session_id, plan_id),
        "meta": {
            "generationMs": round((time.perf_counter() - started) * 1000),
            "algorithm": "greedy+backtracking",
        },
    }


def list_plans(db, session_id, member_id, limit, cursor):
    if member_id is not None:
        member(db, session_id, member_id)
    rows, next_cursor = menu_plan_repository.list_owned(
        db, session_id, member_id, limit, cursor
    )
    return {
        "data": [
            {
                "planId": row["menu_plan_id"],
                "memberId": row["member_id"],
                "startDate": _iso(row["start_date"]),
                "days": row["duration_days"],
                "hardConstraintsPassed": bool(
                    json.loads(row.get("validation_json") or "{}").get(
                        "hardConstraintsPassed", False
                    )
                ),
                "createdAt": _iso(row["created_at"]),
            }
            for row in rows
        ],
        "meta": {"nextCursor": next_cursor},
    }


def _snapshot(plan, items):
    return {
        "member_id": plan["member_id"],
        "start_date": _iso(plan["start_date"]),
        "duration_days": plan["duration_days"],
        "status": plan["status"],
        "revision": plan["revision"],
        "validation_json": plan.get("validation_json"),
        "soft_score": plan.get("soft_score"),
        "soft_score_json": plan.get("soft_score_json"),
        "generation_json": plan.get("generation_json"),
        "items": [
            {
                "menu_item_id": row["menu_item_id"],
                "food_id": row["food_id"],
                "meal_type": row["meal_type"],
                "portion_g": row["portion_g"],
                "day_index": row["day_index"],
                "locked": bool(row.get("locked")),
            }
            for row in items
        ],
    }


def _save_revision(db, plan, items):
    menu_plan_repository.save_revision(
        db,
        plan["menu_plan_id"],
        plan["revision"],
        json.dumps(_snapshot(plan, items), default=str),
    )


def _advance_revision(db, plan, profile, updated_items, generation):
    validation = _validation_for_items(db, profile, updated_items, plan)
    if not validation["hardConstraintsPassed"]:
        raise AppException(
            "HARD_CONSTRAINT_VIOLATION",
            "The updated menu does not satisfy all hard constraints.",
            422,
            details={"violations": validation["violations"]},
        )
    preferred = set(generation.get("preferDishIds", []))
    score = _soft_score(
        updated_items,
        profile.get("energy_target_kcal"),
        preferred,
        generation.get("maxCookingEffort"),
    )
    menu_plan_repository.update_plan(
        db,
        plan["menu_plan_id"],
        plan["revision"] + 1,
        json.dumps(validation),
        score["total"],
        json.dumps(score),
        json.dumps(generation),
    )
    return validation, score


def _get_plan_and_profile(db, session_id, plan_id, lock=False):
    plan = menu_plan_repository.find_owned(db, plan_id, session_id, lock=lock)
    if not plan:
        raise AppException("NOT_FOUND", "Menu plan not found", 404)
    profile = member(db, session_id, plan["member_id"])
    return plan, profile


def _replace_day_item(items, item_id, replacement):
    return [replacement if row["menu_item_id"] == item_id else row for row in items]


def _alternatives_for(db, profile, plan, all_items, current, limit, enabled_rules=None):
    day_index = current["day_index"]
    day_date = plan["start_date"]
    if isinstance(day_date, str):
        day_date = date.fromisoformat(day_date)
    day_date += timedelta(days=day_index - 1)
    generation = json.loads(plan.get("generation_json") or "{}")
    excluded = set(generation.get("excludeDishIds", []))
    candidates, _ = _candidate_pool(
        db, profile, excluded | {current["food_id"]}, generation.get("maxCookingEffort")
    )
    current_day = [row for row in all_items if row["day_index"] == day_index]
    old_totals = _nutrition_totals(current_day)
    old_score = _soft_score(
        all_items,
        profile.get("energy_target_kcal"),
        set(generation.get("preferDishIds", [])),
        generation.get("maxCookingEffort"),
    )["total"]
    choices = []
    for dish in candidates:
        if dish.get("category") != current.get("category"):
            continue
        replacement = dict(current)
        replacement.update(dish)
        replacement["food_id"] = dish["food_id"]
        replacement["portion_g"] = current["portion_g"]
        changed = _replace_day_item(all_items, current["menu_item_id"], replacement)
        day_rows = [row for row in changed if row["day_index"] == day_index]
        violations, _ = _validate_day(db, profile, day_rows, day_date, enabled_rules)
        if violations:
            continue
        new_totals = _nutrition_totals(day_rows)
        new_score = _soft_score(
            changed,
            profile.get("energy_target_kcal"),
            set(generation.get("preferDishIds", [])),
            generation.get("maxCookingEffort"),
        )["total"]
        sodium_delta = (
            round(new_totals["sodiumMg"] - old_totals["sodiumMg"], 2)
            if new_totals["sodiumMg"] is not None and old_totals["sodiumMg"] is not None
            else None
        )
        reason = "Same dish group; candidate passes hard constraints."
        if sodium_delta is not None and sodium_delta < 0:
            reason = "Same dish group, lower sodium, and passes hard constraints."
        choices.append(
            {
                "dishId": dish["food_id"],
                "name": dish["name"],
                "grams": _as_float(current["portion_g"]),
                "nutritionDelta": {
                    "energyKcal": (
                        round(new_totals["energyKcal"] - old_totals["energyKcal"], 2)
                        if new_totals["energyKcal"] is not None
                        and old_totals["energyKcal"] is not None
                        else None
                    ),
                    "sodiumMg": sodium_delta,
                },
                "softScoreDelta": round(new_score - old_score, 2),
                "reason": reason,
            }
        )
    choices.sort(key=lambda row: row["softScoreDelta"], reverse=True)
    return choices[:limit]


def alternatives(db, session_id, plan_id, item_id, limit):
    plan, profile = _get_plan_and_profile(db, session_id, plan_id)
    items = menu_plan_repository.items(db, plan_id)
    current = next((row for row in items if row["menu_item_id"] == item_id), None)
    if not current:
        raise AppException("NOT_FOUND", "Menu item not found", 404)
    rules = rule_repository.enabled_rules(db)
    return {"data": _alternatives_for(db, profile, plan, items, current, limit, rules)}


def change_item(db, session_id, plan_id, item_id, payload):
    plan, profile = _get_plan_and_profile(db, session_id, plan_id, lock=True)
    items = menu_plan_repository.items(db, plan_id)
    current = next((row for row in items if row["menu_item_id"] == item_id), None)
    if not current:
        raise AppException("NOT_FOUND", "Menu item not found", 404)
    dish = dish_repository.find(db, payload.dish_id)
    if not dish:
        raise AppException("NOT_FOUND", "Dish not found", 404)
    replacement = dict(current)
    replacement.update(dish)
    replacement["food_id"] = payload.dish_id
    replacement["portion_g"] = payload.grams
    updated = _replace_day_item(items, item_id, replacement)
    validation = _validation_for_items(db, profile, updated, plan)
    if not validation["hardConstraintsPassed"]:
        generation = json.loads(plan.get("generation_json") or "{}")
        suggestions = _alternatives_for(
            db,
            profile,
            plan,
            items,
            current,
            3,
            rule_repository.enabled_rules(db),
        )
        raise AppException(
            "HARD_CONSTRAINT_VIOLATION",
            "The replacement violates hard constraints.",
            422,
            details={
                "violations": validation["violations"],
                "alternatives": suggestions,
            },
        )
    generation = json.loads(plan.get("generation_json") or "{}")
    _save_revision(db, plan, items)
    menu_plan_repository.update_item(
        db, plan_id, item_id, payload.dish_id, payload.grams
    )
    validation, score = _advance_revision(db, plan, profile, updated, generation)
    day_items = [row for row in updated if row["day_index"] == current["day_index"]]
    return {
        "data": {
            "item": _item_output(replacement),
            "dayTotals": _nutrition_totals(day_items),
            "validation": validation,
            "revision": plan["revision"] + 1,
            "canUndo": True,
        }
    }


def lock_item(db, session_id, plan_id, item_id, locked):
    _plan, _profile = _get_plan_and_profile(db, session_id, plan_id, lock=True)
    current = menu_plan_repository.item(db, plan_id, item_id)
    if not current:
        raise AppException("NOT_FOUND", "Menu item not found", 404)
    if bool(current["locked"]) != locked:
        menu_plan_repository.set_locked(db, plan_id, item_id, locked)
    return {"data": {"itemId": item_id, "locked": locked}}


def _target_items(plan, items, payload):
    start = plan["start_date"]
    if isinstance(start, str):
        start = date.fromisoformat(start)
    target_date = payload.date
    if payload.scope == "all_unlocked":
        return [item for item in items if not item["locked"]]
    if payload.scope == "item":
        return [item for item in items if item["menu_item_id"] == payload.item_id]
    if payload.scope in {"day", "meal"}:
        if target_date < start or target_date >= start + timedelta(
            days=plan["duration_days"]
        ):
            raise AppException("VALIDATION_ERROR", "date is outside the plan", 422)
        day_index = (target_date - start).days + 1
        return [
            item
            for item in items
            if item["day_index"] == day_index
            and not item["locked"]
            and (payload.scope != "meal" or item["meal_type"] == payload.meal_type)
        ]
    return []


def regenerate(db, session_id, plan_id, payload):
    plan, profile = _get_plan_and_profile(db, session_id, plan_id, lock=True)
    current_items = menu_plan_repository.items(db, plan_id)
    targets = _target_items(plan, current_items, payload)
    if payload.scope == "item":
        if not targets:
            raise AppException("NOT_FOUND", "Menu item not found", 404)
        locked = next((row for row in targets if row["locked"]), None)
        if locked:
            raise AppException("CONFLICT", "A locked item cannot be regenerated", 409)
    if not targets:
        raise AppException(
            "CONSTRAINT_UNSATISFIABLE",
            "There are no unlocked items in the requested scope.",
            422,
        )
    generation = json.loads(plan.get("generation_json") or "{}")
    if not profile.get("energy_target_kcal"):
        raise AppException("PROFILE_INCOMPLETE", "Energy goal is required", 422)
    if payload.seed is not None:
        generation["seed"] = payload.seed
    rng = random.Random(generation.get("seed"))
    candidates, rejected = _candidate_pool(
        db,
        profile,
        set(generation.get("excludeDishIds", [])),
        generation.get("maxCookingEffort"),
    )
    if not candidates:
        raise AppException(
            "CONSTRAINT_UNSATISFIABLE",
            "No eligible replacement dishes are available.",
            422,
            details={"violations": rejected[:20]},
        )
    rules = rule_repository.enabled_rules(db)
    target_ids = {row["menu_item_id"] for row in targets}
    replacements = {}
    failure_details = []
    for day_index in sorted({row["day_index"] for row in targets}):
        day_targets = [row for row in targets if row["day_index"] == day_index]
        fixed = [
            row
            for row in current_items
            if row["day_index"] == day_index and row["menu_item_id"] not in target_ids
        ]
        meal_types = [row["meal_type"] for row in day_targets]
        day_date = plan["start_date"]
        if isinstance(day_date, str):
            day_date = date.fromisoformat(day_date)
        day_date += timedelta(days=day_index - 1)
        selected, violations = _search_day(
            db,
            profile,
            day_date,
            day_index,
            meal_types,
            candidates,
            fixed,
            {row["food_id"] for row in fixed},
            set(generation.get("preferDishIds", [])),
            float(profile["energy_target_kcal"]),
            rules,
            rng,
        )
        if selected is None:
            failure_details.extend(violations)
            raise AppException(
                "CONSTRAINT_UNSATISFIABLE",
                "Locked and unchanged items prevent a safe regeneration.",
                422,
                details={"violations": failure_details[:30]},
            )
        for target, selected_item in zip(day_targets, selected):
            replacements[target["menu_item_id"]] = selected_item

    updated = [
        {
            **item,
            **(
                {
                    "food_id": replacements[item["menu_item_id"]]["food_id"],
                    "portion_g": replacements[item["menu_item_id"]]["portion_g"],
                }
                if item["menu_item_id"] in replacements
                else {}
            ),
        }
        for item in current_items
    ]
    validation = _validation_for_items(db, profile, updated, plan)
    if not validation["hardConstraintsPassed"]:
        raise AppException(
            "CONSTRAINT_UNSATISFIABLE",
            "The regenerated plan failed final hard-constraint validation.",
            422,
            details={"violations": validation["violations"]},
        )
    _save_revision(db, plan, current_items)
    for item_id, selected_item in replacements.items():
        menu_plan_repository.update_item(
            db,
            plan_id,
            item_id,
            selected_item["food_id"],
            selected_item["portion_g"],
        )
    _advance_revision(db, plan, profile, updated, generation)
    return {
        "data": detail(db, session_id, plan_id),
        "meta": {"regeneratedItems": len(replacements)},
    }


def undo(db, session_id, plan_id, steps):
    plan, _profile = _get_plan_and_profile(db, session_id, plan_id, lock=True)
    target_revision = plan["revision"] - steps
    snapshot_row = (
        menu_plan_repository.get_revision(db, plan_id, target_revision)
        if target_revision >= 1
        else None
    )
    if not snapshot_row:
        raise AppException("NOTHING_TO_UNDO", "No earlier menu revision", 409)
    snapshot = json.loads(snapshot_row["snapshot_json"])
    old_items = menu_plan_repository.items(db, plan_id)
    current_locks = {row["menu_item_id"]: bool(row["locked"]) for row in old_items}
    for item in snapshot["items"]:
        if item["menu_item_id"] in current_locks:
            item["locked"] = current_locks[item["menu_item_id"]]
    menu_plan_repository.restore_plan(db, plan_id, snapshot)
    menu_plan_repository.replace_items(db, plan_id, snapshot["items"])
    menu_plan_repository.delete_revisions_from(db, plan_id, target_revision)
    return {"data": detail(db, session_id, plan_id)}


def validate(db, session_id, plan_id):
    plan, profile = _get_plan_and_profile(db, session_id, plan_id)
    items = menu_plan_repository.items(db, plan_id)
    result = _validation_for_items(db, profile, items, plan)
    return {
        "data": {
            "hardConstraintsPassed": result["hardConstraintsPassed"],
            "checkedAt": datetime.now(UTC).isoformat(),
            "rulesetVersion": result["rulesetVersion"],
            "profileVersion": profile.get("profile_version", 1),
            "violations": result["violations"],
        }
    }


def delete(db, session_id, plan_id):
    plan = menu_plan_repository.find_owned(db, plan_id, session_id, lock=True)
    if not plan:
        raise AppException("NOT_FOUND", "Menu plan not found", 404)
    menu_plan_repository.delete(db, plan_id)


def _export_lines(plan, include_nutrition):
    lines = [f"NutriPlan - Menu for {plan['startDate']}"]
    lines.append(f"Revision {plan['revision']}")
    for day in plan["days"]:
        lines.append("")
        lines.append(day["date"])
        for meal in day["meals"]:
            lines.append(f"  {meal['mealType'].title()}")
            for item in meal["items"]:
                lines.append(
                    f"    {item['name']} - {item['grams']:g} g"
                    + (" (locked)" if item["locked"] else "")
                )
                if include_nutrition:
                    nutrition = item["nutrition"]
                    lines.append(
                        f"      Energy: {nutrition['energyKcal']} kcal; "
                        f"Sodium: {nutrition['sodiumMg']} mg"
                    )
    lines.extend(
        [
            "",
            "Thông tin hỗ trợ, không thay thế tư vấn của bác sĩ.",
        ]
    )
    return lines


def _html_export(plan, include_nutrition, font_scale):
    sizes = {"normal": "1rem", "large": "1.25rem", "xlarge": "1.5rem"}
    lines = _export_lines(plan, include_nutrition)
    body = "\n".join(f"<p>{html.escape(line)}</p>" for line in lines)
    return (
        '<!doctype html><html lang="vi"><meta charset="utf-8">'
        f"<title>Thực đơn {html.escape(plan['startDate'])}</title>"
        f'<body style="font-family:Arial,sans-serif;font-size:{sizes[font_scale]}">'
        f"{body}</body></html>"
    )


def _pdf_export(lines, font_scale):
    font_size = {"normal": 11, "large": 14, "xlarge": 18}[font_scale]
    line_height = font_size + 8
    lines_per_page = max(1, 740 // line_height)
    pages = [
        lines[index : index + lines_per_page]
        for index in range(0, len(lines), lines_per_page)
    ]
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    page_ids = []
    for page_lines in pages:
        page_id = len(objects) + 1
        content_id = page_id + 1
        page_ids.append(page_id)
        commands = [f"BT /F1 {font_size} Tf 50 790 Td"]
        for index, line in enumerate(page_lines):
            text = (
                unicodedata.normalize("NFKD", line)
                .replace("Đ", "D")
                .replace("đ", "d")
                .encode("ascii", "ignore")
                .decode("ascii")
                .replace("\\", "\\\\")
                .replace("(", "\\(")
                .replace(")", "\\)")
            )
            if index:
                commands.append(f"0 -{line_height} Td")
            commands.append(f"({text}) Tj")
        commands.append("ET")
        stream = "\n".join(commands).encode("ascii")
        objects.extend(
            [
                (
                    f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] "
                    f"/Resources << /Font << /F1 3 0 R >> >> "
                    f"/Contents {content_id} 0 R >>"
                ).encode("ascii"),
                b"<< /Length "
                + str(len(stream)).encode("ascii")
                + b" >>\nstream\n"
                + stream
                + b"\nendstream",
            ]
        )
    objects[1] = (
        f"<< /Type /Pages /Kids [{' '.join(f'{item} 0 R' for item in page_ids)}] "
        f"/Count {len(page_ids)} >>"
    ).encode("ascii")
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)


def export(db, session_id, plan_id, output_format, font_scale, include_nutrition):
    from fastapi.responses import Response

    validation = validate(db, session_id, plan_id)["data"]
    if not validation["hardConstraintsPassed"]:
        raise AppException(
            "PLAN_INVALID",
            "Menu plan does not satisfy current hard constraints.",
            409,
            details={"violations": validation["violations"]},
        )
    plan = detail(db, session_id, plan_id)
    filename = f"thuc-don-{plan['startDate']}.{output_format}"
    if output_format == "html":
        content = _html_export(plan, include_nutrition, font_scale)
        media_type = "text/html; charset=utf-8"
    else:
        content = _pdf_export(_export_lines(plan, include_nutrition), font_scale)
        media_type = "application/pdf"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
