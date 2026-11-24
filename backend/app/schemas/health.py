from typing import Literal

from pydantic import BaseModel, Field


class ServiceHealth(BaseModel):
    db: Literal["ok", "down"]
    vision: Literal["ok", "degraded", "down"]
    llm: Literal["disabled"] = "disabled"


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]

    version: str
    ruleset_version: str | None = Field(serialization_alias="rulesetVersion")
    services: ServiceHealth
