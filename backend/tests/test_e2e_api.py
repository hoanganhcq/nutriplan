from fastapi.testclient import TestClient

from app.dependencies import get_current_session, get_db
from app.main import app


class DummyDB:
    pass


def test_upload_rejects_bad_signature_without_database():
    app.dependency_overrides[get_current_session] = lambda: {"session_id": 1}
    app.dependency_overrides[get_db] = lambda: DummyDB()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/meals/analyze",
                data={"householdId": "1"},
                files=[("images", ("bad.png", b"not an image", "image/png"))],
            )
        assert response.status_code == 415
        assert response.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"
    finally:
        app.dependency_overrides.clear()


def test_new_private_endpoints_require_session():
    app.dependency_overrides[get_db] = lambda: DummyDB()
    try:
        with TestClient(app) as client:
            for path in (
                "/consents?householdId=1",
                "/members?householdId=1",
                "/dishes",
                "/meals",
                "/menu-plans/1",
            ):
                response = client.get(path)
                assert response.status_code == 401, path
    finally:
        app.dependency_overrides.clear()


def test_dish_response_matches_openapi_schema(monkeypatch):
    app.dependency_overrides[get_current_session] = lambda: {"session_id": 1}
    app.dependency_overrides[get_db] = lambda: DummyDB()
    monkeypatch.setattr(
        "app.routers.dishes.dish_service.search",
        lambda *args: {
            "data": [
                {
                    "dishId": 7,
                    "name": "Test dish",
                    "category": None,
                    "defaultPortionG": 100,
                    "per100g": {"kcal": 120, "proteinG": 5, "carbG": 15, "fatG": 4},
                    "source": {"name": "Test source", "url": "https://example.test"},
                }
            ],
            "meta": {"nextCursor": None},
        },
    )
    try:
        with TestClient(app) as client:
            response = client.get("/dishes")
        assert response.status_code == 200
        assert response.json()["data"][0]["dishId"] == 7
    finally:
        app.dependency_overrides.clear()


def test_openapi_includes_all_e2e_paths():
    schema = app.openapi()
    for path in (
        "/consents",
        "/members",
        "/dishes",
        "/meals/analyze",
        "/meals/{meal_id}/assessments",
        "/meals/{meal_id}/undo",
        "/meals/{meal_id}/confirm",
        "/meals/{meal_id}",
        "/assessments/{assessment_id}/explain",
        "/menu-plans/generate",
    ):
        assert path in schema["paths"]
    assert "get" in schema["paths"]["/meals/{meal_id}/assessments"]
    assert "delete" in schema["paths"]["/meals/{meal_id}"]
