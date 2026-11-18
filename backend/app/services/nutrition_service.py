KEYS = {
    "kcal": "kcal_per_100g",
    "proteinG": "protein_per_100g",
    "carbG": "carb_per_100g",
    "fatG": "fat_per_100g",
}


def portion(food, grams):
    result = {}
    for output, column in KEYS.items():
        value = food.get(column)
        result[output] = (
            round(float(value) * float(grams) / 100, 2) if value is not None else None
        )
    return result


def totals(items):
    if not items:
        return {key: None for key in KEYS}
    result = {}
    for key in KEYS:
        values = [item["nutrition"][key] for item in items]
        result[key] = (
            round(sum(values), 2)
            if all(value is not None for value in values)
            else None
        )
    return result
