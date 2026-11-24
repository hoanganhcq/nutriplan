def analytics_allowed(db, session_id):
    # The request has no householdId. Require consent from every owned household.
    # Lock consent rows so a concurrent revocation cannot race the insert.
    rows = db.execute(
        """SELECT h.household_id, c.granted FROM HOUSEHOLD h
           LEFT JOIN CONSENT c ON c.household_id = h.household_id
             AND c.consent_type = 'usage_analytics'
           WHERE h.session_id = %s ORDER BY h.household_id FOR UPDATE""",
        (session_id,),
    ).fetchall()
    return bool(rows) and all(row["granted"] == 1 for row in rows)


def save(db, session_id, study_session_id, participant_id, event, meta_json, at):
    db.execute(
        """INSERT INTO USAGE_EVENT
           (session_id, study_session_id, participant_id, event_type, task,
            occurred_at, meta_json)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (
            session_id,
            study_session_id,
            participant_id,
            event.type,
            event.task,
            at,
            meta_json,
        ),
    )
