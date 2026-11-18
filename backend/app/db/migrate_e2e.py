"""Additive E2E schema migration. Run only after reviewing the target database."""

"""
    Script này được dùng để thêm các cột mới vào các bảng hiện có và tạo các bảng mới trong cơ sở dữ liệu. 
    Nó được thiết kế để chạy một lần duy nhất, sau khi đã kiểm tra kỹ lưỡng cơ sở dữ liệu mục tiêu. 
    Các thay đổi bao gồm việc thêm các cột mới vào các bảng MEMBER, FOOD_ITEM, MEAL, MEAL_ITEM, ASSESSMENT 
    và MENU_PLAN, cũng như tạo các bảng mới CONSENT, CONSENT_HISTORY, MEAL_MEMBER và NUTRITION_RULE.
"""
import sys
from pathlib import Path

from app.db.database import get_connection

COLUMNS = {
    "MEMBER": {
        "is_simulated": "BOOLEAN NOT NULL DEFAULT FALSE",
        "profile_version": "INTEGER NOT NULL DEFAULT 1",
    },
    "FOOD_ITEM": {
        "aliases": "TEXT",
        "default_portion_g": "DECIMAL(8,2)",
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
        "soft_score": "DECIMAL(5,2)",
    },
}

NEW_TABLES = ("CONSENT", "CONSENT_HISTORY", "MEAL_MEMBER", "NUTRITION_RULE")

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
    return planned


if __name__ == "__main__":
    with get_connection() as connection:
        for operation in migrate(connection, dry_run="--check" in sys.argv):
            print(operation)
