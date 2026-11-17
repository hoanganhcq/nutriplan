import json
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.exceptions import AppException
from app.dependencies import get_current_session, get_db
from app.schemas.profiles import (
    MemberResponse,
    MemberUpdate,
    ProfileCreateRequest,
    ProfileResponse,
)

router = APIRouter(prefix="/profiles", tags=["Profiles"])
Session = Annotated[dict, Depends(get_current_session)]


def _member_response(row) -> MemberResponse:
    return MemberResponse(
        member_id=row["member_id"],
        name=row["full_name"],
        age=row["age"],
        sex=row["sex"],
        weight_kg=row["weight_kg"],
        height_cm=row["height_cm"],
        conditions=json.loads(row["health_conditions"] or "[]"),
        allergies=json.loads(row["allergies"] or "[]"),
        food_preferences=json.loads(row["preferences"] or "[]"),
        energy_target_kcal=row["energy_target_kcal"],
        texture_requirements=row["texture_requirements"],
    )


def _profile_response(db, household_id: int, household_name: str) -> ProfileResponse:
    rows = db.execute(
        "SELECT * FROM MEMBER WHERE household_id = %s ORDER BY member_id",
        (household_id,),
    ).fetchall()
    return ProfileResponse(
        profile_id=household_id,
        household_name=household_name,
        members=[_member_response(row) for row in rows],
    )


def _owned_member(db, member_id: int, session_id: int):
    return db.execute(
        """
        SELECT p.*, h.name AS household_name, h.household_id
        FROM MEMBER p
        JOIN HOUSEHOLD h ON h.household_id = p.household_id
        WHERE p.member_id = %s AND h.session_id = %s
        """,
        (member_id, session_id),
    ).fetchone()


@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(
    payload: ProfileCreateRequest,
    session: Session,
    db=Depends(get_db),
):
    cursor = db.execute(
        "INSERT INTO HOUSEHOLD (session_id, name) VALUES (%s, %s)",
        (session["session_id"], payload.household_name),
    )
    household_id = cursor.lastrowid
    for member in payload.members:
        db.execute(
            """
            INSERT INTO MEMBER
            (household_id, full_name, age, sex, weight_kg, height_cm,
             health_conditions, allergies, preferences, energy_target_kcal,
             texture_requirements)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                household_id,
                member.name,
                member.age,
                member.sex,
                member.weight_kg,
                member.height_cm,
                json.dumps(member.conditions),
                json.dumps(member.allergies),
                json.dumps(member.food_preferences),
                member.energy_target_kcal,
                member.texture_requirements,
            ),
        )
    return _profile_response(db, household_id, payload.household_name)


@router.get("", response_model=list[ProfileResponse])
def list_profiles(session: Session, db=Depends(get_db)):
    households = db.execute(
        "SELECT household_id, name FROM HOUSEHOLD WHERE session_id = %s",
        (session["session_id"],),
    ).fetchall()
    return [
        _profile_response(db, row["household_id"], row["name"])
        for row in households
    ]


@router.get("/{profile_id}", response_model=MemberResponse)
def get_profile(profile_id: int, session: Session, db=Depends(get_db)):
    row = _owned_member(db, profile_id, session["session_id"])
    if not row:
        raise AppException("NOT_FOUND", "Không tìm thấy hồ sơ", 404)
    return _member_response(row)


@router.put("/{profile_id}", response_model=MemberResponse)
def update_profile(
    profile_id: int,
    payload: MemberUpdate,
    session: Session,
    db=Depends(get_db),
):
    row = _owned_member(db, profile_id, session["session_id"])
    if not row:
        raise AppException("NOT_FOUND", "Không tìm thấy hồ sơ", 404)
    db.execute(
        """
        UPDATE MEMBER
        SET full_name = %s, age = %s, sex = %s, weight_kg = %s, height_cm = %s,
            health_conditions = %s, allergies = %s, preferences = %s,
            energy_target_kcal = %s, texture_requirements = %s
        WHERE member_id = %s
        """,
        (
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
            profile_id,
        ),
    )
    return _member_response(_owned_member(db, profile_id, session["session_id"]))


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(profile_id: int, session: Session, db=Depends(get_db)):
    row = _owned_member(db, profile_id, session["session_id"])
    if not row:
        raise AppException("NOT_FOUND", "Không tìm thấy hồ sơ", 404)
    db.execute("DELETE FROM MEMBER WHERE member_id = %s", (profile_id,))
