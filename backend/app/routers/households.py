from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.dependencies import get_current_session, get_db
from app.schemas.profiles import HouseholdCreate, MemberCreate, MemberResponse
from app.services import household_service

router = APIRouter(prefix="/households", tags=["Households"])
alias_router = APIRouter(prefix="/household", tags=["Households"])
Session = Annotated[dict, Depends(get_current_session)]

@router.get("")
def get_households(
    household_id: int = Query(gt=0, alias="householdId"),
    session: Session = None,
    db=Depends(get_db),
):
    return {"data": household_service.detail(db, session["session_id"], household_id)}

@router.get("/{household_id}")
def get_household(
    household_id: int,
    session: Session,
    db=Depends(get_db),
):
    return {"data": household_service.detail(db, session["session_id"], household_id)}

@alias_router.get("")
def get_household_alias(
    household_id: int = Query(gt=0, alias="householdId"),
    session: Session = None,
    db=Depends(get_db),
):
    return {"data": household_service.detail(db, session["session_id"], household_id)}


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
