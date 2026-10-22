"""Verification script for Phase 5 raw response storage.

Demonstrates inserting a vendor raw JSON payload and reading it back
from the database (PostgreSQL if connected, or SQLite fallback).
"""

from datetime import datetime
import json
from pathlib import Path
import sys

# Ensure backend root is on sys.path so 'app' imports cleanly from any directory
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.connection import db_manager
from app.ingestion.raw_response_store import raw_response_store
from app.repositories.raw_response_repository import raw_response_repository


def main():
    print("=" * 60)
    print("PHASE 5: RAW RESPONSE STORAGE VERIFICATION")
    print("=" * 60)

    # 1. Initialize tables
    print("\n1. Initializing database tables...")
    db_manager.init_tables()

    # 2. Sample raw vendor response payload
    sample_payload = {
        "ticker": "INFY",
        "companyName": "Infosys Limited",
        "currency": "INR",
        "closePrice": 1850.0,
        "marketCap": 7750000000000,
        "ebitda": 380000000000,
        "forwardPE": 24.2,
        "analystConsensus": "Buy",
        "timestamp": datetime.utcnow().isoformat(),
    }

    # 3. Store raw response
    print("\n2. Storing raw response into database...")
    stored = raw_response_store.store_response(
        provider="eodhd",
        endpoint="/fundamentals/INFY.NSE",
        response_body=sample_payload,
        request_params={"api_token": "demo_sample_token", "fmt": "json"},
        run_id="run-test-001",
        status_code=200,
        latency_ms=185.4,
    )

    print(f"   -> Created Raw Response ID: {stored.id}")
    print(f"   -> Fingerprint (SHA-256):   {stored.fingerprint[:16]}...")
    print(f"   -> Sanitized Params:        {stored.request_params}")

    # 4. Read it back from database
    print("\n3. Reading it back from database...")
    retrieved = raw_response_repository.get_by_id(stored.id)

    if retrieved:
        print("   SUCCESS! Row retrieved from database:")
        print(f"   ID:          {retrieved.id}")
        print(f"   Provider:    {retrieved.provider}")
        print(f"   Endpoint:    {retrieved.endpoint}")
        print(f"   Status Code: {retrieved.status_code}")
        print(f"   Latency:     {retrieved.latency_ms} ms")
        print(f"   Saved Body:  {json.dumps(retrieved.response_body)[:80]}...")
    else:
        print("   FAILED to retrieve row.")

    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
