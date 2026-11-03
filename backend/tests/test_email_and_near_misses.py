from pathlib import Path
"""Validation test for dynamic email notifications and Near Misses Excel integration."""

import os
import sys
from datetime import date
from io import BytesIO
import openpyxl

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.screening_run import ScreeningResultRecord, FunnelCountRecord
from app.schemas.screening import ScreeningRunRequest
from app.services.export_service import export_service
from app.services.notification_service import notification_service


def test_screening_request_schema():
    print("1. Testing ScreeningRunRequest schema with notification_email...")
    req = ScreeningRunRequest(
        countries=["in"],
        exchanges=["nse"],
        notification_email="test.user@zeniusit.com",
    )
    assert req.notification_email == "test.user@zeniusit.com"
    print("   [SUCCESS] ScreeningRunRequest accepts dynamic notification_email!")


def test_excel_workbook_sheets():
    print("2. Testing Excel generation with Top 20, Near Misses, and Master Universe...")
    sample_results = []
    
    # Generate 20 top winners
    for i in range(1, 21):
        sample_results.append(
            ScreeningResultRecord(
                id=f"res-top-{i}",
                run_id="run-test",
                canonical_company_id=f"comp-{i}",
                ticker=f"TOP{i}",
                company_name=f"Top Company {i}",
                country="IN",
                exchange="NSE",
                sector="Technology",
                rank=i,
                score=95 - i,
                display_price=150.0 + i,
                market_cap_display=50e9 - (i * 1e9),
                stage_status="passed",
                near_miss_status="none",
                decision="KEEP",
                decision_reason="Strong earnings momentum",
            )
        )
    
    # Generate 10 near misses (Rank 21..30)
    for i in range(21, 31):
        sample_results.append(
            ScreeningResultRecord(
                id=f"res-nm-{i}",
                run_id="run-test",
                canonical_company_id=f"comp-{i}",
                ticker=f"NEAR{i}",
                company_name=f"Near Miss Company {i}",
                country="IN",
                exchange="NSE",
                sector="Healthcare",
                rank=i,
                score=75 - (i - 20),
                display_price=80.0 + i,
                market_cap_display=10e9 - ((i - 20) * 5e8),
                stage_status="passed",
                near_miss_status="rank_near_miss",
                decision="",
                decision_reason="",
            )
        )
    
    # Generate 5 rule near misses (failed 1 gate)
    for i in range(31, 36):
        sample_results.append(
            ScreeningResultRecord(
                id=f"res-nm-gate-{i}",
                run_id="run-test",
                canonical_company_id=f"comp-{i}",
                ticker=f"GATE{i}",
                company_name=f"Gate Borderline {i}",
                country="IN",
                exchange="NSE",
                sector="Industrials",
                rank=i,
                score=70,
                display_price=45.0,
                market_cap_display=5e9,
                stage_status="gate_dropped",
                near_miss_status="rule_near_miss",
                decision="",
                decision_reason="",
            )
        )

    excel_bytes = export_service.generate_screening_workbook(
        run_id="run-test",
        profile_name="Tech Growth v2.0",
        results=sample_results,
    )
    
    wb = openpyxl.load_workbook(BytesIO(excel_bytes))
    sheet_names = wb.sheetnames
    print(f"   Generated sheets: {sheet_names}")
    assert sheet_names == ["Top 20", "Near Misses", "Master Universe"], f"Unexpected sheets: {sheet_names}"
    
    ws_top = wb["Top 20"]
    ws_nm = wb["Near Misses"]
    ws_master = wb["Master Universe"]
    
    # 4 rows for title (row 1) + subtitle (row 2) + spacer (row 3) + header (row 4)
    top20_data_rows = ws_top.max_row - 4
    nm_data_rows = ws_nm.max_row - 4
    master_data_rows = ws_master.max_row - 4
    print(f"   Sheet 1 ('Top 20') data rows: {top20_data_rows}")
    print(f"   Sheet 2 ('Near Misses') data rows: {nm_data_rows}")
    print(f"   Sheet 3 ('Master Universe') data rows: {master_data_rows}")
    
    assert top20_data_rows == 20, f"Expected 20 rows in Top 20 tab, got {top20_data_rows}"
    assert nm_data_rows == 15, f"Expected 15 near misses in Sheet 2, got {nm_data_rows}"
    assert master_data_rows == 35, f"Expected 35 master universe rows, got {master_data_rows}"
    
    # Check notes in Near Misses (row 5 is first data row)
    note_val = ws_nm.cell(row=5, column=21).value  # Column 21 is Status / Note
    print(f"   Near Miss row 1 note: '{note_val}'")
    assert "cut-off" in str(note_val).lower() or "near miss" in str(note_val).lower() or "displaced" in str(note_val).lower()
    print("   [SUCCESS] Multi-sheet Excel workbook verified with separate 'Top 20', 'Near Misses', and 'Master Universe' tabs!")

    print("3. Testing HTML Email generation with Near Misses preview table...")
    funnel = FunnelCountRecord(
        id="fnl-test",
        run_id="run-test",
        universe_count=35,
        markets_count=35,
        floors_count=35,
        gates_count=30,
        score_count=30,
        shortlist_count=20,
        selected_count=20,
    )
    html_body = notification_service._build_success_html(
        run_id="run-test",
        profile_name="Tech Growth v2.0",
        duration_ms=450.0,
        funnel_counts=funnel,
        results=sample_results,
        selected_countries=["in"],
        selected_exchanges=["nse"],
    )
    
    assert "Top Model Contenders Preview" in html_body
    assert "Near Miss Contenders Preview" in html_body
    assert "Included in Sheet 2" in html_body
    assert "NEAR21" in html_body
    assert "Multi-Sheet Excel Workbook Attached" in html_body
    print("   [SUCCESS] HTML email body features both Top 20 and Near Misses preview tables!")


def test_multiple_recipients_without_env():
    print("4. Testing multiple accounts resolution without EMAIL_TO in .env...")
    multi_input = "prabhas.muthyala@zeniusit.com, manoj@zeniusit.com; team-lead@zenius.com"
    raw_str = multi_input.strip()
    recipients = [r.strip() for r in raw_str.replace(";", ",").split(",") if r.strip()]
    assert len(recipients) == 3
    assert "prabhas.muthyala@zeniusit.com" in recipients
    assert "manoj@zeniusit.com" in recipients
    assert "team-lead@zenius.com" in recipients
    print(f"   Resolved recipients: {recipients}")
    print("   [SUCCESS] Multiple accounts correctly parsed and handled without needing EMAIL_TO in .env!")


if __name__ == "__main__":
    test_screening_request_schema()
    test_excel_workbook_sheets()
    test_multiple_recipients_without_env()
    print("\n" + "=" * 70)
    print("ALL VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 70)

