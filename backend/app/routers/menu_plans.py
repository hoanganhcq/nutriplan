from fastapi import APIRouter, Depends

from app.dependencies import get_current_session, get_db
from app.schemas.e2e import MenuGenerateInput, MenuResponse
from app.schemas.error import ErrorResponse
from app.services import menu_plan_service

router = APIRouter(
    prefix="/menu-plans",
    tags=["Menu plans"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 409)},
)

# lấy danh sách các quyền consent cho một hộ gia đình cụ thể
@router.post("/generate", status_code=201, response_model=MenuResponse)
def generate(
    payload: MenuGenerateInput, session=Depends(get_current_session), db=Depends(get_db)
):
    return {"data": menu_plan_service.generate(db, session["session_id"], payload)}

# lấy chi tiết một kế hoạch thực đơn cụ thể
@router.get("/{plan_id}", response_model=MenuResponse)
def get_plan(plan_id: int, session=Depends(get_current_session), db=Depends(get_db)):
    return {"data": menu_plan_service.detail(db, session["session_id"], plan_id)}
