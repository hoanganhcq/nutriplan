def create(db, token_hash: str) -> int:
    cursor = db.execute(
        "INSERT INTO SESSION (token_hash) VALUES (%s)", (token_hash,)
    )
    return cursor.lastrowid


def find_by_token_hash(db, token_hash: str):
    return db.execute(
        "SELECT * FROM SESSION WHERE token_hash = %s", (token_hash,)
    ).fetchone()
