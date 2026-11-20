import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.exceptions import AppException
from app.routers.consents import router as consents_router
from app.routers.dishes import router as dishes_router
from app.routers.health import router as health_router
from app.routers.households import router as households_router
from app.routers.meals import router as meals_router
from app.routers.members import router as members_router
from app.routers.menu_plans import router as menu_plans_router
from app.routers.profiles import router as profiles_router
from app.routers.sessions import router as sessions_router

logger = logging.getLogger(__name__)


# 1. Khởi tạo FastAPI
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Backend API for AI Meal Analysis System",
)


# 2. Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 3. Xử lý lỗi nghiệp vụ
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


# 4. Xử lý lỗi HTTP
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "HTTP_ERROR", "message": str(exc.detail)}},
        headers=exc.headers,
    )


# 5. Xử lý lỗi dữ liệu đầu vào
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request data is invalid.",
                "details": jsonable_encoder(exc.errors()),
            }
        },
    )


# 6. Xử lý lỗi server không dự kiến
@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception):

    # Không log ảnh, request body hoặc dữ liệu sức khỏe cá nhân.
    logger.error("Unhandled %s at %s", type(exc).__name__, request.url.path)

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred.",
            }
        },
    )


# 7. Đăng ký router
app.include_router(health_router)
app.include_router(households_router)
app.include_router(sessions_router)
app.include_router(profiles_router)
app.include_router(consents_router)
app.include_router(members_router)
app.include_router(dishes_router)
app.include_router(meals_router)
app.include_router(menu_plans_router)
