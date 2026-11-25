from app.repositories import dish_repository


def serialize(row):
    return {
        "dishId": row["food_id"],
        "name": row["name"],
        "category": row.get("category"),
        "entityType": "INGREDIENT"
        if str(row.get("category") or "").casefold() == "ingredient"
        else "DISH",
        "defaultPortionG": float(row["default_portion_g"])
        if row.get("default_portion_g") is not None
        else None,
        "per100g": {
            "kcal": _number(row.get("kcal_per_100g")),
            "proteinG": _number(row.get("protein_per_100g")),
            "carbG": _number(row.get("carb_per_100g")),
            "fatG": _number(row.get("fat_per_100g")),
        },
        "source": {"name": row.get("source_name"), "url": row.get("source_url")},
    }


def _number(value):
    return float(value) if value is not None else None


def search(db, q, category, limit, cursor):
    rows = dish_repository.search(db, q, category, limit, cursor)
    return {
        "data": [serialize(row) for row in rows],
        "meta": {"nextCursor": rows[-1]["food_id"] if len(rows) == limit else None},
    }

def detail(db, dish_id):
    from app.core.exceptions import AppException

    row = dish_repository.find(db, dish_id)
    if not row:
        raise AppException("NOT_FOUND", "Dish not found", 404)
    return {"data": serialize(row)}
