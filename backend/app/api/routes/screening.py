"""Screening execution and run management API routes."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.core.logging import DiagnosticLogger
from app.models.screening_run import ScreeningRunRecord
from app.repositories.screening_repository import screening_repository
from app.schemas.screening import (
    FunnelStageCounts,
    ScreeningRunRequest,
    ScreeningRunResponse,
)
from app.services.screening_service import screening_service

logger = DiagnosticLogger("screening_api")
router = APIRouter(prefix="/api/screenings", tags=["screenings"])


@router.post("", response_model=ScreeningRunResponse, status_code=status.HTTP_201_CREATED)
async def trigger_screening_run(request: ScreeningRunRequest):
    """Initiate a screening execution for selected countries, exchanges, and rules."""
    logger.calc_info(
        "API",
        "POST",
        f"Incoming screening request: {len(request.countries)} countries, {len(request.exchanges)} exchanges"
    )
    return await screening_service.initiate_screening_run(request)


@router.get("", response_model=List[ScreeningRunRecord])
def list_screening_runs(limit: int = Query(default=20, ge=1, le=100)):
    """List historical screening run executions ordered by start time descending."""
    return screening_service.list_runs(limit=limit)


@router.get("/{run_id}", response_model=ScreeningRunRecord)
def get_screening_run(run_id: str):
    """Retrieve metadata and status for a specific screening run."""
    run = screening_service.get_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screening run '{run_id}' not found.",
        )
        return run


@router.get("/{run_id}/results")
def get_screening_results(
    run_id: str,
    view: str = Query(default="all"),
    sector: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    """Retrieve individual security results, ranks, and score breakdowns for a screening run."""
    run = screening_service.get_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screening run '{run_id}' not found.",
        )
    return screening_repository.get_results_by_run(run_id, view=view, sector=sector, limit=limit)


@router.get("/{run_id}/funnel", response_model=FunnelStageCounts)
def get_run_funnel(run_id: str):
    """Retrieve funnel stage counts (Universe -> Markets -> Floors -> Gates -> Shortlist -> Selected) for a run."""
    funnel = screening_repository.get_funnel_counts(run_id)
    if not funnel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Funnel counts for run '{run_id}' not found.",
        )
    return FunnelStageCounts(
        universe=funnel.universe_count,
        markets=funnel.markets_count,
        floors=funnel.floors_count,
        gates=funnel.gates_count,
        score=funnel.score_count,
        shortlist=funnel.shortlist_count,
        selected=funnel.selected_count,
    )


@router.get("/{run_id}/compare/{prev_run_id}")
def compare_screening_runs(run_id: str, prev_run_id: str):
    """Compare two screening executions, detecting rule diffs, entered/exited stocks, and root causes."""
    from app.services.funnel_service import funnel_service
    curr_run = screening_service.get_run(run_id)
    if not curr_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found.",
        )
    prev_run = screening_service.get_run(prev_run_id)
    if not prev_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{prev_run_id}' not found.",
        )

    curr_results = screening_repository.get_results_by_run(run_id, view="all", limit=500)
    prev_results = screening_repository.get_results_by_run(prev_run_id, view="all", limit=500)

    return funnel_service.compare_runs(curr_run, prev_run, curr_results, prev_results)
