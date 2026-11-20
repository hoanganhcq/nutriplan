import json
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.core.exceptions import AppException
from app.dependencies import get_current_session, get_db
from app.schemas.e2e import (
    AssessmentInput,
    AssessmentResponse,
    MealItemUpdate,
    MealListResponse,
    MealResponse,
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

# truy vấn các bữa ăn và các mục liên quan đến bữa ăn, bao gồm phân tích hình ảnh, xác nhận và đánh giá
@router.post("/analyze", status_code=201, response_model=MealResponse)
async def analyze_meal(
    images: list[UploadFile] = File(...),
    household_id: int = Form(..., alias="householdId"),
    meal_type: str | None = Form(None, alias="mealType"),
    eaten_at: datetime | None = Form(None, alias="eatenAt"),
    member_ids: str = Form("[]", alias="memberIds"),
    reference_object: str | None = Form(None, alias="referenceObject"),
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
        )
    }


# truy vấn các bữa ăn đã được xác nhận cho một thành viên cụ thể trong một khoảng thời gian nhất định, với phân trang
@router.get("", response_model=MealListResponse)
def list_meals(
    member_id: int | None = Query(None, alias="memberId"),
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
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


# truy vấn chi tiết một bữa ăn cụ thể, bao gồm các mục liên quan đến bữa ăn, đánh giá và xác nhận
@router.get("/{meal_id}", response_model=MealResponse)
def get_meal(meal_id: int, session=Depends(get_current_session), db=Depends(get_db)):
    return {"data": meal_service.detail(db, session["session_id"], meal_id)}


# cập nhật chi tiết một bữa ăn cụ thể, bao gồm các mục liên quan đến bữa ăn, đánh giá và xác nhận
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

# xóa một mục cụ thể khỏi một bữa ăn cụ thể, bao gồm các mục liên quan đến bữa ăn, đánh giá và xác nhận
@router.post("/{meal_id}/items", status_code=201, response_model=MealResponse)
def post_item(
    meal_id: int,
    payload: MealItemUpdate,
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    return {"data": meal_service.add_item(db, session["session_id"], meal_id, payload)}


# xóa một mục cụ thể khỏi một bữa ăn cụ thể, bao gồm các mục liên quan đến bữa ăn, đánh giá và xác nhận
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


# xóa một mục cụ thể khỏi một bữa ăn cụ thể, bao gồm các mục liên quan đến bữa ăn, đánh giá và xác nhận
@router.post("/{meal_id}/confirm", response_model=MealResponse)
def confirm(meal_id: int, session=Depends(get_current_session), db=Depends(get_db)):
    return {"data": assessment_service.confirm(db, session["session_id"], meal_id)}
