"""Screening execution and run management API routes."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.logging import DiagnosticLogger
from app.models.screening_run import ScreeningRunRecord
from app.models.user import UserRecord
from app.repositories.screening_repository import screening_repository
from app.schemas.screening import (
    FunnelStageCounts,
    ScreeningRunRequest,
    ScreeningRunResponse,
)
from app.services.auth_service import get_optional_user
from app.services.screening_service import screening_service

logger = DiagnosticLogger("screening_api")
router = APIRouter(prefix="/api/screenings", tags=["screenings"])


def _get_owned_run_or_404(
    run_id: str,
    current_user: Optional[UserRecord],
) -> ScreeningRunRecord:
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access screening runs.",
        )
    run = screening_service.get_run(
        run_id,
        owner_email=current_user.email,
        user_id=current_user.id,
    )
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screening run '{run_id}' not found.",
        )
    return run


@router.post("", response_model=ScreeningRunResponse, status_code=status.HTTP_201_CREATED)
async def trigger_screening_run(
    request: ScreeningRunRequest,
    current_user: Optional[UserRecord] = Depends(get_optional_user),
):
    """Initiate a screening execution for selected countries, exchanges, and rules."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to run screening."
        )
    user_email = current_user.email
    logger.calc_info(
        "API",
        "POST",
        f"Incoming screening request from {user_email}: {len(request.countries or [])} countries, {len(request.exchanges or [])} exchanges"
    )
    return await screening_service.initiate_screening_run(
        request,
        owner_email=user_email,
        user_id=current_user.id,
    )


@router.get("", response_model=List[ScreeningRunRecord])
def list_screening_runs(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: Optional[UserRecord] = Depends(get_optional_user),
):
    """List historical screening run executions ordered by start time descending for current user."""
    if not current_user:
        return []
    return screening_service.list_runs(
        limit=limit,
        owner_email=current_user.email,
        user_id=current_user.id,
    )


@router.get("/{run_id}", response_model=ScreeningRunRecord)
def get_screening_run(
    run_id: str,
    current_user: Optional[UserRecord] = Depends(get_optional_user),
):
    """Retrieve metadata and status for a specific screening run."""
    return _get_owned_run_or_404(run_id, current_user)


@router.get("/{run_id}/results")
def get_screening_results(
    run_id: str,
    view: str = Query(default="all"),
    sector: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    current_user: Optional[UserRecord] = Depends(get_optional_user),
):
    """Retrieve individual security results, ranks, and score breakdowns for a screening run."""
    _get_owned_run_or_404(run_id, current_user)
    return screening_repository.get_results_by_run(run_id, view=view, sector=sector, limit=limit)


@router.get("/{run_id}/funnel", response_model=FunnelStageCounts)
def get_run_funnel(
    run_id: str,
    current_user: Optional[UserRecord] = Depends(get_optional_user),
):
    """Retrieve funnel stage counts (Universe -> Markets -> Floors -> Gates -> Shortlist -> Selected) for a run."""
    run = _get_owned_run_or_404(run_id, current_user)
    funnel = screening_repository.get_funnel_counts(run_id)
    if not funnel:
        # Blocked or interrupted runs may lack a persisted funnel row; return zeroed counts when the run exists.
        universe_total = run.universe_count or 0
        return FunnelStageCounts(
            universe=universe_total,
            markets=universe_total,
            floors=0,
            gates=0,
            score=0,
            shortlist=0,
            selected=0,
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
def compare_screening_runs(
    run_id: str,
    prev_run_id: str,
    current_user: Optional[UserRecord] = Depends(get_optional_user),
):
    """Compare two screening executions, detecting rule diffs, entered/exited stocks, and root causes."""
    from app.services.funnel_service import funnel_service
    curr_run = _get_owned_run_or_404(run_id, current_user)
    prev_run = _get_owned_run_or_404(prev_run_id, current_user)

    curr_results = screening_repository.get_results_by_run(run_id, view="all", limit=500)
    prev_results = screening_repository.get_results_by_run(prev_run_id, view="all", limit=500)

    return funnel_service.compare_runs(curr_run, prev_run, curr_results, prev_results)



@router.delete("/{run_id}", status_code=status.HTTP_200_OK)
def delete_screening_run(
    run_id: str,
    current_user: Optional[UserRecord] = Depends(get_optional_user),
):
    """Permanently delete a single screening run owned by caller from the database."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to delete screening runs.",
        )
    try:
        deleted = screening_repository.delete_run(
            run_id,
            owner_email=current_user.email,
            user_id=current_user.id,
        )
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Screening run '{run_id}' not found.",
            )
        return {
            "success": True,
            "message": f"Run '{run_id}' deleted successfully.",
            "deleted_run_id": run_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting run '{run_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete run '{run_id}': {str(e)}",
        )


@router.delete("", status_code=status.HTTP_200_OK)
def clear_all_screening_runs(
    current_user: Optional[UserRecord] = Depends(get_optional_user),
):
    """Permanently delete all screening runs and results belonging to the authenticated user."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to clear screening runs.",
        )
    try:
        count = screening_repository.clear_all_runs(
            owner_email=current_user.email,
            user_id=current_user.id,
        )
        return {
            "success": True,
            "message": f"Successfully cleared all screening runs ({count} removed).",
            "cleared_count": count,
        }
    except Exception as e:
        logger.error(f"Error clearing screening runs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear screening runs: {str(e)}",
        )
