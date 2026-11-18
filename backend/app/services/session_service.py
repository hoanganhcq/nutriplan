import secrets
from hashlib import sha256

from app.core.exceptions import AppException
from app.repositories import session_repository


def create_session(db):
    token = secrets.token_urlsafe(32)
    token_hash = sha256(token.encode("utf-8")).hexdigest()
    session_id = session_repository.create(db, token_hash)
    return {"session_id": session_id, "token": token}


def get_current_session(db, token: str):
    token_hash = sha256(token.encode("utf-8")).hexdigest()
    session = session_repository.find_by_token_hash(db, token_hash)
    if not session:
        raise AppException("UNAUTHORIZED", "Phiên không hợp lệ", 401)
    return session
