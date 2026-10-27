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
        elif not request.rules_config:
            active_version = self.rule_repo.get_active_version()

        if active_version:
            v_num = getattr(active_version, "version_number", None) or "1.0"
            base_name = active_version.profile_name
            if request.profile_name and ("version" in request.profile_name.lower() or f"v{v_num}" in request.profile_name.lower()):
                profile_name = request.profile_name
            elif f"version {v_num}" not in base_name.lower() and f"v{v_num}" not in base_name.lower():
                profile_name = f"{base_name} - Version {v_num}"
            else:
                profile_name = base_name
            rule_version_id = active_version.version_id
        else:
            profile_name = request.profile_name or "Custom Strategy"
            rule_version_id = "prof-custom"

        # Check if the active_version saved a specific exchange universe in its snapshot (only if not specified)
        if not clean_exchanges and active_version:
            saved_snapshot = getattr(active_version, "diversification_rules", {}).get("snapshot", {})
            if saved_snapshot and "exchanges" in saved_snapshot:
                saved_exchs = [e["id"].lower() for e in saved_snapshot["exchanges"] if e.get("selected")]
                if saved_exchs:
                    clean_exchanges = saved_exchs

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

        try:
            # 4. Trigger Data Ingestion Service (Phase 9)
            ingestion_result = await self.ingestion_service.ingest_market_data(
                countries=clean_countries,
                exchanges=clean_exchanges,
                run_id=run_id,
                display_currency=request.display_currency.upper(),
            )

            # 5. Retrieve Ingested Fundamentals & Evaluate Rules (Phase 11 & Phase 13)
            from app.models.company_metrics import CompanyMetricsRecord
            from app.repositories.company_metrics_repository import CompanyMetricsRepository
            from app.repositories.company_repository import company_repository
            from app.rules.rule_engine import RuleEngine

            comp_metrics_repo = CompanyMetricsRepository()
            all_metrics = comp_metrics_repo.list_metrics(limit=5000)
            metrics_by_id = {m.canonical_company_id: m for m in all_metrics}

            all_companies = company_repository.list_companies(limit=5000)
            companies_by_id = {c.canonical_id: c for c in all_companies}

            # Identify banks for leverage gate exemption
            bank_ids: Set[str] = {
                c.canonical_id for c in all_companies
                if (c.sector and c.sector.lower() in ("financials", "banking", "finance", "banks")) or c.is_bank
            }

            # Filter target universe by selected markets (Country AND Exchange)
            country_alias_map = {
                "us": "us", "usa": "us", "united states": "us",
                "in": "in", "ind": "in", "india": "in",
                "uk": "uk", "gb": "uk", "gbr": "uk", "united kingdom": "uk",
                "jp": "jp", "jpn": "jp", "japan": "jp",
                "de": "de", "deu": "de", "germany": "de", "deutschland": "de",
                "fr": "fr", "fra": "fr", "france": "fr",
                "ch": "ch", "che": "ch", "switzerland": "ch",
                "hk": "hk", "hkg": "hk", "hong kong": "hk",
                "tw": "tw", "twn": "tw", "taiwan": "tw",
                "kr": "kr", "kor": "kr", "south korea": "kr", "korea": "kr",
                "ca": "ca", "can": "ca", "canada": "ca",
                "au": "au", "aus": "au", "australia": "au",
                "nl": "nl", "nld": "nl", "netherlands": "nl",
            }
            target_country_set = {country_alias_map.get(c.lower(), c.lower()) for c in clean_countries}
            target_exchange_set = {e.lower() for e in clean_exchanges}

            all_listings = company_repository.list_listings(limit=10000)
            from collections import defaultdict
            company_exchanges: Dict[str, Set[str]] = defaultdict(set)
            company_countries: Dict[str, Set[str]] = defaultdict(set)
            for l in all_listings:
                company_exchanges[l.canonical_company_id].add(l.exchange_id.lower())
                c_norm = country_alias_map.get(l.country_id.lower(), l.country_id.lower())
                company_countries[l.canonical_company_id].add(c_norm)

            screened_metrics: List[CompanyMetricsRecord] = []
            for m in all_metrics:
                comp = companies_by_id.get(m.canonical_company_id)
                if not comp:
                    continue

                # Country filter (checks company primary country & listing countries)
                comp_c_norm = country_alias_map.get(comp.country.lower().strip(), comp.country.lower().strip())
                comp_countries = {comp_c_norm}.union(company_countries.get(comp.canonical_id, set()))
                if target_country_set and not comp_countries.intersection(target_country_set):
                    continue

                # Exchange filter (checks company primary exchange & listing exchanges)
                comp_exchs = set(company_exchanges.get(comp.canonical_id, set()))
                if comp.primary_exchange:
                    comp_exchs.add(comp.primary_exchange.lower())
                if target_exchange_set and not comp_exchs.intersection(target_exchange_set):
                    continue

                screened_metrics.append(m)

            if not target_country_set and not target_exchange_set:
                screened_metrics = all_metrics

            # Evaluate entire universe against active rule profile
            rule_profile_to_use = active_version or request.rules_config
            evaluations = RuleEngine.evaluate_batch(
                companies_metrics=screened_metrics,
                profile=rule_profile_to_use,
                bank_ids=bank_ids,
            )

            passed_evals = [e for e in evaluations if e.passed_overall]
            non_passed_evals = [e for e in evaluations if not e.passed_overall]

            results_to_save: List[ScreeningResultRecord] = []
            top_screened_results: List[ScreenedSecurityResult] = []

            curr_currency = request.display_currency.upper()
            primary_exchange_default = clean_exchanges[0].upper() if clean_exchanges else "NSE"

            def _format_net_debt(m_rec: Optional[CompanyMetricsRecord]) -> str:
                if not m_rec or m_rec.net_debt_ebitda is None:
                    return "N/A"
                if m_rec.net_debt is not None and m_rec.net_debt < 0:
                    return "Net Cash"
                return f"{m_rec.net_debt_ebitda:.1f}x"

            def _get_cap_category(m_rec: Optional[CompanyMetricsRecord]) -> str:
                if not m_rec or not m_rec.market_cap_usd:
                    return "Mid-cap Value"
                cap = m_rec.market_cap_usd
                if cap >= 10e9:
                    return "Large-cap Quality"
                if cap >= 2e9:
                    return "Mid-cap Value"
                return "Small-cap Growth"

            # 5A. Process passing securities (Rank 1..N)
            for idx, e in enumerate(passed_evals):
                rank = idx + 1
                is_top20 = rank <= 20
                stage_status = "passed" 
                near_miss_status = "none" if is_top20 else "rank_near_miss"

                comp = companies_by_id.get(e.canonical_company_id)
                m_rec = metrics_by_id.get(e.canonical_company_id)
                ticker = comp.primary_ticker if comp else e.ticker
                company_name = comp.name if comp else f"{ticker} Ltd"
                country = comp.country.upper() if comp else "IN"
                sector = comp.sector if comp else "General"

                metric_statuses = {item.name: item.status for item in e.score_breakdown}
                score_breakdown_dicts = [
                    item.model_dump() if hasattr(item, "model_dump") else item.__dict__
                    for item in e.score_breakdown
                ]

                res_record = ScreeningResultRecord(
                    id=f"res-{run_id}-{e.canonical_company_id}",
                    run_id=run_id,
                    canonical_company_id=e.canonical_company_id,
                    ticker=ticker,
                    company_name=company_name,
                    country=country,
                    exchange=primary_exchange_default,
                    sector=sector,
                    rank=rank,
                    score=int(round(e.total_score)),
                    display_price=m_rec.price_usd if m_rec else None,
                    market_cap_display=m_rec.market_cap_usd if m_rec else None,
                    display_currency=curr_currency,
                    fwd_pe=m_rec.forward_pe if m_rec else None,
                    peg=m_rec.peg_ratio if m_rec else None,
                    ev_ebitda=m_rec.ev_ebitda if m_rec else None,
                    beta=m_rec.beta if m_rec else None,
                    nd_ebitda=_format_net_debt(m_rec),
                    yield_pct=m_rec.dividend_yield if m_rec else None,
                    eps_growth_pct=m_rec.eps_growth_fwd if m_rec else None,
                    pe_vs_benchmark=m_rec.pe_vs_benchmark if m_rec else None,
                    price_to_sales=m_rec.price_to_sales if m_rec else None,
                    price_to_cash_flow=m_rec.price_to_cash_flow if m_rec else None,
                    revenue_growth_fwd=m_rec.revenue_growth_fwd if m_rec else None,
                    avg_daily_volume=m_rec.avg_daily_volume if m_rec else None,
                    avg_daily_traded_value=m_rec.avg_daily_traded_value if m_rec else None,
                    data_confidence=m_rec.data_confidence if (m_rec and m_rec.data_confidence) else "High",
                    stage_status=stage_status,
                    near_miss_status=near_miss_status,
                    score_breakdown=score_breakdown_dicts,
                    metric_statuses=metric_statuses,
                    created_at=now,
                )
                results_to_save.append(res_record)

                if is_top20:
                    top_screened_results.append(
                        ScreenedSecurityResult(
                            id=e.canonical_company_id,
                            rank=rank,
                            name=company_name,
                            ticker=ticker,
                            country=country,
                            exchange=primary_exchange_default,
                            sector=sector,
                            market_cap_category=_get_cap_category(m_rec),
                            score=int(round(e.total_score)),
                            display_currency=curr_currency,
                            display_price=m_rec.price_usd if m_rec else None,
                            market_cap_display=m_rec.market_cap_usd if m_rec else None,
                            fwd_pe=m_rec.forward_pe if m_rec else None,
                            peg=m_rec.peg_ratio if m_rec else None,
                            ev_ebitda=m_rec.ev_ebitda if m_rec else None,
                            beta=m_rec.beta if m_rec else None,
                            nd_ebitda=_format_net_debt(m_rec),
                            yield_pct=m_rec.dividend_yield if m_rec else None,
                            eps_growth_pct=m_rec.eps_growth_fwd if m_rec else None,
                            pe_vs_benchmark=m_rec.pe_vs_benchmark if m_rec else None,
                            price_to_sales=m_rec.price_to_sales if m_rec else None,
                            price_to_cash_flow=m_rec.price_to_cash_flow if m_rec else None,
                            revenue_growth_fwd=m_rec.revenue_growth_fwd if m_rec else None,
                            avg_daily_volume=m_rec.avg_daily_volume if m_rec else None,
                            avg_daily_traded_value=m_rec.avg_daily_traded_value if m_rec else None,
                            data_confidence=m_rec.data_confidence if (m_rec and m_rec.data_confidence) else "High",  # type: ignore
                            metric_statuses=metric_statuses,
                            score_breakdown=e.score_breakdown,
                        )
                    )

            # 5B. Process knocked-out securities (Rank len(passed)+1..N)
            for idx, e in enumerate(non_passed_evals):
                rank = len(passed_evals) + idx + 1
                near_miss_status = "rule_near_miss" if e.near_miss else "none"

                comp = companies_by_id.get(e.canonical_company_id)
                m_rec = metrics_by_id.get(e.canonical_company_id)
                ticker = comp.primary_ticker if comp else e.ticker
                company_name = comp.name if comp else f"{ticker} Ltd"
                country = comp.country.upper() if comp else "IN"
                sector = comp.sector if comp else "General"

                metric_statuses = {item.name: item.status for item in e.score_breakdown}
                score_breakdown_dicts = [
                    item.model_dump() if hasattr(item, "model_dump") else item.__dict__
                    for item in e.score_breakdown
                ]

                res_record = ScreeningResultRecord(
                    id=f"res-{run_id}-{e.canonical_company_id}",
                    run_id=run_id,
                    canonical_company_id=e.canonical_company_id,
                    ticker=ticker,
                    company_name=company_name,
                    country=country,
                    exchange=primary_exchange_default,
                    sector=sector,
                    rank=rank,
                    score=int(round(e.total_score)),
                    display_price=m_rec.price_usd if m_rec else None,
                    market_cap_display=m_rec.market_cap_usd if m_rec else None,
                    display_currency=curr_currency,
                    fwd_pe=m_rec.forward_pe if m_rec else None,
                    peg=m_rec.peg_ratio if m_rec else None,
                    ev_ebitda=m_rec.ev_ebitda if m_rec else None,
                    beta=m_rec.beta if m_rec else None,
                    nd_ebitda=_format_net_debt(m_rec),
                    yield_pct=m_rec.dividend_yield if m_rec else None,
                    eps_growth_pct=m_rec.eps_growth_fwd if m_rec else None,
                    pe_vs_benchmark=m_rec.pe_vs_benchmark if m_rec else None,
                    price_to_sales=m_rec.price_to_sales if m_rec else None,
                    price_to_cash_flow=m_rec.price_to_cash_flow if m_rec else None,
                    revenue_growth_fwd=m_rec.revenue_growth_fwd if m_rec else None,
                    avg_daily_volume=m_rec.avg_daily_volume if m_rec else None,
                    avg_daily_traded_value=m_rec.avg_daily_traded_value if m_rec else None,
                    data_confidence=m_rec.data_confidence if (m_rec and m_rec.data_confidence) else "High",
                    stage_status="floor_dropped" if not e.passed_floors else "gate_dropped",
                    near_miss_status=near_miss_status,
                    score_breakdown=score_breakdown_dicts,
                    metric_statuses=metric_statuses,
                    created_at=now,
                )
                results_to_save.append(res_record)

            # Save all results to PostgreSQL screening_results
            self.screening_repo.save_results_batch(results_to_save)

            # 6. Compute Real Funnel Counts
            floors_passed = sum(1 for e in evaluations if e.passed_floors)
            gates_passed = sum(1 for e in evaluations if e.passed_floors and e.passed_gates)
            score_passed = len(passed_evals)
            shortlist_count = min(score_passed, 35) if score_passed > 0 else 0
            selected_count = min(score_passed, 20) if score_passed > 0 else 0

            funnel_record = FunnelCountRecord(
                id=f"fnl-{run_id}",
                run_id=run_id,
                universe_count=ingestion_result.total_listings_fetched,
                markets_count=len(evaluations),
                floors_count=floors_passed,
                gates_count=gates_passed,
                score_count=score_passed,
                shortlist_count=shortlist_count,
                selected_count=selected_count,
                created_at=now,
            )
            self.screening_repo.save_funnel_counts(funnel_record)

            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            run_record.duration_ms = duration_ms
            run_record.status = "succeeded"
            run_record.completed_at = datetime.now(timezone.utc)
            run_record.universe_count = funnel_record.universe_count
            run_record.selected_count = funnel_record.selected_count
            self.screening_repo.save_run(run_record)

            logger.calc_info(
                "SCREENING",
                run_id,
                f"Screening run '{run_id}' completed: {funnel_record.universe_count} screened, "
                f"{selected_count} selected winners ({duration_ms:.1f}ms)"
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
                results_count=len(results_to_save),
                top_results=top_screened_results,
            )
        except Exception as exc:
            run_record.status = "failed"
            run_record.completed_at = datetime.now(timezone.utc)
            run_record.duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self.screening_repo.save_run(run_record)
            logger.calc_warn("SCREENING", run_id, f"Screening run '{run_id}' failed: {exc}")
            raise exc

    def get_run(self, run_id: str) -> Optional[ScreeningRunRecord]:
        """Fetch a specific screening run by its ID."""
        return self.screening_repo.get_run(run_id)

    def list_runs(self, limit: int = 50) -> List[ScreeningRunRecord]:
        """Fetch historical screening executions."""
        return self.screening_repo.list_runs(limit)


# Global screening service instance
screening_service = ScreeningService()
