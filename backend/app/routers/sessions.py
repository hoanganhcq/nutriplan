import secrets
from hashlib import sha256

from fastapi import APIRouter, status

from app.db.database import get_connection

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_session():
    token = secrets.token_urlsafe(32)
    token_hash = sha256(token.encode("utf-8")).hexdigest()
    with get_connection() as db:
        cursor = db.execute(
            "INSERT INTO SESSION (token_hash) VALUES (%s)", (token_hash,)
        )
        session_id = cursor.lastrowid
    return {"session_id": session_id, "token": token}
