import json
import re
from datetime import UTC

from app.repositories import event_repository

ERROR_CODES = {
    "VALIDATION_ERROR",
    "UNAUTHORIZED",
    "NOT_FOUND",
    "CONFLICT",
    "MEAL_LOCKED",
    "VISION_UNAVAILABLE",
    "INTERNAL_SERVER_ERROR",
    "CONSENT_REQUIRED",
    "PROFILE_INCOMPLETE",
    "HARD_CONSTRAINT_VIOLATION",
    "CONSTRAINT_UNSATISFIABLE",
    "UNDO_UNAVAILABLE",
    "RULES_UNAVAILABLE",
}


def _safe_metadata(meta):
    # No free-text fields, nested objects, nutrition values, images or filenames.
    if set(meta) - {"itemId", "success", "errorCode"}:
        return False
    if "itemId" in meta:
        value = meta["itemId"]
        if type(value) is int:
            if not 0 < value <= 2**31 - 1:
                return False
        elif not isinstance(value, str) or not re.fullmatch(
            r"(?:item|dish|food|menu_item)_[1-9][0-9]{0,9}|[1-9][0-9]{0,9}", value
        ):
            return False
    if "success" in meta and type(meta["success"]) is not bool:
        return False
    if "errorCode" in meta and (
        not isinstance(meta["errorCode"], str) or meta["errorCode"] not in ERROR_CODES
    ):
        return False
    return True


def record(db, session_id, payload):
    accepted = 0
    if event_repository.analytics_allowed(db, session_id):
        for event in payload.events:
            if not _safe_metadata(event.meta):
                continue
            event_repository.save(
                db,
                session_id,
                payload.session_id,
                payload.participant_id,
                event,
                json.dumps(event.meta, separators=(",", ":")),
                event.at.astimezone(UTC).replace(tzinfo=None),
            )
            accepted += 1
    return {"data": {"accepted": accepted, "dropped": len(payload.events) - accepted}}
