"""Phase 10: Metrics Engine - Institutional financial ratio calculation engine.

Calculates all 16 screening metrics from normalized raw financial inputs.
Every calculation records:
  - The formula version used ("v1.0-standard")
  - The exact input values consumed
  - The computed output
  - The reason for any None result (missing data, bank exemption, math trap)

Key design principles:
  1. Pure functions - no database access, no side effects
  2. Never crash on bad data - always return None + reason instead
  3. Bank/financial institutions are automatically exempt from leverage ratios
  4. All ratios are calculated consistently regardless of data source vendor
"""

from dataclasses import dataclass, field
from typing import Dict, Optional

from app.core.logging import DiagnosticLogger

logger = DiagnosticLogger("metrics_engine")

# Formula version tag - bump this when formulas change so historical runs stay reproducible
FORMULA_VERSION = "v1.0-standard"

# Standard S&P 500 forward P/E used as the market benchmark for P/E vs Benchmark metric
SP500_FORWARD_PE_BENCHMARK = 22.5


@dataclass
class MetricResult:
    """Result of a single metric calculation with full audit trail."""
    metric_name: str
    value: Optional[float]
    formula_version: str = FORMULA_VERSION
    inputs_used: Dict[str, Optional[float]] = field(default_factory=dict)
    missing_reason: Optional[str] = None
    is_exempt: bool = False
    exempt_reason: Optional[str] = None


@dataclass
class MetricsCalculationOutput:
    """Complete set of computed derived metrics for one company.

    Produced by MetricsEngine.compute_all() after reading raw vendor financials.
    Written back to company_metrics table by MetricsService.
    """
    canonical_company_id: str
    ticker: str
    formula_version: str = FORMULA_VERSION

    # Derived metrics Phase 10 computes (not directly from vendors)
    avg_daily_traded_value: Optional[float] = None
    pe_vs_benchmark: Optional[float] = None
    peg_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    price_to_sales: Optional[float] = None
    price_to_cash_flow: Optional[float] = None
    net_debt: Optional[float] = None
    net_debt_ebitda: Optional[float] = None
    revenue_growth_fwd: Optional[float] = None
    data_confidence: str = "High"

    # Audit trail - reasons any metric could not be computed
    missing_reasons: Dict[str, str] = field(default_factory=dict)
    # Exempt flags - metrics skipped intentionally (e.g., bank leverage)
    exempt_flags: Dict[str, str] = field(default_factory=dict)


class MetricsEngine:
    """
    Stateless institutional metrics calculation engine.

    All methods are pure functions - they take raw numbers as input
    and return computed ratios. No database calls. No side effects.
    Safe to call with any combination of None values.
    """

    # ------------------------------------------------------------------
    # SIZE & LIQUIDITY
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_avg_traded_value(
        price_usd: Optional[float],
        avg_daily_volume: Optional[float],
        ticker: str = "",
    ) -> MetricResult:
        """
        Avg Daily Traded Value (USD) = Price (USD) x Average Daily Volume

        Vendors do NOT provide this directly. We compute it to measure
        true liquidity in dollar terms, enabling cross-country comparison.
        A fund cannot invest in a stock with < $1M daily traded value
        because buying would crash the price.
        """
        if price_usd is None:
            return MetricResult(
                metric_name="avg_daily_traded_value",
                value=None,
                inputs_used={"price_usd": None, "avg_daily_volume": avg_daily_volume},
                missing_reason="price_usd not available for this security",
            )
        if avg_daily_volume is None:
            return MetricResult(
                metric_name="avg_daily_traded_value",
                value=None,
                inputs_used={"price_usd": price_usd, "avg_daily_volume": None},
                missing_reason="avg_daily_volume not reported by vendor",
            )
        if price_usd <= 0 or avg_daily_volume <= 0:
            return MetricResult(
                metric_name="avg_daily_traded_value",
                value=None,
                inputs_used={"price_usd": price_usd, "avg_daily_volume": avg_daily_volume},
                missing_reason="price_usd or avg_daily_volume is zero/negative",
            )

        value = round(price_usd * avg_daily_volume, 2)
        logger.calc_info(
            "avg_traded_value", ticker,
            f"${price_usd:.4f} x {avg_daily_volume:,.0f} shares = ${value:,.0f}/day"
        )
        return MetricResult(
            metric_name="avg_daily_traded_value",
            value=value,
            inputs_used={"price_usd": price_usd, "avg_daily_volume": avg_daily_volume},
        )

    # ------------------------------------------------------------------
    # VALUATION
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_pe_vs_benchmark(
        forward_pe: Optional[float],
        benchmark: float = SP500_FORWARD_PE_BENCHMARK,
        ticker: str = "",
    ) -> MetricResult:
        """
        Forward P/E vs S&P 500 Benchmark = Forward P/E - 22.5x

        Negative result = stock is cheaper than market average (desirable).
        Positive result = stock is more expensive than market average.
        Benchmark of 22.5x is the standard S&P 500 forward P/E
        tagged in formula version v1.0-standard.

        Vendors never provide this metric. Entirely our own calculation.
        """
        if forward_pe is None:
            return MetricResult(
                metric_name="pe_vs_benchmark",
                value=None,
                inputs_used={"forward_pe": None, "sp500_benchmark": benchmark},
                missing_reason="forward_pe not reported by vendor",
            )
        if forward_pe <= 0:
            return MetricResult(
                metric_name="pe_vs_benchmark",
                value=None,
                inputs_used={"forward_pe": forward_pe, "sp500_benchmark": benchmark},
                missing_reason=f"forward_pe is {forward_pe} (loss-making company)",
            )

        value = round(forward_pe - benchmark, 4)
        logger.calc_info(
            "pe_vs_benchmark", ticker,
            f"{forward_pe:.2f}x - {benchmark}x S&P500 benchmark = {value:+.2f}x spread"
        )
        return MetricResult(
            metric_name="pe_vs_benchmark",
            value=value,
            inputs_used={"forward_pe": forward_pe, "sp500_benchmark": benchmark},
        )

    @staticmethod
    def calculate_peg_ratio(
        forward_pe: Optional[float],
        eps_growth_fwd_pct: Optional[float],
        ticker: str = "",
    ) -> MetricResult:
        """
        PEG Ratio = Forward P/E / EPS Growth Rate (%)

        Adjusts raw P/E for the company's earnings growth speed.
        PEG < 1.0 = attractive. PEG > 2.0 = expensive relative to growth.

        Critical edge case: division by zero if growth is 0% or negative.
        Phase 10 catches this safely and records the reason.
        """
        if forward_pe is None:
            return MetricResult(
                metric_name="peg_ratio",
                value=None,
                inputs_used={"forward_pe": None, "eps_growth_fwd_pct": eps_growth_fwd_pct},
                missing_reason="forward_pe not available",
            )
        if eps_growth_fwd_pct is None:
            return MetricResult(
                metric_name="peg_ratio",
                value=None,
                inputs_used={"forward_pe": forward_pe, "eps_growth_fwd_pct": None},
                missing_reason="eps_growth_fwd_pct not reported by vendor consensus",
            )
        if eps_growth_fwd_pct <= 0:
            return MetricResult(
                metric_name="peg_ratio",
                value=None,
                inputs_used={"forward_pe": forward_pe, "eps_growth_fwd_pct": eps_growth_fwd_pct},
                missing_reason=(
                    f"EPS growth is {eps_growth_fwd_pct}% "
                    f"(zero or negative - division by zero prevented)"
                ),
            )
        if forward_pe <= 0:
            return MetricResult(
                metric_name="peg_ratio",
                value=None,
                inputs_used={"forward_pe": forward_pe, "eps_growth_fwd_pct": eps_growth_fwd_pct},
                missing_reason="forward_pe is zero/negative",
            )

        value = round(forward_pe / eps_growth_fwd_pct, 4)
        logger.calc_info(
            "peg_ratio", ticker,
            f"{forward_pe:.2f}x P/E / {eps_growth_fwd_pct:.1f}% growth = {value:.2f}x PEG"
        )
        return MetricResult(
            metric_name="peg_ratio",
            value=value,
            inputs_used={"forward_pe": forward_pe, "eps_growth_fwd_pct": eps_growth_fwd_pct},
        )

    @staticmethod
    def calculate_ev_ebitda(
        market_cap_usd: Optional[float],
        total_debt: Optional[float],
        cash: Optional[float],
        ebitda: Optional[float],
        ticker: str = "",
    ) -> MetricResult:
        """
        EV/EBITDA = (Market Cap + Total Debt - Cash) / EBITDA

        Enterprise Value (EV) = Real cost to buy the whole company
        including inheriting its debts and receiving its cash.

        EBITDA = Operating profit before tax/interest/depreciation deductions.
        The most cross-country comparable profitability measure.

        Edge cases:
          - Negative/zero EBITDA = ratio is meaningless (stored as None)
          - Missing debt/cash = use 0 as conservative assumption
        """
        if market_cap_usd is None:
            return MetricResult(
                metric_name="ev_ebitda",
                value=None,
                inputs_used={"market_cap_usd": None, "total_debt": total_debt, "cash": cash, "ebitda": ebitda},
                missing_reason="market_cap_usd not available",
            )
        if ebitda is None:
            return MetricResult(
                metric_name="ev_ebitda",
                value=None,
                inputs_used={"market_cap_usd": market_cap_usd, "total_debt": total_debt, "cash": cash, "ebitda": None},
                missing_reason="ebitda not reported by vendor",
            )
        if ebitda <= 0:
            return MetricResult(
                metric_name="ev_ebitda",
                value=None,
                inputs_used={"market_cap_usd": market_cap_usd, "total_debt": total_debt, "cash": cash, "ebitda": ebitda},
                missing_reason=f"EBITDA is {ebitda:,.0f} (negative/zero - ratio undefined)",
            )

        safe_debt = total_debt if total_debt is not None else 0.0
        safe_cash = cash if cash is not None else 0.0
        ev = market_cap_usd + safe_debt - safe_cash
        value = round(ev / ebitda, 4)

        logger.calc_info(
            "ev_ebitda", ticker,
            (
                f"EV=(${market_cap_usd / 1e9:.2f}B mktcap "
                f"+ ${safe_debt / 1e9:.2f}B debt "
                f"- ${safe_cash / 1e9:.2f}B cash) "
                f"= ${ev / 1e9:.2f}B EV "
                f"/ ${ebitda / 1e9:.2f}B EBITDA "
                f"= {value:.2f}x"
            ),
        )
        return MetricResult(
            metric_name="ev_ebitda",
            value=value,
            inputs_used={
                "market_cap_usd": market_cap_usd,
                "total_debt": safe_debt,
                "cash": safe_cash,
                "ebitda": ebitda,
                "ev_computed": round(ev, 2),
            },
        )

    @staticmethod
    def calculate_price_to_sales(
        market_cap_usd: Optional[float],
        revenue: Optional[float],
        ticker: str = "",
    ) -> MetricResult:
        """
        Price/Sales = Market Cap / Total Annual Revenue

        Measures how much investors pay for every $1 of the company's sales.
        Useful for high-growth companies with small or negative profits.
        """
        if market_cap_usd is None:
            return MetricResult(
                metric_name="price_to_sales",
                value=None,
                inputs_used={"market_cap_usd": None, "revenue": revenue},
                missing_reason="market_cap_usd not available",
            )
        if revenue is None:
            return MetricResult(
                metric_name="price_to_sales",
                value=None,
                inputs_used={"market_cap_usd": market_cap_usd, "revenue": None},
                missing_reason="revenue not reported by vendor",
            )
        if revenue <= 0:
            return MetricResult(
                metric_name="price_to_sales",
                value=None,
                inputs_used={"market_cap_usd": market_cap_usd, "revenue": revenue},
                missing_reason=f"Revenue is {revenue:,.0f} (zero/negative - ratio undefined)",
            )

        value = round(market_cap_usd / revenue, 4)
        logger.calc_info(
            "price_to_sales", ticker,
            f"${market_cap_usd / 1e9:.2f}B / ${revenue / 1e9:.2f}B revenue = {value:.2f}x P/S"
        )
        return MetricResult(
            metric_name="price_to_sales",
            value=value,
            inputs_used={"market_cap_usd": market_cap_usd, "revenue": revenue},
        )

    @staticmethod
    def calculate_price_to_cash_flow(
        market_cap_usd: Optional[float],
        free_cash_flow: Optional[float],
        ticker: str = "",
    ) -> MetricResult:
        """
        Price/Cash Flow = Market Cap / Free Cash Flow

        Free Cash Flow = real cash generated after capital expenditures.
        Most reliable profitability measure, harder to manipulate than EPS.
        Commonly missing for smaller/emerging market companies.
        """
        if market_cap_usd is None:
            return MetricResult(
                metric_name="price_to_cash_flow",
                value=None,
                inputs_used={"market_cap_usd": None, "free_cash_flow": free_cash_flow},
                missing_reason="market_cap_usd not available",
            )
        if free_cash_flow is None:
            return MetricResult(
                metric_name="price_to_cash_flow",
                value=None,
                inputs_used={"market_cap_usd": market_cap_usd, "free_cash_flow": None},
                missing_reason="free_cash_flow not reported by vendor for this security",
            )
        if free_cash_flow <= 0:
            return MetricResult(
                metric_name="price_to_cash_flow",
                value=None,
                inputs_used={"market_cap_usd": market_cap_usd, "free_cash_flow": free_cash_flow},
                missing_reason=f"Free cash flow is {free_cash_flow:,.0f} (negative/zero - ratio undefined)",
            )

        value = round(market_cap_usd / free_cash_flow, 4)
        logger.calc_info(
            "price_to_cash_flow", ticker,
            f"${market_cap_usd / 1e9:.2f}B / ${free_cash_flow / 1e9:.2f}B FCF = {value:.2f}x P/CF"
        )
        return MetricResult(
            metric_name="price_to_cash_flow",
            value=value,
            inputs_used={"market_cap_usd": market_cap_usd, "free_cash_flow": free_cash_flow},
        )

    # ------------------------------------------------------------------
    # RISK & LEVERAGE
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_net_debt(
        total_debt: Optional[float],
        cash: Optional[float],
        ticker: str = "",
    ) -> MetricResult:
        """
        Net Debt = Total Debt - Cash

        Negative value = company has MORE cash than debt (excellent health).
        Used as intermediate input for Net Debt/EBITDA.
        """
        safe_debt = total_debt if total_debt is not None else 0.0
        safe_cash = cash if cash is not None else 0.0
        value = round(safe_debt - safe_cash, 2)

        logger.calc_info(
            "net_debt", ticker,
            f"${safe_debt / 1e9:.2f}B debt - ${safe_cash / 1e9:.2f}B cash = ${value / 1e9:.2f}B net debt"
        )
        return MetricResult(
            metric_name="net_debt",
            value=value,
            inputs_used={"total_debt": safe_debt, "cash": safe_cash},
        )

    @staticmethod
    def calculate_net_debt_ebitda(
        net_debt: Optional[float],
        ebitda: Optional[float],
        is_bank: bool = False,
        ticker: str = "",
    ) -> MetricResult:
        """
        Net Debt/EBITDA = Net Debt / EBITDA

        Answers: 'How many years of profit to pay off all debt?'
        Lower is better. Above 3x is risky for most sectors.

        BANK EXEMPTION: Banks borrow customer deposits as their core business.
        Their 'debt' is always hundreds of billions, making this ratio
        meaninglessly high (30x+) and unfairly disqualifying them.
        Phase 10 marks is_bank=True companies as Exempt automatically.
        """
        if is_bank:
            logger.calc_info(
                "net_debt_ebitda", ticker,
                "EXEMPT: Financial institution - leverage ratio not applicable"
            )
            return MetricResult(
                metric_name="net_debt_ebitda",
                value=None,
                inputs_used={"net_debt": net_debt, "ebitda": ebitda, "is_bank": True},
                is_exempt=True,
                exempt_reason=(
                    "Financial institution - Net Debt/EBITDA not applicable. "
                    "Customer deposits are structural liabilities, not financial risk."
                ),
            )

        if net_debt is None:
            return MetricResult(
                metric_name="net_debt_ebitda",
                value=None,
                inputs_used={"net_debt": None, "ebitda": ebitda},
                missing_reason="net_debt not computable (total_debt and/or cash missing from vendor)",
            )
        if ebitda is None:
            return MetricResult(
                metric_name="net_debt_ebitda",
                value=None,
                inputs_used={"net_debt": net_debt, "ebitda": None},
                missing_reason="ebitda not reported by vendor",
            )
        if ebitda <= 0:
            return MetricResult(
                metric_name="net_debt_ebitda",
                value=None,
                inputs_used={"net_debt": net_debt, "ebitda": ebitda},
                missing_reason=f"EBITDA is {ebitda:,.0f} (negative/zero - ratio undefined)",
            )

        value = round(net_debt / ebitda, 4)
        logger.calc_info(
            "net_debt_ebitda", ticker,
            f"${net_debt / 1e9:.2f}B net debt / ${ebitda / 1e9:.2f}B EBITDA = {value:.2f}x"
        )
        return MetricResult(
            metric_name="net_debt_ebitda",
            value=value,
            inputs_used={"net_debt": net_debt, "ebitda": ebitda},
        )

    # ------------------------------------------------------------------
    # DATA QUALITY
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_data_confidence(
        market_cap_usd: Optional[float],
        price_usd: Optional[float],
        forward_pe: Optional[float],
        ebitda: Optional[float],
        revenue: Optional[float],
        total_debt: Optional[float],
        cash: Optional[float],
        beta: Optional[float],
        eps_growth_fwd: Optional[float],
        dividend_yield: Optional[float],
        ticker: str = "",
    ) -> str:
        """
        Data Confidence = High / Medium / Low based on 10 key field completeness.

          High   = all 10 key fields present (full institutional quality)
          Medium = 7-9 present (some estimates missing, usable)
          Low    = fewer than 7 present (sparse data, analyst review recommended)

        Vendors never provide this. Phase 10 computes it from field presence.
        """
        key_fields = {
            "market_cap_usd": market_cap_usd,
            "price_usd": price_usd,
            "forward_pe": forward_pe,
            "ebitda": ebitda,
            "revenue": revenue,
            "total_debt": total_debt,
            "cash": cash,
            "beta": beta,
            "eps_growth_fwd": eps_growth_fwd,
            "dividend_yield": dividend_yield,
        }
        present_count = sum(1 for v in key_fields.values() if v is not None)
        missing = [k for k, v in key_fields.items() if v is None]

        if present_count >= 10:
            confidence = "High"
        elif present_count >= 7:
            confidence = "Medium"
        else:
            confidence = "Low"

        logger.calc_info(
            "data_confidence", ticker,
            f"{present_count}/10 fields present -> {confidence}"
            + (f" | missing: {', '.join(missing)}" if missing else ""),
        )
        return confidence

    # ------------------------------------------------------------------
    # MASTER COMPUTE METHOD
    # ------------------------------------------------------------------

    @classmethod
    def compute_all(
        cls,
        canonical_company_id: str,
        ticker: str,
        market_cap_usd: Optional[float],
        price_usd: Optional[float],
        avg_daily_volume: Optional[float],
        forward_pe: Optional[float],
        revenue: Optional[float],
        ebitda: Optional[float],
        total_debt: Optional[float],
        cash: Optional[float],
        net_debt: Optional[float],
        free_cash_flow: Optional[float],
        eps_growth_fwd_pct: Optional[float],
        revenue_growth_fwd_pct: Optional[float],
        dividend_yield: Optional[float],
        beta: Optional[float],
        is_bank: bool = False,
    ) -> "MetricsCalculationOutput":
        """
        Master method - computes all derived metrics for one company in one call.

        Runs every formula in sequence. Collects missing reasons and exempt flags.
        Returns MetricsCalculationOutput written back to company_metrics by MetricsService.
        Called once per company during Phase 10 batch run.
        """
        output = MetricsCalculationOutput(
            canonical_company_id=canonical_company_id,
            ticker=ticker,
            formula_version=FORMULA_VERSION,
        )

        logger.info(
            f"[METRICS:START:{ticker}] Computing all metrics "
            f"(formula={FORMULA_VERSION}, is_bank={is_bank})"
        )

        # 1. Avg Daily Traded Value
        r = cls.calculate_avg_traded_value(price_usd, avg_daily_volume, ticker)
        output.avg_daily_traded_value = r.value
        if r.missing_reason:
            output.missing_reasons["avg_daily_traded_value"] = r.missing_reason

        # 2. P/E vs S&P 500 Benchmark
        r = cls.calculate_pe_vs_benchmark(forward_pe, SP500_FORWARD_PE_BENCHMARK, ticker)
        output.pe_vs_benchmark = r.value
        if r.missing_reason:
            output.missing_reasons["pe_vs_benchmark"] = r.missing_reason

        # 3. PEG Ratio
        r = cls.calculate_peg_ratio(forward_pe, eps_growth_fwd_pct, ticker)
        output.peg_ratio = r.value
        if r.missing_reason:
            output.missing_reasons["peg_ratio"] = r.missing_reason

        # 4. EV / EBITDA
        r = cls.calculate_ev_ebitda(market_cap_usd, total_debt, cash, ebitda, ticker)
        output.ev_ebitda = r.value
        if r.missing_reason:
            output.missing_reasons["ev_ebitda"] = r.missing_reason

        # 5. Price / Sales
        r = cls.calculate_price_to_sales(market_cap_usd, revenue, ticker)
        output.price_to_sales = r.value
        if r.missing_reason:
            output.missing_reasons["price_to_sales"] = r.missing_reason

        # 6. Price / Cash Flow
        r = cls.calculate_price_to_cash_flow(market_cap_usd, free_cash_flow, ticker)
        output.price_to_cash_flow = r.value
        if r.missing_reason:
            output.missing_reasons["price_to_cash_flow"] = r.missing_reason

        # 7. Net Debt (recalculate from raw components for accuracy)
        if total_debt is not None or cash is not None:
            r = cls.calculate_net_debt(total_debt, cash, ticker)
            output.net_debt = r.value
        else:
            output.net_debt = net_debt
            if net_debt is None:
                output.missing_reasons["net_debt"] = (
                    "total_debt and cash not reported by vendor"
                )

        # 8. Net Debt / EBITDA (with bank exemption)
        r = cls.calculate_net_debt_ebitda(output.net_debt, ebitda, is_bank, ticker)
        output.net_debt_ebitda = r.value
        if r.is_exempt:
            output.exempt_flags["net_debt_ebitda"] = r.exempt_reason
        elif r.missing_reason:
            output.missing_reasons["net_debt_ebitda"] = r.missing_reason

        # 9. Revenue Growth Forward (pass-through from estimates)
        output.revenue_growth_fwd = revenue_growth_fwd_pct
        if revenue_growth_fwd_pct is None:
            output.missing_reasons["revenue_growth_fwd"] = (
                "revenue_growth_fwd_pct not reported by vendor consensus"
            )

        # 10. Data Confidence
        output.data_confidence = cls.calculate_data_confidence(
            market_cap_usd=market_cap_usd,
            price_usd=price_usd,
            forward_pe=forward_pe,
            ebitda=ebitda,
            revenue=revenue,
            total_debt=total_debt,
            cash=cash,
            beta=beta,
            eps_growth_fwd=eps_growth_fwd_pct,
            dividend_yield=dividend_yield,
            ticker=ticker,
        )

        logger.info(
            f"[METRICS:DONE:{ticker}] "
            f"ev_ebitda={output.ev_ebitda}, "
            f"pe_vs_bm={output.pe_vs_benchmark}, "
            f"peg={output.peg_ratio}, "
            f"nd_ebitda={output.net_debt_ebitda}, "
            f"p_sales={output.price_to_sales}, "
            f"confidence={output.data_confidence} | "
            f"missing={len(output.missing_reasons)} metrics, "
            f"exempt={len(output.exempt_flags)} metrics"
        )

        return output
