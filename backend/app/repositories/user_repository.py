"""Repository for user account persistence.

Handles all SQL read/write operations against the 'users' table in PostgreSQL.
Supports email verification, password reset tokens, and profile updates.
"""

from datetime import datetime, timezone
import logging
from typing import Optional
import uuid

from app.core.security import hash_password
from app.db.connection import db_manager
from app.models.user import UserRecord

logger = logging.getLogger("app.repositories.user")


class UserRepository:
    """SQL repository for the 'users' table in PostgreSQL."""

    def __init__(self):
        db_manager.init_tables()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_record(row) -> Optional[UserRecord]:
        """Convert a PostgreSQL DB row to a UserRecord."""
        if row is None:
            return None

        # Helper to parse datetime
        def _parse_dt(val):
            if val is None:
                return None
            if isinstance(val, datetime):
                return val
            try:
                return datetime.fromisoformat(str(val))
            except Exception:
                return None

        return UserRecord(
            id=str(row[0]),
            email=row[1],
            hashed_password=row[2],
            full_name=row[3],
            is_active=bool(row[4]),
            created_at=_parse_dt(row[5]) or datetime.now(timezone.utc),
            updated_at=_parse_dt(row[6]) or datetime.now(timezone.utc),
            created_by_email=row[7] if len(row) > 7 else None,
            is_verified=bool(row[8]) if len(row) > 8 and row[8] is not None else False,
            verification_code=row[9] if len(row) > 9 else None,
            verification_expires_at=_parse_dt(row[10]) if len(row) > 10 else None,
            reset_token=row[11] if len(row) > 11 else None,
            reset_expires_at=_parse_dt(row[12]) if len(row) > 12 else None,
        )

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_by_email(self, email: str) -> Optional[UserRecord]:
        """Fetch a user record by their email address (case-insensitive)."""
        conn = db_manager.get_connection()
        try:
            cur = conn.cursor()
            sql = (
                "SELECT id, email, hashed_password, full_name, is_active, "
                "created_at, updated_at, created_by_email, is_verified, "
                "verification_code, verification_expires_at, reset_token, reset_expires_at "
                "FROM users WHERE LOWER(email) = LOWER(%s);"
            )
            cur.execute(sql, (email.strip(),))
            return self._row_to_record(cur.fetchone())
        except Exception as e:
            logger.error(f"get_by_email failed for '{email}': {e}")
            return None
        finally:
            conn.close()

    def get_by_id(self, user_id: str) -> Optional[UserRecord]:
        """Fetch a user record by their UUID."""
        conn = db_manager.get_connection()
        try:
            cur = conn.cursor()
            sql = (
                "SELECT id, email, hashed_password, full_name, is_active, "
                "created_at, updated_at, created_by_email, is_verified, "
                "verification_code, verification_expires_at, reset_token, reset_expires_at "
                "FROM users WHERE id = %s;"
            )
            cur.execute(sql, (user_id,))
            return self._row_to_record(cur.fetchone())
        except Exception as e:
            logger.error(f"get_by_id failed for '{user_id}': {e}")
            return None
        finally:
            conn.close()

    def email_exists(self, email: str) -> bool:
        """Check whether an email is already registered."""
        return self.get_by_email(email) is not None

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def create_user(
        self,
        email: str,
        plain_password: str,
        full_name: Optional[str] = None,
        verification_code: Optional[str] = None,
        verification_expires_at: Optional[datetime] = None,
        is_verified: bool = False,
        created_by_email: Optional[str] = None,
    ) -> UserRecord:
        """Create a new user account with a securely hashed password."""
        clean_email = email.lower().strip()
        if self.email_exists(clean_email):
            raise ValueError(f"Email '{clean_email}' is already registered.")

        user_id = str(uuid.uuid4())
        hashed = hash_password(plain_password)
        now = datetime.now(timezone.utc)

        conn = db_manager.get_connection()
        try:
            cur = conn.cursor()
            sql = (
                "INSERT INTO users "
                "(id, email, hashed_password, full_name, is_active, is_verified, "
                "verification_code, verification_expires_at, created_at, updated_at, created_by_email) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"
            )
            cur.execute(
                sql,
                (
                    user_id,
                    clean_email,
                    hashed,
                    full_name,
                    True,
                    is_verified,
                    verification_code,
                    verification_expires_at,
                    now,
                    now,
                    created_by_email,
                ),
            )
            conn.commit()
            logger.info(f"Created new user account: '{clean_email}' (id={user_id}, verified={is_verified})")
        except Exception as e:
            conn.rollback()
            logger.error(f"create_user failed for '{clean_email}': {e}")
            raise RuntimeError(f"Could not create user account: {e}") from e
        finally:
            conn.close()

        return UserRecord(
            id=user_id,
            email=clean_email,
            hashed_password=hashed,
            full_name=full_name,
            is_active=True,
            is_verified=is_verified,
            verification_code=verification_code,
            verification_expires_at=verification_expires_at,
            created_at=now,
            updated_at=now,
            created_by_email=created_by_email,
        )

    def set_verification_code(self, email: str, code: str, expires_at: datetime) -> bool:
        """Assign or update a 6-digit email verification code for an account."""
        conn = db_manager.get_connection()
        now = datetime.now(timezone.utc)
        try:
            cur = conn.cursor()
            sql = (
                "UPDATE users SET verification_code = %s, verification_expires_at = %s, updated_at = %s "
                "WHERE LOWER(email) = LOWER(%s);"
            )
            cur.execute(sql, (code, expires_at, now, email.strip()))
            conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            conn.rollback()
            logger.error(f"set_verification_code failed for '{email}': {e}")
            return False
        finally:
            conn.close()

    def verify_email(self, email: str, code: str) -> bool:
        """Confirm corporate email ownership if code matches and has not expired."""
        user = self.get_by_email(email)
        if not user:
            return False

        if user.is_verified:
            return True

        if not user.verification_code or user.verification_code.strip() != code.strip():
            return False

        now = datetime.now(timezone.utc)
        if user.verification_expires_at and user.verification_expires_at < now:
            return False

        conn = db_manager.get_connection()
        try:
            cur = conn.cursor()
            sql = (
                "UPDATE users SET is_verified = TRUE, verification_code = NULL, "
                "verification_expires_at = NULL, updated_at = %s "
                "WHERE id = %s;"
            )
            cur.execute(sql, (now, user.id))
            conn.commit()
            logger.info(f"Email verified successfully for user '{user.email}' (id={user.id})")
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"verify_email database update failed: {e}")
            return False
        finally:
            conn.close()

    def set_reset_token(self, email: str, token: str, expires_at: datetime) -> bool:
        """Store a 6-digit password reset authorization code."""
        conn = db_manager.get_connection()
        now = datetime.now(timezone.utc)
        try:
            cur = conn.cursor()
            sql = (
                "UPDATE users SET reset_token = %s, reset_expires_at = %s, updated_at = %s "
                "WHERE LOWER(email) = LOWER(%s);"
            )
            cur.execute(sql, (token, expires_at, now, email.strip()))
            conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            conn.rollback()
            logger.error(f"set_reset_token failed for '{email}': {e}")
            return False
        finally:
            conn.close()

    def reset_password_with_token(self, email: str, token: str, new_plain_password: str) -> bool:
        """Reset password if the token matches and has not expired."""
        user = self.get_by_email(email)
        if not user or not user.reset_token:
            return False

        if user.reset_token.strip() != token.strip():
            return False

        now = datetime.now(timezone.utc)
        if user.reset_expires_at and user.reset_expires_at < now:
            return False

        new_hashed = hash_password(new_plain_password)
        conn = db_manager.get_connection()
        try:
            cur = conn.cursor()
            sql = (
                "UPDATE users SET hashed_password = %s, reset_token = NULL, "
                "reset_expires_at = NULL, updated_at = %s "
                "WHERE id = %s;"
            )
            cur.execute(sql, (new_hashed, now, user.id))
            conn.commit()
            logger.info(f"Password reset completed for '{user.email}' (id={user.id})")
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"reset_password_with_token failed: {e}")
            return False
        finally:
            conn.close()

    def update_password(self, user_id: str, new_plain_password: str) -> bool:
        """Update password for an authenticated session user."""
        new_hashed = hash_password(new_plain_password)
        now = datetime.now(timezone.utc)
        conn = db_manager.get_connection()
        try:
            cur = conn.cursor()
            sql = "UPDATE users SET hashed_password = %s, updated_at = %s WHERE id = %s;"
            cur.execute(sql, (new_hashed, now, user_id))
            conn.commit()
            logger.info(f"Password updated by user id={user_id}")
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"update_password failed for id={user_id}: {e}")
            return False
        finally:
            conn.close()

    def update_profile(self, user_id: str, full_name: str) -> Optional[UserRecord]:
        """Update user profile display name."""
        now = datetime.now(timezone.utc)
        conn = db_manager.get_connection()
        try:
            cur = conn.cursor()
            sql = "UPDATE users SET full_name = %s, updated_at = %s WHERE id = %s;"
            cur.execute(sql, (full_name.strip(), now, user_id))
            conn.commit()
            return self.get_by_id(user_id)
        except Exception as e:
            conn.rollback()
            logger.error(f"update_profile failed for id={user_id}: {e}")
            return None
        finally:
            conn.close()

    def update_last_seen(self, user_id: str) -> None:
        """Bump the updated_at timestamp for a user (used as a last-active marker)."""
        conn = db_manager.get_connection()
        now = datetime.now(timezone.utc)
        try:
            cur = conn.cursor()
            sql = "UPDATE users SET updated_at = %s WHERE id = %s;"
            cur.execute(sql, (now, user_id))
            conn.commit()
        except Exception as e:
            logger.warning(f"update_last_seen failed for '{user_id}': {e}")
        finally:
            conn.close()


# Module-level singleton — imported by auth_service and future routes
user_repository = UserRepository()
