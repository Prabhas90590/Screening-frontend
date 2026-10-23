"""Consolidated company metrics database model.

Stores all 16 calculated metrics per company in one unified row, bridging
the raw vendor financial snapshots and the rule/ranking evaluation engine.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CompanyMetricsRecord(BaseModel):
    """Database model for 'company_metrics' table."""

    canonical_company_id: str = Field(..., description="Foreign key to companies.canonical_id")
    ticker: str = Field(..., description="Primary ticker symbol")
    as_of_date: str = Field(..., description="Date stamp of financial observations (YYYY-MM-DD)")

    # 1. Size & Liquidity
    market_cap_usd: Optional[float] = None
    price_usd: Optional[float] = None
    avg_daily_volume: Optional[float] = None
    avg_daily_traded_value: Optional[float] = None

    # 2. Valuation
    forward_pe: Optional[float] = None
    pe_vs_benchmark: Optional[float] = None  # Forward P/E vs S&P 500
    peg_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    price_to_sales: Optional[float] = None
    price_to_cash_flow: Optional[float] = None

    # 3. Growth, Leverage & Income
    revenue_growth_fwd: Optional[float] = None
    eps_growth_fwd: Optional[float] = None
    beta: Optional[float] = None
    net_debt_ebitda: Optional[float] = None
    dividend_yield: Optional[float] = None

    # 4. Raw Financial Building Blocks (from vendor response)
    revenue: Optional[float] = None
    ebitda: Optional[float] = None
    total_debt: Optional[float] = None
    cash: Optional[float] = None
    net_debt: Optional[float] = None

    # 5. Quality & Audit
    data_confidence: str = "High"  # High, Medium, Low
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

