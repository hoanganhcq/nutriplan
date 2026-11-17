import json
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.exceptions import AppException
from app.dependencies import get_current_session, get_db
from app.routers.profiles import _member_response
from app.schemas.profiles import HouseholdCreate, MemberCreate, MemberResponse

router = APIRouter(prefix="/households", tags=["Households"])
Session = Annotated[dict, Depends(get_current_session)]


def _owned_household(db, household_id: int, session_id: int):
    return db.execute(
        "SELECT * FROM HOUSEHOLD WHERE household_id = %s AND session_id = %s",
        (household_id, session_id),
    ).fetchone()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_household(
    payload: HouseholdCreate,
    session: Session,
    db=Depends(get_db),
):
    cursor = db.execute(
        "INSERT INTO HOUSEHOLD (session_id, name) VALUES (%s, %s)",
        (session["session_id"], payload.name),
    )
    return {"household_id": cursor.lastrowid, "name": payload.name}


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
    if not _owned_household(db, household_id, session["session_id"]):
        raise AppException("NOT_FOUND", "Không tìm thấy household", 404)

    cursor = db.execute(
        """
        INSERT INTO MEMBER
        (household_id, full_name, age, sex, weight_kg, height_cm,
         health_conditions, allergies, preferences, energy_target_kcal,
         texture_requirements)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            household_id,
            payload.name,
            payload.age,
            payload.sex,
            payload.weight_kg,
            payload.height_cm,
            json.dumps(payload.conditions),
            json.dumps(payload.allergies),
            json.dumps(payload.food_preferences),
            payload.energy_target_kcal,
            payload.texture_requirements,
        ),
    )
    row = db.execute(
        "SELECT * FROM MEMBER WHERE member_id = %s", (cursor.lastrowid,)
    ).fetchone()
    return _member_response(row)
