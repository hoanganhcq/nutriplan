import json

from app.repositories import member_repository
from app.schemas.profiles import MemberCreate
from app.services import consent_service
from app.services.ownership import household


def serialize(row):
    weight = float(row["weight_kg"]) if row.get("weight_kg") is not None else None
    height = float(row["height_cm"]) if row.get("height_cm") is not None else None
    return {
        "memberId": row["member_id"],
        "householdId": row["household_id"],
        "name": row["full_name"],
        "age": row["age"],
        "sex": row.get("sex"),
        "weightKg": weight,
        "heightCm": height,
        "bmi": round(weight / (height / 100) ** 2, 2) if weight and height else None,
        "conditions": json.loads(row.get("health_conditions") or "[]"),
        "allergies": json.loads(row.get("allergies") or "[]"),
        "preferences": json.loads(row.get("preferences") or "[]"),
        "energyGoalKcal": row.get("energy_target_kcal"),
        "texture": row.get("texture_requirements"),
        "isSimulated": bool(row.get("is_simulated")),
        "profileVersion": row.get("profile_version", 1),
    }


def create(db, session_id, payload):
    household(db, session_id, payload.household_id)
    consent_service.require(
        db, session_id, payload.household_id, "store_health_profile"
    )
    legacy = MemberCreate(
        name=payload.name,
        age=payload.age,
        sex=payload.sex,
        weight_kg=payload.weight_kg,
        height_cm=payload.height_cm,
        conditions=payload.conditions,
        allergies=payload.allergies,
        food_preferences=payload.preferences,
        energy_target_kcal=payload.energy_goal_kcal,
        texture_requirements=payload.texture,
    )
    member_id = member_repository.create(db, payload.household_id, legacy)
    if payload.is_simulated:
        db.execute(
            "UPDATE MEMBER SET is_simulated = TRUE WHERE member_id = %s", (member_id,)
        )
    return serialize(member_repository.find(db, member_id))


def list_members(db, session_id, household_id):
    household(db, session_id, household_id)
    return [
        serialize(row) for row in member_repository.list_by_household(db, household_id)
    ]
