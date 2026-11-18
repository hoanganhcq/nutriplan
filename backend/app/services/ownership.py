from app.core.exceptions import AppException
from app.repositories import household_repository, member_repository


def household(db, session_id, household_id):
    row = household_repository.find_owned(db, household_id, session_id)
    if not row:
        raise AppException("NOT_FOUND", "Household not found", 404)
    return row


def member(db, session_id, member_id):
    row = member_repository.find_owned(db, member_id, session_id)
    if not row:
        raise AppException("NOT_FOUND", "Member not found", 404)
    return row
