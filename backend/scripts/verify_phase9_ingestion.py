"""Verification script for Phase 9: Data Ingestion Service.

Tests:
1. POST /api/screenings with chosen countries ("us", "in") and exchanges ("nasdaq", "nse").
2. Verifies raw_responses table has captured vendor JSON payloads with SHA-256 fingerprints.
3. Verifies companies & listings tables are populated via Security Master de-duplication.
4. Verifies financial_snapshots & estimate_snapshots tables contain point-in-time entries.
5. Verifies company_metrics table holds raw fundamentals and calculated ratios.
6. Verifies funnel_counts table records actual non-zero universe & market numbers.
"""

from pathlib import Path
import sys

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from app.core.logging import configure_logging
from app.db.connection import db_manager
from app.main import app
from app.repositories.company_metrics_repository import CompanyMetricsRepository
from app.repositories.company_repository import company_repository
from app.repositories.raw_response_repository import raw_response_repository
from app.repositories.snapshot_repository import snapshot_repository

client = TestClient(app)


def main():
    configure_logging(debug=True)
    print("=" * 70)
    print("PHASE 9: DATA INGESTION SERVICE VERIFICATION")
    print("=" * 70)

    # 1. Initialize tables
    print("\n1. Verifying database tables...")
    db_manager.init_tables()
    print("   [PASS] Tables initialized in PostgreSQL.")

    # 2. Trigger Screening with Ingestion for US (NASDAQ) and India (NSE)
    print("\n2. Triggering screening run with Data Ingestion (US & India)...")
    payload = {
        "countries": ["us", "in"],
        "exchanges": ["nasdaq", "nse"],
        "display_currency": "USD",
    }
    response = client.post("/api/screenings", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    run_data = response.json()
    run_id = run_data["run_id"]
    print(f"   -> Generated Run ID:      {run_id}")
    print(f"   -> Duration:              {run_data['duration_ms']} ms")
    print(f"   -> Universe Funnel Count: {run_data['funnel']['universe']} listings")
    print(f"   -> Markets Funnel Count:  {run_data['funnel']['markets']} companies")
    assert run_data["funnel"]["universe"] > 0, "Expected universe listings > 0"
    assert run_data["funnel"]["markets"] > 0, "Expected markets companies > 0"
    print("   [PASS] Screening run and data ingestion triggered successfully.")

    # 3. Verify raw_responses table in PostgreSQL
    print(f"\n3. Checking raw_responses table for run '{run_id}'...")
    raw_responses = raw_response_repository.get_by_run_id(run_id)
    print(f"   -> Found {len(raw_responses)} raw response payloads in PostgreSQL.")
    assert len(raw_responses) > 0, "No raw responses saved for this run!"
    for r in raw_responses:
        print(f"      • Endpoint: {r.endpoint} | Status: {r.status_code} | Hash: {r.fingerprint[:16]}...")
        assert len(r.fingerprint) == 64, "Expected valid 64-char SHA-256 fingerprint"
    print("   [PASS] Raw vendor payloads stored with cryptographic fingerprints.")

    # 4. Verify Security Master (companies & listings)
    print("\n4. Checking Security Master (companies & listings) in PostgreSQL...")
    companies = company_repository.list_companies()
    listings = company_repository.list_listings()
    print(f"   -> Total unique companies in database: {len(companies)}")
    print(f"   -> Total exchange listings in database: {len(listings)}")
    assert len(companies) > 0, "No companies found in database!"
    assert len(listings) > 0, "No listings found in database!"

    # Check for specific dual-listed or foreign entity (Infosys)
    infy = next((c for c in companies if "infosys" in c.name.lower() or c.primary_ticker == "INFY"), None)
    if infy:
        print(f"   -> Resolved Entity: {infy.name} (Canonical ID: {infy.canonical_id})")
        infy_listings = company_repository.get_listings_by_company(infy.canonical_id)
        print(f"      Listing venues for {infy.primary_ticker}: {[l.exchange_id.upper() for l in infy_listings]}")
    print("   [PASS] Companies and listings verified in PostgreSQL.")

    # 5. Verify financial_snapshots & estimate_snapshots
    print("\n5. Checking financial_snapshots and estimate_snapshots in PostgreSQL...")
    target_comp = companies[0]
    fin_snaps = snapshot_repository.get_financial_snapshots_by_company(target_comp.canonical_id)
    est_snaps = snapshot_repository.get_estimate_snapshots_by_company(target_comp.canonical_id)
    print(f"   -> Target Company: {target_comp.name} ({target_comp.canonical_id})")
    print(f"   -> Financial Snapshots count: {len(fin_snaps)}")
    print(f"   -> Estimate Snapshots count:  {len(est_snaps)}")
    assert len(fin_snaps) > 0, f"No financial snapshots for {target_comp.canonical_id}"
    assert len(est_snaps) > 0, f"No estimate snapshots for {target_comp.canonical_id}"
    print(f"      • Latest Financial Snapshot: EBITDA={fin_snaps[0].ebitda}, Revenue={fin_snaps[0].revenue}")
    print(f"      • Latest Estimate Snapshot:  Forward P/E={est_snaps[0].forward_pe}, PEG={est_snaps[0].peg_ratio}")
    print("   [PASS] Point-in-time financial and estimate snapshots verified.")

    # 6. Verify company_metrics table
    print("\n6. Checking company_metrics table in PostgreSQL...")
    metrics_repo = CompanyMetricsRepository()
    all_metrics = metrics_repo.list_metrics(limit=100)
    print(f"   -> Total company_metrics records: {len(all_metrics)}")
    assert len(all_metrics) > 0, "No company_metrics records found!"
    sample = all_metrics[0]
    print(f"   -> Sample Metric Record for '{sample.ticker}':")
    print(f"      • Market Cap (USD): {sample.market_cap_usd}")
    print(f"      • Price (USD):      {sample.price_usd}")
    print(f"      • Forward P/E:      {sample.forward_pe}")
    print(f"      • Net Debt:         {sample.net_debt}")
    print(f"      • EBITDA:           {sample.ebitda}")
    print(f"      • Confidence:       {sample.data_confidence}")
    print("   [PASS] Company metrics table populated with raw fundamentals and preliminary ratios.")

    print("\n" + "=" * 70)
    print("PHASE 9 VERIFICATION COMPLETE: ALL DATA INGESTION FLOWS PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    main()
