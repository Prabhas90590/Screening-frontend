"""Database connection manager supporting PostgreSQL (with SQLite development fallback).

Automatically initializes database tables on startup without requiring manual SQL commands.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional
import urllib.parse

from app.core.config import settings

logger = logging.getLogger("app.db")

# Table schema DDL for PostgreSQL
POSTGRES_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS raw_responses (
    id VARCHAR(64) PRIMARY KEY,
    run_id VARCHAR(64),
    provider VARCHAR(32) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    request_params JSONB DEFAULT '{}',
    response_body JSONB NOT NULL,
    fingerprint VARCHAR(64) NOT NULL,
    status_code INTEGER DEFAULT 200,
    latency_ms REAL DEFAULT 0.0,
    received_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_raw_responses_run_id ON raw_responses(run_id);
CREATE INDEX IF NOT EXISTS idx_raw_responses_fingerprint ON raw_responses(fingerprint);
"""

# SQLite equivalent DDL (for automatic fallback if Postgres is offline)
SQLITE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS raw_responses (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    provider TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    request_params TEXT DEFAULT '{}',
    response_body TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    status_code INTEGER DEFAULT 200,
    latency_ms REAL DEFAULT 0.0,
    received_at TEXT DEFAULT CURRENT_TIMESTAMP,
    is_success INTEGER DEFAULT 1,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_raw_responses_run_id ON raw_responses(run_id);
CREATE INDEX IF NOT EXISTS idx_raw_responses_fingerprint ON raw_responses(fingerprint);
"""


class DatabaseManager:
    """Manages database connection lifecycle and schema auto-creation."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.is_postgres = database_url.startswith("postgresql://") or database_url.startswith("postgres://")
        self._initialized = False

    def get_connection(self):
        """Obtain a live database connection."""
        if self.is_postgres:
            try:
                import psycopg2
                from psycopg2.extras import RealDictCursor
                conn = psycopg2.connect(self.database_url)
                return conn
            except ImportError:
                logger.warning("psycopg2 is not installed. Run 'pip install psycopg2-binary'. Falling back to SQLite.")
            except Exception as e:
                logger.warning(
                    f"Could not connect to PostgreSQL at '{self.database_url}' ({e}). "
                    "Make sure PostgreSQL is running. Falling back to local SQLite temporarily."
                )

        # SQLite fallback connection
        import sqlite3
        db_path = Path("./screening.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_tables(self):
        """Automatically create tables in the database if they don't already exist."""
        if self._initialized:
            return

        conn = self.get_connection()
        is_postgres_active = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        try:
            cursor = conn.cursor()
            if is_postgres_active:
                logger.info("Initializing PostgreSQL database schema (raw_responses table)...")
                cursor.execute(POSTGRES_SCHEMA_SQL)
                conn.commit()
                logger.info("PostgreSQL table 'raw_responses' verified/created successfully.")
            else:
                logger.info("Initializing SQLite database schema (raw_responses table)...")
                cursor.executescript(SQLITE_SCHEMA_SQL)
                conn.commit()
                logger.info("SQLite table 'raw_responses' verified/created successfully.")
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize database tables: {e}")
        finally:
            conn.close()


# Global database manager instance
db_manager = DatabaseManager(settings.database_url)
