import base64
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import settings
from app.core.exceptions import AppException


def mode():
    return settings.vision_provider


def recognize(images):
    """Return provider detections; never invent food labels in production."""
    if settings.vision_provider == "mock" and settings.environment in {"test", "demo"}:
        try:
            detections = json.loads(settings.vision_mock_detections)
        except ValueError as exc:
            raise AppException(
                "VISION_UNAVAILABLE", "Mock detections are invalid", 503
            ) from exc
        if not isinstance(detections, list):
            raise AppException("VISION_UNAVAILABLE", "Mock detections are invalid", 503)
        return detections, ["Demo vision mode; detections are mocked"]
    if settings.vision_provider != "http" or not settings.vision_url:
        raise AppException(
            "VISION_UNAVAILABLE", "Vision provider is not configured", 503
        )
    payload = {
        "images": [
            {"mimeType": mime, "base64": base64.b64encode(content).decode("ascii")}
            for mime, content in images
        ]
    }
    request = Request(
        settings.vision_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            **(
                {"Authorization": f"Bearer {settings.vision_api_key}"}
                if settings.vision_api_key
                else {}
            ),
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            body = json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise AppException("VISION_UNAVAILABLE", "Vision provider failed", 502) from exc
    detections = body.get("detections")
    if not isinstance(detections, list):
        raise AppException("VISION_UNAVAILABLE", "Vision response is invalid", 502)
    return detections, []
