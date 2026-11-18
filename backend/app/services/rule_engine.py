import json

from app.repositories import rule_repository


def _values(raw):
    if isinstance(raw, str):
        try:
            value = json.loads(raw or "[]")
        except ValueError:
            return None
        return value if isinstance(value, list) else None
    return raw if isinstance(raw, list) else None


def evaluate(db, profile, foods):
    """Fail closed when rule coverage or food evidence is missing."""
    rules = rule_repository.active_verified(db)
    by_key = {(r["rule_type"], r["subject"]): r for r in rules}
    profile_conditions = _values(profile.get("health_conditions"))
    profile_allergies = _values(profile.get("allergies"))
    if profile_conditions is None or profile_allergies is None:
        return {
            "level": "INSUFFICIENT_DATA",
            "reasons": ["Profile data is invalid"],
            "rulesetVersion": None,
            "hardConstraintsPassed": False,
        }
    conditions = [x for x in profile_conditions if x != "none"]
    allergies = [x for x in profile_allergies if x != "none"]
    needed = (
        [("general", "nutrition")]
        + [("condition", x) for x in conditions]
        + [("allergy", x) for x in allergies]
    )
    missing = [
        f"Missing verified rule: {kind}/{subject}"
        for kind, subject in needed
        if (kind, subject) not in by_key
    ]
    if conditions:
        missing.append("Condition-specific evaluation is not configured")
    if not foods:
        missing.append("Meal contains no dishes")
    for food in foods:
        if (
            not food.get("source_name")
            or not food.get("source_url")
            or any(
                food.get(key) is None
                for key in (
                    "kcal_per_100g",
                    "protein_per_100g",
                    "carb_per_100g",
                    "fat_per_100g",
                )
            )
        ):
            missing.append(f"Nutrition source incomplete for {food['name']}")
        if allergies and not food.get("allergen_verified"):
            missing.append(f"Allergen data unverified for {food['name']}")
        if allergies and _values(food.get("allergen_codes")) is None:
            missing.append(f"Allergen codes missing for {food['name']}")
        texture = profile.get("texture_requirements")
        if texture and texture != "normal" and food.get("texture") != texture:
            missing.append(f"Texture not verified for {food['name']}")
    if missing:
        return {
            "level": "INSUFFICIENT_DATA",
            "reasons": missing,
            "rulesetVersion": None,
            "hardConstraintsPassed": False,
        }
    matched = []
    for food in foods:
        ingredients = {
            part.strip().casefold() for part in _values(food.get("allergen_codes"))
        }
        for allergy in allergies:
            if allergy.casefold() in ingredients:
                matched.append(f"Allergen {allergy} in {food['name']}")
    versions = {by_key[key]["ruleset_version"] for key in needed}
    if len(versions) != 1:
        return {
            "level": "INSUFFICIENT_DATA",
            "reasons": ["Verified rules have different versions"],
            "rulesetVersion": None,
            "hardConstraintsPassed": False,
        }
    return {
        "level": "RED" if matched else "GREEN",
        "reasons": matched or ["Verified rules found; no known hard violation"],
        "rulesetVersion": versions.pop(),
        "hardConstraintsPassed": not matched,
    }
