from typing import Literal

from pydantic import (
    AwareDatetime,
    ConfigDict,
    Field,
    JsonValue,
    StrictBool,
    model_validator,
)

from app.schemas.e2e import CamelModel


class SupportModel(CamelModel):
    model_config = ConfigDict(extra="forbid")


class DemoSeedInput(SupportModel):
    reset: StrictBool = False


class DemoSeedOutput(SupportModel):
    household_id: int
    token: str
    members: int
    dishes: int
    rules: int


class DemoSeedResponse(SupportModel):
    data: DemoSeedOutput


EventType = Literal[
    "task_start",
    "task_end",
    "dish_corrected",
    "portion_corrected",
    "error_shown",
    "undo_used",
    "menu_item_swapped",
    "menu_item_locked",
]
TaskType = Literal[
    "log_meal",
    "review_meal",
    "generate_menu",
    "plan_menu",
    "edit_menu",
    "manage_profiles",
]


class UsageEventInput(SupportModel):
    type: EventType
    task: TaskType | None = None
    at: AwareDatetime
    # Arbitrary JSON is inspected before persistence, never copied into storage.
    meta: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_task(self):
        if self.type in {"task_start", "task_end"} and self.task is None:
            raise ValueError("task is required for task_start and task_end")
        return self


class EventsInput(SupportModel):
    session_id: str = Field(
        min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$", strict=True
    )
    participant_id: str = Field(pattern=r"^P[0-9]{1,4}$", strict=True)
    events: list[UsageEventInput] = Field(min_length=1, max_length=100)


class EventsOutput(SupportModel):
    accepted: int
    dropped: int


class EventsResponse(SupportModel):
    data: EventsOutput
