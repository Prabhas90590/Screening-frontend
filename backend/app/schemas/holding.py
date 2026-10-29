"""Phase 15: Holdings Import and Management Schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HoldingItemSchema(BaseModel):
    """Schema for an individual portfolio holding returned to the client."""
    holding_id: str
    canonical_company_id: str
    ticker: str
    name: str
    country: str
    exchange: str
    sector: str = "Unclassified"
    shares: float = 0.0
    cost_basis: float = 0.0
    weight_pct: float = 0.0
    holding_rank: Optional[int] = None
    portfolio_name: str = "Core Equity Fund"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CreateHoldingRequest(BaseModel):
    """Request schema for manually entering a single portfolio holding."""
    ticker: str = Field(..., description="Ticker symbol or identifier (e.g. 'AAPL', 'INFY')")
    country: Optional[str] = Field(default="US", description="Country code (e.g. 'US', 'IN')")
    exchange: Optional[str] = Field(default=None, description="Optional exchange (e.g. 'NYSE', 'NSE')")
    shares: Optional[float] = Field(default=0.0, description="Quantity of shares held")
    cost_basis: Optional[float] = Field(default=0.0, description="Total or per-share cost basis")
    weight_pct: Optional[float] = Field(default=0.0, description="Portfolio weighting percentage (0..100)")
    holding_rank: Optional[int] = Field(default=None, description="Rank in portfolio or screening run")
    portfolio_name: Optional[str] = Field(default="Core Equity Fund", description="Fund / Portfolio name")


class UnmatchedHoldingRow(BaseModel):
    """Explains why a row in the imported file could not be reconciled."""
    row_index: int
    raw_identifier: str
    reason: str
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class HoldingsImportResponse(BaseModel):
    """Response returned after processing a CSV or Excel holdings file."""
    portfolio_name: str = "Core Equity Fund"
    total_rows: int
    matched_count: int
    unmatched_count: int
    holdings: List[HoldingItemSchema] = Field(default_factory=list)
    unmatched: List[UnmatchedHoldingRow] = Field(default_factory=list)
    message: str


class HoldingsSummary(BaseModel):
    """High-level summary of active fund holdings."""
    portfolio_name: str
    total_positions: int
    total_weight_pct: float
    sectors_represented: List[str] = Field(default_factory=list)
    countries_represented: List[str] = Field(default_factory=list)
    holdings: List[HoldingItemSchema] = Field(default_factory=list)

