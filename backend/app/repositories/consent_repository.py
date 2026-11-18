def list_for_household(db, household_id):
    return db.execute(
        "SELECT consent_type, granted, policy_version, updated_at "
        "FROM CONSENT WHERE household_id = %s",
        (household_id,),
    ).fetchall()


def set_consent(db, household_id, consent_type, granted, policy_version):
    db.execute(
        """INSERT INTO CONSENT (household_id, consent_type, granted, policy_version)
           VALUES (%s, %s, %s, %s)
           ON DUPLICATE KEY UPDATE granted = VALUES(granted),
             policy_version = VALUES(policy_version), updated_at = CURRENT_TIMESTAMP""",
        (household_id, consent_type, granted, policy_version),
    )
    db.execute(
        """INSERT INTO CONSENT_HISTORY
           (household_id, consent_type, granted, policy_version)
           VALUES (%s, %s, %s, %s)""",
        (household_id, consent_type, granted, policy_version),
    )
