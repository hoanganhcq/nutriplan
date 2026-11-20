# truy vấn tất cả các quy tắc dinh dưỡng đang hoạt động và đã được xác minh
def active_verified(db):
    return db.execute(
        """SELECT rule_type, subject, severity, ruleset_version, source_name, source_url
           FROM NUTRITION_RULE WHERE active = TRUE AND verified = TRUE"""
    ).fetchall()
