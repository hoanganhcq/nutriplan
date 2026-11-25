# truy vấn tất cả các quy tắc dinh dưỡng đang hoạt động và đã được xác minh
def active_verified(db):
    return db.execute(
        """SELECT rule_type, subject, severity, ruleset_version, source_name, source_url
           FROM NUTRITION_RULE WHERE active = TRUE AND verified = TRUE"""
    ).fetchall()


RULE_COLUMNS = """h.rule_code AS rule_id,
                  h.condition_code AS condition_name,
                  h.nutrient, h.scope, h.operator, h.threshold, h.unit,
                  h.severity AS severity_when_violated, h.enabled, h.version,
                  s.organization AS source_org, s.title AS source_title,
                  s.published_year AS source_year,
                  s.applicability AS source_applicability,
                  s.source_url, s.updated_at AS source_updated_at,
                  h.rationale, h.change_log"""

RULE_TABLES = """HEALTH_RULE h
                 LEFT JOIN RULE_SOURCE s ON s.source_id = h.source_id"""


def list_rules(db, filters, limit, cursor):
    clauses = []
    params = []
    for key, column in (
        ("condition", "h.condition_code"),
        ("nutrient", "h.nutrient"),
        ("scope", "h.scope"),
        ("enabled", "h.enabled"),
    ):
        value = filters.get(key)
        if value is not None:
            clauses.append(f"{column} = %s")
            params.append(value)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = db.execute(
        f"""SELECT {RULE_COLUMNS} FROM {RULE_TABLES} {where}
            ORDER BY h.rule_id LIMIT %s OFFSET %s""",
        (*params, limit + 1, cursor),
    ).fetchall()
    has_more = len(rows) > limit
    return rows[:limit], cursor + limit if has_more else None


def find_rule(db, rule_id):
    return db.execute(
        f"""SELECT {RULE_COLUMNS} FROM {RULE_TABLES}
            WHERE h.rule_code = %s""",
        (rule_id,),
    ).fetchone()


def enabled_rules(db):
    return db.execute(
        f"""SELECT {RULE_COLUMNS} FROM {RULE_TABLES}
            WHERE h.enabled = TRUE ORDER BY h.rule_id"""
    ).fetchall()
