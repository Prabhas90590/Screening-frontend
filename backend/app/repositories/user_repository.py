"""Repository for user account persistence.

Handles all SQL read/write operations against the 'users' table.
Follows the same pattern as DecisionRepository and RuleRepository.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.core.security import hash_password
from app.db.connection import db_manager
from app.models.user import UserRecord

logger = logging.getLogger("app.repositories.user")


class UserRepository:
    """SQL repository for the 'users' table."""

    def __init__(self):
        db_manager.init_tables()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_postgres(conn) -> bool:
        return hasattr(conn, "info") or "psycopg2" in str(type(conn))

    @staticmethod
    def _row_to_record(row) -> Optional[UserRecord]:
        """Convert a DB row (psycopg2 tuple or sqlite3 Row) to a UserRecord."""
        if row is None:
            return None
        return UserRecord(
            id=str(row[0]),
            email=row[1],
            hashed_password=row[2],
            full_name=row[3],
            is_active=bool(row[4]),
            created_at=row[5] if isinstance(row[5], datetime) else datetime.fromisoformat(str(row[5])),
            updated_at=row[6] if isinstance(row[6], datetime) else datetime.fromisoformat(str(row[6])),
            created_by_email=row[7] if len(row) > 7 else None,
        )

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_by_email(self, email: str) -> Optional[UserRecord]:
        """Fetch a user record by their email address (case-insensitive).

        Args:
            email: The email address to look up.

        Returns:
            A UserRecord if found, None otherwise.
        """
        conn = db_manager.get_connection()
        is_pg = self._is_postgres(conn)
        try:
            cur = conn.cursor()
            sql = (
                "SELECT id, email, hashed_password, full_name, is_active, "
                "created_at, updated_at, created_by_email "
                "FROM users WHERE LOWER(email) = LOWER(%s);"
                if is_pg else
                "SELECT id, email, hashed_password, full_name, is_active, "
                "created_at, updated_at, created_by_email "
                "FROM users WHERE LOWER(email) = LOWER(?);"
            )
            cur.execute(sql, (email,))
            return self._row_to_record(cur.fetchone())
        except Exception as e:
            logger.error(f"get_by_email failed for '{email}': {e}")
            return None
        finally:
            conn.close()

    def get_by_id(self, user_id: str) -> Optional[UserRecord]:
        """Fetch a user record by their UUID.

        Args:
            user_id: The UUID string of the user.

        Returns:
            A UserRecord if found, None otherwise.
        """
        conn = db_manager.get_connection()
        is_pg = self._is_postgres(conn)
        try:
            cur = conn.cursor()
            sql = (
                "SELECT id, email, hashed_password, full_name, is_active, "
                "created_at, updated_at, created_by_email "
                "FROM users WHERE id = %s;"
                if is_pg else
                "SELECT id, email, hashed_password, full_name, is_active, "
                "created_at, updated_at, created_by_email "
                "FROM users WHERE id = ?;"
            )
            cur.execute(sql, (user_id,))
            return self._row_to_record(cur.fetchone())
        except Exception as e:
            logger.error(f"get_by_id failed for '{user_id}': {e}")
            return None
        finally:
            conn.close()

    def email_exists(self, email: str) -> bool:
        """Check whether an email is already registered.

        Args:
            email: Email to check.

        Returns:
            True if the email is in the users table, False otherwise.
        """
        return self.get_by_email(email) is not None

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def create_user(
        self,
        email: str,
        plain_password: str,
        full_name: Optional[str] = None,
        created_by_email: Optional[str] = None,
    ) -> UserRecord:
        """Create a new user account with a securely hashed password.

        Args:
            email:             Unique email address for the new account.
            plain_password:    The raw password supplied at sign-up (will be hashed).
            full_name:         Optional display name.
            created_by_email:  Reserved for the Phase-9 ownership migration.

        Returns:
            The newly created UserRecord.

        Raises:
            ValueError: If the email is already registered.
            RuntimeError: If the INSERT fails at the database level.
        """
        if self.email_exists(email):
            raise ValueError(f"Email '{email}' is already registered.")

        user_id = str(uuid.uuid4())
        hashed = hash_password(plain_password)
        now = datetime.now(timezone.utc)

        conn = db_manager.get_connection()
        is_pg = self._is_postgres(conn)
        try:
            cur = conn.cursor()
            sql = (
                "INSERT INTO users "
                "(id, email, hashed_password, full_name, is_active, created_at, updated_at, created_by_email) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s);"
                if is_pg else
                "INSERT INTO users "
                "(id, email, hashed_password, full_name, is_active, created_at, updated_at, created_by_email) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?);"
            )
            cur.execute(sql, (
                user_id,
                email.lower().strip(),
                hashed,
                full_name,
                True,
                now.isoformat(),
                now.isoformat(),
                created_by_email,
            ))
            conn.commit()
            logger.info(f"Created new user account: '{email}' (id={user_id})")
        except Exception as e:
            conn.rollback()
            logger.error(f"create_user failed for '{email}': {e}")
            raise RuntimeError(f"Could not create user account: {e}") from e
        finally:
            conn.close()

        return UserRecord(
            id=user_id,
            email=email.lower().strip(),
            hashed_password=hashed,
            full_name=full_name,
            is_active=True,
            created_at=now,
            updated_at=now,
            created_by_email=created_by_email,
        )

    def update_last_seen(self, user_id: str) -> None:
        """Bump the updated_at timestamp for a user (used as a last-active marker).

        Args:
            user_id: UUID of the user to update.
        """
        conn = db_manager.get_connection()
        is_pg = self._is_postgres(conn)
        now = datetime.now(timezone.utc).isoformat()
        try:
            cur = conn.cursor()
            sql = (
                "UPDATE users SET updated_at = %s WHERE id = %s;"
                if is_pg else
                "UPDATE users SET updated_at = ? WHERE id = ?;"
            )
            cur.execute(sql, (now, user_id))
            conn.commit()
        except Exception as e:
            logger.warning(f"update_last_seen failed for '{user_id}': {e}")
        finally:
            conn.close()


# Module-level singleton — imported by auth_service and future routes
user_repository = UserRepository()

