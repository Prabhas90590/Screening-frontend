"""Phase 15: Portfolio Holdings API Routes.

Provides endpoints to upload holdings files (CSV/Excel), manually manage positions,
and query current fund holdings.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.schemas.holding import (
    CreateHoldingRequest,
    HoldingItemSchema,
    HoldingsImportResponse,
    HoldingsSummary,
)
from app.services.holdings_service import holdings_service

logger = logging.getLogger("app.api.routes.holdings")
router = APIRouter(prefix="/api/holdings", tags=["holdings"])


@router.post(
    "/import",
    response_model=HoldingsImportResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and ingest a portfolio holdings file (CSV, XLS, XLSX)",
)
async def import_holdings(
    file: UploadFile = File(..., description="Holdings file (.csv, .xlsx, .xls)"),
    portfolio_name: str = Form("Core Equity Fund", description="Name of the fund"),
):
    """Parse CSV or Excel file, reconcile tickers against Security Master, and persist holdings."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload payload.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    try:
        response = holdings_service.import_holdings_file(
            file_bytes=content,
            filename=file.filename,
            portfolio_name=portfolio_name,
        )
        return response
    except Exception as e:
        logger.error(f"Failed to process holdings file '{file.filename}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse holdings file: {str(e)}",
        )


@router.get(
    "",
    response_model=List[HoldingItemSchema],
    summary="List active holdings for a portfolio",
)
def list_holdings(portfolio_name: Optional[str] = None):
    """Retrieve all saved holdings enriched with Security Master details."""
    return holdings_service.list_holdings(portfolio_name)


@router.get(
    "/summary",
    response_model=HoldingsSummary,
    summary="Get allocation and diversification summary for active holdings",
)
def get_holdings_summary(portfolio_name: str = "Core Equity Fund"):
    """Retrieve portfolio metrics, total weight, sector and country counts."""
    return holdings_service.get_summary(portfolio_name)


@router.post(
    "",
    response_model=HoldingItemSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Manually add a holding to a portfolio",
)
def create_holding(request: CreateHoldingRequest):
    """Reconcile ticker against Security Master and add position to fund."""
    try:
        return holdings_service.add_manual_holding(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to create holding '{request.ticker}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save holding: {str(e)}",
        )


@router.delete(
    "/{holding_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove a holding from a portfolio",
)
def delete_holding(holding_id: str):
    """Delete a single holding by ID."""
    deleted = holdings_service.delete_holding(holding_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Holding '{holding_id}' not found.",
        )
    return {"message": f"Holding '{holding_id}' deleted successfully.", "deleted": True}


@router.delete(
    "",
    status_code=status.HTTP_200_OK,
    summary="Clear all holdings for a portfolio",
)
def clear_portfolio(portfolio_name: Optional[str] = None):
    """Remove all positions in a portfolio."""
    count = holdings_service.clear_holdings(portfolio_name)
    return {
        "message": f"Cleared {count} holdings.",
        "portfolio_name": portfolio_name or "All",
        "cleared_count": count,
    }
