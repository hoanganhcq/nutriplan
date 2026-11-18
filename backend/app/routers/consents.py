from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_session, get_db
from app.schemas.e2e import ConsentResponse, ConsentUpdate
from app.schemas.error import ErrorResponse
from app.services import consent_service

router = APIRouter(
    prefix="/consents",
    tags=["Consents"],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
Session = Annotated[dict, Depends(get_current_session)]

# lấy danh sách các quyền consent cho một hộ gia đình cụ thể
@router.get("", response_model=ConsentResponse)
def get_consents(
    household_id: int = Query(gt=0, alias="householdId"),
    session: Session = None,
    db=Depends(get_db),
):
    return {"data": consent_service.get(db, session["session_id"], household_id)}

# cập nhật danh sách các quyền consent cho một hộ gia đình cụ thể
@router.put("", response_model=ConsentResponse)
def put_consents(payload: ConsentUpdate, session: Session, db=Depends(get_db)):
    return {"data": consent_service.update(db, session["session_id"], payload)}
