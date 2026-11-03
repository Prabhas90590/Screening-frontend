"""Phase 10 Verification Script — Metrics Engine.

Tests all metric calculation formulas in isolation (pure unit tests)
then runs the batch metrics service against the DB populated by Phase 9.

Test cases covered:
  1. Normal company   — all 10 metrics compute correctly
  2. Bank exemption   — Net Debt/EBITDA skipped, not None due to missing data
  3. Negative EBITDA  — EV/EBITDA and Net Debt/EBITDA return None with reasons
  4. Zero EPS growth  — PEG safely returns None (division-by-zero guard)
  5. Missing data     — Data confidence degrades to Medium/Low appropriately
  6. Database batch   — MetricsService processes real DB records from Phase 9
"""

import sys
import os

# Allow running from repo root or backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.logging import configure_logging
configure_logging(debug=False)

from app.metrics.metrics_engine import MetricsEngine, FORMULA_VERSION
from app.services.metrics_service import metrics_service

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
INFO = "\033[94m[INFO]\033[0m"

failures = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"{PASS} {label}" + (f" — {detail}" if detail else ""))
    else:
        print(f"{FAIL} {label}" + (f" — {detail}" if detail else ""))
        failures.append(label)


# ──────────────────────────────────────────────────────────────────────────────
# TEST SUITE 1: Normal Company (Infosys-like)
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("TEST 1: Normal company — all metrics compute")
print("=" * 65)

out = MetricsEngine.compute_all(
    canonical_company_id="comp-test-infy",
    ticker="INFY",
    market_cap_usd=91_000_000_000,    # $91B
    price_usd=21.84,
    avg_daily_volume=3_500_000,
    forward_pe=21.5,
    revenue=18_200_000_000,
    ebitda=4_460_000_000,
    total_debt=2_100_000_000,
    cash=4_800_000_000,
    net_debt=-2_700_000_000,          # net cash position
    free_cash_flow=2_900_000_000,
    eps_growth_fwd_pct=9.6,
    revenue_growth_fwd_pct=8.8,
    dividend_yield=2.1,
    beta=0.82,
    is_bank=False,
)

check("Formula version tagged", out.formula_version == FORMULA_VERSION, out.formula_version)
check("Avg traded value computed", out.avg_daily_traded_value is not None,
      f"${out.avg_daily_traded_value:,.0f}/day" if out.avg_daily_traded_value else "None")
check("Avg traded value correct", out.avg_daily_traded_value == round(21.84 * 3_500_000, 2),
      f"expected ${21.84 * 3_500_000:,.0f}")
check("P/E vs benchmark computed", out.pe_vs_benchmark is not None, str(out.pe_vs_benchmark))
check("P/E vs benchmark correct", abs(out.pe_vs_benchmark - (21.5 - 22.5)) < 0.001,
      f"21.5 - 22.5 = -1.0, got {out.pe_vs_benchmark}")
check("PEG ratio computed", out.peg_ratio is not None, str(out.peg_ratio))
check("PEG ratio correct", abs(out.peg_ratio - round(21.5 / 9.6, 4)) < 0.001,
      f"21.5/9.6 = {round(21.5/9.6, 4)}, got {out.peg_ratio}")
check("EV/EBITDA computed", out.ev_ebitda is not None, str(out.ev_ebitda))
expected_ev = 91e9 + 2.1e9 - 4.8e9
expected_ev_ebitda = round(expected_ev / 4.46e9, 4)
check("EV/EBITDA correct", abs(out.ev_ebitda - expected_ev_ebitda) < 0.01,
      f"expected {expected_ev_ebitda:.2f}x, got {out.ev_ebitda}")
check("Price/Sales computed", out.price_to_sales is not None, f"{out.price_to_sales:.2f}x")
check("Price/Cash Flow computed", out.price_to_cash_flow is not None, f"{out.price_to_cash_flow:.2f}x")
check("Net debt recalculated", out.net_debt == round(2.1e9 - 4.8e9, 2),
      f"expected ${-2.7e9:,.0f}, got ${out.net_debt:,.0f}" if out.net_debt else "None")
check("Net Debt/EBITDA computed", out.net_debt_ebitda is not None, str(out.net_debt_ebitda))
check("Net Debt/EBITDA is negative", out.net_debt_ebitda < 0,
      f"{out.net_debt_ebitda:.2f}x (net cash company)")
check("Revenue growth stored", out.revenue_growth_fwd == 8.8, str(out.revenue_growth_fwd))
check("Data confidence = High", out.data_confidence == "High", out.data_confidence)
check("No missing reasons for normal co", len(out.missing_reasons) == 0,
      str(out.missing_reasons) if out.missing_reasons else "none")

# ──────────────────────────────────────────────────────────────────────────────
# TEST SUITE 2: Bank Exemption (HDFC Bank-like)
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("TEST 2: Bank company — Net Debt/EBITDA exempt")
print("=" * 65)

bank_out = MetricsEngine.compute_all(
    canonical_company_id="comp-test-hdfc",
    ticker="HDFCBANK",
    market_cap_usd=150_000_000_000,
    price_usd=68.5,
    avg_daily_volume=8_000_000,
    forward_pe=18.2,
    revenue=25_000_000_000,
    ebitda=12_000_000_000,
    total_debt=180_000_000_000,   # Banks have huge debt (deposits)
    cash=15_000_000_000,
    net_debt=165_000_000_000,
    free_cash_flow=None,
    eps_growth_fwd_pct=12.0,
    revenue_growth_fwd_pct=10.5,
    dividend_yield=1.2,
    beta=0.95,
    is_bank=True,  # <-- THIS IS THE KEY FLAG
)

check("Bank: Net Debt/EBITDA is None", bank_out.net_debt_ebitda is None,
      "correctly exempted from leverage ratio")
check("Bank: Exempt flag recorded", "net_debt_ebitda" in bank_out.exempt_flags,
      bank_out.exempt_flags.get("net_debt_ebitda", "missing"))
check("Bank: EV/EBITDA still computes", bank_out.ev_ebitda is not None,
      f"{bank_out.ev_ebitda:.2f}x (EV/EBITDA not exempt)")
check("Bank: P/E vs benchmark computes", bank_out.pe_vs_benchmark is not None,
      f"{bank_out.pe_vs_benchmark:+.2f}x")
check("Bank: Data confidence = High", bank_out.data_confidence == "High", bank_out.data_confidence)

# ──────────────────────────────────────────────────────────────────────────────
# TEST SUITE 3: Negative EBITDA (Loss-making startup)
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("TEST 3: Negative EBITDA — ratios safely return None")
print("=" * 65)

loss_out = MetricsEngine.compute_all(
    canonical_company_id="comp-test-loss",
    ticker="STARTUP",
    market_cap_usd=5_000_000_000,
    price_usd=12.0,
    avg_daily_volume=500_000,
    forward_pe=None,              # No P/E for loss-making company
    revenue=500_000_000,
    ebitda=-200_000_000,          # NEGATIVE EBITDA
    total_debt=800_000_000,
    cash=300_000_000,
    net_debt=500_000_000,
    free_cash_flow=-150_000_000,  # Burning cash
    eps_growth_fwd_pct=None,
    revenue_growth_fwd_pct=45.0,
    dividend_yield=None,
    beta=1.8,
    is_bank=False,
)

check("Neg EBITDA: EV/EBITDA is None", loss_out.ev_ebitda is None,
      "correctly handles negative EBITDA")
check("Neg EBITDA: EV/EBITDA has reason", "ev_ebitda" in loss_out.missing_reasons,
      loss_out.missing_reasons.get("ev_ebitda", "missing"))
check("Neg EBITDA: Net Debt/EBITDA is None", loss_out.net_debt_ebitda is None,
      "correctly handles negative EBITDA for leverage")
check("Neg EBITDA: P/CF is None (neg FCF)", loss_out.price_to_cash_flow is None,
      "negative free cash flow handled")
check("Neg EBITDA: Price/Sales still works", loss_out.price_to_sales is not None,
      f"{loss_out.price_to_sales:.2f}x (P/S doesn't need EBITDA)")
check("Neg EBITDA: data_confidence = Medium", loss_out.data_confidence == "Medium",
      f"{loss_out.data_confidence} (7/10 fields present)")

# ──────────────────────────────────────────────────────────────────────────────
# TEST SUITE 4: Zero EPS Growth (PEG division-by-zero guard)
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("TEST 4: Zero EPS growth — PEG division-by-zero guard")
print("=" * 65)

zero_growth_out = MetricsEngine.compute_all(
    canonical_company_id="comp-test-zero",
    ticker="FLATCO",
    market_cap_usd=20_000_000_000,
    price_usd=45.0,
    avg_daily_volume=1_000_000,
    forward_pe=18.0,
    revenue=8_000_000_000,
    ebitda=2_000_000_000,
    total_debt=1_000_000_000,
    cash=500_000_000,
    net_debt=500_000_000,
    free_cash_flow=1_200_000_000,
    eps_growth_fwd_pct=0.0,         # ZERO growth -> PEG = P/E / 0 = undefined
    revenue_growth_fwd_pct=2.0,
    dividend_yield=3.5,
    beta=0.75,
    is_bank=False,
)

check("Zero growth: PEG is None", zero_growth_out.peg_ratio is None,
      "division by zero correctly prevented")
check("Zero growth: PEG missing reason", "peg_ratio" in zero_growth_out.missing_reasons,
      zero_growth_out.missing_reasons.get("peg_ratio", "missing"))
check("Zero growth: EV/EBITDA still works", zero_growth_out.ev_ebitda is not None,
      f"{zero_growth_out.ev_ebitda:.2f}x")
check("Zero growth: P/CF works", zero_growth_out.price_to_cash_flow is not None,
      f"{zero_growth_out.price_to_cash_flow:.2f}x")

# ──────────────────────────────────────────────────────────────────────────────
# TEST SUITE 5: Sparse data — Data Confidence degrades
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("TEST 5: Sparse vendor data — Data Confidence degrades")
print("=" * 65)

sparse_out = MetricsEngine.compute_all(
    canonical_company_id="comp-test-sparse",
    ticker="SMALLCAP",
    market_cap_usd=200_000_000,
    price_usd=3.5,
    avg_daily_volume=50_000,
    forward_pe=None,      # No analyst coverage
    revenue=None,         # No revenue reported
    ebitda=None,          # No EBITDA
    total_debt=None,
    cash=None,
    net_debt=None,
    free_cash_flow=None,
    eps_growth_fwd_pct=None,
    revenue_growth_fwd_pct=None,
    dividend_yield=None,
    beta=None,
    is_bank=False,
)

check("Sparse: Data confidence = Low", sparse_out.data_confidence == "Low",
      f"{sparse_out.data_confidence} (too many fields missing)")
check("Sparse: Avg traded value computable", sparse_out.avg_daily_traded_value is not None,
      f"${sparse_out.avg_daily_traded_value:,.0f}/day (only needs price + volume)")
check("Sparse: EV/EBITDA is None", sparse_out.ev_ebitda is None, "correctly None")
check("Sparse: multiple missing reasons", len(sparse_out.missing_reasons) >= 5,
      f"{len(sparse_out.missing_reasons)} reasons recorded")

# ──────────────────────────────────────────────────────────────────────────────
# TEST SUITE 6: Database Batch — MetricsService on real Phase 9 data
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("TEST 6: Database batch — MetricsService on Phase 9 DB records")
print("=" * 65)

try:
    batch_result = metrics_service.run_batch_metrics(limit=500)
    print(f"{INFO} Companies processed : {batch_result.total_companies}")
    print(f"{INFO} Succeeded            : {batch_result.succeeded}")
    print(f"{INFO} Failed               : {batch_result.failed}")
    print(f"{INFO} Banks exempted       : {batch_result.banks_exempted}")
    print(f"{INFO} Duration             : {batch_result.duration_ms:.1f}ms")

    if batch_result.missing_summary:
        print(f"{INFO} Top missing metrics  :")
        for metric, count in sorted(batch_result.missing_summary.items(), key=lambda x: -x[1])[:5]:
            print(f"      {metric}: {count} companies missing this")

    check("DB batch: some companies processed", batch_result.total_companies > 0,
          f"{batch_result.total_companies} companies found in DB")
    check("DB batch: no failures", batch_result.failed == 0,
          f"{batch_result.failed} failures")
    check("DB batch: completed successfully", batch_result.succeeded == batch_result.total_companies,
          f"{batch_result.succeeded}/{batch_result.total_companies} succeeded")

except Exception as e:
    print(f"{FAIL} DB batch failed: {e}")
    failures.append("DB batch run")
    import traceback
    traceback.print_exc()

# ──────────────────────────────────────────────────────────────────────────────
# FINAL REPORT
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
if failures:
    print(f"\033[91m[FAIL] {len(failures)} test(s) failed:\033[0m")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print(f"\033[92m[PASS] All Phase 10 Metrics Engine tests passed!\033[0m")
    print(f"       Formula version: {FORMULA_VERSION}")
    print(f"       Bank exemption: working")
    print(f"       Division-by-zero guards: working")
    print(f"       Missing data degradation: working")
    print(f"       DB batch calculation: working")
    sys.exit(0)

