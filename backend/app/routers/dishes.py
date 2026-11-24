from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_session, get_db
from app.schemas.e2e import DishListResponse
from app.schemas.error import ErrorResponse
from app.services import dish_service

router = APIRouter(
    prefix="/dishes",
    tags=["Dishes"],
    responses={
        401: {"model": ErrorResponse},
    },
)

# truy vấn danh sách các món ăn với các tham số tìm kiếm và phân trang
@router.get("", response_model=DishListResponse)
def list_dishes(
    q: str | None = None,
    category: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: int = Query(default=0, ge=0),
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    return dish_service.search(db, q, category, limit, cursor)

@router.get("/{dish_id}", response_model=dict)
def get_dish(
    dish_id: int,
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    return dish_service.detail(db, dish_id)
