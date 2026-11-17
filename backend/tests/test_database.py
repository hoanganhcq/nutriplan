import pytest

from app.core.config import settings
from app.db.database import get_connection


class FakeCursor:
    fetched = False

    def execute(self, query, params):
        self.query = query
        self.params = params

    def fetchone(self):
        self.fetched = True
        return {"1": 1}


class FakeMySQLConnection:
    def __init__(self):
        self.cursor_options = None
        self.committed = False
        self.rolled_back = False
        self.closed = False
        self.fake_cursor = FakeCursor()

    def cursor(self, **options):
        self.cursor_options = options
        return self.fake_cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_mysql_connection_executes_and_commits(monkeypatch):
    fake_connection = FakeMySQLConnection()
    connect_options = {}

    def fake_connect(**options):
        connect_options.update(options)
        return fake_connection

    monkeypatch.setattr("app.db.database.mysql.connector.connect", fake_connect)
    monkeypatch.setattr(
        settings,
        "database_url",
        "mysql://db_user:pass%40word@db.example:3307/nutriplan",
    )

    with get_connection() as connection:
        cursor = connection.execute(
            "SELECT * FROM SESSION WHERE session_id = %s", (12,)
        )

    assert connect_options == {
        "host": "db.example",
        "port": 3307,
        "user": "db_user",
        "password": "pass@word",
        "database": "nutriplan",
        "charset": "utf8mb4",
        "autocommit": False,
    }
    assert fake_connection.cursor_options == {"dictionary": True}
    assert cursor.query == "SELECT * FROM SESSION WHERE session_id = %s"
    assert cursor.params == (12,)
    assert fake_connection.committed
    assert not fake_connection.rolled_back
    assert fake_connection.closed


def test_mysql_connection_rolls_back_on_error(monkeypatch):
    fake_connection = FakeMySQLConnection()
    monkeypatch.setattr(
        "app.db.database.mysql.connector.connect",
        lambda **options: fake_connection,
    )
    monkeypatch.setattr(
        settings, "database_url", "mysql://db_user:password@localhost/nutriplan"
    )

    with pytest.raises(RuntimeError, match="request failed"):
        with get_connection():
            raise RuntimeError("request failed")

    assert not fake_connection.committed
    assert fake_connection.rolled_back
    assert fake_connection.closed


def test_health_connection_check_consumes_probe_result(monkeypatch):
    from app.db.database import check_database_connection

    fake_connection = FakeMySQLConnection()
    monkeypatch.setattr(
        "app.db.database.mysql.connector.connect",
        lambda **options: fake_connection,
    )
    monkeypatch.setattr(
        settings, "database_url", "mysql://db_user:password@localhost/nutriplan"
    )

    assert check_database_connection()
    assert fake_connection.fake_cursor.fetched
