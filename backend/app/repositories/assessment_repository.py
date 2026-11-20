import json

# lưu trữ kết quả đánh giá vào CSDL
def save(db, meal_id, member_id, result, meal_revision, profile_version):
    db.execute(
        """INSERT INTO ASSESSMENT (meal_id, member_id, suitability_level, explanation,
               suggestion_text, created_at, meal_revision, profile_version,
               ruleset_version, reasons)
           VALUES (%s, %s, %s, %s, NULL, CURRENT_TIMESTAMP, %s, %s, %s, %s)
           ON DUPLICATE KEY UPDATE suitability_level = VALUES(suitability_level),
               explanation = VALUES(explanation), created_at = VALUES(created_at),
               meal_revision = VALUES(meal_revision),
               profile_version = VALUES(profile_version),
               ruleset_version = VALUES(ruleset_version), reasons = VALUES(reasons)""",
        (
            meal_id,
            member_id,
            result["level"],
            "; ".join(result["reasons"]),
            meal_revision,
            profile_version,
            result["rulesetVersion"],
            json.dumps(result["reasons"]),
        ),
    )

# truy vấn tất cả các bản ghi đánh giá cho một bữa ăn cụ thể
def list_for_meal(db, meal_id):
    return db.execute(
        "SELECT * FROM ASSESSMENT WHERE meal_id = %s", (meal_id,)
    ).fetchall()
