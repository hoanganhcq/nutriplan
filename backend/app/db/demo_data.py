"""Synthetic UI fixtures, not nutrition reference data or medical guidance."""

DATASET_KEY = "group-h-demo-v1"
SOURCE = "GROUP_H_DEMO_SYNTHETIC_UNVERIFIED"
RULESET_VERSION = "demo-unverified-v1"
HOUSEHOLD_NAME = "DEMO - Gia đình bà Trung và ông Thanh"

# Names identify familiar dishes; all nutrient values below are synthetic.
DISHES = (
    ("Cháo yến mạch", "porridge"),
    ("Cháo gà", "porridge"),
    ("Cháo bí đỏ", "porridge"),
    ("Cháo cá", "porridge"),
    ("Cơm trắng", "staple"),
    ("Cơm gạo lứt", "staple"),
    ("Bún tươi", "staple"),
    ("Khoai lang hấp", "staple"),
    ("Ức gà hấp", "protein"),
    ("Cá hấp gừng", "protein"),
    ("Đậu phụ hấp", "protein"),
    ("Trứng hấp", "protein"),
    ("Thịt nạc luộc", "protein"),
    ("Cá nướng", "protein"),
    ("Gà xào nấm", "protein"),
    ("Đậu phụ sốt cà chua", "protein"),
    ("Canh bí xanh", "soup"),
    ("Canh bầu", "soup"),
    ("Canh rau cải", "soup"),
    ("Canh nấm", "soup"),
    ("Bắp cải luộc", "vegetable"),
    ("Su su luộc", "vegetable"),
    ("Bí xanh hấp", "vegetable"),
    ("Rau củ hấp", "vegetable"),
    ("Táo", "fruit"),
    ("Lê", "fruit"),
    ("Thanh long", "fruit"),
    ("Sữa chua không đường", "snack"),
)

MEMBERS = (
    {
        "name": "Bà Trung",
        "age": 66,
        "sex": "female",
        "conditions": ["diabetes", "hypertension"],
    },
    {"name": "Ông Thanh", "age": 70, "sex": "male", "conditions": ["kidney_disease"]},
)

# Arbitrary fixture limits exercise the three condition groups and two scopes.
# They intentionally have no source and must stay disabled.
RULES = tuple(
    {
        "code": f"demo_h_{condition.lower()}_{nutrient}_{scope}",
        "condition": condition,
        "nutrient": nutrient,
        "scope": scope,
        "operator": operator,
        "threshold": threshold,
        "unit": unit,
    }
    for condition in ("T2D", "HTN", "CKD")
    for nutrient, scope, operator, threshold, unit in (
        ("sodium_mg", "meal", "lte", 800, "mg"),
        ("sodium_mg", "day", "lte", 2400, "mg"),
        ("sugar_g", "meal", "lte", 30, "g"),
        ("fiber_g", "day", "gte", 20, "g"),
    )
)
