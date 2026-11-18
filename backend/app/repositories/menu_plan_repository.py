def create(db, member_id, start_date, validation, soft_score):
    return db.execute(
        """INSERT INTO MENU_PLAN (member_id, start_date, duration_days,
               status, revision, validation_json, soft_score)
           VALUES (%s, %s, 1, 'generated', 1, %s, %s)""",
        (member_id, start_date, validation, soft_score),
    ).lastrowid


def add_item(db, plan_id, food_id, meal_type, grams):
    db.execute(
        "INSERT INTO MENU_ITEM (menu_plan_id, food_id, meal_type, portion_g) "
        "VALUES (%s, %s, %s, %s)",
        (plan_id, food_id, meal_type, grams),
    )


def find_owned(db, plan_id, session_id):
    return db.execute(
        """SELECT p.* FROM MENU_PLAN p JOIN MEMBER m ON m.member_id = p.member_id
           JOIN HOUSEHOLD h ON h.household_id = m.household_id
           WHERE p.menu_plan_id = %s AND h.session_id = %s""",
        (plan_id, session_id),
    ).fetchone()


def items(db, plan_id):
    return db.execute(
        """SELECT i.*, f.name, f.kcal_per_100g, f.protein_per_100g,
                  f.carb_per_100g, f.fat_per_100g FROM MENU_ITEM i
           JOIN FOOD_ITEM f ON f.food_id = i.food_id WHERE i.menu_plan_id = %s
           ORDER BY i.menu_item_id""",
        (plan_id,),
    ).fetchall()
