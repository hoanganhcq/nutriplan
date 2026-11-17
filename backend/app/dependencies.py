from hashlib import sha256
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import AppException
from app.db.database import get_connection

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

    token_hash = sha256(token.encode("utf-8")).hexdigest()
    session = db.execute(
        "SELECT * FROM SESSION WHERE token_hash = ?", (token_hash,)
    ).fetchone()
    if not session:
        raise AppException("UNAUTHORIZED", "Phiên không hợp lệ", 401)
    return session
