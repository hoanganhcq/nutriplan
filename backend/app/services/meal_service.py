import json
from datetime import UTC, datetime

from app.core.exceptions import AppException
from app.repositories import dish_repository, meal_repository
from app.services import consent_service, nutrition_service, vision_service
from app.services.ownership import member

MAGIC = {
    "image/jpeg": lambda b: b.startswith(b"\xff\xd8\xff"),
    "image/png": lambda b: b.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/webp": lambda b: b.startswith(b"RIFF") and b[8:12] == b"WEBP",
}


async def validate_images(files):
    if not 1 <= len(files) <= 5:
        raise AppException("VALIDATION_ERROR", "Provide 1 to 5 images", 422)
    result = []
    for file in files:
        mime = file.content_type
        if mime not in MAGIC:
            raise AppException(
                "UNSUPPORTED_MEDIA_TYPE", "JPEG, PNG or WebP required", 415
            )
        content = await file.read(8 * 1024 * 1024 + 1)
        if len(content) > 8 * 1024 * 1024:
            raise AppException("FILE_TOO_LARGE", "Each image must be at most 8 MB", 413)
        if not MAGIC[mime](content):
            raise AppException(
                "UNSUPPORTED_MEDIA_TYPE", "Image signature does not match type", 415
            )
        result.append((mime, content))
    return result


def _item(row):
    grams = float(row["confirmed_weight_g"] or row["estimated_weight_g"] or 0)
    return {
        "itemId": row["meal_item_id"],
        "dishId": row["food_id"],
        "name": row["name"],
        "grams": grams,
        "seasoning": row.get("seasoning"),
        "confidence": float(row["confidence"])
        if row.get("confidence") is not None
        else None,
        "isEstimate": row["confirmed_weight_g"] is None,
        "nutrition": nutrition_service.portion(row, grams),
    }


def owned(db, session_id, meal_id, lock=False):
    row = meal_repository.find_owned(db, meal_id, session_id, lock)
    if not row:
        raise AppException("NOT_FOUND", "Meal not found", 404)
    return row


def detail(db, session_id, meal_id):
    row = owned(db, session_id, meal_id)
    items = [_item(item) for item in meal_repository.items(db, meal_id)]
    return {
        "mealId": meal_id,
        "householdId": row["household_id"],
        "mealType": row.get("meal_type"),
        "eatenAt": row["eaten_at"],
        "status": row["status"],
        "revision": row["revision"],
        "items": items,
        "confidence": (
            round(
                sum(
                    item["confidence"]
                    for item in items
                    if item["confidence"] is not None
                )
                / len([item for item in items if item["confidence"] is not None]),
                3,
            )
            if any(item["confidence"] is not None for item in items)
            else None
        ),
        "totals": nutrition_service.totals(items),
        "memberIds": meal_repository.member_ids(db, meal_id),
        "isEstimate": bool(row["is_estimate"]),
        "warnings": json.loads(row.get("warnings") or "[]"),
    }


def analyze(
    db,
    session_id,
    household_id,
    images,
    meal_type,
    eaten_at,
    member_ids,
    use_external_vision,
):
    consent_service.require(
        db, session_id, household_id, "store_health_profile"
    ) if member_ids else consent_service.get(db, session_id, household_id)
    for member_id in member_ids:
        if member(db, session_id, member_id)["household_id"] != household_id:
            raise AppException("NOT_FOUND", "Member not found", 404)
    if vision_service.mode() == "http":
        if not use_external_vision:
            raise AppException(
                "VISION_UNAVAILABLE", "External vision was not requested", 503
            )
        consent_service.require(
            db, session_id, household_id, "send_image_to_ai_provider"
        )
    detections, warnings = vision_service.recognize(images)
    meal_id = meal_repository.create(
        db,
        household_id,
        meal_type,
        eaten_at or datetime.now(UTC).replace(tzinfo=None),
        len(images),
        True,
        json.dumps(warnings),
    )
    for member_id in member_ids:
        meal_repository.add_member(db, meal_id, member_id)
    for detection in detections:
        if not isinstance(detection, dict) or not isinstance(
            detection.get("name"), str
        ):
            continue
        food = dish_repository.match_name(db, detection["name"])
        if not food:
            warnings.append(f"Unmatched dish: {detection['name'][:100]}")
            continue
        grams = detection.get("grams") or food.get("default_portion_g")
        if grams is None or not 0 < float(grams) <= 10000:
            warnings.append(f"Portion unknown: {food['name']}")
            continue
        confidence = detection.get("confidence")
        meal_repository.add_item(
            db,
            meal_id,
            food["food_id"],
            grams,
            confidence=confidence
            if isinstance(confidence, (int, float)) and 0 <= confidence <= 1
            else None,
        )
    if not detections:
        warnings.append("No dishes recognized; add items manually")
    db.execute(
        "UPDATE MEAL SET warnings = %s WHERE meal_id = %s",
        (json.dumps(warnings), meal_id),
    )
    return detail(db, session_id, meal_id)


def change_item(db, session_id, meal_id, item_id, payload):
    row = owned(db, session_id, meal_id, lock=True)
    if row["status"] != "draft":
        raise AppException("MEAL_LOCKED", "Confirmed meal cannot be edited", 409)
    current = next(
        (
            item
            for item in meal_repository.items(db, meal_id)
            if item["meal_item_id"] == item_id
        ),
        None,
    )
    if not current:
        raise AppException("NOT_FOUND", "Meal item not found", 404)
    food_id = payload.dish_id or current["food_id"]
    if not dish_repository.find(db, food_id):
        raise AppException("NOT_FOUND", "Dish not found", 404)
    grams = (
        payload.grams or current["confirmed_weight_g"] or current["estimated_weight_g"]
    )
    meal_repository.update_item(
        db,
        meal_id,
        item_id,
        food_id,
        grams,
        payload.seasoning if payload.seasoning is not None else current["seasoning"],
    )
    meal_repository.increment_revision(db, meal_id)
    return detail(db, session_id, meal_id)


def add_item(db, session_id, meal_id, payload):
    row = owned(db, session_id, meal_id, lock=True)
    if row["status"] != "draft":
        raise AppException("MEAL_LOCKED", "Confirmed meal cannot be edited", 409)
    if not payload.dish_id or not payload.grams:
        raise AppException("VALIDATION_ERROR", "dishId and grams required", 422)
    if not dish_repository.find(db, payload.dish_id):
        raise AppException("NOT_FOUND", "Dish not found", 404)
    meal_repository.add_item(
        db, meal_id, payload.dish_id, payload.grams, payload.seasoning
    )
    meal_repository.increment_revision(db, meal_id)
    return detail(db, session_id, meal_id)


def journal(db, session_id, member_id, from_date, to_date, limit, cursor):
    if member_id:
        member(db, session_id, member_id)
    rows = meal_repository.list_confirmed(
        db, session_id, member_id, from_date, to_date, limit, cursor
    )
    data = [detail(db, session_id, row["meal_id"]) for row in rows]
    return {
        "data": data,
        "meta": {"nextCursor": rows[-1]["meal_id"] if len(rows) == limit else None},
    }
