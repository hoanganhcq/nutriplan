"""Create and use a dedicated local MySQL test database; never touch source rows."""

import os
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit

import mysql.connector
import pytest
from mysql.connector import Error as MySQLError


def main():
    from app.core.config import settings

    if os.getenv("TEST_DATABASE_URL"):
        test_url = os.environ["TEST_DATABASE_URL"]
        if not urlsplit(test_url).path.lstrip("/").endswith("_test"):
            raise SystemExit(
                "TEST_DATABASE_URL must point to a database ending in _test"
            )
        settings.database_url = test_url
        settings.environment = "test"
        settings.vision_provider = "mock"
        return pytest.main(["-q", "-p", "no:cacheprovider", "tests"])

    parsed = urlsplit(settings.database_url)
    source_name = unquote(parsed.path.lstrip("/"))
    if not re.fullmatch(r"[A-Za-z0-9_]+", source_name):
        raise ValueError("Unsafe database name")
    test_name = f"{source_name}_e2e_test"
    connection = mysql.connector.connect(
        host=parsed.hostname,
        port=parsed.port or 3306,
        user=unquote(parsed.username),
        password=unquote(parsed.password or ""),
        charset="utf8mb4",
        autocommit=True,
    )
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{test_name}` CHARACTER SET utf8mb4"
        )
    except MySQLError as exc:
        raise SystemExit(
            "Cannot create the isolated test database. Supply TEST_DATABASE_URL "
            "with a dedicated database or grant CREATE to a test administrator."
        ) from exc
    cursor.execute(f"USE `{test_name}`")
    schema = Path(__file__).parents[1] / "app" / "db" / "schema.sql"
    for statement in schema.read_text(encoding="utf-8").split(";"):
        if statement.strip():
            cursor.execute(statement)
    cursor.close()
    connection.close()
    os.environ["DATABASE_URL"] = urlunsplit(parsed._replace(path=f"/{test_name}"))
    os.environ["TEST_DATABASE_URL"] = os.environ["DATABASE_URL"]
    os.environ["ENVIRONMENT"] = "test"
    os.environ["VISION_PROVIDER"] = "mock"
    settings.database_url = os.environ["DATABASE_URL"]
    settings.environment = "test"
    settings.vision_provider = "mock"
    return pytest.main(["-q", "-p", "no:cacheprovider", "tests"])


if __name__ == "__main__":
    raise SystemExit(main())
