import logging
from functools import lru_cache
from importlib.util import find_spec, module_from_spec, spec_from_file_location
from pathlib import Path
from threading import Lock

from app.core.exceptions import AppException
from app.repositories import dish_repository

ROOT = Path(__file__).resolve().parents[3]
AI = ROOT / "ai"
MODEL_DIR = AI / "models/vietfood"
KB_DIR = ROOT / "data/knowledge_base/vietfood"
LOCK = Lock()
logger = logging.getLogger(__name__)


def _load_module(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=1)
def _catalog():
    tools = _load_module("vietfood_kb", AI / "src/rag/vietfood_kb.py")
    kb = tools.load_kb(KB_DIR)
    tools.validate(kb)
    foods = {food["food_id"]: food for food in kb["food"]["foods"]}
    sources = {source["source_id"]: source for source in kb["sources"]["sources"]}
    return tools, kb, foods, sources


def _import_food(db, food, sources):
    source = sources[food["nutrition"]["source_id"]]
    return dish_repository.import_vietfood(db, food, source)


def import_catalog(db):
    _, _, foods, sources = _catalog()
    for food in foods.values():
        _import_food(db, food, sources)
    return len(foods)


def available():
    return all(
        find_spec(name) is not None
        for name in (
            "torch",
            "torchvision",
            "ultralytics",
            "PIL",
            "jsonschema",
        )
    ) and all(
        path.is_file()
        for path in (
            MODEL_DIR / "models/food_detector.pt",
            MODEL_DIR / "models/portion_foodcnn_v2.pt",
            KB_DIR / "data/food_kb.json",
        )
    )


@lru_cache(maxsize=1)
def _model():
    adapter = _load_module("vietfood_adapter", AI / "src/vision/vietfood_adapter.py")
    return adapter.FoodAdapter(MODEL_DIR, device="cpu")


def recognize(db, images):
    if len(images) != 1:
        raise AppException(
            "VALIDATION_ERROR", "VietFood accepts one image per meal", 422
        )
    if not available():
        raise AppException(
            "VISION_UNAVAILABLE", "VietFood assets or libraries missing", 503
        )

    from PIL import Image, UnidentifiedImageError

    with LOCK:
        try:
            model = _model()
            tools, kb, foods, sources = _catalog()
        except Exception as exc:
            logger.exception("Could not initialize VietFood")
            raise AppException(
                "VISION_UNAVAILABLE", "Could not initialize VietFood", 503
            ) from exc
        try:
            prediction = model.predict(images[0][1])
        except (
            UnidentifiedImageError,
            Image.DecompressionBombError,
            OSError,
            ValueError,
        ) as exc:
            raise AppException(
                "INVALID_IMAGE", "Invalid image for VietFood", 422
            ) from exc

    labels = {
        entry["model_label"]: entry["name_vi"] for entry in kb["mapping"]["entries"]
    }
    scores = {
        row["detection_id"]: row["confidence"] for row in prediction["detections"]
    }
    candidates = tools.adapter_candidates(kb, prediction)
    food_ids = {food_id for row in candidates for food_id in row["candidate_food_ids"]}
    dish_ids = {
        food_id: _import_food(db, foods[food_id], sources)
        for food_id in sorted(food_ids)
    }
    suggestions = []
    for row in candidates:
        suggestions.append(
            {
                "name": labels[row["model_label"]],
                "confidence": scores[row["detection_id"]],
                "grams": row["suggested_mass_g"],
                "dishes": [
                    {"dishId": dish_ids[food_id], "name": foods[food_id]["name_vi"]}
                    for food_id in row["candidate_food_ids"]
                ],
            }
        )
    return suggestions, prediction["warnings"]
