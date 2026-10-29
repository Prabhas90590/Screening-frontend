"""Analyst Decisions API Routes (Phase 16).

Provides REST endpoints to record, inspect, and bulk-sync Keep/Drop analyst decisions.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.decision import (
    DecisionUpdateRequest,
    DecisionBulkSyncRequest,
    DecisionResponse,
)
from app.services.decision_service import decision_service

router = APIRouter(prefix="/api/decisions", tags=["Decisions"])


@router.post("", response_model=DecisionResponse, status_code=status.HTTP_200_OK)
def record_analyst_decision(request: DecisionUpdateRequest):
    """Record or update an analyst Keep or Drop decision for a security."""
    try:
        return decision_service.record_decision(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record analyst decision: {str(e)}",
        )


@router.post("/sync", response_model=List[DecisionResponse], status_code=status.HTTP_200_OK)
def bulk_sync_analyst_decisions(request: DecisionBulkSyncRequest):
    """Bulk-sync and persist all decisions for a profile upon Excel export."""
    try:
        return decision_service.bulk_sync_decisions(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk-sync decisions: {str(e)}",
        )


@router.get("", response_model=List[DecisionResponse])
def list_analyst_decisions(
    profile_name: Optional[str] = Query(default=None),
    run_id: Optional[str] = Query(default=None),
):
    """Retrieve recorded analyst decisions, optionally filtered by profile_name or run_id."""
    try:
        return decision_service.list_decisions(profile_name=profile_name, run_id=run_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve analyst decisions: {str(e)}",
        )


@router.get("/{canonical_company_id}", response_model=DecisionResponse)
def get_analyst_decision(
    canonical_company_id: str,
    profile_name: Optional[str] = Query(default=None),
):
    """Retrieve the latest Keep/Drop decision for a specific company."""
    decision = decision_service.get_decision(canonical_company_id, profile_name=profile_name)
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No analyst decision recorded for company '{canonical_company_id}'.",
        )
    return decision
