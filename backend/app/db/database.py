from collections.abc import Sequence
from urllib.parse import unquote, urlsplit

import mysql.connector
from mysql.connector import Error as MySQLError

from app.core.config import settings


class DatabaseConnection:
    def __init__(self) -> None:
        url = urlsplit(settings.database_url)
        if url.scheme not in {"mysql", "mysql+mysqlconnector"}:
            raise ValueError("DATABASE_URL must use the mysql:// scheme.")
        if not url.hostname or not url.username or not url.path.strip("/"):
            raise ValueError(
                "DATABASE_URL must include a host, username, and database name."
            )

        self._connection = mysql.connector.connect(
            host=url.hostname,
            port=url.port or 3306,
            user=unquote(url.username),
            password=unquote(url.password or ""),
            database=unquote(url.path.lstrip("/")),
            charset="utf8mb4",
            autocommit=False,
        )

    def execute(
        self, query: str, params: Sequence[object] = ()
    ) -> mysql.connector.cursor.MySQLCursorDict:
        cursor = self._connection.cursor(dictionary=True)
        cursor.execute(query, params)
        return cursor

    def __enter__(self) -> "DatabaseConnection":
        return self

    def __exit__(self, exception_type, _exception, _traceback) -> None:
        try:
            if exception_type is None:
                self._connection.commit()
            else:
                self._connection.rollback()
        finally:
            self._connection.close()


def get_connection() -> DatabaseConnection:
    """Open a transactional connection to the configured MySQL database."""
    return DatabaseConnection()


def check_database_connection() -> bool:
    try:
        with get_connection() as connection:
            connection.execute("SELECT 1").fetchone()
        return True
    except (MySQLError, ValueError, OSError):
        return False
