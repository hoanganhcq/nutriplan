from urllib.error import URLError
from urllib.request import Request, urlopen

from mysql.connector import Error as MySQLError

from app.core.config import settings
from app.db.database import get_connection
from app.repositories import health_repository
from app.schemas.health import HealthResponse, ServiceHealth
from app.services import vietfood, vision_service


def vision_status():
    if vision_service.mode() == "vietfood":
        return "ok" if vietfood.available() else "degraded"
    # An inference URL alone does not establish that a provider is reachable.
    if (
        vision_service.mode() != "http"
        or not settings.vision_url
        or not settings.vision_health_url
    ):
        return "degraded"
    try:
        request = Request(
            settings.vision_health_url,
            headers=(
                {"Authorization": f"Bearer {settings.vision_api_key}"}
                if settings.vision_api_key
                else {}
            ),
        )
        with urlopen(
            request, timeout=settings.vision_health_timeout_seconds
        ) as response:
            return "ok" if 200 <= response.status < 300 else "down"
    except (URLError, OSError, ValueError):
        return "down"


def health_check() -> HealthResponse:
    db_status = "ok"
    versions = []
    try:
        with get_connection() as db:
            versions = health_repository.probe(db)
    except (MySQLError, ValueError, OSError):
        db_status = "down"
    vision = vision_status()
    return HealthResponse(
        status=(
            "ok"
            if db_status == "ok" and vision == "ok" and len(versions) <= 1
            else "degraded"
        ),
        version=settings.app_version,
        ruleset_version=versions[0] if len(versions) == 1 else None,
        services=ServiceHealth(db=db_status, vision=vision),
    )
