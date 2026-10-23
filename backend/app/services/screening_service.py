"""Screening execution and validation service.

Orchestrates input validation, market relationship checks, rule resolution,
and screening run creation in PostgreSQL.
"""

from datetime import datetime, timezone
import logging
import time
from typing import Dict, List, Optional, Set, Tuple
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import DiagnosticLogger
from app.models.screening_run import (
    FunnelCountRecord,
    ScreeningResultRecord,
    ScreeningRunRecord,
)
from app.repositories.rule_repository import rule_repository
from app.repositories.screening_repository import screening_repository
from app.schemas.market import SUPPORTED_COUNTRIES, SUPPORTED_EXCHANGES
from app.schemas.screening import (
    FunnelStageCounts,
    ScreenedSecurityResult,
    ScreeningRunRequest,
    ScreeningRunResponse,
)

logger = DiagnosticLogger("screening_service")

# Map of exchange_id -> country_id for cross-validation
EXCHANGE_TO_COUNTRY: Dict[str, str] = {
    e.id.lower(): e.country_id.lower() for e in SUPPORTED_EXCHANGES
}
VALID_COUNTRY_IDS: Set[str] = {c.id.lower() for c in SUPPORTED_COUNTRIES}
VALID_EXCHANGE_IDS: Set[str] = {e.id.lower() for e in SUPPORTED_EXCHANGES}


class ScreeningService:
    """Service handling screening request validation and execution orchestration."""

    def __init__(
        self,
        screening_repo=screening_repository,
        rule_repo=rule_repository,
        ingestion_srv=None,
    ):
        self.screening_repo = screening_repo
        self.rule_repo = rule_repo
        from app.ingestion.ingestion_service import ingestion_service
        self.ingestion_service = ingestion_srv or ingestion_service

    def validate_market_selection(
        self, countries: List[str], exchanges: List[str]
    ) -> Tuple[List[str], List[str]]:
        """Validate country/exchange inputs and ensure every exchange belongs to a selected country.

        Raises HTTPException(422) if validation fails.
        """
        if not countries:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one country must be selected for screening.",
            )

        if not exchanges:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one stock exchange must be selected for screening.",
            )

        clean_countries = [c.strip().lower() for c in countries if c.strip()]
        clean_exchanges = [e.strip().lower() for e in exchanges if e.strip()]

        # Validate country codes
        invalid_countries = [c for c in clean_countries if c not in VALID_COUNTRY_IDS]
        if invalid_countries:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported country identifier(s): {invalid_countries}. Choose from supported 26 countries.",
            )

        # Validate exchange codes
        invalid_exchanges = [e for e in clean_exchanges if e not in VALID_EXCHANGE_IDS]
        if invalid_exchanges:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported exchange identifier(s): {invalid_exchanges}. Choose from supported 34 exchanges.",
            )

        # Cross-validate: ensure every selected exchange belongs to a selected country
        country_set = set(clean_countries)
        mismatched: List[str] = []
        for exc in clean_exchanges:
            parent_country = EXCHANGE_TO_COUNTRY.get(exc)
            if parent_country and parent_country not in country_set:
                mismatched.append(f"Exchange '{exc.upper()}' belongs to country '{parent_country.upper()}', which is not selected.")

        if mismatched:
            raise HTTPException(
                status_code=422,
                detail=f"Exchange / Country mismatch: {'; '.join(mismatched)}",
            )

        return clean_countries, clean_exchanges

    async def initiate_screening_run(self, request: ScreeningRunRequest) -> ScreeningRunResponse:
        """Validate screening request, resolve rules, ingest market data, and record the screening run."""
        start_time = time.perf_counter()
        now = datetime.now(timezone.utc)

        # 1. Validate markets
        clean_countries, clean_exchanges = self.validate_market_selection(
            request.countries, request.exchanges
        )

        # 2. Resolve Rule Profile
        active_version = None
        if request.rule_version_id:
            active_version = self.rule_repo.get_version_by_id(request.rule_version_id)
            if not active_version:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Rule profile '{request.rule_version_id}' not found in database.",
                )
        else:
            active_version = self.rule_repo.get_active_version()

        profile_name = active_version.profile_name if active_version else (request.profile_name or "Default Strategy")
        rule_version_id = active_version.version_id if active_version else "prof-default"

        # Freeze rules snapshot
        rules_snapshot: List[dict] = []
        if active_version and active_version.rules:
            for r in active_version.rules:
                rules_snapshot.append({
                    "id": r.metric_name,
                    "name": r.label,
                    "category": r.category,
                    "condition": r.condition,
                    "threshold_value": r.threshold_value,
                    "weight": r.weight,
                    "mode": r.mode,
                })
        elif request.rules_config:
            rules_snapshot = request.rules_config

        # 3. Create persistent run record in PostgreSQL
        run_id = f"run-{now.strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6]}"
        run_record = ScreeningRunRecord(
            run_id=run_id,
            status="running",
            provider=settings.data_provider.lower(),
            rule_version_id=rule_version_id,
            profile_name=profile_name,
            display_currency=request.display_currency.upper(),
            selected_countries=clean_countries,
            selected_exchanges=clean_exchanges,
            rules_snapshot=rules_snapshot,
            duration_ms=0.0,
            started_at=now,
            completed_at=None,
        )
        self.screening_repo.save_run(run_record)

        # 4. Trigger Data Ingestion Service (Phase 9)
        ingestion_result = await self.ingestion_service.ingest_market_data(
            countries=clean_countries,
            exchanges=clean_exchanges,
            run_id=run_id,
            display_currency=request.display_currency.upper(),
        )

        # 5. Populate funnel stage progression with real universe and markets
        funnel_record = FunnelCountRecord(
            id=f"fnl-{run_id}",
            run_id=run_id,
            universe_count=ingestion_result.total_listings_fetched,
            markets_count=ingestion_result.unique_companies_saved,
            floors_count=ingestion_result.unique_companies_saved,
            gates_count=ingestion_result.unique_companies_saved,
            score_count=0,
            shortlist_count=0,
            selected_count=0,
            created_at=now,
        )
        self.screening_repo.save_funnel_counts(funnel_record)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        run_record.duration_ms = duration_ms
        run_record.status = "succeeded"
        run_record.completed_at = datetime.now(timezone.utc)
        self.screening_repo.save_run(run_record)

        logger.calc_info(
            "SCREENING",
            run_id,
            f"Created screening run '{run_id}' for {len(clean_countries)} countries, "
            f"{len(clean_exchanges)} exchanges using profile '{profile_name}' ({duration_ms:.1f}ms)"
        )

        return ScreeningRunResponse(
            run_id=run_id,
            status="succeeded",
            display_currency=request.display_currency.upper(),
            started_at=now,
            completed_at=run_record.completed_at,
            duration_ms=duration_ms,
            provider_used=settings.data_provider.lower(),
            funnel=FunnelStageCounts(
                universe=funnel_record.universe_count,
                markets=funnel_record.markets_count,
                floors=funnel_record.floors_count,
                gates=funnel_record.gates_count,
                score=funnel_record.score_count,
                shortlist=funnel_record.shortlist_count,
                selected=funnel_record.selected_count,
            ),
            results_count=0,
            top_results=[],
        )

    def get_run(self, run_id: str) -> Optional[ScreeningRunRecord]:
        """Fetch a specific screening run by its ID."""
        return self.screening_repo.get_run(run_id)

    def list_runs(self, limit: int = 50) -> List[ScreeningRunRecord]:
        """Fetch historical screening executions."""
        return self.screening_repo.list_runs(limit)


# Global screening service instance
screening_service = ScreeningService()
