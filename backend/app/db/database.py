import sqlite3
from pathlib import Path

from app.core.config import settings


def get_database_path() -> str:
    """
    Chuyển DATABASE_URL thành đường dẫn file SQLite.
    """

    prefix = "sqlite:///"

    if not settings.database_url.startswith(prefix):
        raise ValueError("Only SQLite database URLs are supported.")

    raw_path = settings.database_url[len(prefix) :]

    if raw_path == ":memory:":
        return raw_path

    path = Path(raw_path)

    if not path.is_absolute():
        path = Path.cwd() / path

    path.parent.mkdir(parents=True, exist_ok=True)

    return str(path)


def check_database_connection() -> bool:
    """
    Kiểm tra database có kết nối được hay không.
    """

    try:
        with sqlite3.connect(get_database_path(), timeout=2) as connection:
            connection.execute("SELECT 1")

        return True

    except (sqlite3.Error, ValueError, OSError):
        return False
