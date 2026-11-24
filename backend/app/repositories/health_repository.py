def probe(db):
    db.execute("SELECT 1").fetchone()
    return [
        row["version"]
        for row in db.execute(
            "SELECT DISTINCT version FROM HEALTH_RULE WHERE enabled = TRUE"
        ).fetchall()
    ]
