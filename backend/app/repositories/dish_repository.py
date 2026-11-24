# tìm kiếm các món ăn trong CSDL
def search(db, q=None, category=None, limit=20, cursor=0):
    clauses = ["food_id > %s"]
    params = [cursor]
    if q:
        clauses.append("(name LIKE %s OR aliases LIKE %s)")
        params.extend((f"%{q}%", f"%{q}%"))
    if category:
        clauses.append("category = %s")
        params.append(category)
    params.append(limit)
    return db.execute(
        "SELECT * FROM FOOD_ITEM WHERE "
        + " AND ".join(clauses)
        + " ORDER BY food_id LIMIT %s",
        tuple(params),
    ).fetchall()


# truy vấn một món ăn cụ thể theo ID
def find(db, dish_id):
    return db.execute(
        "SELECT * FROM FOOD_ITEM WHERE food_id = %s", (dish_id,)
    ).fetchone()


def import_vietfood(db, food, source):
    nutrition = food["nutrition"]
    values = nutrition["values"]
    return db.execute(
        """INSERT INTO FOOD_ITEM (
               vietfood_food_id, name, category, kcal_per_100g, protein_per_100g,
               carb_per_100g, fat_per_100g, sugar_per_100g, fiber_per_100g,
               sodium_mg_per_100g, potassium_mg_per_100g, phosphorus_mg_per_100g,
               default_portion_g, aliases, source_name, source_url
           ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
           ON DUPLICATE KEY UPDATE food_id = LAST_INSERT_ID(food_id)""",
        (
            food["food_id"], food["name_vi"], food["category"],
            values["energy_kcal"], values["protein_g"], values["carb_g"],
            values["fat_g"], values["sugar_g"], values["fiber_g"],
            values["sodium_mg"], values["potassium_mg"], values["phosphorus_mg"],
            food["reference_serving"]["grams"], ",".join(food["aliases"]),
            source["organization"], nutrition["record_url"],
        ),
    ).lastrowid


# truy vấn tất cả các món ăn có nguồn gốc được xác định
def list_candidates(db):
    return db.execute(
        """SELECT * FROM FOOD_ITEM
           WHERE entity_type = 'DISH'
             AND (category IS NULL OR LOWER(category) <> 'ingredient')
             AND source_name IS NOT NULL AND source_name <> ''
           ORDER BY food_id"""
    ).fetchall()


# truy vấn một món ăn cụ thể theo tên hoặc bí danh
def match_name(db, name):
    rows = db.execute(
        "SELECT * FROM FOOD_ITEM WHERE LOWER(name) = LOWER(%s) "
        "OR aliases LIKE %s ORDER BY food_id LIMIT 20",
        (name, f"%{name}%"),
    ).fetchall()
    return next(
        (
            row
            for row in rows
            if row["name"].casefold() == name.casefold()
            or name.casefold() in (row.get("aliases") or "").casefold().split(",")
        ),
        None,
    )
