from fastapi import APIRouter

from app.db.database import check_database_connection
from app.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health_check():

    database_status = "ok" if check_database_connection() else "unavailable"

    overall_status = "ok" if database_status == "ok" else "degraded"

    return HealthResponse(status=overall_status, database=database_status)
