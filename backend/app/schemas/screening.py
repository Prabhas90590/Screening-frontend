"""Screening request, result, and run execution schemas.

Connects frontend screening actions to the backend screening pipeline,
supporting client-specified display currencies (defaulting to USD / $).
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class MetricScoreBreakdownItem(BaseModel):
    """Explains a single metric's contribution to the total company score."""
    name: str = Field(..., description="Metric display name, e.g. 'Forward P/E'")
    score: float = Field(..., description="Points awarded")
    max_score: float = Field(..., description="Maximum possible points for this metric")
    value_display: str = Field(..., description="Formatted actual value, e.g. '$10.4' or '3.4x'")
    benchmark_display: str = Field(default="", description="Benchmark target or constraint, e.g. 'vs S&P 22.5'")
    percentage: float = Field(..., description="Score ratio 0-100")
    status: Literal["full", "threshold", "miss", "off", "exempt"] = Field(
        default="full", description="Pass/threshold/miss/exempt status"
    )


class ScreenedSecurityResult(BaseModel):
    """Complete screened output row returned to the frontend."""
    id: str = Field(..., description="Frontend security key / canonical ID")
    rank: int = Field(..., description="Relative rank from 1..N")
    name: str
    ticker: str
    country: str
    exchange: str
    sector: str
    market_cap_category: str = Field(default="Mid-cap Value")
    score: int = Field(..., description="Aggregate score 0-100")
    display_currency: str = Field(default="USD", description="Currency applied to prices and financial figures")
    display_price: Optional[float] = None
    market_cap_display: Optional[float] = None
    fwd_pe: Optional[float] = None
    peg: Optional[float] = None
    ev_ebitda: Optional[float] = None
    beta: Optional[float] = None
    nd_ebitda: Optional[str] = None  # e.g. '3.4x' or 'net cash'
    yield_pct: Optional[float] = None
    eps_growth_pct: Optional[float] = None
    pe_vs_benchmark: Optional[float] = None
    price_to_sales: Optional[float] = None
    price_to_cash_flow: Optional[float] = None
    revenue_growth_fwd: Optional[float] = None
    avg_daily_volume: Optional[float] = None
    avg_daily_traded_value: Optional[float] = None
    data_confidence: Literal["High", "Medium", "Low"] = "High"
    decision: Optional[Literal["keep", "drop"]] = None
    decision_reason: Optional[str] = None
    decision_note: Optional[str] = None
    metric_statuses: Dict[str, str] = Field(default_factory=dict)
    score_breakdown: List[MetricScoreBreakdownItem] = Field(default_factory=list)
    confidence_details: Dict[str, Any] = Field(default_factory=dict)
    rank_history: List[str] = Field(default_factory=list)


class FunnelStageCounts(BaseModel):
    """Audit funnel progression tracking attrition across screening stages."""
    universe: int = Field(..., description="Total universe count across all markets")
    markets: int = Field(..., description="Count in selected countries/exchanges")
    floors: int = Field(..., description="Count surviving market cap/liquidity floors")
    gates: int = Field(..., description="Count passing strict required gates")
    score: int = Field(..., description="Count evaluated by scoring engine")
    shortlist: int = Field(..., description="Count in top scoring tier")
    selected: int = Field(..., description="Count in final selected list (e.g. Top 20/50)")


class ScreeningRunRequest(BaseModel):
    """Payload to trigger a screening run for selected markets and rules."""
    countries: List[str] = Field(..., description="List of country IDs, e.g. ['us', 'ca', 'in']")
    exchanges: List[str] = Field(..., description="List of exchange IDs, e.g. ['nasdaq', 'nyse', 'nse']")
    display_currency: str = Field(
        default="USD",
        description="Client-selected reporting currency for all values and market caps (default: '$' / 'USD')"
    )
    rule_version_id: Optional[str] = Field(None, description="Profile version reference")
    profile_name: Optional[str] = Field(None, description="Active profile name")
    rules_config: Optional[List[Dict[str, Any]]] = Field(None, description="Active rule overrides")
    sector_limits: Optional[Dict[str, float]] = Field(None, description="Sector debt limit overrides")


class ScreeningRunResponse(BaseModel):
    """Response returned upon initiating or completing a screening run."""
    run_id: str
    status: Literal["queued", "running", "succeeded", "failed"] = "succeeded"
    display_currency: str = Field(default="USD", description="Currency used for all reported values")
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0
    provider_used: str = "mock"
    funnel: FunnelStageCounts
    results_count: int = 0
    top_results: List[ScreenedSecurityResult] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
