"""Portfolio holding database models for Phase 15."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class HoldingRecord(BaseModel):
    """Database model for 'holdings' table."""
    holding_id: str = Field(..., description="Unique holding ID, e.g. 'hld-comp-001'")
    canonical_company_id: str = Field(..., description="Foreign key to companies.canonical_id")
    portfolio_name: str = Field(default="Core Equity Fund", description="Name of the fund / portfolio")
    shares: float = Field(default=0.0, description="Number of shares held")
    cost_basis: float = Field(default=0.0, description="Purchase cost basis per share or total")
    weight_pct: float = Field(default=0.0, description="Portfolio weighting percentage (0 to 100)")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class HoldingWithDetails(HoldingRecord):
    """Holding record enriched with Security Master company details."""
    ticker: str = Field(..., description="Primary ticker symbol")
    company_name: str = Field(..., description="Official company legal name")
    country: str = Field(..., description="Country code (e.g. 'US', 'IN')")
    exchange: str = Field(..., description="Stock exchange (e.g. 'NYSE', 'NSE')")
    sector: str = Field(default="Unclassified", description="GICS sector")
    market_cap_display: Optional[float] = None
    price_usd: Optional[float] = None

