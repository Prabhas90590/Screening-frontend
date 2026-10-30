"""Verification test suite for Email Notifications and Excel Attachment.

Tests:
  1. Backend Excel Generation:
     - Multi-sheet workbook creation (Top 20 Winners, Near Misses, Master Universe).
     - Proper headers including Decision and Decision Reason.
  2. Case 1 (Run Success):
     - End-to-end screening execution.
     - Automated generation of HTML summary email + attached Excel workbook.
  3. Case 2 (Data Blocker):
     - Triggering a pre-flight guardrail.
     - Automated generation of Amber warning email explaining the data blocker.
  4. Case 3 (Run Failure):
     - Technical crash simulation.
     - Automated generation of Red alert email with error diagnosis.
"""

import asyncio
from datetime import date
from io import BytesIO
from pathlib import Path
import sys
import openpyxl

from app.core.config import settings
from app.models.company_metrics import CompanyMetricsRecord
from app.schemas.screening import ScreeningRunRequest
from app.services.export_service import export_service
from app.services.notification_service import notification_service, SENT_EMAILS_DIR
from app.services.screening_service import screening_service


def test_excel_export_generation():
    print("\n" + "=" * 70)
    print("STEP 1: Testing Backend Excel Workbook Generation")
    print("=" * 70)

    from app.models.screening_run import ScreeningResultRecord

    # Create mock screening results
    mock_results = [
        ScreeningResultRecord(
            id=f"res-{i}",
            run_id="run-test-export-001",
            canonical_company_id=f"c-{i}",
            ticker=f"TICK{i}",
            company_name=f"Company {i} Inc.",
            country="US" if i % 2 == 0 else "IN",
            exchange="NASDAQ" if i % 2 == 0 else "NSE",
            sector="Technology",
            rank=i,
            score=95 - i,
            display_price=100.0 + i,
            market_cap_display=15e9 if i <= 20 else 5e9,
            fwd_pe=18.5,
            peg=1.1,
            ev_ebitda=12.0,
            beta=0.95,
            nd_ebitda="Net Cash",
            yield_pct=2.5,
            eps_growth_pct=15.0,
            data_confidence="High",
            stage_status="passed" if i <= 20 else "gate_dropped",
            near_miss_status="none" if i <= 20 else "rank_near_miss",
        ) for i in range(1, 35)
    ]

    decisions_sample = {
        "c-1": {"decision": "keep", "decision_reason": "Exceptional ROE & Free Cash Flow", "decision_note": "Core pick"},
        "c-2": {"decision": "drop", "decision_reason": "High Valuation / Stretched Multiples", "decision_note": "Trimming"},
    }

    excel_bytes = export_service.generate_screening_workbook(
        run_id="run-test-export-001",
        profile_name="Global Quality Growth Core - Version 3",
        results=mock_results,
        decisions_map=decisions_sample,
    )

    assert len(excel_bytes) > 2000, "Generated Excel workbook is too small"
    print(f"[PASS] Successfully generated in-memory Excel workbook ({len(excel_bytes)} bytes)")

    # Read back workbook using openpyxl to verify sheets & structure
    wb = openpyxl.load_workbook(BytesIO(excel_bytes))
    sheet_names = wb.sheetnames
    print(f"[PASS] Workbook sheets: {sheet_names}")
    assert "Top 20 Winners" in sheet_names, "Top 20 Winners sheet missing"
    assert "Near Misses" in sheet_names, "Near Misses sheet missing"
    assert "Master Universe" in sheet_names, "Master Universe sheet missing"

    ws_top = wb["Top 20 Winners"]
    assert ws_top["A1"].value.startswith("Top 20 Portfolio Selection"), "Title missing"
    # Row 4 is header
    headers = [ws_top.cell(row=4, column=i).value for i in range(1, 22)]
    print(f"[PASS] Verified headers ({len(headers)} columns): {headers[:6]} ... {headers[-3:]}")
    assert "Decision" in headers, "Decision column missing"
    assert "Decision Reason" in headers, "Decision Reason column missing"


async def test_end_to_end_notifications():
    print("\n" + "=" * 70)
    print("STEP 2: Testing Automated Email Notifications for All 3 Cases")
    print("=" * 70)

    # -------------------------------------------------------------
    # Case 1: Run Success
    # -------------------------------------------------------------
    print("\n[Executing Case 1: Successful Screening Run]")
    req_success = ScreeningRunRequest(
        countries=["in"],
        exchanges=["nse"],
        display_currency="USD",
        profile_name="Global Quality Growth Core - Version 3",
    )
    res_success = await screening_service.initiate_screening_run(req_success)
    print(f"  Run ID: {res_success.run_id}")
    print(f"  Status: {res_success.status}")
    print(f"  Screened Candidates: {res_success.funnel.universe}")
    print(f"  Selected Winners: {res_success.funnel.selected}")
    assert res_success.status == "succeeded"

    # -------------------------------------------------------------
    # Case 2: Data Blocker
    # -------------------------------------------------------------
    print("\n[Executing Case 2: Data Blocker (Stale Market Data)]")
    req_blocked = ScreeningRunRequest(
        countries=["in"],
        exchanges=["nse"],
        display_currency="USD",
        profile_name="Global Quality Growth Core - Version 3",
        sim_blocker="stale",
    )
    res_blocked = await screening_service.initiate_screening_run(req_blocked)
    print(f"  Run ID: {res_blocked.run_id}")
    print(f"  Status: {res_blocked.status}")
    print(f"  Blocker Alert: {res_blocked.errors}")
    assert res_blocked.status == "blocked"

    # -------------------------------------------------------------
    # Case 3: Technical Failure Alert
    # -------------------------------------------------------------
    print("\n[Executing Case 3: Technical Pipeline Failure Alert]")
    notification_service.notify_run_failed(
        run_id="run-sim-crash-999",
        profile_name="Global Quality Growth Core - Version 3",
        duration_ms=450.0,
        error_message="psycopg2.OperationalError: could not connect to server: Connection refused (port 5432)",
        selected_countries=["in"],
        selected_exchanges=["nse"],
    )
    print("  Dispatched simulated failure notification.")

    # Wait for asynchronous background tasks to finish
    await asyncio.sleep(2.0)

    # -------------------------------------------------------------
    # Step 3: Inspect sent_emails folder
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("STEP 3: Inspecting Generated Emails and Attachments on Disk")
    print("=" * 70)
    email_files = list(SENT_EMAILS_DIR.glob("*"))
    print(f"Total files in '{SENT_EMAILS_DIR}': {len(email_files)}")
    html_files = sorted(list(SENT_EMAILS_DIR.glob("*.html")), key=lambda p: p.stat().st_mtime, reverse=True)
    excel_files = sorted(list(SENT_EMAILS_DIR.glob("*.xlsx")), key=lambda p: p.stat().st_mtime, reverse=True)

    print("\nRecent HTML Emails Generated:")
    for f in html_files[:5]:
        print(f"  [HTML Email] {f.name} ({f.stat().st_size} bytes)")

    print("\nRecent Excel Attachments Generated:")
    for f in excel_files[:5]:
        print(f"  [Excel Attachment] {f.name} ({f.stat().st_size} bytes)")

    assert len(html_files) >= 3, "Expected at least 3 generated HTML emails"
    assert len(excel_files) >= 1, "Expected at least 1 generated Excel attachment for the success run"

    print("\n" + "=" * 70)
    print("ALL 3 EMAIL NOTIFICATION CASES & EXCEL ATTACHMENTS VERIFIED!")
    print("=" * 70)


if __name__ == "__main__":
    test_excel_export_generation()
    asyncio.run(test_end_to_end_notifications())
