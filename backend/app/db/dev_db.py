"""Các lệnh thủ công để khởi tạo, seed và reset database development."""

import argparse
import json
import re
import secrets
from hashlib import sha256
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

import mysql.connector
from mysql.connector import Error as MySQLError

from app.core.config import settings
from app.db.database import get_connection
from app.db.migrate_e2e import migrate

DB_NAME = "nutriplan"
SCHEMA = Path(__file__).with_name("schema.sql")
DEMO_TOKEN_FILE = Path(__file__).resolve().parents[2] / ".demo-session-token"
DEMO_SOURCE = "DEMO_SYNTHETIC_UNVERIFIED"
DEMO_SOURCE_URL = "https://example.invalid/nutriplan-demo"
RESET_ORDER = (
    "MENU_ITEM",
    "MENU_PLAN",
    "ASSESSMENT",
    "MEAL_MEMBER",
    "MEAL_REVISION_HISTORY",
    "MEAL_ITEM",
    "MEAL",
    "CONSENT_HISTORY",
    "CONSENT",
    "MEMBER",
    "HOUSEHOLD",
    "SESSION",
    "FOOD_ITEM",
    "NUTRITION_RULE",
)
DISHES = (
    ("DEMO - Món A", "demo", 100, 5, 15, 2, 150, "easy"),
    ("DEMO - Món B", "demo", 120, 8, 12, 4, 180, "medium"),
    ("DEMO - Món C", "demo", 140, 10, 18, 3, 120, "easy"),
)
RULES = (
    ("general", "nutrition"),
    ("allergy", "peanut"),
    ("condition", "diabetes"),
)


def connection_options() -> dict:
    parsed = urlsplit(settings.database_url)
    if (
        settings.environment != "development"
        or parsed.scheme not in {"mysql", "mysql+mysqlconnector"}
        or not parsed.hostname
        or not parsed.username
        or unquote(parsed.path.lstrip("/")) != DB_NAME
        or parse_qs(parsed.query) not in ({}, {"charset": ["utf8mb4"]})
        or parsed.fragment
    ):
        raise SystemExit(
            "Chỉ chạy khi ENVIRONMENT=development và "
            "DATABASE_URL trỏ đến nutriplan"
        )
    return {
        "host": parsed.hostname,
        "port": parsed.port or 3306,
        "user": unquote(parsed.username),
        "password": unquote(parsed.password or ""),
        "charset": "utf8mb4",
    }


def assert_database(db) -> None:
    row = db.execute("SELECT DATABASE() AS name").fetchone()
    if row["name"] != DB_NAME:
        raise SystemExit("Đã kết nối sai database; không thực hiện thay đổi")


def init() -> None:
    options = connection_options()
    try:
        with get_connection() as db:
            assert_database(db)
    except MySQLError as exc:
        if exc.errno != 1049:
            raise
        server = mysql.connector.connect(**options, autocommit=True)
        try:
            cursor = server.cursor()
            cursor.execute(
                "CREATE DATABASE IF NOT EXISTS nutriplan "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            cursor.close()
        finally:
            server.close()

    with get_connection() as db:
        assert_database(db)
        for statement in SCHEMA.read_text(encoding="utf-8").split(";"):
            if statement.strip():
                match = re.match(
                    r"CREATE TABLE IF NOT EXISTS ([A-Za-z_]+)\s*\(",
                    statement.strip(),
                    re.IGNORECASE,
                )
                if not match:
                    raise ValueError("schema.sql chỉ được chứa CREATE TABLE")
                exists = db.execute(
                    """SELECT 1 FROM information_schema.TABLES
                       WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s""",
                    (match.group(1),),
                ).fetchone()
                if not exists:
                    db.execute(statement)
        operations = migrate(db)
    print(f"Schema initialized in {DB_NAME}; migration operations: {len(operations)}")


def seed() -> None:
    connection_options()
    stored_token = (
        DEMO_TOKEN_FILE.read_text(encoding="utf-8").strip()
        if DEMO_TOKEN_FILE.exists()
        else ""
    )
    token = stored_token or secrets.token_urlsafe(32)
    token_hash = sha256(token.encode("utf-8")).hexdigest()
    with get_connection() as db:
        assert_database(db)
        for name, category, kcal, protein, carb, fat, portion, effort in DISHES:
            exists = db.execute(
                "SELECT food_id FROM FOOD_ITEM WHERE name = %s AND source_name = %s",
                (name, DEMO_SOURCE),
            ).fetchone()
            if not exists:
                db.execute(
                    """INSERT INTO FOOD_ITEM
                       (name, category, kcal_per_100g, protein_per_100g,
                        carb_per_100g, fat_per_100g, source_name, source_url,
                        default_portion_g, allergen_codes, allergen_verified,
                        texture, cooking_effort)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s, %s)""",
                    (
                        name, category, kcal, protein, carb, fat, DEMO_SOURCE,
                        None, portion, json.dumps([]), "normal", effort,
                    ),
                )
        for rule_type, subject in RULES:
            exists = db.execute(
                """SELECT rule_id FROM NUTRITION_RULE
                   WHERE rule_type = %s AND subject = %s
                     AND ruleset_version = 'demo-unverified-v1'""",
                (rule_type, subject),
            ).fetchone()
            if not exists:
                db.execute(
                    """INSERT INTO NUTRITION_RULE
                       (rule_type, subject, severity, ruleset_version,
                        source_name, source_url, verified, active)
                       VALUES (%s, %s, 'info', 'demo-unverified-v1',
                               %s, %s, 0, 0)""",
                    (rule_type, subject, DEMO_SOURCE, DEMO_SOURCE_URL),
                )

        session = db.execute(
            "SELECT session_id FROM SESSION WHERE token_hash = %s", (token_hash,)
        ).fetchone()
        if session:
            session_id = session["session_id"]
        else:
            session_id = db.execute(
                "INSERT INTO SESSION (token_hash) VALUES (%s)", (token_hash,)
            ).lastrowid
        household = db.execute(
            "SELECT household_id FROM HOUSEHOLD WHERE session_id = %s AND name = %s",
            (session_id, "DEMO NutriPlan"),
        ).fetchone()
        if household:
            household_id = household["household_id"]
        else:
            household_id = db.execute(
                "INSERT INTO HOUSEHOLD (session_id, name) VALUES (%s, %s)",
                (session_id, "DEMO NutriPlan"),
            ).lastrowid
        member = db.execute(
            """SELECT member_id FROM MEMBER
               WHERE household_id = %s AND full_name = %s""",
            (household_id, "Thành viên mô phỏng"),
        ).fetchone()
        if not member:
            db.execute(
                """INSERT INTO MEMBER
                   (household_id, full_name, age, health_conditions, allergies,
                    preferences, energy_target_kcal, texture_requirements,
                    is_simulated)
                   VALUES (%s, %s, 30, %s, %s, %s, 2000, 'normal', 1)""",
                (
                    household_id, "Thành viên mô phỏng",
                    json.dumps(["none"]), json.dumps(["none"]), json.dumps([]),
                ),
            )
        consent = db.execute(
            """SELECT 1 FROM CONSENT
               WHERE household_id = %s AND consent_type = 'store_health_profile'""",
            (household_id,),
        ).fetchone()
        if not consent:
            db.execute(
                """INSERT INTO CONSENT
                   (household_id, consent_type, granted, policy_version)
                   VALUES (%s, 'store_health_profile', 1, '0.1')""",
                (household_id,),
            )
    DEMO_TOKEN_FILE.write_text(token + "\n", encoding="utf-8")
    print(f"Demo data seeded in {DB_NAME}. Token: {DEMO_TOKEN_FILE}")


def reset(confirm: bool) -> None:
    connection_options()
    if not confirm:
        raise SystemExit("Cần cờ --confirm-reset-nutriplan")
    if input("Nhập RESET nutriplan để xóa dữ liệu development: ").strip() != (
        "RESET nutriplan"
    ):
        raise SystemExit("Đã hủy reset")
    with get_connection() as db:
        assert_database(db)
        for table in RESET_ORDER:
            db.execute(f"DELETE FROM {table}")
    print(f"Development data deleted from {DB_NAME}; schema kept")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("init")
    subcommands.add_parser("seed")
    reset_parser = subcommands.add_parser("reset")
    reset_parser.add_argument("--confirm-reset-nutriplan", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "init":
            init()
        elif args.command == "seed":
            seed()
        else:
            reset(args.confirm_reset_nutriplan)
    except MySQLError as exc:
        if exc.errno in {1044, 1142}:
            raise SystemExit(
                "Tài khoản MySQL thiếu quyền trên nutriplan; cần quyền CREATE/ALTER "
                "để khởi tạo schema, hoặc nhờ quản trị viên chạy lệnh init"
            ) from exc
        raise


if __name__ == "__main__":
    main()

