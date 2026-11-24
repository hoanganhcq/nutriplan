ITEM_SELECT = """SELECT i.*, f.name, f.category, f.entity_type, f.source_name,
                        f.source_url, f.kcal_per_100g, f.protein_per_100g,
                        f.carb_per_100g, f.fat_per_100g, f.sugar_per_100g,
                        f.fiber_per_100g, f.sodium_mg_per_100g,
                        f.potassium_mg_per_100g, f.phosphorus_mg_per_100g,
                        f.allergen_codes, f.allergen_verified, f.texture,
                        f.cooking_effort
                 FROM MENU_ITEM i JOIN FOOD_ITEM f ON f.food_id = i.food_id"""


def create(
    db,
    member_id,
    start_date,
    duration_days,
    validation,
    soft_score,
    soft_score_json,
    generation_json,
):
    return db.execute(
        """INSERT INTO MENU_PLAN
           (member_id, start_date, duration_days, status, revision,
            validation_json, soft_score, soft_score_json, generation_json)
           VALUES (%s, %s, %s, 'generated', 1, %s, %s, %s, %s)""",
        (
            member_id,
            start_date,
            duration_days,
            validation,
            soft_score,
            soft_score_json,
            generation_json,
        ),
    ).lastrowid


def add_item(db, plan_id, food_id, meal_type, grams, day_index, locked=False):
    return db.execute(
        """INSERT INTO MENU_ITEM
           (menu_plan_id, food_id, meal_type, portion_g, day_index, locked)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (plan_id, food_id, meal_type, grams, day_index, locked),
    ).lastrowid


def find_owned(db, plan_id, session_id, lock=False):
    return db.execute(
        """SELECT p.* FROM MENU_PLAN p
           JOIN MEMBER m ON m.member_id = p.member_id
           JOIN HOUSEHOLD h ON h.household_id = m.household_id
           WHERE p.menu_plan_id = %s AND h.session_id = %s"""
        + (" FOR UPDATE" if lock else ""),
        (plan_id, session_id),
    ).fetchone()


def list_owned(db, session_id, member_id, limit, cursor):
    clauses = ["h.session_id = %s"]
    params = [session_id]
    if member_id is not None:
        clauses.append("p.member_id = %s")
        params.append(member_id)
    if cursor:
        clauses.append("p.menu_plan_id < %s")
        params.append(cursor)
    rows = db.execute(
        """SELECT p.* FROM MENU_PLAN p
           JOIN MEMBER m ON m.member_id = p.member_id
           JOIN HOUSEHOLD h ON h.household_id = m.household_id
           WHERE """
        + " AND ".join(clauses)
        + " ORDER BY p.menu_plan_id DESC LIMIT %s",
        (*params, limit + 1),
    ).fetchall()
    has_more = len(rows) > limit
    return rows[:limit], rows[limit - 1]["menu_plan_id"] if has_more else None


def items(db, plan_id):
    return db.execute(
        ITEM_SELECT
        + """ WHERE i.menu_plan_id = %s
              ORDER BY i.day_index,
                FIELD(i.meal_type, 'breakfast', 'lunch', 'dinner',
                      'snack', 'snack2', 'snack3'),
                i.menu_item_id""",
        (plan_id,),
    ).fetchall()


def item(db, plan_id, item_id):
    return db.execute(
        ITEM_SELECT + " WHERE i.menu_plan_id = %s AND i.menu_item_id = %s",
        (plan_id, item_id),
    ).fetchone()


def update_item(db, plan_id, item_id, food_id, grams):
    db.execute(
        """UPDATE MENU_ITEM SET food_id = %s, portion_g = %s
           WHERE menu_plan_id = %s AND menu_item_id = %s""",
        (food_id, grams, plan_id, item_id),
    )


def set_locked(db, plan_id, item_id, locked):
    db.execute(
        """UPDATE MENU_ITEM SET locked = %s
           WHERE menu_plan_id = %s AND menu_item_id = %s""",
        (locked, plan_id, item_id),
    )


def update_plan(
    db, plan_id, revision, validation, soft_score, soft_score_json, generation_json
):
    db.execute(
        """UPDATE MENU_PLAN
           SET revision = %s, validation_json = %s, soft_score = %s,
               soft_score_json = %s, generation_json = %s
           WHERE menu_plan_id = %s""",
        (
            revision,
            validation,
            soft_score,
            soft_score_json,
            generation_json,
            plan_id,
        ),
    )


def restore_plan(db, plan_id, snapshot):
    db.execute(
        """UPDATE MENU_PLAN
           SET start_date = %s, duration_days = %s, status = %s, revision = %s,
               validation_json = %s, soft_score = %s, soft_score_json = %s,
               generation_json = %s
           WHERE menu_plan_id = %s""",
        (
            snapshot["start_date"],
            snapshot["duration_days"],
            snapshot["status"],
            snapshot["revision"],
            snapshot["validation_json"],
            snapshot["soft_score"],
            snapshot["soft_score_json"],
            snapshot["generation_json"],
            plan_id,
        ),
    )


def save_revision(db, plan_id, revision, snapshot_json):
    db.execute(
        """INSERT INTO MENU_PLAN_REVISION_HISTORY
           (menu_plan_id, revision, snapshot_json)
           VALUES (%s, %s, %s)
           ON DUPLICATE KEY UPDATE snapshot_json = VALUES(snapshot_json),
             created_at = CURRENT_TIMESTAMP""",
        (plan_id, revision, snapshot_json),
    )
    db.execute(
        """DELETE FROM MENU_PLAN_REVISION_HISTORY
           WHERE menu_plan_id = %s AND revision NOT IN (
             SELECT revision FROM (
               SELECT revision FROM MENU_PLAN_REVISION_HISTORY
               WHERE menu_plan_id = %s ORDER BY revision DESC LIMIT 20
             ) AS recent_revisions
           )""",
        (plan_id, plan_id),
    )


def get_revision(db, plan_id, revision):
    return db.execute(
        """SELECT snapshot_json FROM MENU_PLAN_REVISION_HISTORY
           WHERE menu_plan_id = %s AND revision = %s""",
        (plan_id, revision),
    ).fetchone()


def delete_revisions_from(db, plan_id, revision):
    db.execute(
        """DELETE FROM MENU_PLAN_REVISION_HISTORY
           WHERE menu_plan_id = %s AND revision >= %s""",
        (plan_id, revision),
    )


def replace_items(db, plan_id, items):
    db.execute("DELETE FROM MENU_ITEM WHERE menu_plan_id = %s", (plan_id,))
    for item_row in items:
        db.execute(
            """INSERT INTO MENU_ITEM
               (menu_item_id, menu_plan_id, food_id, meal_type, portion_g,
                day_index, locked)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (
                item_row["menu_item_id"],
                plan_id,
                item_row["food_id"],
                item_row["meal_type"],
                item_row["portion_g"],
                item_row["day_index"],
                item_row["locked"],
            ),
        )


def delete(db, plan_id):
    db.execute(
        "DELETE FROM MENU_PLAN_REVISION_HISTORY WHERE menu_plan_id = %s",
        (plan_id,),
    )
    db.execute("DELETE FROM MENU_ITEM WHERE menu_plan_id = %s", (plan_id,))
    db.execute("DELETE FROM MENU_PLAN WHERE menu_plan_id = %s", (plan_id,))
