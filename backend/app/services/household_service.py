from app.core.exceptions import AppException
from app.repositories import household_repository, member_repository
from app.schemas.profiles import HouseholdCreate, MemberCreate
from app.services.member_mapper import member_response


def create_household(db, session_id: int, payload: HouseholdCreate):
    household_id = household_repository.create(db, session_id, payload.name)
    return {"household_id": household_id, "name": payload.name}


def create_member(db, session_id: int, household_id: int, payload: MemberCreate):
    if not household_repository.find_owned(db, household_id, session_id):
        raise AppException("NOT_FOUND", "Không tìm thấy household", 404)

    member_id = member_repository.create(db, household_id, payload)
    return member_response(member_repository.find(db, member_id))
