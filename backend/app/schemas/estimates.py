"""Canonical consensus analyst estimates schema.

Represents forward-looking projections: Forward P/E, PEG, forward EPS/revenue growth.
"""

from typing import Optional
from pydantic import BaseModel, Field


class NormalizedEstimates(BaseModel):
    """Normalized consensus analyst estimates and forward valuation ratios."""
    ticker: str = Field(..., description="Ticker symbol")
    currency: str = Field(default="USD", description="Currency of estimates")
    forward_pe: Optional[float] = Field(None, description="Consensus Forward P/E ratio")
    forward_eps: Optional[float] = Field(None, description="Next 12 months consensus EPS forecast")
    forward_revenue: Optional[float] = Field(None, description="Next 12 months consensus Revenue forecast")
    peg_ratio: Optional[float] = Field(None, description="Price / Earnings to Growth ratio")
    eps_growth_fwd_pct: Optional[float] = Field(None, description="Projected forward EPS growth rate percentage")
    revenue_growth_fwd_pct: Optional[float] = Field(None, description="Projected forward revenue growth rate percentage")
    analyst_count: Optional[int] = Field(None, description="Number of contributing sell-side analysts")
    estimate_dispersion_pct: Optional[float] = Field(
        None, description="Standard deviation / mean of estimates; higher indicates greater uncertainty"
    )
    consensus_rating: Optional[str] = Field(None, description="Consensus recommendation, e.g. 'Buy', 'Hold'")
    as_of_date: Optional[str] = Field(None, description="Date stamp of consensus snapshot")

