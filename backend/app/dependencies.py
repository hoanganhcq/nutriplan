from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import AppException
from app.db.database import get_connection
from app.services import session_service

bearer_scheme = HTTPBearer(auto_error=False)


def get_db():
    with get_connection() as connection:
        yield connection


def get_current_session(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
    db=Depends(get_db),
):
    if not credentials:
        raise AppException("UNAUTHORIZED", "Thiếu token phiên", 401)

    token = credentials.credentials.strip()
    if not token:
        raise AppException("UNAUTHORIZED", "Thiếu token phiên", 401)

    return session_service.get_current_session(db, token)
