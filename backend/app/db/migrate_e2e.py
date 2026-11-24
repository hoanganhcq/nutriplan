"""Bổ sung bảng, cột và index E2E còn thiếu; kiểm tra trước khi áp dụng."""

import sys
from pathlib import Path

from app.db.database import get_connection

COLUMNS = {
    "MEMBER": {
        "is_simulated": "BOOLEAN NOT NULL DEFAULT FALSE",
        "profile_version": "INTEGER NOT NULL DEFAULT 1",
    },
    "FOOD_ITEM": {
        "vietfood_food_id": "VARCHAR(80) UNIQUE",
        "entity_type": "VARCHAR(20) NOT NULL DEFAULT 'DISH'",
        "aliases": "TEXT",
        "default_portion_g": "DECIMAL(8,2)",
        "sugar_per_100g": "DECIMAL(8,2)",
        "fiber_per_100g": "DECIMAL(8,2)",
        "sodium_mg_per_100g": "DECIMAL(8,2)",
        "potassium_mg_per_100g": "DECIMAL(8,2)",
        "phosphorus_mg_per_100g": "DECIMAL(8,2)",
        "ingredients": "TEXT",
        "allergen_codes": "TEXT",
        "allergen_verified": "BOOLEAN NOT NULL DEFAULT FALSE",
        "texture": "VARCHAR(20)",
        "cooking_effort": "VARCHAR(20)",
    },
    "MEAL": {
        "meal_type": "VARCHAR(30)",
        "revision": "INTEGER NOT NULL DEFAULT 1",
        "image_count": "INTEGER NOT NULL DEFAULT 0",
        "is_estimate": "BOOLEAN NOT NULL DEFAULT TRUE",
        "warnings": "TEXT",
        "confirmed_at": "DATETIME",
        "note": "TEXT",
    },
    "MEAL_ITEM": {"seasoning": "TEXT", "confidence": "DECIMAL(4,3)"},
    "ASSESSMENT": {
        "meal_revision": "INTEGER NOT NULL DEFAULT 1",
        "profile_version": "INTEGER NOT NULL DEFAULT 1",
        "ruleset_version": "VARCHAR(30)",
        "reasons": "TEXT",
    },
    "MENU_PLAN": {
        "revision": "INTEGER NOT NULL DEFAULT 1",
        "validation_json": "TEXT",
        "soft_score_json": "TEXT",
        "generation_json": "TEXT",
        "soft_score": "DECIMAL(5,2)",
        "created_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
    },
    "MENU_ITEM": {
        "day_index": "TINYINT NOT NULL DEFAULT 1",
        "locked": "BOOLEAN NOT NULL DEFAULT FALSE",
    },
    "HEALTH_RULE": {"change_log": "TEXT"},
}

NEW_TABLES = (
    "CONSENT",
    "CONSENT_HISTORY",
    "MEAL_MEMBER",
    "NUTRITION_RULE",
    "MEAL_REVISION_HISTORY",
    "RULE_SOURCE",
    "HEALTH_RULE",
    "MENU_PLAN_REVISION_HISTORY",
    "USAGE_EVENT",
    "DEMO_DATASET",
)
INDEXES = {
    "FOOD_ITEM": {
        "idx_food_item_category_food": "(category, food_id)",
    },
    "MEAL": {
        "idx_meal_status_eaten": "(status, eaten_at)",
    },
    "MEAL_MEMBER": {
        "idx_meal_member_member": "(member_id)",
    },
    "NUTRITION_RULE": {
        "idx_rule_active_verified": "(active, verified, rule_type, subject)",
    },
    "HEALTH_RULE": {
        "idx_health_rule_enabled_filter": "(enabled, condition_code, nutrient, scope)",
    },
}


# hàm migrate() thực hiện việc thêm các cột mới và tạo các bảng mới trong cơ sở dữ liệu.
def migrate(db, dry_run=False):
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    planned = []
    for table in NEW_TABLES:
        statement = next(
            part.strip()
            for part in schema.split(";")
            if part.strip().startswith(f"CREATE TABLE IF NOT EXISTS {table} (")
        )
        exists = db.execute(
            """SELECT 1 FROM information_schema.TABLES
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s""",
            (table,),
        ).fetchone()
        if not exists:
            planned.append(f"CREATE TABLE {table}")
            if not dry_run:
                db.execute(statement)
    for table, columns in COLUMNS.items():
        for column, definition in columns.items():
            exists = db.execute(
                """SELECT 1 FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                     AND COLUMN_NAME = %s""",
                (table, column),
            ).fetchone()
            if not exists:
                planned.append(f"ALTER TABLE {table} ADD COLUMN {column}")
                # Identifiers and definitions come only from the constant map above.
                if not dry_run:
                    db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    for table, indexes in INDEXES.items():
        for name, fields in indexes.items():
            exists = db.execute(
                """SELECT 1 FROM information_schema.STATISTICS
                   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                     AND INDEX_NAME = %s LIMIT 1""",
                (table, name),
            ).fetchone()
            if not exists:
                planned.append(f"CREATE INDEX {name} ON {table}")
                if not dry_run:
                    db.execute(f"CREATE INDEX {name} ON {table} {fields}")
    return planned


if __name__ == "__main__":
    with get_connection() as connection:
        for operation in migrate(connection, dry_run="--check" in sys.argv):
            print(operation)
