"""Data ingestion service for multi-country market universe.

Orchestrates the complete data intake pipeline:
1. Calls data provider (Mock, EODHD, or LSEG) for selected countries and exchanges.
2. Captures raw vendor responses and writes them to 'raw_responses' with SHA-256 hashes.
3. Normalizes payloads into canonical models.
4. Feeds records to Security Master to de-duplicate dual-listings into 'companies' and 'listings'.
5. Extracts and stores point-in-time 'financial_snapshots' and 'estimate_snapshots'.
6. Populates the 'company_metrics' table with raw fundamentals and preliminary metric fields.
"""

from datetime import date, datetime
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.adapters.registry import get_data_provider
from app.core.logging import DiagnosticLogger
from app.ingestion.raw_response_store import RawResponseStore
from app.models.company_metrics import CompanyMetricsRecord
from app.models.financial_snapshot import EstimateSnapshotRecord, FinancialSnapshotRecord
from app.repositories.company_metrics_repository import CompanyMetricsRepository
from app.repositories.raw_response_repository import raw_response_repository
from app.repositories.snapshot_repository import snapshot_repository
from app.schemas.normalized_data import NormalizedSecurityData
from app.security_master.company_service import company_service
from app.security_master.listing_service import listing_service
from app.services.metrics_service import metrics_service

logger = DiagnosticLogger("ingestion_service")


class IngestionResult(BaseModel):
    """Execution summary of a market data ingestion run."""
    run_id: str
    provider: str
    selected_countries: List[str]
    selected_exchanges: List[str]
    total_listings_fetched: int = 0
    unique_companies_saved: int = 0
    raw_responses_stored: int = 0
    snapshots_saved: int = 0
    metrics_saved: int = 0
    duration_ms: float = 0.0
    status: str = "succeeded"


class IngestionService:
    """Service orchestrating bulk market data ingestion, normalization, and persistence."""

    def __init__(
        self,
        raw_store: Optional[RawResponseStore] = None,
        company_metrics_repo: Optional[CompanyMetricsRepository] = None,
    ):
        self.raw_store = raw_store or RawResponseStore(repository=raw_response_repository)
        self.metrics_repo = company_metrics_repo or CompanyMetricsRepository()

    async def ingest_market_data(
        self,
        countries: List[str],
        exchanges: List[str],
        run_id: str,
        display_currency: str = "USD",
    ) -> IngestionResult:
        """Fetch and persist market data for all chosen countries and exchanges.

        Args:
            countries: Canonical country identifiers, e.g. ['us', 'in']
            exchanges: Canonical exchange identifiers, e.g. ['nasdaq', 'nse']
            run_id: Unique screening execution run ID
            display_currency: Currency for converted values (default USD)

        Returns:
            IngestionResult summarizing the records ingested and written to PostgreSQL.
        """
        start_time = time.perf_counter()
        provider = get_data_provider()
        provider_name = provider.provider_name
        as_of_date = str(date.today())

        clean_countries = [c.strip().lower() for c in countries]
        clean_exchanges = [e.strip().lower() for e in exchanges]

        logger.info(
            f"[INGEST:START:{run_id}] Initiating ingestion using provider '{provider_name}' "
            f"for {len(clean_countries)} countries, {len(clean_exchanges)} exchanges"
        )

        all_normalized_securities: List[NormalizedSecurityData] = []
        raw_stored_count = 0

        # 1. Fetch data per exchange from active provider
        for ex in clean_exchanges:
            logger.info(f"[INGEST:FETCH:{ex}] Querying securities from provider '{provider_name}'")
            try:
                securities = await provider.fetch_batch_securities(exchange_id=ex)
                logger.info(f"[INGEST:FETCH:{ex}] Retrieved {len(securities)} securities")
                all_normalized_securities.extend(securities)

                # Persist raw batch response for this exchange into 'raw_responses'
                raw_payloads = [
                    sec.model_dump(mode="json") for sec in securities
                ]
                self.raw_store.store_response(
                    provider=provider_name,
                    endpoint=f"/batch/{ex}",
                    response_body=raw_payloads,
                    request_params={"exchange": ex, "countries": clean_countries},
                    run_id=run_id,
                    status_code=200,
                    is_success=True,
                )
                raw_stored_count += 1
            except Exception as e:
                logger.error(f"[INGEST:ERROR:{ex}] Failed to fetch batch for exchange '{ex}': {e}")

        # 2. Process each normalized security through Security Master & Repositories
        seen_companies = set()
        snapshots_count = 0
        metrics_count = 0

        for sec in all_normalized_securities:
            # A. Security Master: Resolve Legal Entity (Companies Table)
            comp_record = company_service.upsert_company_from_normalized(sec.company)
            canonical_id = comp_record.canonical_id
            seen_companies.add(canonical_id)

            # B. Security Master: Register Exchange Venue (Listings Table)
            listing_service.register_listing(
                listing_data=sec.listing,
                canonical_company_id=canonical_id,
                is_home_country=(sec.listing.country_id.lower() == comp_record.country.lower()),
            )

            # C. Financial Statement Snapshot (financial_snapshots Table)
            obs_date = sec.company.as_of_date or as_of_date
            fin_snapshot = FinancialSnapshotRecord(
                id=f"snap-fin-{canonical_id}-{obs_date}",
                canonical_company_id=canonical_id,
                as_of_date=obs_date,
                currency=sec.company.currency,
                ebitda=sec.financials.ebitda,
                net_debt=sec.financials.net_debt,
                revenue=sec.financials.revenue,
                free_cash_flow=None,
                created_at=datetime.utcnow(),
            )
            snapshot_repository.save_financial_snapshot(fin_snapshot)

            # D. Analyst Estimate Snapshot (estimate_snapshots Table)
            est_snapshot = EstimateSnapshotRecord(
                id=f"snap-est-{canonical_id}-{obs_date}",
                canonical_company_id=canonical_id,
                as_of_date=obs_date,
                forward_pe=sec.estimates.forward_pe,
                peg_ratio=sec.estimates.peg_ratio,
                eps_growth_fwd=sec.estimates.eps_growth_fwd_pct,
                created_at=datetime.utcnow(),
            )
            snapshot_repository.save_estimate_snapshot(est_snapshot)
            snapshots_count += 2

            # E. Company Metrics Store (company_metrics Table)
            # Store raw financial building blocks + preliminary ratios for rule filtering
            traded_val = (
                (sec.price.price_usd or 0.0) * (sec.price.avg_daily_volume or 0.0)
                if sec.price.price_usd and sec.price.avg_daily_volume
                else None
            )

            metrics_record = CompanyMetricsRecord(
                canonical_company_id=canonical_id,
                ticker=comp_record.primary_ticker,
                as_of_date=obs_date,
                market_cap_usd=sec.company.market_cap,
                price_usd=sec.price.price_usd,
                avg_daily_volume=sec.price.avg_daily_volume,
                avg_daily_traded_value=traded_val,
                forward_pe=sec.estimates.forward_pe,
                peg_ratio=sec.estimates.peg_ratio,
                beta=sec.price.beta,
                revenue=sec.financials.revenue,
                ebitda=sec.financials.ebitda,
                # Phase 10 needs total_debt and cash separately for EV/EBITDA
                total_debt=sec.financials.total_debt,
                cash=sec.financials.cash_and_equivalents,
                net_debt=sec.financials.net_debt,
                dividend_yield=sec.financials.dividend_yield_pct,
                eps_growth_fwd=sec.estimates.eps_growth_fwd_pct,
                revenue_growth_fwd=sec.estimates.revenue_growth_fwd_pct,
                data_confidence=sec.data_confidence,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.metrics_repo.save_metrics(metrics_record)
            metrics_count += 1

        # Run Phase 10 Metrics Engine to calculate derived ratios immediately
        try:
            metrics_service.run_batch_metrics()
        except Exception as e:
            logger.error(f'[INGEST:METRICS:ERROR] Failed to run metrics engine after ingestion: {e}')

        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            f"[INGEST:COMPLETE:{run_id}] Finished in {duration_ms:.1f}ms: "
            f"{len(all_normalized_securities)} listings fetched, "
            f"{len(seen_companies)} companies upserted, "
            f"{snapshots_count} snapshots stored, "
            f"{metrics_count} company_metrics saved"
        )

        return IngestionResult(
            run_id=run_id,
            provider=provider_name,
            selected_countries=clean_countries,
            selected_exchanges=clean_exchanges,
            total_listings_fetched=len(all_normalized_securities),
            unique_companies_saved=len(seen_companies),
            raw_responses_stored=raw_stored_count,
            snapshots_saved=snapshots_count,
            metrics_saved=metrics_count,
            duration_ms=round(duration_ms, 2),
            status="succeeded",
        )


ingestion_service = IngestionService()
