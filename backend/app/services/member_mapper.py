import json

from app.schemas.profiles import MemberResponse


def member_response(row) -> MemberResponse:
    return MemberResponse(
        member_id=row["member_id"],
        name=row["full_name"],
        age=row["age"],
        sex=row["sex"],
        weight_kg=row["weight_kg"],
        height_cm=row["height_cm"],
        conditions=json.loads(row["health_conditions"] or "[]"),
        allergies=json.loads(row["allergies"] or "[]"),
        food_preferences=json.loads(row["preferences"] or "[]"),
        energy_target_kcal=row["energy_target_kcal"],
        texture_requirements=row["texture_requirements"],
    )
