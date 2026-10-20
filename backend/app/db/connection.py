import sqlite3
from pathlib import Path


def create_sqlite_connection(database_url: str) -> sqlite3.Connection:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError("Only SQLite database URLs are supported in Phase 1.")

    database_path = Path(database_url[len(prefix):])
    database_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(database_path)
