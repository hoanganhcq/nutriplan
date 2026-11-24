from fastapi import APIRouter, Depends

from app.dependencies import get_current_session, get_db
from app.schemas.error import ErrorResponse
from app.schemas.system_support import EventsInput, EventsResponse
from app.services import event_service

router = APIRouter(tags=["System support"])


@router.post(
    "/events",
    status_code=202,
    response_model=EventsResponse,
    responses={401: {"model": ErrorResponse}},
)
def record_events(
    payload: EventsInput,
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    return event_service.record(db, session["session_id"], payload)
