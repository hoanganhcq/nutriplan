import os
from urllib.parse import urlsplit

import pytest


def pytest_configure():
    test_url = os.getenv("TEST_DATABASE_URL")
    if test_url:
        if not urlsplit(test_url).path.lstrip("/").endswith("_test"):
            raise pytest.UsageError(
                "TEST_DATABASE_URL must point to a database ending in _test"
            )
        from app.core.config import settings

        settings.database_url = test_url
        settings.environment = "test"
        settings.vision_provider = "mock"


def pytest_collection_modifyitems(items):
    if os.getenv("TEST_DATABASE_URL"):
        return
    marker = pytest.mark.skip(
        reason="Set TEST_DATABASE_URL or use tests/run_isolated.py"
    )
    for item in items:
        if item.path.name in {"test_households.py", "test_profiles.py"}:
            item.add_marker(marker)
