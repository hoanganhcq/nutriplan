from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies import get_current_session, get_db
from app.schemas.profiles import (
    MemberResponse,
    MemberUpdate,
    ProfileCreateRequest,
    ProfileResponse,
)
from app.services import profile_service

router = APIRouter(prefix="/profiles", tags=["Profiles"])
Session = Annotated[dict, Depends(get_current_session)]


@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(
    payload: ProfileCreateRequest,
    session: Session,
    db=Depends(get_db),
):
    return profile_service.create_profile(db, session["session_id"], payload)


@router.get("", response_model=list[ProfileResponse])
def list_profiles(session: Session, db=Depends(get_db)):
    return profile_service.list_profiles(db, session["session_id"])


@router.get("/{profile_id}", response_model=MemberResponse)
def get_profile(profile_id: int, session: Session, db=Depends(get_db)):
    return profile_service.get_profile(db, session["session_id"], profile_id)


@router.put("/{profile_id}", response_model=MemberResponse)
def update_profile(
    profile_id: int,
    payload: MemberUpdate,
    session: Session,
    db=Depends(get_db),
):
    return profile_service.update_profile(
        db, session["session_id"], profile_id, payload
    )


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(profile_id: int, session: Session, db=Depends(get_db)):
    profile_service.delete_profile(db, session["session_id"], profile_id)
