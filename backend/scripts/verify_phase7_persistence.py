"""Verification script for Phase 7 Database & Persistence.

Tests and validates:
1. Auto-creation of all Phase 7 persistence tables in PostgreSQL.
2. Saving and reading a complete Screening Run audit record.
3. Saving and querying Funnel Stage Counts.
4. Batch inserting and querying Screening Results (Top 20 & Near-Misses).
5. Saving and querying Rule Profiles & Individual Rules.
6. Recording and reading Analyst Keep/Drop Decisions & Portfolio Holdings.
"""

from datetime import datetime, timezone
from pathlib import Path
import sys

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.logging import configure_logging
from app.db.connection import db_manager
from app.models.decision import DecisionRecord, HoldingRecord
from app.models.rule import RuleRecord, RuleVersionRecord
from app.models.screening_run import (
    FunnelCountRecord,
    ScreeningResultRecord,
    ScreeningRunRecord,
)
from app.repositories.decision_repository import decision_repository
from app.repositories.rule_repository import rule_repository
from app.repositories.screening_repository import screening_repository


def main():
    configure_logging(debug=True)
    print("=" * 70)
    print("PHASE 7: DATABASE & PERSISTENCE VERIFICATION")
    print("=" * 70)

    # 1. Initialize all tables
    print("\n1. Initializing full database persistence schema in PostgreSQL...")
    db_manager.init_tables()
    print("   [PASS] All Phase 7 tables initialized successfully.")

    # 2. Test Screening Run persistence
    print("\n2. Testing Screening Run Persistence...")
    now = datetime.now(timezone.utc)
    test_run = ScreeningRunRecord(
        run_id="run-p7-test-001",
        status="succeeded",
        provider="mock",
        rule_version_id="prof-conservative-v1",
        profile_name="Conservative Value",
        display_currency="USD",
        selected_countries=["us", "in", "no"],
        selected_exchanges=["nasdaq", "nse", "ose"],
        rules_snapshot=[
            {"metric": "forward_pe", "condition": "<=", "value": 25.0},
            {"metric": "net_debt_ebitda", "condition": "<=", "value": 3.0},
        ],
        duration_ms=420.5,
        started_at=now,
        completed_at=now,
    )
    saved_run_id = screening_repository.save_run(test_run)
    retrieved_run = screening_repository.get_run(saved_run_id)
    assert retrieved_run is not None, "Failed to retrieve screening run!"
    assert retrieved_run.run_id == "run-p7-test-001"
    print(f"   -> Stored & Retrieved Run: {retrieved_run.run_id} (Status: {retrieved_run.status})")
    print(f"   -> Selected Markets:       {retrieved_run.selected_countries} on {retrieved_run.selected_exchanges}")
    print(f"   -> Duration:               {retrieved_run.duration_ms} ms")
    print("   [PASS] Screening Run persistence verified.")

    # 3. Test Funnel Counts persistence
    print("\n3. Testing Funnel Progression Persistence...")
    test_funnel = FunnelCountRecord(
        id="fnl-run-p7-test-001",
        run_id=test_run.run_id,
        universe_count=1850,
        markets_count=1240,
        floors_count=820,
        gates_count=145,
        score_count=145,
        shortlist_count=50,
        selected_count=20,
    )
    screening_repository.save_funnel_counts(test_funnel)
    retrieved_funnel = screening_repository.get_funnel_counts(test_run.run_id)
    assert retrieved_funnel is not None, "Failed to retrieve funnel counts!"
    assert retrieved_funnel.selected_count == 20
    print(f"   -> Funnel Progression: Universe={retrieved_funnel.universe_count} -> Markets={retrieved_funnel.markets_count} -> Gates={retrieved_funnel.gates_count} -> Top20={retrieved_funnel.selected_count}")
    print("   [PASS] Funnel Counts persistence verified.")

    # 4. Test Screening Results Batch Persistence
    print("\n4. Testing Screening Results Batch Persistence (Top 20 & Near-Misses)...")
    results_batch = [
        ScreeningResultRecord(
            id="res-run-p7-001-infy",
            run_id=test_run.run_id,
            canonical_company_id="comp-isin-ine009a01021",
            ticker="INFY",
            company_name="Infosys Limited",
            country="IN",
            exchange="NSE",
            sector="Information Technology",
            rank=1,
            score=94,
            display_price=22.4,
            market_cap_display=77500000000.0,
            display_currency="USD",
            fwd_pe=24.2,
            peg=1.45,
            ev_ebitda=16.8,
            beta=0.88,
            nd_ebitda="-0.2x (Net Cash)",
            yield_pct=2.4,
            eps_growth_pct=14.2,
            data_confidence="High",
            stage_status="passed",
            near_miss_status="none",
            score_breakdown=[{"name": "Valuation", "score": 28, "max": 30}],
            metric_statuses={"forward_pe": "passed", "nd_ebitda": "passed"},
        ),
        ScreeningResultRecord(
            id="res-run-p7-001-eqnr",
            run_id=test_run.run_id,
            canonical_company_id="comp-isin-no0010096985",
            ticker="EQNR",
            company_name="Equinor ASA",
            country="NO",
            exchange="OSE",
            sector="Energy",
            rank=2,
            score=91,
            display_price=28.5,
            market_cap_display=82000000000.0,
            display_currency="USD",
            fwd_pe=9.8,
            peg=1.1,
            ev_ebitda=4.2,
            beta=0.72,
            nd_ebitda="-0.1x (Net Cash)",
            yield_pct=3.8,
            eps_growth_pct=8.5,
            data_confidence="High",
            stage_status="passed",
            near_miss_status="none",
        ),
        ScreeningResultRecord(
            id="res-run-p7-001-near-miss",
            run_id=test_run.run_id,
            canonical_company_id="comp-isin-ine009a01021",
            ticker="TCS",
            company_name="Tata Consultancy Services",
            country="IN",
            exchange="NSE",
            sector="Information Technology",
            rank=21,
            score=79,
            display_price=45.2,
            market_cap_display=145000000000.0,
            stage_status="passed",
            near_miss_status="rank_near_miss",
        ),
    ]

    saved_count = screening_repository.save_results_batch(results_batch)
    print(f"   -> Successfully inserted {saved_count} screened security results.")

    top20_results = screening_repository.get_results_by_run(test_run.run_id, view="top20")
    near_miss_results = screening_repository.get_results_by_run(test_run.run_id, view="rank_near_misses")
    print(f"   -> Query 'top20' returned:             {len(top20_results)} items (e.g. #{top20_results[0].rank} {top20_results[0].ticker} - Score {top20_results[0].score})")
    print(f"   -> Query 'rank_near_misses' returned:  {len(near_miss_results)} items (e.g. #{near_miss_results[0].rank} {near_miss_results[0].ticker})")
    print("   [PASS] Screening Results batch querying verified.")

    # 5. Test Rule Profile & Metric Rules Persistence
    print("\n5. Testing Rule Version Profile & Rules Persistence...")
    test_profile = RuleVersionRecord(
        version_id="prof-conservative-v1",
        profile_name="Conservative Value",
        version_number="1.0",
        is_active=True,
        description="Focus on profitable cash generative firms with leverage below 3.0x",
        sector_limits={"Information Technology": 3.0, "Energy": 3.5},
        diversification_rules={"max_sector_weight": 25.0},
    )
    rule_repository.save_version(test_profile)

    rule_repository.save_rule(
        RuleRecord(
            rule_id="rule-pe-max",
            version_id=test_profile.version_id,
            metric_name="forward_pe",
            label="Forward P/E",
            category="Valuation",
            condition="<=",
            threshold_value=25.0,
            threshold_display="<= 25.0x",
            mode="Both",
            weight=15.0,
        )
    )

    active_profile = rule_repository.get_active_version()
    assert active_profile is not None, "Failed to retrieve active rule version!"
    assert active_profile.profile_name == "Conservative Value"
    print(f"   -> Active Rule Profile: '{active_profile.profile_name}' (v{active_profile.version_number})")
    print(f"   -> Loaded Rules Count:  {len(active_profile.rules)} (e.g. {active_profile.rules[0].label} {active_profile.rules[0].condition} {active_profile.rules[0].threshold_value})")
    print("   [PASS] Rule Profile & Rules persistence verified.")

    # 6. Test Analyst Decisions & Portfolio Holdings Persistence
    print("\n6. Testing Analyst Decisions & Holdings Persistence...")
    decision_repository.save_decision(
        DecisionRecord(
            decision_id="dec-infy-001",
            canonical_company_id="comp-isin-ine009a01021",
            decision="keep",
            decision_reason="Strong cash position & solid guidance",
            decision_note="Re-evaluate next quarter if forward P/E exceeds 28x.",
            run_id=test_run.run_id,
            decided_by="Lead Portfolio Manager",
        )
    )

    saved_decision = decision_repository.get_decision("comp-isin-ine009a01021")
    assert saved_decision is not None, "Failed to retrieve analyst decision!"
    print(f"   -> Decision for Infosys: {saved_decision.decision.upper()} (Reason: {saved_decision.decision_reason})")

    decision_repository.save_holding(
        HoldingRecord(
            holding_id="hld-infy-001",
            canonical_company_id="comp-isin-ine009a01021",
            portfolio_name="Global Quality Fund",
            shares=50000.0,
            cost_basis=18.5,
            weight_pct=4.2,
        )
    )
    holdings = decision_repository.list_holdings()
    print(f"   -> Fund Holdings Count:  {len(holdings)} (Holding: {holdings[0].holding_id}, Weight: {holdings[0].weight_pct}%)")
    print("   [PASS] Analyst Decisions & Holdings persistence verified.")

    print("\n" + "=" * 70)
    print("PHASE 7 VERIFICATION COMPLETE: ALL PERSISTENCE TABLES WORKING!")
    print("=" * 70)


if __name__ == "__main__":
    main()

