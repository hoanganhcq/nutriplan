import sqlite3
from pathlib import Path

from app.core.config import settings

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


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


def get_connection() -> sqlite3.Connection:
    """Mở kết nối SQLite với kiểm tra khóa ngoại được bật."""

    connection = sqlite3.connect(get_database_path(), timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    """Tạo các bảng/index nếu database chưa được khởi tạo."""

    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as connection:
        household_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(HOUSEHOLD)")
        }
        if household_columns and "session_id" not in household_columns:
            connection.execute(
                "ALTER TABLE HOUSEHOLD ADD COLUMN session_id INTEGER"
            )
        table_names = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if "USER_PROFILE" in table_names and "MEMBER" not in table_names:
            connection.execute("ALTER TABLE USER_PROFILE RENAME TO MEMBER")
        connection.executescript(schema)
        profile_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(MEMBER)")
        }
        for column, definition in {
            "sex": "VARCHAR(20)",
            "energy_target_kcal": "INTEGER",
            "texture_requirements": "VARCHAR(20)",
        }.items():
            if profile_columns and column not in profile_columns:
                connection.execute(
                    f"ALTER TABLE MEMBER ADD COLUMN {column} {definition}"
                )


def check_database_connection() -> bool:
    """
    Kiểm tra database có kết nối được hay không.
    """

    try:
        with get_connection() as connection:
            connection.execute("SELECT 1")

        return True

    except (sqlite3.Error, ValueError, OSError):
        return False
