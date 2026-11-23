import math
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RuleEvaluationProfile(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    conditions: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    texture: str | None = None
    energy_goal_kcal: int | None = Field(default=None, alias="energyGoalKcal", ge=0)


class RuleEvaluationInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    profile: RuleEvaluationProfile
    nutrition: dict[str, Annotated[float, Field(allow_inf_nan=False, ge=0)]]
    dish_ids: list[str] = Field(alias="dishIds", default_factory=list)

    @field_validator("nutrition")
    @classmethod
    def require_finite_nutrients(cls, values: dict[str, float]) -> dict[str, float]:
        if any(not math.isfinite(value) for value in values.values()):
            raise ValueError("Nutrition values must be finite")
        return values


RuleScope = Literal["meal", "day", "dish"]
