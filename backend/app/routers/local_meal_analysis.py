from typing import Literal

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.services import local_meal_analysis
from app.services.meal_service import validate_images

router = APIRouter(prefix="/local-meal-analysis", tags=["local meal analysis"])


class ReviewedItem(BaseModel):
    food_id: str = Field(min_length=1, max_length=80)
    grams: float = Field(gt=0, le=10000, allow_inf_nan=False)
    quantity_source: Literal["user_entered", "model_estimate"]
    detection_id: str | None = Field(default=None, pattern=r"^det_\d{4}$")


class ReviewedMeal(BaseModel):
    items: list[ReviewedItem] = Field(min_length=1, max_length=25)
    overlap_reviewed: Literal[True]
    query: str = Field(default="Carbohydrate và natri", min_length=1, max_length=300)


@router.get("/foods")
def foods():
    return local_meal_analysis.catalog()


@router.post("/recognize")
async def recognize(image: UploadFile = File()):
    [(_, content)] = await validate_images([image])
    return await run_in_threadpool(local_meal_analysis.recognize, content)


@router.post("/assess")
def assess(meal: ReviewedMeal):
    return local_meal_analysis.assess(meal.items, meal.query)
