"""Comprehensive verification suite for Data Blockers and Run Statuses.

Tests:
  1. Real Data Blocker Unit Logic:
     - Trigger 1: Stale market data (business day lag calculation & threshold detection)
     - Trigger 2: Missing FX exchange rates (currency normalization guardrail)
     - Trigger 3: Vendor HTTP 429 rate limit tolerance (> 5%)
     - Trigger 4: Universe coverage completeness cutoff (< 75%)
  2. End-to-End Screening Pipeline Execution:
     - Normal Run -> Status: SUCCEEDED
     - Stale Market Data -> Status: BLOCKED
     - Missing FX Rates -> Status: BLOCKED
     - Vendor Rate Limit -> Status: BLOCKED
     - Low Universe Coverage -> Status: BLOCKED
"""

import os
import sys
from pathlib import Path

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


import asyncio
from datetime import date, timedelta
import sys

from app.models.company_metrics import CompanyMetricsRecord
from app.schemas.screening import ScreeningRunRequest
from app.services.data_blocker_service import data_blocker_service, DataBlockerService
from app.services.screening_service import screening_service


def test_unit_triggers():
    print("\n" + "=" * 70)
    print("STEP 1: Testing Pure Unit Guardrail Logic (All 4 Triggers)")
    print("=" * 70)

    # -------------------------------------------------------------
    # Trigger 1: Staleness Check
    # -------------------------------------------------------------
    today = date(2026, 10, 30)  # Friday
    fresh_date = str(date(2026, 10, 29))  # Thursday (1 business day)
    stale_date = str(date(2026, 10, 20))  # 8 business days ago

    # Fresh universe
    res_fresh = DataBlockerService.check_market_staleness(
        as_of_dates=[fresh_date] * 20, reference_date=today
    )
    assert res_fresh.passed, "Fresh quotes should pass staleness check"
    print(f"[PASS] Trigger 1 (Fresh Data): {res_fresh.summary}")

    # Stale universe (100% stale)
    res_stale = DataBlockerService.check_market_staleness(
        as_of_dates=[stale_date] * 20, reference_date=today
    )
    assert not res_stale.passed, "Stale quotes must fail staleness check"
    print(f"[PASS] Trigger 1 (Stale Data Detected): {res_stale.summary}")

    # -------------------------------------------------------------
    # Trigger 2: Missing FX Rates Check
    # -------------------------------------------------------------
    res_fx_good = DataBlockerService.check_fx_availability(
        required_currencies={"INR", "EUR", "USD"}
    )
    assert res_fx_good.passed, "Known currencies should pass"
    print(f"[PASS] Trigger 2 (Known Currencies): {res_fx_good.summary}")

    # Missing fake currency 'XYZ'
    res_fx_missing = DataBlockerService.check_fx_availability(
        required_currencies={"INR", "XYZ", "ABC"}
    )
    assert not res_fx_missing.passed, "Missing currencies must be blocked"
    print(f"[PASS] Trigger 2 (Missing FX Blocked): {res_fx_missing.summary}")

    # -------------------------------------------------------------
    # Trigger 3: Vendor Rate Limits (HTTP 429)
    # -------------------------------------------------------------
    # Low throttle (2 / 100 = 2% < 5%)
    res_rate_ok = DataBlockerService.check_vendor_rate_limits(
        total_requests=100, rate_limited_requests=2, max_rate_limit_pct=5.0
    )
    assert res_rate_ok.passed, "Low throttle rate should pass"
    print(f"[PASS] Trigger 3 (Normal Throttle 2%): {res_rate_ok.summary}")

    # High throttle (15 / 100 = 15% >= 5%)
    res_rate_blocked = DataBlockerService.check_vendor_rate_limits(
        total_requests=100, rate_limited_requests=15, max_rate_limit_pct=5.0
    )
    assert not res_rate_blocked.passed, "15% throttle must trigger a blocker"
    print(f"[PASS] Trigger 3 (Rate Limit Blocked 15%): {res_rate_blocked.summary}")

    # -------------------------------------------------------------
    # Trigger 4: Universe Coverage Threshold (< 75%)
    # -------------------------------------------------------------
    # Good universe: 10 stocks, 9 complete (90%)
    good_metrics = [
        CompanyMetricsRecord(
            canonical_company_id=f"c-{i}", ticker=f"T{i}",
            as_of_date=str(date.today()),
            market_cap_usd=1e9, price_usd=10.0, forward_pe=15.0
        ) for i in range(10)
    ]
    res_cov_good = DataBlockerService.check_universe_coverage(good_metrics, min_coverage_pct=75.0)
    assert res_cov_good.passed, "90% coverage should pass"
    print(f"[PASS] Trigger 4 (Good Coverage 100%): {res_cov_good.summary}")

    # Incomplete universe: 10 stocks, only 4 complete (40% < 75%)
    poor_metrics = [
        CompanyMetricsRecord(
            canonical_company_id=f"c-{i}", ticker=f"T{i}",
            as_of_date=str(date.today()),
            market_cap_usd=None if i >= 4 else 1e9,
            price_usd=None if i >= 4 else 10.0,
            forward_pe=None
        ) for i in range(10)
    ]
    res_cov_blocked = DataBlockerService.check_universe_coverage(poor_metrics, min_coverage_pct=75.0)
    assert not res_cov_blocked.passed, "40% coverage must trigger a blocker"
    print(f"[PASS] Trigger 4 (Low Coverage Blocked 40%): {res_cov_blocked.summary}")


async def test_end_to_end_pipeline():
    print("\n" + "=" * 70)
    print("STEP 2: Testing End-to-End Screening Pipeline Execution")
    print("=" * 70)

    # 1. Normal Screening Run -> Succeeded
    req_normal = ScreeningRunRequest(
        countries=["in"],
        exchanges=["nse"],
        display_currency="USD",
        profile_name="Global Quality Growth Core - Version 3",
    )
    res_normal = await screening_service.initiate_screening_run(req_normal)
    print(f"\n[Case 1: SUCCESSFUL RUN]")
    print(f"  Run ID: {res_normal.run_id}")
    print(f"  Status: {res_normal.status}")
    print(f"  Total Screened: {res_normal.funnel.universe}")
    print(f"  Selected Top 20: {res_normal.funnel.selected}")
    assert res_normal.status == "succeeded", "Normal run should succeed"

    # 2. Stale Market Data -> Blocked
    req_stale = ScreeningRunRequest(
        countries=["in"],
        exchanges=["nse"],
        display_currency="USD",
        profile_name="Global Quality Growth Core - Version 3",
        sim_blocker="stale",
    )
    res_stale = await screening_service.initiate_screening_run(req_stale)
    print(f"\n[Case 2: DATA BLOCKER - STALE MARKET DATA]")
    print(f"  Run ID: {res_stale.run_id}")
    print(f"  Status: {res_stale.status}")
    print(f"  Errors: {res_stale.errors}")
    print(f"  Blocker Details: {res_stale.blocker_details.get('blocker_type')}")
    assert res_stale.status == "blocked", "Stale data must return status='blocked'"

    # 3. Missing FX Rates -> Blocked
    req_fx = ScreeningRunRequest(
        countries=["in"],
        exchanges=["nse"],
        display_currency="USD",
        profile_name="Global Quality Growth Core - Version 3",
        sim_blocker="fx",
    )
    res_fx = await screening_service.initiate_screening_run(req_fx)
    print(f"\n[Case 3: DATA BLOCKER - MISSING FX RATES]")
    print(f"  Run ID: {res_fx.run_id}")
    print(f"  Status: {res_fx.status}")
    print(f"  Errors: {res_fx.errors}")
    print(f"  Blocker Details: {res_fx.blocker_details.get('blocker_type')}")
    assert res_fx.status == "blocked", "Missing FX must return status='blocked'"

    # 4. Vendor Rate Limit (429) -> Blocked
    req_rate = ScreeningRunRequest(
        countries=["in"],
        exchanges=["nse"],
        display_currency="USD",
        profile_name="Global Quality Growth Core - Version 3",
        sim_blocker="rate_limit",
    )
    res_rate = await screening_service.initiate_screening_run(req_rate)
    print(f"\n[Case 4: DATA BLOCKER - VENDOR RATE LIMIT (429)]")
    print(f"  Run ID: {res_rate.run_id}")
    print(f"  Status: {res_rate.status}")
    print(f"  Errors: {res_rate.errors}")
    print(f"  Blocker Details: {res_rate.blocker_details.get('blocker_type')}")
    assert res_rate.status == "blocked", "Vendor 429 throttle must return status='blocked'"

    # 5. Low Universe Coverage -> Blocked
    req_cov = ScreeningRunRequest(
        countries=["in"],
        exchanges=["nse"],
        display_currency="USD",
        profile_name="Global Quality Growth Core - Version 3",
        sim_blocker="coverage",
    )
    res_cov = await screening_service.initiate_screening_run(req_cov)
    print(f"\n[Case 5: DATA BLOCKER - LOW UNIVERSE COVERAGE]")
    print(f"  Run ID: {res_cov.run_id}")
    print(f"  Status: {res_cov.status}")
    print(f"  Errors: {res_cov.errors}")
    print(f"  Blocker Details: {res_cov.blocker_details.get('blocker_type')}")
    assert res_cov.status == "blocked", "Low coverage must return status='blocked'"

    print("\n" + "=" * 70)
    print("ALL 5 DATA BLOCKER & RUN STATUS CASES VERIFIED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    test_unit_triggers()
    asyncio.run(test_end_to_end_pipeline())
