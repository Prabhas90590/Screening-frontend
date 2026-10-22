"""PostgreSQL setup and table creation helper.

Connects to the PostgreSQL instance specified in backend/.env,
executes the table creation script, and confirms the table is visible.
"""

from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.db.connection import POSTGRES_SCHEMA_SQL


def main():
    print("=" * 60)
    print("POSTGRESQL TABLE CREATION CHECK")
    print("=" * 60)

    db_url = settings.database_url
    print(f"\n1. Target Database URL from .env:\n   {db_url}")

    # Check if psycopg2 driver is installed
    print("\n2. Checking PostgreSQL Python driver (psycopg2)...")
    try:
        import psycopg2
        print("   [OK] psycopg2 driver is installed.")
    except ImportError:
        print("   [ERROR] psycopg2 is NOT installed in this Python environment.")
        print("   Please run:")
        print("   .venv\\Scripts\\python.exe -m pip install psycopg2-binary")
        return

    # Try connecting to PostgreSQL
    print("\n3. Connecting to PostgreSQL...")
    try:
        conn = psycopg2.connect(db_url)
        print("   [OK] Connected successfully to PostgreSQL!")
    except Exception as e:
        print(f"   [ERROR] Could not connect to PostgreSQL: {e}")
        print("\nTroubleshooting tips:")
        print("1. Did you create a database named 'screening_db' in pgAdmin?")
        print("2. Is your password correct in .env?")
        print("3. Is the PostgreSQL service running in Windows?")
        return

    # Execute table creation query
    print("\n4. Creating 'raw_responses' table in PostgreSQL...")
    try:
        cursor = conn.cursor()
        cursor.execute(POSTGRES_SCHEMA_SQL)
        conn.commit()
        print("   [OK] SQL query executed successfully.")
    except Exception as e:
        print(f"   [ERROR] Failed to execute SQL: {e}")
        conn.rollback()
        conn.close()
        return

    # Verify table exists in PostgreSQL public schema
    print("\n5. Verifying table in PostgreSQL catalog...")
    try:
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'raw_responses';
        """)
        row = cursor.fetchone()
        if row:
            print("   [SUCCESS] Table 'raw_responses' EXISTS in PostgreSQL!")
            print("\n" + "=" * 60)
            print("HOW TO SEE IT IN PGADMIN:")
            print("1. Open pgAdmin 4.")
            print("2. Expand: Databases -> screening_db -> Schemas -> public -> Tables.")
            print("3. IMPORTANT: Right-click 'Tables' and click 'Refresh'!")
            print("4. You will now see 'raw_responses'.")
            print("=" * 60)
        else:
            print("   [WARN] Query finished but table was not found in public schema.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

