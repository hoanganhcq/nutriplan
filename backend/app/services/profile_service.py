from app.core.exceptions import AppException
from app.repositories import household_repository, member_repository
from app.schemas.profiles import MemberUpdate, ProfileCreateRequest, ProfileResponse
from app.services.member_mapper import member_response


def _profile_response(db, household_id: int, household_name: str) -> ProfileResponse:
    rows = member_repository.list_by_household(db, household_id)
    return ProfileResponse(
        profile_id=household_id,
        household_name=household_name,
        members=[member_response(row) for row in rows],
    )


def _owned_member(db, member_id: int, session_id: int):
    row = member_repository.find_owned(db, member_id, session_id)
    if not row:
        raise AppException("NOT_FOUND", "Không tìm thấy hồ sơ", 404)
    return row


def create_profile(db, session_id: int, payload: ProfileCreateRequest):
    household_id = household_repository.create(db, session_id, payload.household_name)
    for member in payload.members:
        member_repository.create(db, household_id, member)
    return _profile_response(db, household_id, payload.household_name)


def list_profiles(db, session_id: int):
    households = household_repository.list_by_session(db, session_id)
    return [
        _profile_response(db, row["household_id"], row["name"])
        for row in households
    ]


def get_profile(db, session_id: int, profile_id: int):
    return member_response(_owned_member(db, profile_id, session_id))


def update_profile(db, session_id: int, profile_id: int, payload: MemberUpdate):
    _owned_member(db, profile_id, session_id)
    member_repository.update(db, profile_id, payload)
    return member_response(_owned_member(db, profile_id, session_id))


def delete_profile(db, session_id: int, profile_id: int) -> None:
    _owned_member(db, profile_id, session_id)
    member_repository.delete(db, profile_id)
