from app.db.database import check_database_connection
from app.schemas.health import HealthResponse
from app.services import vision_service


def health_check() -> HealthResponse:
    database_status = "ok" if check_database_connection() else "unavailable"
    vision_status = "ok" if vision_service.mode() in {"mock", "http"} else "degraded"
    overall_status = "ok" if database_status == "ok" and vision_status == "ok" else "degraded"
    return HealthResponse(status=overall_status, database=database_status)
