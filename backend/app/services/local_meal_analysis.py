import json
import logging
from functools import lru_cache
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from threading import Lock
from uuid import uuid4

from app.core.config import settings
from app.core.exceptions import AppException

ROOT = Path(__file__).resolve().parents[3]
AI_ROOT = ROOT / "ai"
KB_ROOT = ROOT / "data/knowledge_base/vietfood"
MODEL_ROOT = AI_ROOT / "models/vietfood"
MODEL_LOCK = Lock()
logger = logging.getLogger(__name__)


def load_module(name, path):
    spec = spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {name}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=1)
def knowledge_base():
    tools = load_module("vietfood_kb", AI_ROOT / "src/rag/vietfood_kb.py")
    kb = tools.load_kb(KB_ROOT)
    tools.validate(kb)
    profile_path = KB_ROOT / "examples/user_profile.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    tools.validate_document(kb, profile, "Profile")
    return tools, kb, profile


@lru_cache(maxsize=1)
def model():
    adapter_path = AI_ROOT / "src/vision/vietfood_adapter.py"
    adapter = load_module("vietfood_adapter", adapter_path)
    return adapter.FoodAdapter(MODEL_ROOT, device=settings.local_meal_analysis_device)


def catalog():
    _, kb, _ = knowledge_base()
    return [
        {"food_id": food["food_id"], "name_vi": food["name_vi"]}
        for food in kb["food"]["foods"]
    ]


def recognize(content):
    from PIL import Image, UnidentifiedImageError

    with MODEL_LOCK:
        try:
            adapter = model()
        except Exception as exc:
            logger.error("Local VietFood load failed (%s)", type(exc).__name__)
            raise AppException(
                "VISION_UNAVAILABLE", "Không nạp được model VietFood.", 503
            ) from exc
        try:
            prediction = adapter.predict(content)
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
            raise AppException(
                "INVALID_IMAGE", "Ảnh bị lỗi hoặc vượt giới hạn.", 422
            ) from exc
        except ValueError as exc:
            raise AppException(
                "INVALID_IMAGE", "Ảnh hoặc kết quả nhận diện không hợp lệ.", 422
            ) from exc

    tools, kb, _ = knowledge_base()
    candidates = tools.adapter_candidates(kb, prediction)
    labels = {
        entry["model_label"]: entry["name_vi"] for entry in kb["mapping"]["entries"]
    }
    scores = {
        detection["detection_id"]: detection["confidence"]
        for detection in prediction["detections"]
    }
    return {
        "detections": [
            {
                **candidate,
                "name_vi": labels[candidate["model_label"]],
                "confidence": scores[candidate["detection_id"]],
            }
            for candidate in candidates
        ],
        "warnings": prediction["warnings"],
    }


def assess(items, query):
    tools, kb, profile = knowledge_base()
    request = {
        "request_id": str(uuid4()),
        "period": "meal",
        "day_log_complete": False,
        "overlap_reviewed": True,
        "items": [
            {
                "item_id": str(index),
                "food_id": item.food_id,
                "amount": item.grams,
                "unit": "g",
                "quantity_source": item.quantity_source,
                "food_confirmed": True,
                "quantity_confirmed": item.quantity_source != "model_estimate",
                "detection_ids": [item.detection_id] if item.detection_id else [],
            }
            for index, item in enumerate(items, 1)
        ],
    }
    try:
        payload = tools.prepare_rag(kb, request, profile, query)
    except ValueError as exc:
        raise AppException("INVALID_MEAL", str(exc), 422) from exc
    return {
        "nutrition": payload["nutrition"],
        "clinical_evidence": payload["clinical_evidence"],
        "clinical_review_status": payload["clinical_review_status"],
        "missing_context": payload["assessment"]["missing_context"],
        "demo_conditions": profile["conditions"],
    }
