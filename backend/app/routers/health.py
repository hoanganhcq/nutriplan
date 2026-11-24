from fastapi import APIRouter, Response

from app.schemas.health import HealthResponse
from app.services import health_service

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse, "description": "Database unavailable"}},
)
def health_check(response: Response):
    result = health_service.health_check()
    if result.services.db == "down":
        response.status_code = 503
    return result


@router.get("/services/vision")
def vision_status():
    mode = health_service.vision_service.mode()
    status = "available" if health_service.vision_status() == "ok" else "unavailable"
    return {
        "status": status,
        "provider": mode,
        "supports": {
            "referenceObject": True,
            "portionConfidence": True,
            "entityTypes": ["DISH", "INGREDIENT", "NON_FOOD"],
        },
    }
