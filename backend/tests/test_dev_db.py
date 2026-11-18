import pytest

from app.core.config import settings
from app.db import dev_db


def test_dev_commands_require_development_and_nutriplan(monkeypatch):
    monkeypatch.setattr(
        settings, "database_url", "mysql://user:pass@localhost/nutriplan"
    )
    monkeypatch.setattr(settings, "environment", "production")
    with pytest.raises(SystemExit, match="development"):
        dev_db.connection_options()

    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(
        settings, "database_url", "mysql://user:pass@localhost/another_db"
    )
    with pytest.raises(SystemExit, match="nutriplan"):
        dev_db.connection_options()


def test_reset_requires_flag_and_typed_confirmation_before_connection(monkeypatch):
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(
        settings, "database_url", "mysql://user:pass@localhost/nutriplan"
    )
    monkeypatch.setattr(
        dev_db, "get_connection", lambda: pytest.fail("Không được kết nối DB")
    )

    with pytest.raises(SystemExit, match="confirm-reset"):
        dev_db.reset(False)

    monkeypatch.setattr("builtins.input", lambda prompt: "không")
    with pytest.raises(SystemExit, match="hủy reset"):
        dev_db.reset(True)


def test_database_guard_rejects_other_database():
    class OtherDatabase:
        def execute(self, query):
            assert query == "SELECT DATABASE() AS name"
            return self

        def fetchone(self):
            return {"name": "other_db"}

    with pytest.raises(SystemExit, match="kết nối sai database"):
        dev_db.assert_database(OtherDatabase())

