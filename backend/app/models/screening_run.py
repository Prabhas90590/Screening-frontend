"""Screening execution run, result, and funnel progression database models."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class ScreeningRunRecord(BaseModel):
    """Database model for 'screening_runs' table."""
    run_id: str = Field(..., description="Unique execution ID, e.g. 'run-20261023-001'")
    status: Literal["queued", "running", "succeeded", "failed"] = "succeeded"
    provider: str = Field(default="mock", description="Data provider used: 'mock', 'eodhd', 'lseg'")
    rule_version_id: Optional[str] = Field(None, description="Profile ID locked to this run")
    profile_name: Optional[str] = Field(None, description="Name of profile applied")
    display_currency: str = Field(default="USD", description="Currency reported to client")
    selected_countries: List[str] = Field(default_factory=list)
    selected_exchanges: List[str] = Field(default_factory=list)
    rules_snapshot: List[Dict[str, Any]] = Field(default_factory=list, description="Frozen rules used")
    duration_ms: float = 0.0
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class FunnelCountRecord(BaseModel):
    """Database model for 'funnel_counts' table."""
    id: str = Field(..., description="Unique record ID, e.g. 'fnl-run-20261023-001'")
    run_id: str = Field(..., description="Foreign key to screening_runs.run_id")
    universe_count: int = 0
    markets_count: int = 0
    floors_count: int = 0
    gates_count: int = 0
    score_count: int = 0
    shortlist_count: int = 0
    selected_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ScreeningResultRecord(BaseModel):
    """Database model for 'screening_results' table."""
    id: str = Field(..., description="Unique row ID, e.g. 'res-run-001-comp-001'")
    run_id: str = Field(..., description="Foreign key to screening_runs.run_id")
    canonical_company_id: str = Field(..., description="Foreign key to companies.canonical_id")
    ticker: str
    company_name: str
    country: str
    exchange: str
    sector: str
    rank: int
    score: int = 0
    display_price: Optional[float] = None
    market_cap_display: Optional[float] = None
    display_currency: str = "USD"
    fwd_pe: Optional[float] = None
    peg: Optional[float] = None
    ev_ebitda: Optional[float] = None
    beta: Optional[float] = None
    nd_ebitda: Optional[str] = None
    yield_pct: Optional[float] = None
    eps_growth_pct: Optional[float] = None
    data_confidence: str = "High"
    stage_status: Literal["passed", "gate_dropped", "floor_dropped"] = "passed"
    near_miss_status: Literal["none", "rank_near_miss", "rule_near_miss"] = "none"
    score_breakdown: List[Dict[str, Any]] = Field(default_factory=list)
    metric_statuses: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
