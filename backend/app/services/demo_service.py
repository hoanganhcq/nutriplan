import secrets
from hashlib import sha256

from app.core.config import settings
from app.core.exceptions import AppException
from app.db import demo_data
from app.repositories import consent_repository, demo_repository, household_repository
from app.services import session_service


def require_demo_environment():
    if settings.environment.casefold() not in {"dev", "development", "demo"}:
        raise AppException("NOT_FOUND", "Not found", 404)


def seed(db, reset=False):
    require_demo_environment()
    dataset = demo_repository.lock_dataset(db)
    household_id = dataset["household_id"]
    session_id = dataset["session_id"]
    if household_id is not None:
        demo_repository.check_simulated_members(db, household_id)
        if reset:
            demo_repository.reset_household(db, household_id, session_id)
            household_id = None
    if household_id is None:
        session = session_service.create_session(db)
        session_id, token = session["session_id"], session["token"]
        household_id = household_repository.create(
            db, session_id, demo_data.HOUSEHOLD_NAME
        )
        demo_repository.set_household(db, household_id)
        consent_repository.set_consent(
            db, household_id, "store_health_profile", True, "0.1"
        )
    else:
        # Store only a hash; re-seeding issues a new token for the same demo session.
        token = secrets.token_urlsafe(32)
        demo_repository.rotate_token(db, session_id, sha256(token.encode()).hexdigest())
    for member in demo_data.MEMBERS:
        demo_repository.seed_member(db, household_id, member)
    for index, (name, category) in enumerate(demo_data.DISHES):
        demo_repository.seed_dish(db, index, name, category, reset)
    for rule in demo_data.RULES:
        demo_repository.seed_rule(db, rule, reset)
    return {
        "data": {
            "householdId": household_id,
            "token": token,
            "members": demo_repository.member_count(db, household_id),
            "dishes": len(demo_data.DISHES),
            "rules": len(demo_data.RULES),
        }
    }
