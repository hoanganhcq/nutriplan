from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_current_session, get_db
from app.schemas.e2e import ExplainInput, ExplainResponse
from app.schemas.error import ErrorResponse
from app.services import assessment_service

router = APIRouter(
    prefix="/assessments",
    tags=["Assessments"],
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
Session = Annotated[dict, Depends(get_current_session)]


@router.post("/{assessment_id}/explain", response_model=ExplainResponse)
def explain(
    assessment_id: int,
    payload: ExplainInput,
    session: Session,
    db=Depends(get_db),
):
    return {
        "data": assessment_service.explain(
            db, session["session_id"], assessment_id, payload.max_words
        )
    }
