def create(db, household_id, meal_type, eaten_at, image_count, is_estimate, warnings):
    cursor = db.execute(
        """INSERT INTO MEAL (household_id, eaten_at, status, meal_type,
               revision, image_count, is_estimate, warnings)
           VALUES (%s, %s, 'draft', %s, 1, %s, %s, %s)""",
        (household_id, eaten_at, meal_type, image_count, is_estimate, warnings),
    )
    return cursor.lastrowid


def find_owned(db, meal_id, session_id, lock=False):
    return db.execute(
        """SELECT m.* FROM MEAL m JOIN HOUSEHOLD h ON h.household_id = m.household_id
           WHERE m.meal_id = %s AND h.session_id = %s"""
        + (" FOR UPDATE" if lock else ""),
        (meal_id, session_id),
    ).fetchone()


def add_item(db, meal_id, food_id, grams, seasoning=None, confidence=None):
    return db.execute(
        """INSERT INTO MEAL_ITEM (meal_id, food_id, estimated_weight_g,
               confirmed_weight_g, seasoning, confidence)
           VALUES (%s, %s, %s, NULL, %s, %s)""",
        (meal_id, food_id, grams, seasoning, confidence),
    ).lastrowid


def items(db, meal_id):
    return db.execute(
        """SELECT i.*, f.name, f.category, f.kcal_per_100g, f.protein_per_100g,
                  f.carb_per_100g, f.fat_per_100g, f.source_name, f.source_url,
                  f.ingredients, f.allergen_codes, f.allergen_verified, f.texture
           FROM MEAL_ITEM i JOIN FOOD_ITEM f ON f.food_id = i.food_id
           WHERE i.meal_id = %s ORDER BY i.meal_item_id""",
        (meal_id,),
    ).fetchall()


def update_item(db, meal_id, item_id, food_id, grams, seasoning):
    db.execute(
        """UPDATE MEAL_ITEM SET food_id = %s, confirmed_weight_g = %s, seasoning = %s
           WHERE meal_id = %s AND meal_item_id = %s""",
        (food_id, grams, seasoning, meal_id, item_id),
    )

def delete_item(db, meal_id, item_id):
    db.execute(
        "DELETE FROM MEAL_ITEM WHERE meal_id = %s AND meal_item_id = %s",
        (meal_id, item_id),
    )


def increment_revision(db, meal_id):
    db.execute("UPDATE MEAL SET revision = revision + 1 WHERE meal_id = %s", (meal_id,))


def add_member(db, meal_id, member_id):
    db.execute(
        "INSERT IGNORE INTO MEAL_MEMBER (meal_id, member_id) VALUES (%s, %s)",
        (meal_id, member_id),
    )


def member_ids(db, meal_id):
    return [
        row["member_id"]
        for row in db.execute(
            "SELECT member_id FROM MEAL_MEMBER WHERE meal_id = %s", (meal_id,)
        ).fetchall()
    ]


def list_confirmed(db, session_id, member_id, from_date, to_date, limit, cursor):
    clauses = ["h.session_id = %s", "m.status = 'confirmed'", "m.meal_id > %s"]
    params = [session_id, cursor]
    if member_id:
        clauses.append(
            "EXISTS (SELECT 1 FROM MEAL_MEMBER mm WHERE mm.meal_id = m.meal_id "
            "AND mm.member_id = %s)"
        )
        params.append(member_id)
    if from_date:
        clauses.append("m.eaten_at >= %s")
        params.append(from_date)
    if to_date:
        clauses.append("m.eaten_at <= %s")
        params.append(to_date)
    params.append(limit)
    return db.execute(
        "SELECT m.* FROM MEAL m JOIN HOUSEHOLD h "
        "ON h.household_id = m.household_id WHERE "
        + " AND ".join(clauses)
        + " ORDER BY m.meal_id LIMIT %s",
        tuple(params),
    ).fetchall()
