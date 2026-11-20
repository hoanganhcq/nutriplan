# truy vấn tất cả các hộ gia đình thuộc một phiên làm việc cụ thể
def create(db, session_id: int, name: str) -> int:
    cursor = db.execute(
        "INSERT INTO HOUSEHOLD (session_id, name) VALUES (%s, %s)",
        (session_id, name),
    )
    return cursor.lastrowid

# truy vấn một hộ gia đình cụ thể theo ID và phiên làm việc
def find_owned(db, household_id: int, session_id: int):
    return db.execute(
        "SELECT * FROM HOUSEHOLD WHERE household_id = %s AND session_id = %s",
        (household_id, session_id),
    ).fetchone()

def list_by_session(db, session_id: int):
    return db.execute(
        "SELECT household_id, name FROM HOUSEHOLD WHERE session_id = %s",
        (session_id,),
    ).fetchall()
