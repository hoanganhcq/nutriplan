from datetime import date as Date
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.profiles import ALLOWED_ALLERGIES, ALLOWED_CONDITIONS


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda s: (
            s.split("_")[0] + "".join(p.title() for p in s.split("_")[1:])
        ),
        populate_by_name=True,
    )


ConsentType = Literal[
    "store_health_profile",
    "send_image_to_ai_provider",
    "llm_explanation",
    "usage_analytics",
]


class ConsentUpdate(CamelModel):
    household_id: int = Field(gt=0)
    policy_version: str = Field(min_length=1, max_length=30)
    consents: dict[ConsentType, bool] = Field(min_length=1)


class MemberInput(CamelModel):
    household_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=1, le=120)
    sex: Literal["male", "female", "other", "undisclosed"] | None = None
    weight_kg: float | None = Field(default=None, gt=0, le=500)
    height_cm: float | None = Field(default=None, gt=30, le=250)
    conditions: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    energy_goal_kcal: int | None = Field(default=None, ge=1, le=10000)
    preferences: list[str] = Field(default_factory=list)
    texture: Literal["normal", "soft", "minced", "liquid", "other"] | None = None
    is_simulated: bool = False

    @field_validator("conditions")
    @classmethod
    def validate_conditions(cls, values: list[str]) -> list[str]:
        if set(values) - ALLOWED_CONDITIONS or ("none" in values and len(values) > 1):
            raise ValueError("Unsupported conditions")
        return values

    @field_validator("allergies")
    @classmethod
    def validate_allergies(cls, values: list[str]) -> list[str]:
        if set(values) - ALLOWED_ALLERGIES or ("none" in values and len(values) > 1):
            raise ValueError("Unsupported allergies")
        return values


class MealItemUpdate(CamelModel):
    dish_id: int | None = Field(default=None, gt=0)
    grams: float | None = Field(default=None, gt=0, le=10000)
    seasoning: str | None = Field(default=None, max_length=500)


class AssessmentInput(CamelModel):
    member_ids: list[int] | None = None


class UndoInput(CamelModel):
    steps: int = Field(default=1, ge=1, le=5)


class ConfirmInput(CamelModel):
    eaten_by: list[int] | None = Field(default=None, min_length=1)
    note: str | None = Field(default=None, max_length=2000)


class ExplainInput(CamelModel):
    style: Literal["simple"] = "simple"
    max_words: int = Field(default=80, ge=1, le=200)


class MenuGenerateInput(CamelModel):
    member_id: int = Field(gt=0)
    days: int = Field(default=1, ge=1, le=3)
    start_date: Date
    meals_per_day: (
        list[Literal["breakfast", "lunch", "dinner", "snack", "snack2", "snack3"]] | int
    ) = Field(default_factory=lambda: ["breakfast", "lunch", "dinner"])
    prefer_dish_ids: list[int] = Field(default_factory=list)
    exclude_dish_ids: list[int] = Field(default_factory=list)
    max_cooking_effort: Literal["easy", "medium", "hard"] | None = None
    seed: int | None = None

    @field_validator("meals_per_day")
    @classmethod
    def validate_meals_per_day(cls, value):
        if isinstance(value, int):
            if not 1 <= value <= 6:
                raise ValueError("mealsPerDay count must be between 1 and 6")
        elif not value or len(value) > 6 or len(set(value)) != len(value):
            raise ValueError("mealsPerDay must contain 1 to 6 unique meal types")
        return value

    @property
    def meal_types(self):
        if isinstance(self.meals_per_day, int):
            return ["breakfast", "lunch", "dinner", "snack", "snack2", "snack3"][
                : self.meals_per_day
            ]
        return self.meals_per_day


class MenuItemUpdate(CamelModel):
    dish_id: int = Field(gt=0)
    grams: float = Field(gt=0, le=10000, allow_inf_nan=False)


class MenuItemLock(CamelModel):
    locked: bool


class MenuRegenerateInput(CamelModel):
    scope: Literal["all_unlocked", "day", "meal", "item"] = "all_unlocked"
    date: Date | None = None
    meal_type: (
        Literal["breakfast", "lunch", "dinner", "snack", "snack2", "snack3"] | None
    ) = None
    item_id: int | None = Field(default=None, gt=0)
    seed: int | None = None

    @model_validator(mode="after")
    def validate_scope_fields(self):
        if self.scope == "day" and self.date is None:
            raise ValueError("date is required for day scope")
        if self.scope == "meal" and (self.date is None or self.meal_type is None):
            raise ValueError("date and mealType are required for meal scope")
        if self.scope == "item" and self.item_id is None:
            raise ValueError("itemId is required for item scope")
        return self


class PageMeta(CamelModel):
    next_cursor: int | None = None


class ConsentOutput(CamelModel):
    household_id: int
    policy_version: str
    consents: dict[ConsentType, bool]


class MemberOutput(CamelModel):
    member_id: int
    household_id: int
    name: str
    age: int
    sex: str | None
    weight_kg: float | None
    height_cm: float | None
    bmi: float | None
    conditions: list[str]
    allergies: list[str]
    preferences: list[str]
    energy_goal_kcal: int | None
    texture: str | None
    is_simulated: bool
    profile_version: int


class NutritionOutput(CamelModel):
    kcal: float | None
    protein_g: float | None
    carb_g: float | None
    fat_g: float | None


class SourceOutput(BaseModel):
    name: str | None
    url: str | None


class DishOutput(CamelModel):
    dish_id: int
    name: str
    category: str | None
    entity_type: str = "DISH"
    default_portion_g: float | None
    per100g: NutritionOutput
    source: SourceOutput


class MealItemOutput(CamelModel):
    item_id: int
    dish_id: int
    name: str
    grams: float
    seasoning: str | None
    confidence: float | None
    portion_confidence: float | None = None
    portion_method: str | None = None
    entity_type: str = "DISH"
    bbox: dict | None = None
    is_estimate: bool
    nutrition: NutritionOutput


class MealOutput(CamelModel):
    meal_id: int
    household_id: int
    meal_type: str | None
    eaten_at: datetime
    status: str
    revision: int
    items: list[MealItemOutput]
    confidence: float | None
    totals: NutritionOutput
    member_ids: list[int]
    is_estimate: bool
    warnings: list[str]


class AssessmentOutput(CamelModel):
    assessment_id: int
    member_id: int
    meal_revision: int
    profile_version: int
    level: str
    reasons: list[str]
    ruleset_version: str | None
    hard_constraints_passed: bool
    key_metrics: NutritionOutput
    alternatives: list[str]
    stale: bool


class JournalLevelOutput(CamelModel):
    member_id: int
    level: str


class JournalEntryOutput(CamelModel):
    meal_id: int
    eaten_at: datetime
    meal_type: str | None
    thumbnail_url: str | None
    item_names: list[str]
    totals: NutritionOutput
    levels: list[JournalLevelOutput]


class ExplainOutput(CamelModel):
    assessment_id: int
    generated_by: Literal["template", "llm"]
    explanation: str
    disclaimer: str


class MealUndoOutput(CamelModel):
    revision: int
    can_undo: bool
    meal: "MealOutput"


class AssessmentRunOutput(CamelModel):
    meal_id: int
    assessments: list[AssessmentOutput]
    warnings: list[str]


class ConfirmedMealOutput(CamelModel):
    meal_id: int
    status: str
    confirmed_at: datetime
    journal_entries: list[JournalLevelOutput]


class ValidationOutput(CamelModel):
    level: str
    reasons: list[str]
    ruleset_version: str | None
    hard_constraints_passed: bool


class MenuItemOutput(CamelModel):
    meal_type: str
    dish_id: int
    name: str
    grams: float
    nutrition: NutritionOutput


class MenuOutput(CamelModel):
    plan_id: int
    member_id: int
    start_date: Date
    days: int
    status: str
    revision: int
    meals: list[MenuItemOutput]
    day_totals: NutritionOutput
    validation: ValidationOutput
    soft_score: float | None


class ConsentResponse(BaseModel):
    data: ConsentOutput


class MemberResponseE2E(BaseModel):
    data: MemberOutput


class MemberListResponse(BaseModel):
    data: list[MemberOutput]


class DishListResponse(BaseModel):
    data: list[DishOutput]
    meta: PageMeta


class MealResponse(BaseModel):
    data: MealOutput


class MealListResponse(BaseModel):
    data: list[JournalEntryOutput]
    meta: PageMeta


class MealUndoResponse(BaseModel):
    data: MealUndoOutput


class AssessmentResponse(BaseModel):
    data: AssessmentRunOutput


class ExplainResponse(BaseModel):
    data: ExplainOutput


class ConfirmResponse(BaseModel):
    data: ConfirmedMealOutput


class MenuResponse(BaseModel):
    data: MenuOutput
