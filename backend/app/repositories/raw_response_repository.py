"""Repository for persisting and querying raw external API responses in PostgreSQL.

Supports JSONB serialization, duplicate prevention via SHA-256 fingerprinting,
and run-level receipt retrieval.
"""

from datetime import datetime
import json
import logging
from typing import Any, Dict, List, Optional

from app.db.connection import db_manager
from app.models.raw_response import RawResponse

logger = logging.getLogger("app.repositories.raw_response")


class RawResponseRepository:
    """SQL repository for the raw_responses table."""

    def __init__(self):
        # Ensure database tables exist automatically
        db_manager.init_tables()

    def save(self, response: RawResponse) -> str:
        """Insert a raw vendor response into the database.

        Uses PostgreSQL JSONB or SQLite TEXT for JSON fields.
        """
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        insert_sql = """
            INSERT INTO raw_responses (
                id, run_id, provider, endpoint, request_params,
                response_body, fingerprint, status_code, latency_ms,
                received_at, is_success, error_message
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (id) DO UPDATE SET
                response_body = EXCLUDED.response_body,
                fingerprint = EXCLUDED.fingerprint;
        """ if is_postgres else """
            INSERT OR REPLACE INTO raw_responses (
                id, run_id, provider, endpoint, request_params,
                response_body, fingerprint, status_code, latency_ms,
                received_at, is_success, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """

        # Serialize body and params to JSON strings
        params_json = json.dumps(response.request_params) if isinstance(response.request_params, dict) else str(response.request_params)
        body_json = json.dumps(response.response_body) if isinstance(response.response_body, (dict, list)) else str(response.response_body)
        received_at_val = response.received_at if is_postgres else response.received_at.isoformat()
        is_success_val = response.is_success if is_postgres else (1 if response.is_success else 0)

        values = (
            response.id,
            response.run_id,
            response.provider,
            response.endpoint,
            params_json,
            body_json,
            response.fingerprint,
            response.status_code,
            response.latency_ms,
            received_at_val,
            is_success_val,
            response.error_message,
        )

        try:
            cursor = conn.cursor()
            cursor.execute(insert_sql, values)
            conn.commit()
            return response.id
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save raw response '{response.id}': {e}")
            raise
        finally:
            conn.close()

    def get_by_id(self, response_id: str) -> Optional[RawResponse]:
        """Retrieve a specific raw response by its unique ID."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        query = "SELECT * FROM raw_responses WHERE id = %s" if is_postgres else "SELECT * FROM raw_responses WHERE id = ?"

        try:
            cursor = conn.cursor()
            cursor.execute(query, (response_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_model(row, is_postgres)
        finally:
            conn.close()

    def get_by_fingerprint(self, fingerprint: str) -> Optional[RawResponse]:
        """Find an existing response by SHA-256 hash to prevent duplicate downloads."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        query = "SELECT * FROM raw_responses WHERE fingerprint = %s LIMIT 1" if is_postgres else "SELECT * FROM raw_responses WHERE fingerprint = ? LIMIT 1"

        try:
            cursor = conn.cursor()
            cursor.execute(query, (fingerprint,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_model(row, is_postgres)
        finally:
            conn.close()

    def get_by_run_id(self, run_id: str) -> List[RawResponse]:
        """Retrieve all raw responses associated with a specific screening execution."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        query = "SELECT * FROM raw_responses WHERE run_id = %s" if is_postgres else "SELECT * FROM raw_responses WHERE run_id = ?"

        try:
            cursor = conn.cursor()
            cursor.execute(query, (run_id,))
            rows = cursor.fetchall()
            return [self._row_to_model(row, is_postgres) for row in rows]
        finally:
            conn.close()

    def _row_to_model(self, row: Any, is_postgres: bool) -> RawResponse:
        """Convert a database row into a Pydantic RawResponse model."""
        if is_postgres:
            # Tuple order: id, run_id, provider, endpoint, request_params, response_body,
            # fingerprint, status_code, latency_ms, received_at, is_success, error_message
            return RawResponse(
                id=row[0],
                run_id=row[1],
                provider=row[2],
                endpoint=row[3],
                request_params=row[4] if isinstance(row[4], dict) else json.loads(row[4] or "{}"),
                response_body=row[5] if isinstance(row[5], (dict, list)) else json.loads(row[5] or "{}"),
                fingerprint=row[6],
                status_code=row[7],
                latency_ms=row[8],
                received_at=row[9] if isinstance(row[9], datetime) else datetime.fromisoformat(str(row[9])),
                is_success=bool(row[10]),
                error_message=row[11],
            )
        else:
            # SQLite sqlite3.Row
            return RawResponse(
                id=row["id"],
                run_id=row["run_id"],
                provider=row["provider"],
                endpoint=row["endpoint"],
                request_params=json.loads(row["request_params"] or "{}"),
                response_body=json.loads(row["response_body"] or "{}"),
                fingerprint=row["fingerprint"],
                status_code=row["status_code"],
                latency_ms=row["latency_ms"],
                received_at=datetime.fromisoformat(row["received_at"]) if "T" in str(row["received_at"]) else datetime.utcnow(),
                is_success=bool(row["is_success"]),
                error_message=row["error_message"],
            )


# Global repository instance
raw_response_repository = RawResponseRepository()
