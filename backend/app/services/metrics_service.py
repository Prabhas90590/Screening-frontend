"""Phase 10: Metrics Service - Orchestrates batch metric calculation for all companies.

Reads raw financial data from company_metrics table (populated by Phase 9 ingestion),
runs MetricsEngine for each company, and writes back the computed derived ratios.

This service is the bridge between:
  - Phase 9 (Data Ingestion)  -> raw vendor financials stored in company_metrics
  - Phase 10 (Metrics Engine) -> derived institutional ratios computed and stored
  - Phase 11 (Rule Engine)    -> reads company_metrics with full ratios for screening
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from app.core.logging import DiagnosticLogger
from app.metrics.metrics_engine import MetricsCalculationOutput, MetricsEngine
from app.repositories.company_metrics_repository import company_metrics_repository
from app.repositories.company_repository import company_repository

logger = DiagnosticLogger("metrics_service")


@dataclass
class MetricsBatchResult:
    """Summary of a complete Phase 10 batch metrics calculation run."""
    total_companies: int = 0
    succeeded: int = 0
    failed: int = 0
    banks_exempted: int = 0
    duration_ms: float = 0.0
    missing_summary: Dict[str, int] = field(default_factory=dict)


class MetricsService:
    """
    Orchestration service that runs Phase 10 metrics calculation for all companies.

    Flow:
      1. Load all company_metrics records from PostgreSQL (raw financials from Phase 9)
      2. For each company, look up the companies table to get is_bank flag
      3. Call MetricsEngine.compute_all() with the raw inputs
      4. Write the computed derived ratios back to company_metrics
    """

    def run_batch_metrics(self, limit: int = 500) -> MetricsBatchResult:
        """
        Run metrics engine for all companies in company_metrics table.

        Called:
          - Automatically after ingestion by IngestionService
          - Manually via verify script or admin endpoint
          - Will be called by Run Manager (Phase 13) before each screening run

        Args:
            limit: Max companies to process in one batch (default 500)

        Returns:
            MetricsBatchResult summary with counts and timing
        """
        result = MetricsBatchResult()
        start_time = time.perf_counter()

        logger.info(f"[METRICS:BATCH:START] Loading up to {limit} company_metrics records")

        # Step 1: Load all raw company_metrics records from DB
        all_metrics = company_metrics_repository.list_metrics(limit=limit)
        result.total_companies = len(all_metrics)

        if not all_metrics:
            logger.warning("[METRICS:BATCH] No company_metrics records found — run ingestion first (Phase 9)")
            return result

        logger.info(f"[METRICS:BATCH] Processing {result.total_companies} companies")

        for raw in all_metrics:
            ticker = raw.ticker or raw.canonical_company_id
            try:
                # Step 2: Lookup company record for is_bank flag
                company = company_repository.get_company_by_id(raw.canonical_company_id)
                is_bank = company.is_bank if company else False

                if is_bank:
                    result.banks_exempted += 1

                # Step 3: Run MetricsEngine for this company
                computed: MetricsCalculationOutput = MetricsEngine.compute_all(
                    canonical_company_id=raw.canonical_company_id,
                    ticker=ticker,
                    market_cap_usd=raw.market_cap_usd,
                    price_usd=raw.price_usd,
                    avg_daily_volume=raw.avg_daily_volume,
                    forward_pe=raw.forward_pe,
                    revenue=raw.revenue,
                    ebitda=raw.ebitda,
                    total_debt=raw.total_debt,
                    cash=raw.cash,
                    net_debt=raw.net_debt,
                    free_cash_flow=None,  # Will be populated when FCF added to ingestion
                    eps_growth_fwd_pct=raw.eps_growth_fwd,
                    revenue_growth_fwd_pct=raw.revenue_growth_fwd,
                    dividend_yield=raw.dividend_yield,
                    beta=raw.beta,
                    is_bank=is_bank,
                )

                # Track missing fields for summary
                for metric_name in computed.missing_reasons:
                    result.missing_summary[metric_name] = (
                        result.missing_summary.get(metric_name, 0) + 1
                    )

                # Step 4: Write computed metrics back to company_metrics
                company_metrics_repository.update_calculated_metrics(
                    canonical_company_id=raw.canonical_company_id,
                    avg_daily_traded_value=computed.avg_daily_traded_value,
                    pe_vs_benchmark=computed.pe_vs_benchmark,
                    peg_ratio=computed.peg_ratio,
                    ev_ebitda=computed.ev_ebitda,
                    price_to_sales=computed.price_to_sales,
                    price_to_cash_flow=computed.price_to_cash_flow,
                    net_debt=computed.net_debt,
                    net_debt_ebitda=computed.net_debt_ebitda,
                    revenue_growth_fwd=computed.revenue_growth_fwd,
                    data_confidence=computed.data_confidence,
                    updated_at=datetime.utcnow(),
                )

                result.succeeded += 1

            except Exception as e:
                result.failed += 1
                logger.error(
                    f"[METRICS:ERROR:{ticker}] Failed to compute metrics: {e}"
                )

        result.duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        logger.info(
            f"[METRICS:BATCH:DONE] {result.succeeded}/{result.total_companies} computed "
            f"in {result.duration_ms}ms | "
            f"banks_exempt={result.banks_exempted}, "
            f"failed={result.failed}"
        )

        if result.missing_summary:
            top_missing = sorted(result.missing_summary.items(), key=lambda x: -x[1])[:5]
            logger.info(
                f"[METRICS:BATCH] Top missing metrics: "
                + ", ".join(f"{k}({v})" for k, v in top_missing)
            )

        return result

    def compute_single(
        self, canonical_company_id: str
    ) -> Optional[MetricsCalculationOutput]:
        """
        Compute and save metrics for a single company by canonical ID.

        Used by admin endpoints for on-demand recalculation of one company.
        """
        raw = company_metrics_repository.get_metrics(canonical_company_id)
        if not raw:
            logger.warning(
                f"[METRICS:SINGLE] No company_metrics record for '{canonical_company_id}'"
            )
            return None

        company = company_repository.get_company_by_id(canonical_company_id)
        is_bank = company.is_bank if company else False
        ticker = raw.ticker or canonical_company_id

        computed = MetricsEngine.compute_all(
            canonical_company_id=canonical_company_id,
            ticker=ticker,
            market_cap_usd=raw.market_cap_usd,
            price_usd=raw.price_usd,
            avg_daily_volume=raw.avg_daily_volume,
            forward_pe=raw.forward_pe,
            revenue=raw.revenue,
            ebitda=raw.ebitda,
            total_debt=raw.total_debt,
            cash=raw.cash,
            net_debt=raw.net_debt,
            free_cash_flow=None,
            eps_growth_fwd_pct=raw.eps_growth_fwd,
            revenue_growth_fwd_pct=raw.revenue_growth_fwd,
            dividend_yield=raw.dividend_yield,
            beta=raw.beta,
            is_bank=is_bank,
        )

        company_metrics_repository.update_calculated_metrics(
            canonical_company_id=canonical_company_id,
            avg_daily_traded_value=computed.avg_daily_traded_value,
            pe_vs_benchmark=computed.pe_vs_benchmark,
            peg_ratio=computed.peg_ratio,
            ev_ebitda=computed.ev_ebitda,
            price_to_sales=computed.price_to_sales,
            price_to_cash_flow=computed.price_to_cash_flow,
            net_debt=computed.net_debt,
            net_debt_ebitda=computed.net_debt_ebitda,
            revenue_growth_fwd=computed.revenue_growth_fwd,
            data_confidence=computed.data_confidence,
            updated_at=datetime.utcnow(),
        )

        return computed


# Global singleton service instance
metrics_service = MetricsService()

