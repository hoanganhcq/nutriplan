import json

from app.core.exceptions import AppException
from app.db import demo_data


def lock_dataset(db):
    db.execute(
        """INSERT INTO DEMO_DATASET (dataset_key) VALUES (%s)
           ON DUPLICATE KEY UPDATE dataset_key = VALUES(dataset_key)""",
        (demo_data.DATASET_KEY,),
    )
    return db.execute(
        """SELECT d.household_id, h.session_id FROM DEMO_DATASET d
           LEFT JOIN HOUSEHOLD h ON h.household_id = d.household_id
           WHERE d.dataset_key = %s FOR UPDATE""",
        (demo_data.DATASET_KEY,),
    ).fetchone()


def set_household(db, household_id):
    db.execute(
        "UPDATE DEMO_DATASET SET household_id = %s WHERE dataset_key = %s",
        (household_id, demo_data.DATASET_KEY),
    )


def check_simulated_members(db, household_id):
    members = db.execute(
        "SELECT is_simulated FROM MEMBER WHERE household_id = %s FOR UPDATE",
        (household_id,),
    ).fetchall()
    if any(not row["is_simulated"] for row in members):
        raise AppException(
            "CONFLICT", "Demo household contains non-simulated profiles", 409
        )


def reset_household(db, household_id, session_id):
    # Every delete is scoped to the dataset's household. Shared dishes stay intact.
    for table, alias in (
        ("ASSESSMENT", "a"),
        ("MEAL_MEMBER", "mm"),
        ("MEAL_REVISION_HISTORY", "r"),
        ("MEAL_ITEM", "i"),
    ):
        db.execute(
            f"DELETE {alias} FROM {table} {alias} "
            f"JOIN MEAL m ON m.meal_id = {alias}.meal_id "
            "WHERE m.household_id = %s",
            (household_id,),
        )
    for table, alias in (("ASSESSMENT", "a"), ("MEAL_MEMBER", "mm")):
        db.execute(
            f"DELETE {alias} FROM {table} {alias} "
            f"JOIN MEMBER m ON m.member_id = {alias}.member_id "
            "WHERE m.household_id = %s",
            (household_id,),
        )
    db.execute("DELETE FROM MEAL WHERE household_id = %s", (household_id,))
    for table, alias in (
        ("MENU_PLAN_REVISION_HISTORY", "r"),
        ("MENU_ITEM", "i"),
    ):
        db.execute(
            f"DELETE {alias} FROM {table} {alias} "
            f"JOIN MENU_PLAN p ON p.menu_plan_id = {alias}.menu_plan_id "
            "JOIN MEMBER m ON m.member_id = p.member_id "
            "WHERE m.household_id = %s",
            (household_id,),
        )
    db.execute(
        """DELETE p FROM MENU_PLAN p JOIN MEMBER m ON m.member_id = p.member_id
           WHERE m.household_id = %s""",
        (household_id,),
    )
    for table in ("MEMBER", "CONSENT_HISTORY", "CONSENT"):
        db.execute(f"DELETE FROM {table} WHERE household_id = %s", (household_id,))
    db.execute("DELETE FROM HOUSEHOLD WHERE household_id = %s", (household_id,))
    # A session reused to create another household is retained.
    db.execute(
        """DELETE FROM SESSION WHERE session_id = %s AND NOT EXISTS
           (SELECT 1 FROM HOUSEHOLD WHERE session_id = %s)""",
        (session_id, session_id),
    )


def rotate_token(db, session_id, token_hash):
    db.execute(
        "UPDATE SESSION SET token_hash = %s WHERE session_id = %s",
        (token_hash, session_id),
    )


def seed_member(db, household_id, member):
    exists = db.execute(
        "SELECT member_id FROM MEMBER WHERE household_id = %s AND full_name = %s",
        (household_id, member["name"]),
    ).fetchone()
    if not exists:
        db.execute(
            """INSERT INTO MEMBER
               (household_id, full_name, age, sex, health_conditions, allergies,
                preferences, energy_target_kcal, texture_requirements, is_simulated)
               VALUES (%s, %s, %s, %s, %s, '[]', '[]', 1800, 'normal', TRUE)""",
            (
                household_id,
                member["name"],
                member["age"],
                member["sex"],
                json.dumps(member["conditions"]),
            ),
        )


def seed_dish(db, index, name, category, reset):
    name = f"DEMO - {name}"
    existing = db.execute(
        "SELECT food_id FROM FOOD_ITEM WHERE name = %s AND source_name = %s",
        (name, demo_data.SOURCE),
    ).fetchone()
    if existing and not reset:
        return
    values = (
        name,
        category,
        80 + index * 3,
        3 + index % 8,
        10 + index % 12,
        1 + index % 5,
        demo_data.SOURCE,
        name.removeprefix("DEMO - "),
        150,
        index % 6,
        1 + index % 4,
        30 + index * 5,
        60 + index * 4,
        40 + index * 2,
    )
    columns = (
        "name, category, kcal_per_100g, protein_per_100g, carb_per_100g, "
        "fat_per_100g, source_name, aliases, default_portion_g, sugar_per_100g, "
        "fiber_per_100g, sodium_mg_per_100g, potassium_mg_per_100g, "
        "phosphorus_mg_per_100g"
    )
    if existing:
        assignments = ", ".join(
            f"{column.strip()} = %s" for column in columns.split(",")
        )
        db.execute(
            f"UPDATE FOOD_ITEM SET {assignments}, source_url = NULL, "
            "allergen_codes = NULL, allergen_verified = FALSE, texture = 'normal', "
            "cooking_effort = 'easy', entity_type = 'DISH' WHERE food_id = %s",
            (*values, existing["food_id"]),
        )
    else:
        db.execute(
            f"INSERT INTO FOOD_ITEM ({columns}, texture, cooking_effort) "
            f"VALUES ({', '.join(['%s'] * len(values))}, 'normal', 'easy')",
            values,
        )


def seed_rule(db, rule, reset):
    existing = db.execute(
        "SELECT version FROM HEALTH_RULE WHERE rule_code = %s", (rule["code"],)
    ).fetchone()
    if existing:
        if existing["version"] != demo_data.RULESET_VERSION:
            raise AppException("CONFLICT", "Demo rule code is already in use", 409)
        if not reset:
            return
    db.execute(
        """INSERT INTO HEALTH_RULE
           (rule_code, condition_code, nutrient, scope, operator, threshold, unit,
            severity, version, enabled, source_id, rationale, change_log)
           VALUES (%s, %s, %s, %s, %s, %s, %s, 'YELLOW', %s, FALSE, NULL, %s, '[]')
           ON DUPLICATE KEY UPDATE condition_code = VALUES(condition_code),
             nutrient = VALUES(nutrient), scope = VALUES(scope),
             operator = VALUES(operator), threshold = VALUES(threshold),
             unit = VALUES(unit), severity = VALUES(severity), enabled = FALSE,
             source_id = NULL, rationale = VALUES(rationale)""",
        (
            rule["code"],
            rule["condition"],
            rule["nutrient"],
            rule["scope"],
            rule["operator"],
            rule["threshold"],
            rule["unit"],
            demo_data.RULESET_VERSION,
            "DEMO ONLY: synthetic limits, no verified medical source. Keep disabled.",
        ),
    )


def member_count(db, household_id):
    return db.execute(
        "SELECT COUNT(*) AS total FROM MEMBER WHERE household_id = %s",
        (household_id,),
    ).fetchone()["total"]
