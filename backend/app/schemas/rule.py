"""Rule catalog, profile, and metric evaluation schemas.

Defines schemas for managing versioned screening profiles, individual metric criteria,
and the catalog specification of all 16 standard screening metrics.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator


# Institutional catalog boundary limits (min, max) for threshold values
CATALOG_BOUNDS = {
    "market_cap": (50_000_000.0, 4_000_000_000_000.0),
    "price_usd": (0.50, 5_000.0),
    "avg_volume": (10_000.0, 500_000_000.0),
    "avg_traded_value": (50_000.0, 5_000_000_000.0),
    "forward_pe": (1.0, 150.0),
    "pe_vs_benchmark": (-30.0, 60.0),
    "peg": (0.1, 5.0),
    "ev_ebitda": (1.0, 60.0),
    "price_to_sales": (0.1, 30.0),
    "price_to_cash_flow": (1.0, 50.0),
    "net_debt_ebitda": (-5.0, 15.0),
    "beta": (0.2, 3.0),
    "eps_growth_fwd": (-20.0, 100.0),
    "revenue_growth_fwd": (-15.0, 80.0),
    "dividend_yield": (0.0, 20.0),
    "data_confidence": (1.0, 3.0),
}


class RuleMetricItem(BaseModel):
    """Individual rule metric item inside a profile."""
    id: str = Field(..., description="Unique metric key, e.g. 'forward_pe', 'net_debt_ebitda'")
    name: str = Field(..., description="Display label, e.g. 'Forward P/E'")
    category: str = Field(default="Valuation", description="Category: Size, Valuation, Growth, Leverage, etc.")
    mode: Literal["Off", "Req.", "Score", "Both"] = Field(default="Both", description="Mode: Off, Req. (Gate), Score, Both")
    condition: str = Field(default=">=", description="Operator: >=, <=, =, <, >")
    value: float = Field(default=0.0, description="Numeric threshold")
    value_display: str = Field(default="", description="Display formatted string, e.g. '<= 25.0x'")
    weight: float = Field(default=0.0, ge=0.0, le=100.0, description="Weight percentage in scoring engine (0-100)")

    @model_validator(mode="after")
    def validate_modes_weights_and_bounds(self) -> "RuleMetricItem":
        """Input validation ensuring modes, weights, and values adhere to institutional screening rules."""
        # 1. Enforce mode vs weight constraints
        if self.mode in ("Off", "Req."):
            # Gates and Off rules NEVER distribute score points
            self.weight = 0.0
        elif self.mode in ("Score", "Both"):
            # Scoring rules must have a positive weight; if 0, assign a sensible default (10.0%)
            if self.weight <= 0.0:
                self.weight = 10.0

        # 2. Validate value bounds if metric is recognized in catalog
        metric_key = self.id.lower().replace("-", "_")
        for key, (min_lim, max_lim) in CATALOG_BOUNDS.items():
            if key in metric_key:
                if self.mode != "Off":
                    if self.value < min_lim or self.value > max_lim:
                        raise ValueError(
                            f"Rule '{self.name}' ({self.id}): value {self.value} is outside valid "
                            f"institutional limits ({min_lim} to {max_lim})"
                        )
                break

        return self


class RuleProfileSchema(BaseModel):
    """Complete rule profile configuration returned to the frontend."""
    version_id: str
    profile_name: str
    version_number: str = "1.0"
    is_active: bool = True
    description: Optional[str] = None
    sector_limits: Dict[str, float] = Field(default_factory=dict)
    diversification_rules: Dict[str, Any] = Field(default_factory=dict)
    changes: List[str] = Field(default_factory=list, description="Comparison diff from previous version")
    selected_countries: List[str] = Field(default_factory=list, description="Selected country names")
    rules: List[RuleMetricItem] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreateProfileRequest(BaseModel):
    """Request payload to create a new rule strategy profile."""
    profile_name: str = Field(..., min_length=1, max_length=128, description="Strategy name, e.g. 'Tech Growth v1'")
    version_number: str = Field(default="1.0", max_length=16)
    description: Optional[str] = Field(None, max_length=500)
    is_active: bool = Field(default=False)
    sector_limits: Dict[str, float] = Field(default_factory=dict)
    diversification_rules: Dict[str, Any] = Field(default_factory=dict)
    changes: List[str] = Field(default_factory=list, description="Comparison diff from previous version")
    selected_countries: List[str] = Field(default_factory=list, description="Selected country names")
    rules: List[RuleMetricItem] = Field(default_factory=list)


class UpdateProfileRequest(BaseModel):
    """Request payload to update an existing rule strategy profile."""
    profile_name: Optional[str] = None
    description: Optional[str] = None
    sector_limits: Optional[Dict[str, float]] = None
    diversification_rules: Optional[Dict[str, Any]] = None
    changes: Optional[List[str]] = None
    selected_countries: Optional[List[str]] = None
    rules: Optional[List[RuleMetricItem]] = None


class MetricCatalogSpecification(BaseModel):
    """Specification of a metric in the rule catalog, including realistic limits."""
    id: str
    name: str
    category: str
    value_type: str  # "Currency", "Ratio", "Percentage", "Integer", "Category"
    unit: str  # "$", "x", "%", "shares"
    min_limit: float
    max_limit: float
    default_condition: str
    default_value: float
    default_display: str
    default_weight: float
    description: str


# 16 Standard Screening Metrics Catalog
STANDARD_RULE_CATALOG: List[MetricCatalogSpecification] = [
    MetricCatalogSpecification(
        id="market_cap",
        name="Market cap (USD)",
        category="Size & liquidity",
        value_type="Currency",
        unit="$ USD",
        min_limit=50_000_000,
        max_limit=4_000_000_000_000,
        default_condition=">=",
        default_value=500_000_000,
        default_display=">= $500M",
        default_weight=0.0,
        description="Consolidated company market capitalization in USD",
    ),
    MetricCatalogSpecification(
        id="price_usd",
        name="Price (USD-equiv.)",
        category="Size & liquidity",
        value_type="Currency",
        unit="$ USD",
        min_limit=0.50,
        max_limit=5_000.0,
        default_condition=">=",
        default_value=5.0,
        default_display=">= $5.00",
        default_weight=0.0,
        description="Share price converted dynamically to USD",
    ),
    MetricCatalogSpecification(
        id="avg_volume",
        name="Avg daily volume (shares)",
        category="Size & liquidity",
        value_type="Integer",
        unit="shares",
        min_limit=10_000,
        max_limit=500_000_000,
        default_condition=">=",
        default_value=100_000,
        default_display=">= 100K",
        default_weight=0.0,
        description="30-day average daily share volume",
    ),
    MetricCatalogSpecification(
        id="avg_traded_value",
        name="Avg daily traded value (USD)",
        category="Size & liquidity",
        value_type="Currency",
        unit="$ USD",
        min_limit=50_000,
        max_limit=5_000_000_000,
        default_condition=">=",
        default_value=1_000_000,
        default_display=">= $1M",
        default_weight=0.0,
        description="30-day average daily traded turnover in USD",
    ),
    MetricCatalogSpecification(
        id="forward_pe",
        name="Forward P/E",
        category="Valuation",
        value_type="Ratio",
        unit="x",
        min_limit=1.0,
        max_limit=150.0,
        default_condition="<=",
        default_value=25.0,
        default_display="<= 25.0x",
        default_weight=15.0,
        description="Consensus Forward Price-to-Earnings multiple",
    ),
    MetricCatalogSpecification(
        id="pe_vs_benchmark",
        name="Forward P/E vs S&P 500",
        category="Valuation",
        value_type="Ratio",
        unit="x",
        min_limit=-30.0,
        max_limit=60.0,
        default_condition="<=",
        default_value=0.0,
        default_display="<= 0.0x",
        default_weight=10.0,
        description="P/E spread relative to S&P 500 benchmark (22.5x)",
    ),
    MetricCatalogSpecification(
        id="peg",
        name="PEG",
        category="Valuation",
        value_type="Ratio",
        unit="x",
        min_limit=0.1,
        max_limit=5.0,
        default_condition="<=",
        default_value=1.5,
        default_display="<= 1.5x",
        default_weight=10.0,
        description="Forward P/E divided by expected EPS growth rate",
    ),
    MetricCatalogSpecification(
        id="ev_ebitda",
        name="EV / EBITDA",
        category="Valuation",
        value_type="Ratio",
        unit="x",
        min_limit=1.0,
        max_limit=60.0,
        default_condition="<=",
        default_value=15.0,
        default_display="<= 15.0x",
        default_weight=15.0,
        description="Enterprise Value over trailing/forward EBITDA",
    ),
    MetricCatalogSpecification(
        id="price_to_sales",
        name="Price / sales",
        category="Valuation",
        value_type="Ratio",
        unit="x",
        min_limit=0.1,
        max_limit=30.0,
        default_condition="<=",
        default_value=5.0,
        default_display="<= 5.0x",
        default_weight=5.0,
        description="Market capitalization over total revenue",
    ),
    MetricCatalogSpecification(
        id="price_to_cash_flow",
        name="Price / cash flow",
        category="Valuation",
        value_type="Ratio",
        unit="x",
        min_limit=1.0,
        max_limit=50.0,
        default_condition="<=",
        default_value=15.0,
        default_display="<= 15.0x",
        default_weight=5.0,
        description="Market cap over operating cash flow",
    ),
    MetricCatalogSpecification(
        id="net_debt_ebitda",
        name="Net debt / EBITDA",
        category="Risk & leverage",
        value_type="Ratio",
        unit="x",
        min_limit=-5.0,
        max_limit=15.0,
        default_condition="<=",
        default_value=3.0,
        default_display="<= 3.0x",
        default_weight=15.0,
        description="Total debt minus cash over EBITDA (bypassed for banks)",
    ),
    MetricCatalogSpecification(
        id="beta",
        name="Beta",
        category="Risk & leverage",
        value_type="Volatility",
        unit="x",
        min_limit=0.2,
        max_limit=3.0,
        default_condition="<=",
        default_value=1.2,
        default_display="<= 1.2x",
        default_weight=5.0,
        description="3-year monthly covariance beta vs market",
    ),
    MetricCatalogSpecification(
        id="eps_growth_fwd",
        name="EPS growth (5y, fwd)",
        category="Growth",
        value_type="Percentage",
        unit="%",
        min_limit=-20.0,
        max_limit=100.0,
        default_condition=">=",
        default_value=10.0,
        default_display=">= 10.0%",
        default_weight=10.0,
        description="Analyst projected 3-5 year annualized EPS growth",
    ),
    MetricCatalogSpecification(
        id="revenue_growth_fwd",
        name="Revenue growth (5y, fwd)",
        category="Growth",
        value_type="Percentage",
        unit="%",
        min_limit=-15.0,
        max_limit=80.0,
        default_condition=">=",
        default_value=8.0,
        default_display=">= 8.0%",
        default_weight=5.0,
        description="Projected annualized sales growth",
    ),
    MetricCatalogSpecification(
        id="dividend_yield",
        name="Dividend yield",
        category="Income",
        value_type="Percentage",
        unit="%",
        min_limit=0.0,
        max_limit=20.0,
        default_condition=">=",
        default_value=2.0,
        default_display=">= 2.0%",
        default_weight=5.0,
        description="Annual indicated dividend over share price",
    ),
    MetricCatalogSpecification(
        id="data_confidence",
        name="Data confidence",
        category="Quality",
        value_type="Category",
        unit="rating",
        min_limit=1.0,
        max_limit=3.0,
        default_condition="=",
        default_value=3.0,
        default_display="High",
        default_weight=0.0,
        description="Vendor data completeness rating (High, Medium, Low)",
    ),
]
