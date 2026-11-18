from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies import get_current_session, get_db
from app.schemas.profiles import HouseholdCreate, MemberCreate, MemberResponse
from app.services import household_service

router = APIRouter(prefix="/households", tags=["Households"])
Session = Annotated[dict, Depends(get_current_session)]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_household(
    payload: HouseholdCreate,
    session: Session,
    db=Depends(get_db),
):
    return household_service.create_household(db, session["session_id"], payload)


@router.post(
    "/{household_id}/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_member(
    household_id: int,
    payload: MemberCreate,
    session: Session,
    db=Depends(get_db),
):
    return household_service.create_member(
        db, session["session_id"], household_id, payload
    )
