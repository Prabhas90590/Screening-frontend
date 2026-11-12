"""Shared database and model ownership helpers for multi-user isolation."""

from typing import Any, Optional, Tuple

EMAIL_OWNED_TABLES = (
    "rule_versions",
    "screening_runs",
    "decisions",
    "holdings",
    "schedules",
    "schedules_daily",
    "schedules_weekly",
    "schedules_monthly",
    "schedules_custom",
)


def reconcile_ownership_with_cursor(
    cursor: Any,
    user_id: Optional[str] = None,
    owner_email: Optional[str] = None,
) -> None:
    """Synchronize user_id/owner_email across user-owned tables without hardcoding accounts.

    Updates rows whose ``owner_email`` matches a registered user when ``user_id``
    is blank or points to an orphaned/non-existent user ID, then cascades parent
    ownership to child tables (``rules``, ``screening_results``, ``funnel_counts``).
    """
    clean_uid = user_id.strip() if isinstance(user_id, str) and user_id.strip() else None
    clean_email = owner_email.strip() if isinstance(owner_email, str) and owner_email.strip() else None

    for tbl in EMAIL_OWNED_TABLES:
        if clean_uid and clean_email:
            cursor.execute(
                f"""
                UPDATE {tbl} t
                SET user_id = %s,
                    owner_email = %s
                WHERE t.owner_email IS NOT NULL AND t.owner_email != ''
                  AND LOWER(t.owner_email) = LOWER(%s)
                  AND (
                      t.user_id IS NULL OR t.user_id = ''
                      OR (
                          t.user_id IS DISTINCT FROM %s
                          AND NOT EXISTS (SELECT 1 FROM users u2 WHERE u2.id::text = t.user_id)
                      )
                  );
                """,
                (clean_uid, clean_email, clean_email, clean_uid),
            )
        else:
            cursor.execute(
                f"""
                UPDATE {tbl} t
                SET user_id = u.id::text
                FROM users u
                WHERE t.owner_email IS NOT NULL AND t.owner_email != ''
                  AND LOWER(t.owner_email) = LOWER(u.email)
                  AND (
                      t.user_id IS NULL OR t.user_id = ''
                      OR (
                          t.user_id IS DISTINCT FROM u.id::text
                          AND NOT EXISTS (SELECT 1 FROM users u2 WHERE u2.id::text = t.user_id)
                      )
                  );
                """
            )
            cursor.execute(
                f"""
                UPDATE {tbl} t
                SET owner_email = u.email
                FROM users u
                WHERE (t.owner_email IS NULL OR t.owner_email = '')
                  AND t.user_id IS NOT NULL AND t.user_id != ''
                  AND t.user_id = u.id::text;
                """
            )

    cursor.execute(
        """
        UPDATE rules r
        SET user_id = rv.user_id,
            owner_email = COALESCE(NULLIF(rv.owner_email, ''), r.owner_email)
        FROM rule_versions rv
        WHERE r.version_id = rv.version_id
          AND (
              (rv.user_id IS NOT NULL AND rv.user_id != '' AND (
                  r.user_id IS NULL OR r.user_id = ''
                  OR (
                      r.user_id IS DISTINCT FROM rv.user_id
                      AND NOT EXISTS (SELECT 1 FROM users u2 WHERE u2.id::text = r.user_id)
                  )
              ))
              OR (rv.owner_email IS NOT NULL AND rv.owner_email != '' AND (r.owner_email IS NULL OR r.owner_email = ''))
          );
        """
    )

    for run_child_tbl in ("screening_results", "funnel_counts"):
        cursor.execute(
            f"""
            UPDATE {run_child_tbl} c
            SET user_id = sr.user_id,
                owner_email = COALESCE(NULLIF(sr.owner_email, ''), c.owner_email)
            FROM screening_runs sr
            WHERE c.run_id = sr.run_id
              AND (
                  (sr.user_id IS NOT NULL AND sr.user_id != '' AND (
                      c.user_id IS NULL OR c.user_id = ''
                      OR (
                          c.user_id IS DISTINCT FROM sr.user_id
                          AND NOT EXISTS (SELECT 1 FROM users u2 WHERE u2.id::text = c.user_id)
                      )
                  ))
                  OR (sr.owner_email IS NOT NULL AND sr.owner_email != '' AND (c.owner_email IS NULL OR c.owner_email = ''))
              );
            """
        )


def reconcile_user_ownership(user_id: str, owner_email: str) -> None:
    """Link any unowned or orphaned email-matched rows to the given verified user."""
    if not user_id or not owner_email:
        return
    from app.db.connection import db_manager

    conn = db_manager.get_connection()
    try:
        cursor = conn.cursor()
        reconcile_ownership_with_cursor(cursor, user_id=user_id, owner_email=owner_email)
        conn.commit()
    finally:
        conn.close()


def build_owner_filter(
    user_id: Optional[str] = None,
    owner_email: Optional[str] = None,
    alias: str = "",
) -> Tuple[str, Tuple[Any, ...]]:
    """Build a parameterized SQL ownership predicate.

    Prefers exact ``user_id`` match when present and falls back to case-insensitive
    ``owner_email`` matching only when the row has no ``user_id`` recorded yet.
    Returns an unsatisfiable predicate when neither identifier is provided.
    """
    prefix = f"{alias}." if alias else ""
    clean_uid = user_id.strip() if isinstance(user_id, str) and user_id.strip() else None
    clean_email = owner_email.strip() if isinstance(owner_email, str) and owner_email.strip() else None

    if clean_uid and clean_email:
        clause = (
            f"({prefix}user_id = %s OR "
            f"(({prefix}user_id IS NULL OR {prefix}user_id = '') "
            f"AND LOWER({prefix}owner_email) = LOWER(%s)))"
        )
        return clause, (clean_uid, clean_email)
    if clean_uid:
        return f"{prefix}user_id = %s", (clean_uid,)
    if clean_email:
        return f"LOWER({prefix}owner_email) = LOWER(%s)", (clean_email,)
    return "1 = 0", ()


def is_record_owned_by(
    record_user_id: Optional[str],
    record_owner_email: Optional[str],
    current_user_id: Optional[str],
    current_user_email: Optional[str],
) -> bool:
    """Return True if a record belongs to the supplied authenticated user."""
    clean_rec_uid = record_user_id.strip() if isinstance(record_user_id, str) and record_user_id.strip() else None
    clean_cur_uid = current_user_id.strip() if isinstance(current_user_id, str) and current_user_id.strip() else None

    if clean_rec_uid:
        return bool(clean_cur_uid and clean_rec_uid == clean_cur_uid)

    clean_rec_email = (
        record_owner_email.strip().lower()
        if isinstance(record_owner_email, str) and record_owner_email.strip()
        else None
    )
    clean_cur_email = (
        current_user_email.strip().lower()
        if isinstance(current_user_email, str) and current_user_email.strip()
        else None
    )
    return bool(clean_rec_email and clean_cur_email and clean_rec_email == clean_cur_email)


def resolve_user_identity(
    user_id: Optional[str] = None,
    owner_email: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Fill in missing user_id or owner_email from the users table without hardcoding."""
    clean_uid = user_id.strip() if isinstance(user_id, str) and user_id.strip() else None
    clean_email = owner_email.strip().lower() if isinstance(owner_email, str) and owner_email.strip() else None

    if clean_uid and clean_email:
        return clean_uid, clean_email

    from app.repositories.user_repository import user_repository

    if clean_uid and not clean_email:
        user = user_repository.get_by_id(clean_uid)
        if user:
            return user.id, user.email
    elif clean_email and not clean_uid:
        user = user_repository.get_by_email(clean_email)
        if user:
            return user.id, user.email

    return clean_uid, clean_email
