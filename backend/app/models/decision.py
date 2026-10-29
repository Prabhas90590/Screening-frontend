"""Analyst decision and portfolio holding database models."""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class DecisionRecord(BaseModel):
    """Database model for 'decisions' table."""
    decision_id: str = Field(..., description="Unique decision ID, e.g. 'dec-comp-001'")
    canonical_company_id: str = Field(..., description="Foreign key to companies.canonical_id")
    company_name: Optional[str] = Field(default=None, description="Name of company decided on")
    profile_name: Optional[str] = Field(default=None, description="Active strategy profile name")
    decision: Literal["keep", "drop"] = Field(..., description="'keep' or 'drop'")
    decision_reason: Optional[str] = None
    decision_note: Optional[str] = None
    run_id: Optional[str] = None
    decided_by: str = "Analyst"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class HoldingRecord(BaseModel):
    """Database model for 'holdings' table."""
    holding_id: str = Field(..., description="Unique holding ID, e.g. 'hld-comp-001'")
    canonical_company_id: str = Field(..., description="Foreign key to companies.canonical_id")
    portfolio_name: str = "Core Equity Fund"
    shares: float = 0.0
    cost_basis: float = 0.0
    weight_pct: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
