import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import BaseModel, Field

from app.core.exceptions import AppException
from app.dependencies import get_current_session, get_db
from app.repositories import meal_repository
from app.schemas.e2e import (
    AssessmentInput,
    AssessmentResponse,
    ConfirmInput,
    ConfirmResponse,
    MealItemUpdate,
    MealListResponse,
    MealResponse,
    MealUndoResponse,
    UndoInput,
)
from app.schemas.error import ErrorResponse
from app.services import assessment_service, meal_service

router = APIRouter(
    prefix="/meals",
    tags=["Meals"],
    responses={
        code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 413, 415, 503)
    },
)


class ClarificationAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=1000)


@router.post("/analyze", status_code=201, response_model=MealResponse)
async def analyze_meal(
    images: list[UploadFile] = File(...),
    household_id: int = Form(..., alias="householdId"),
    meal_type: str | None = Form(None, alias="mealType"),
    eaten_at: datetime | None = Form(None, alias="eatenAt"),
    member_ids: str = Form("[]", alias="memberIds"),
    reference_object: str | None = Form(None, alias="referenceObject"),
    portion_method: str | None = Form("reference_object", alias="portionMethod"),
    use_external_vision: bool = Form(False, alias="useExternalVision"),
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    try:
        parsed_ids = json.loads(member_ids)
        if not isinstance(parsed_ids, list) or any(
            not isinstance(value, int) or value <= 0 for value in parsed_ids
        ):
            raise ValueError
    except ValueError as exc:
        raise AppException(
            "VALIDATION_ERROR", "memberIds must be a JSON array of IDs", 422
        ) from exc
    validated = await meal_service.validate_images(images)
    return {
        "data": meal_service.analyze(
            db,
            session["session_id"],
            household_id,
            validated,
            meal_type,
            eaten_at,
            parsed_ids,
            use_external_vision,
            reference_object,
            portion_method,
        )
    }


@router.get("", response_model=MealListResponse)
def list_meals(
    member_id: int | None = Query(None, alias="memberId"),
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    status: str = "confirmed",
    limit: int = Query(20, ge=1, le=100),
    cursor: int = Query(0, ge=0),
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    if status != "confirmed":
        raise AppException(
            "VALIDATION_ERROR", "Only confirmed journal entries are supported", 422
        )
    return meal_service.journal(
        db, session["session_id"], member_id, from_date, to_date, limit, cursor
    )


@router.get("/{meal_id}", response_model=MealResponse)
def get_meal(meal_id: int, session=Depends(get_current_session), db=Depends(get_db)):
    return {"data": meal_service.detail(db, session["session_id"], meal_id)}


@router.patch("/{meal_id}/items/{item_id}", response_model=MealResponse)
def patch_item(
    meal_id: int,
    item_id: int,
    payload: MealItemUpdate,
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    return {
        "data": meal_service.change_item(
            db, session["session_id"], meal_id, item_id, payload
        )
    }


@router.post("/{meal_id}/items", status_code=201, response_model=MealResponse)
def post_item(
    meal_id: int,
    payload: MealItemUpdate,
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    return {"data": meal_service.add_item(db, session["session_id"], meal_id, payload)}


@router.delete("/{meal_id}/items/{item_id}", response_model=MealResponse)
def delete_item(
    meal_id: int,
    item_id: int,
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    return {
        "data": meal_service.remove_item(db, session["session_id"], meal_id, item_id)
    }


@router.post("/{meal_id}/assessments", response_model=AssessmentResponse)
def assess(
    meal_id: int,
    payload: AssessmentInput,
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    return {
        "data": assessment_service.assess(
            db, session["session_id"], meal_id, payload.member_ids
        )
    }


@router.get("/{meal_id}/assessments", response_model=AssessmentResponse)
def get_assessments(
    meal_id: int,
    member_id: int | None = Query(None, alias="memberId"),
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    return {
        "data": assessment_service.get_assessments(
            db, session["session_id"], meal_id, member_id
        )
    }


@router.post("/{meal_id}/undo", response_model=MealUndoResponse)
def undo_meal(
    meal_id: int,
    payload: UndoInput = UndoInput(),
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    return {
        "data": meal_service.undo(db, session["session_id"], meal_id, payload.steps)
    }


@router.post("/{meal_id}/confirm", response_model=ConfirmResponse)
def confirm(
    meal_id: int,
    payload: ConfirmInput | None = None,
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    return {
        "data": assessment_service.confirm(
            db,
            session["session_id"],
            meal_id,
            payload.eaten_by if payload else None,
            payload.note if payload else None,
        )
    }


@router.post(
    "/{meal_id}/clarifications/{question_id}/answer",
    response_model=MealResponse,
)
def answer_clarification(
    meal_id: int,
    question_id: int,
    payload: ClarificationAnswer,
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    row = meal_service.owned(db, session["session_id"], meal_id, lock=True)
    if row["status"] != "draft":
        raise AppException("MEAL_LOCKED", "Confirmed meal cannot be edited", 409)
    meal_repository.increment_revision(db, meal_id)
    return {"data": meal_service.detail(db, session["session_id"], meal_id)}


@router.delete("/{meal_id}", status_code=204)
def delete_meal(meal_id: int, session=Depends(get_current_session), db=Depends(get_db)):
    meal_service.delete(db, session["session_id"], meal_id)
