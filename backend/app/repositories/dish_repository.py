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

# truy vấn tất cả các món ăn có nguồn gốc được xác định
def list_candidates(db):
    return db.execute(
        "SELECT * FROM FOOD_ITEM WHERE source_name IS NOT NULL "
        "AND source_name <> '' ORDER BY food_id"
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
