from app.core.exceptions import AppException
from app.repositories import consent_repository
from app.services.ownership import household

TYPES = (
    "store_health_profile",
    "send_image_to_ai_provider",
    "llm_explanation",
    "usage_analytics",
)
POLICY_VERSION = "0.1"


def get(db, session_id, household_id):
    household(db, session_id, household_id)
    rows = consent_repository.list_for_household(db, household_id)
    values = {row["consent_type"]: bool(row["granted"]) for row in rows}
    return {
        "householdId": household_id,
        "policyVersion": POLICY_VERSION,
        "consents": {kind: values.get(kind, False) for kind in TYPES},
    }


def update(db, session_id, payload):
    household(db, session_id, payload.household_id)
    if payload.policy_version != POLICY_VERSION:
        raise AppException("CONFLICT", "Unsupported policy version", 409)
    for kind, granted in payload.consents.items():
        consent_repository.set_consent(
            db, payload.household_id, kind, granted, POLICY_VERSION
        )
    return get(db, session_id, payload.household_id)


def require(db, session_id, household_id, kind):
    if not get(db, session_id, household_id)["consents"][kind]:
        raise AppException("CONSENT_REQUIRED", f"Consent required: {kind}", 403)
