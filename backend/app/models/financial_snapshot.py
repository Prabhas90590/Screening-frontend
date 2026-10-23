"""Financial and analyst estimate snapshot database models.

Captures point-in-time financial values and consensus estimates for each company,
preserving historical audit integrity across past screening runs.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class FinancialSnapshotRecord(BaseModel):
    """Database model for 'financial_snapshots' table."""
    id: str = Field(..., description="Unique snapshot ID, e.g. 'snap-fin-comp-001-20261023'")
    canonical_company_id: str = Field(..., description="Foreign key to companies.canonical_id")
    as_of_date: str = Field(..., description="Observation or reporting date (YYYY-MM-DD)")
    currency: str = Field(default="USD", description="Currency of reported figures")
    ebitda: Optional[float] = None
    net_debt: Optional[float] = None
    total_debt: Optional[float] = None
    cash: Optional[float] = None
    revenue: Optional[float] = None
    operating_income: Optional[float] = None
    net_income: Optional[float] = None
    free_cash_flow: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EstimateSnapshotRecord(BaseModel):
    """Database model for 'estimate_snapshots' table."""
    id: str = Field(..., description="Unique estimate ID, e.g. 'snap-est-comp-001-20261023'")
    canonical_company_id: str = Field(..., description="Foreign key to companies.canonical_id")
    as_of_date: str = Field(..., description="Observation date (YYYY-MM-DD)")
    forward_pe: Optional[float] = None
    peg_ratio: Optional[float] = None
    eps_growth_fwd: Optional[float] = None
    analyst_count: Optional[int] = None
    target_price: Optional[float] = None
    recommendation_mean: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

