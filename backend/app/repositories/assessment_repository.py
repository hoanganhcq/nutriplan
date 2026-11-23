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


def find_for_meal_member(db, meal_id, member_id):
    return db.execute(
        """SELECT * FROM ASSESSMENT
           WHERE meal_id = %s AND member_id = %s""",
        (meal_id, member_id),
    ).fetchone()


def find_owned(db, assessment_id, session_id):
    return db.execute(
        """SELECT a.*, m.household_id FROM ASSESSMENT a
           JOIN MEAL m ON m.meal_id = a.meal_id
           JOIN HOUSEHOLD h ON h.household_id = m.household_id
           WHERE a.assessment_id = %s AND h.session_id = %s""",
        (assessment_id, session_id),
    ).fetchone()


def invalidate_for_meal(db, meal_id):
    db.execute(
        "UPDATE ASSESSMENT SET meal_revision = 0 WHERE meal_id = %s", (meal_id,)
    )
