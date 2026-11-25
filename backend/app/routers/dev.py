from fastapi import APIRouter, Depends

from app.dependencies import get_db
from app.schemas.error import ErrorResponse
from app.schemas.system_support import DemoSeedInput, DemoSeedResponse
from app.services import demo_service

router = APIRouter(
    prefix="/dev",
    tags=["System support"],
    dependencies=[Depends(demo_service.require_demo_environment)],
)


@router.post(
    "/seed-demo",
    status_code=201,
    response_model=DemoSeedResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def seed_demo(payload: DemoSeedInput, db=Depends(get_db)):
    return demo_service.seed(db, reset=payload.reset)
