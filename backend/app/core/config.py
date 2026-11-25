from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Meal Analysis API"
    app_version: str = "0.1.0"

    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "ENV", "environment"),
    )

    database_url: str
    vision_provider: str = "unavailable"
    vision_url: str | None = None
    vision_api_key: str | None = None
    vision_mock_detections: str = "[]"
    vision_health_url: str | None = None
    vision_health_timeout_seconds: float = Field(default=1.0, gt=0, le=5)

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
