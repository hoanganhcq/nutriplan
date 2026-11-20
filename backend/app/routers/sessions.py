from fastapi import APIRouter, Depends, status

from app.dependencies import get_db
from app.services import session_service

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_session(db=Depends(get_db)):
    return session_service.create_session(db)
