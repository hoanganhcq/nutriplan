from pydantic import BaseModel, ConfigDict, Field, field_validator

ALLOWED_CONDITIONS = {
    "diabetes",
    "hypertension",
    "dyslipidemia",
    "obesity",
    "kidney_disease",
    "gout",
    "celiac",
    "none",
}
ALLOWED_ALLERGIES = {
    "milk",
    "egg",
    "peanut",
    "tree_nut",
    "soy",
    "wheat",
    "fish",
    "shellfish",
    "none",
}


def _validate_choices(value: list[str], allowed: set[str], field: str) -> list[str]:
    invalid = sorted(set(value) - allowed)
    if invalid:
        raise ValueError(f"{field} contains unsupported values: {', '.join(invalid)}")
    if "none" in value and len(value) > 1:
        raise ValueError(f"{field} cannot combine 'none' with another value")
    return value


class MemberCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=1, le=120)
    sex: str | None = Field(default=None, pattern="^(male|female|other|undisclosed)$")
    weight_kg: float | None = Field(default=None, gt=0, le=500)
    height_cm: float | None = Field(default=None, gt=30, le=250)
    conditions: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    food_preferences: list[str] = Field(default_factory=list)
    energy_target_kcal: int | None = Field(default=None, ge=1, le=10000)
    texture_requirements: str | None = Field(
        default=None, pattern="^(normal|soft|minced|liquid|other)$"
    )

    @field_validator("conditions")
    @classmethod
    def validate_conditions(cls, value: list[str]) -> list[str]:
        return _validate_choices(value, ALLOWED_CONDITIONS, "conditions")

    @field_validator("allergies")
    @classmethod
    def validate_allergies(cls, value: list[str]) -> list[str]:
        return _validate_choices(value, ALLOWED_ALLERGIES, "allergies")


class ProfileCreateRequest(BaseModel):
    household_name: str = Field(min_length=1, max_length=100)
    members: list[MemberCreate] = Field(min_length=1)

    model_config = {
        "json_schema_extra": {
            "example": {
                "household_name": "Gia đình Demo",
                "members": [
                    {
                        "name": "Nguyễn Văn An",
                        "age": 25,
                        "sex": "male",
                        "weight_kg": 65,
                        "height_cm": 170,
                        "conditions": ["diabetes"],
                        "allergies": ["peanut"],
                        "food_preferences": [],
                        "energy_target_kcal": 2200,
                        "texture_requirements": "normal",
                    }
                ],
            }
        }
    }


class MemberUpdate(MemberCreate):
    pass


class MemberResponse(MemberCreate):
    model_config = ConfigDict(from_attributes=True)
    member_id: int


class ProfileResponse(BaseModel):
    profile_id: int
    household_name: str
    members: list[MemberResponse]


class HouseholdCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
