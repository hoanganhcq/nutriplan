import json

from app.schemas.profiles import MemberCreate, MemberUpdate


def create(db, household_id: int, member: MemberCreate) -> int:
    cursor = db.execute(
        """
        INSERT INTO MEMBER
        (household_id, full_name, age, sex, weight_kg, height_cm,
         health_conditions, allergies, preferences, energy_target_kcal,
         texture_requirements)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            household_id,
            member.name,
            member.age,
            member.sex,
            member.weight_kg,
            member.height_cm,
            json.dumps(member.conditions),
            json.dumps(member.allergies),
            json.dumps(member.food_preferences),
            member.energy_target_kcal,
            member.texture_requirements,
        ),
    )
    return cursor.lastrowid


def find(db, member_id: int):
    return db.execute(
        "SELECT * FROM MEMBER WHERE member_id = %s", (member_id,)
    ).fetchone()


def list_by_household(db, household_id: int):
    return db.execute(
        "SELECT * FROM MEMBER WHERE household_id = %s ORDER BY member_id",
        (household_id,),
    ).fetchall()


def find_owned(db, member_id: int, session_id: int):
    return db.execute(
        """
        SELECT p.*, h.name AS household_name, h.household_id
        FROM MEMBER p
        JOIN HOUSEHOLD h ON h.household_id = p.household_id
        WHERE p.member_id = %s AND h.session_id = %s
        """,
        (member_id, session_id),
    ).fetchone()


def update(db, member_id: int, member: MemberUpdate) -> None:
    db.execute(
        """
        UPDATE MEMBER
        SET full_name = %s, age = %s, sex = %s, weight_kg = %s, height_cm = %s,
            health_conditions = %s, allergies = %s, preferences = %s,
            energy_target_kcal = %s, texture_requirements = %s
        WHERE member_id = %s
        """,
        (
            member.name,
            member.age,
            member.sex,
            member.weight_kg,
            member.height_cm,
            json.dumps(member.conditions),
            json.dumps(member.allergies),
            json.dumps(member.food_preferences),
            member.energy_target_kcal,
            member.texture_requirements,
            member_id,
        ),
    )


def delete(db, member_id: int) -> None:
    db.execute("DELETE FROM MEMBER WHERE member_id = %s", (member_id,))
