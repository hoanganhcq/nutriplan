from fastapi import APIRouter

from app.schemas.health import HealthResponse
from app.services import health_service

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health_check():
    return health_service.health_check()

@router.get("/services/vision")
def vision_status():
    mode = health_service.vision_service.mode()
    status = "available" if mode in {"mock", "http"} else "unavailable"
    return {
        "status": status,
        "provider": mode,
        "supports": {
            "referenceObject": True,
            "portionConfidence": True,
            "entityTypes": ["DISH", "INGREDIENT", "NON_FOOD"],
        },
    }
