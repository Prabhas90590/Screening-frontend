"""Verification script for Phase 8: Screening Request API & Rule Management API.

Tests:
1. GET /api/rules/catalog (verifies 16 standard metrics and limits).
2. POST /api/rules/profiles (creates a custom profile in PostgreSQL).
3. GET /api/rules/profiles (verifies persistence across calls).
4. PUT /api/rules/profiles/{id}/activate (verifies setting active strategy).
5. PUT /api/rules/profiles/{id} (verifies updating metric thresholds).
6. POST /api/screenings (valid market request -> creates persistent run).
7. POST /api/screenings (invalid exchange-country mismatch -> HTTP 422 validation error).
8. GET /api/screenings/{run_id} (retrieves run details from PostgreSQL).
9. DELETE /api/rules/profiles/{id} (deletes profile from PostgreSQL).
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

client = TestClient(app)


def main():
    configure_logging(debug=True)
    print("=" * 70)
    print("PHASE 8: SCREENING REQUEST API & RULE MANAGEMENT VERIFICATION")
    print("=" * 70)

    # 1. Initialize tables in PostgreSQL
    print("\n1. Verifying database tables...")
    db_manager.init_tables()
    print("   [PASS] Tables initialized.")

    # 2. Test Rule Catalog
    print("\n2. Testing GET /api/rules/catalog...")
    catalog_resp = client.get("/api/rules/catalog")
    assert catalog_resp.status_code == 200, f"Expected 200, got {catalog_resp.status_code}"
    catalog = catalog_resp.json()
    print(f"   -> Retrieved {len(catalog)} standard metrics in catalog.")
    assert len(catalog) == 16, f"Expected 16 metrics, got {len(catalog)}"
    pe_metric = next(m for m in catalog if m["id"] == "forward_pe")
    print(f"   -> Metric '{pe_metric['name']}': Limits [{pe_metric['min_limit']} - {pe_metric['max_limit']}] {pe_metric['unit']}")
    print("   [PASS] Rule Catalog API verified.")

    # 3. Test Profile Creation (Persistent in PostgreSQL)
    print("\n3. Testing POST /api/rules/profiles (Creating Custom Profile)...")
    profile_payload = {
        "profile_name": "Tech Growth 2026",
        "version_number": "1.0",
        "description": "High growth technology profile with strict leverage gates",
        "is_active": False,
        "sector_limits": {"Information Technology": 2.5, "Communication Services": 3.0},
        "diversification_rules": {"max_sector_weight": 30.0},
        "rules": [
            {
                "id": "forward_pe",
                "name": "Forward P/E",
                "category": "Valuation",
                "mode": "Both",
                "condition": "<=",
                "value": 35.0,
                "value_display": "<= 35.0x",
                "weight": 20.0,
            },
            {
                "id": "net_debt_ebitda",
                "name": "Net debt / EBITDA",
                "category": "Risk & leverage",
                "mode": "Req.",
                "condition": "<=",
                "value": 2.5,
                "value_display": "<= 2.5x",
                "weight": 15.0,
            },
        ],
    }
    create_resp = client.post("/api/rules/profiles", json=profile_payload)
    assert create_resp.status_code == 201, f"Expected 201, got {create_resp.status_code}: {create_resp.text}"
    created_profile = create_resp.json()
    test_version_id = created_profile["version_id"]
    print(f"   -> Created Profile: '{created_profile['profile_name']}' (ID: {test_version_id})")
    print(f"   -> Rules count:     {len(created_profile['rules'])}")
    print("   [PASS] Profile creation verified.")

    # 4. Test Profile Retrieval (Proves persistence across requests)
    print("\n4. Testing GET /api/rules/profiles (Persistence Check)...")
    list_resp = client.get("/api/rules/profiles")
    assert list_resp.status_code == 200
    profiles = list_resp.json()
    found = any(p["version_id"] == test_version_id for p in profiles)
    assert found, "Created profile not found in database!"
    print(f"   -> Successfully retrieved {len(profiles)} profiles from PostgreSQL.")
    print("   [PASS] Profile persistence verified.")

    # 5. Test Profile Activation
    print(f"\n5. Testing PUT /api/rules/profiles/{test_version_id}/activate...")
    act_resp = client.put(f"/api/rules/profiles/{test_version_id}/activate")
    assert act_resp.status_code == 200
    active_profile = act_resp.json()
    assert active_profile["is_active"] is True
    print(f"   -> Active profile is now: '{active_profile['profile_name']}'")
    print("   [PASS] Profile activation verified.")

    # 6. Test Profile Update
    print(f"\n6. Testing PUT /api/rules/profiles/{test_version_id} (Updating Threshold)...")
    update_payload = {
        "description": "Updated description with relaxed P/E limit",
        "rules": [
            {
                "id": "forward_pe",
                "name": "Forward P/E",
                "category": "Valuation",
                "mode": "Both",
                "condition": "<=",
                "value": 30.0,
                "value_display": "<= 30.0x",
                "weight": 25.0,
            }
        ],
    }
    update_resp = client.put(f"/api/rules/profiles/{test_version_id}", json=update_payload)
    assert update_resp.status_code == 200
    updated_data = update_resp.json()
    assert updated_data["rules"][0]["value"] == 30.0
    print(f"   -> Updated Forward P/E threshold to: {updated_data['rules'][0]['value']}x")
    print("   [PASS] Profile update verified.")

    # 7. Test Screening Run Initiation (Valid Markets)
    print("\n7. Testing POST /api/screenings (Valid Request)...")
    run_payload = {
        "countries": ["us", "in"],
        "exchanges": ["nasdaq", "nse"],
        "display_currency": "USD",
        "rule_version_id": test_version_id,
    }
    run_resp = client.post("/api/screenings", json=run_payload)
    assert run_resp.status_code == 201, f"Expected 201, got {run_resp.status_code}: {run_resp.text}"
    run_data = run_resp.json()
    run_id = run_data["run_id"]
    print(f"   -> Generated Run ID:      {run_id}")
    print(f"   -> Status:                {run_data['status']}")
    print(f"   -> Duration:              {run_data['duration_ms']} ms")
    print(f"   -> Active Data Provider:  {run_data['provider_used']}")
    print("   [PASS] Screening run creation verified.")

    # 8. Test Screening Run Validation (Invalid Exchange/Country Mismatch)
    print("\n8. Testing POST /api/screenings with Mismatched Exchange/Country...")
    invalid_payload = {
        "countries": ["us"],  # Only US selected
        "exchanges": ["nse"],  # NSE is in India!
    }
    invalid_resp = client.post("/api/screenings", json=invalid_payload)
    assert invalid_resp.status_code == 422, f"Expected 422, got {invalid_resp.status_code}"
    error_detail = invalid_resp.json()["detail"]
    print(f"   -> Caught Expected 422 Error: {error_detail}")
    print("   [PASS] Market cross-validation rejected invalid selection successfully.")

    # 9. Test GET /api/screenings/{run_id}
    print(f"\n9. Testing GET /api/screenings/{run_id}...")
    get_run_resp = client.get(f"/api/screenings/{run_id}")
    assert get_run_resp.status_code == 200
    retrieved_run = get_run_resp.json()
    assert retrieved_run["run_id"] == run_id
    assert retrieved_run["rule_version_id"] == test_version_id
    print(f"   -> Stored run retrieved: {retrieved_run['run_id']} (Rule Version: {retrieved_run['rule_version_id']})")
    print("   [PASS] Run retrieval verified.")

    # 10. Test Profile Deletion
    print(f"\n10. Testing DELETE /api/rules/profiles/{test_version_id}...")
    del_resp = client.delete(f"/api/rules/profiles/{test_version_id}")
    assert del_resp.status_code == 200
    # Verify it is no longer in DB
    get_del_resp = client.get(f"/api/rules/profiles/{test_version_id}")
    assert get_del_resp.status_code == 404
    print("   -> Profile deleted from PostgreSQL successfully.")
    print("   [PASS] Profile deletion verified.")

    print("\n" + "=" * 70)
    print("PHASE 8 VERIFICATION COMPLETE: ALL APIS TESTED & PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    main()

