"""Kiểm thử tích hợp trên database development bằng giao dịch rollback."""

import os
from urllib.parse import unquote, urlsplit

import pytest

DEVELOPMENT_DATABASES = {"nutriplan", "nutrition_ai"}


def pytest_configure(config):
    if os.getenv("TEST_DATABASE_URL"):
        raise pytest.UsageError(
            "Không dùng TEST_DATABASE_URL ở giai đoạn này; "
            "hãy dùng DATABASE_URL=.../nutriplan"
        )
    from app.core.config import settings

    parsed = urlsplit(settings.database_url)
    if unquote(parsed.path.lstrip("/")) not in DEVELOPMENT_DATABASES:
        raise pytest.UsageError(
            "Pytest chỉ được dùng database development nutriplan hoặc nutrition_ai"
        )
    settings.environment = "test"
    settings.vision_provider = "mock"


@pytest.fixture(autouse=True)
def rollback_integration_data(request):
    if not request.node.get_closest_marker("integration"):
        yield
        return

    from app.db.database import get_connection
    from app.dependencies import get_db
    from app.main import app

    db = get_connection()
    try:
        actual = db.execute("SELECT DATABASE() AS name").fetchone()["name"]
        from app.core.config import settings

        configured = unquote(urlsplit(settings.database_url).path.lstrip("/"))
        if actual not in DEVELOPMENT_DATABASES or actual != configured:
            raise pytest.UsageError("Kết nối sai database; dừng trước khi ghi test")

        def transactional_db():
            yield db

        if get_db in app.dependency_overrides:
            raise pytest.UsageError("Test tích hợp đã ghi đè get_db ngoài fixture")
        app.dependency_overrides[get_db] = transactional_db
        try:
            yield
        finally:
            app.dependency_overrides.pop(get_db, None)
    finally:
        db._connection.rollback()
        db._connection.close()
