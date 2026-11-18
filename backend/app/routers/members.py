from fastapi import APIRouter, Depends, Query, status

from app.dependencies import get_current_session, get_db
from app.schemas.e2e import MemberInput, MemberListResponse, MemberResponseE2E
from app.schemas.error import ErrorResponse
from app.services import member_service

# định nghĩa các endpoint cho quản lý thành viên
router = APIRouter(
    prefix="/members",
    tags=["Members"],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)

# tạo một thành viên mới
@router.post("", status_code=status.HTTP_201_CREATED, response_model=MemberResponseE2E)
def create_member(
    payload: MemberInput, session=Depends(get_current_session), db=Depends(get_db)
):
    return {"data": member_service.create(db, session["session_id"], payload)}

# lấy danh sách các thành viên trong một hộ gia đình
@router.get("", response_model=MemberListResponse)
def get_members(
    household_id: int = Query(gt=0, alias="householdId"),
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    return {
        "data": member_service.list_members(db, session["session_id"], household_id)
    }
