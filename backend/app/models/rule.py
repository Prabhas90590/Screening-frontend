"""Versioned rule and profile database models.

Allows screening rule sets to be versioned, edited, and permanently archived
without altering historical screening run outcomes.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RuleRecord(BaseModel):
    """Database model for 'rules' table."""
    rule_id: str = Field(..., description="Unique rule ID, e.g. 'rule-pe-v1'")
    version_id: str = Field(..., description="Foreign key to rule_versions.version_id")
    metric_name: str = Field(..., description="Metric key, e.g. 'forward_pe', 'net_debt_ebitda'")
    label: str = Field(..., description="Human display label")
    category: str = Field(default="Valuation", description="Category: Valuation, Growth, Quality, etc.")
    condition: str = Field(default=">=", description="Operator: >=, <=, =, <, >")
    threshold_value: float = Field(..., description="Numeric comparison threshold")
    threshold_display: str = Field(default="", description="Display text, e.g. '3.0x' or '$500M'")
    mode: str = Field(default="Both", description="Mode: 'Off', 'Req.', 'Score', 'Both'")
    weight: float = Field(default=0.0, description="Weight percentage in scoring engine (0-100)")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RuleVersionRecord(BaseModel):
    """Database model for 'rule_versions' table."""
    version_id: str = Field(..., description="Unique profile version ID, e.g. 'prof-conservative-v1'")
    profile_name: str = Field(..., description="Strategy name, e.g. 'Conservative Value'")
    version_number: str = Field(default="1.0", description="Semantic or revision version string")
    is_active: bool = Field(default=True, description="True if currently active screening profile")
    description: Optional[str] = Field(None, description="Profile description or thesis")
    sector_limits: Dict[str, float] = Field(default_factory=dict, description="Sector debt limits")
    diversification_rules: Dict[str, Any] = Field(default_factory=dict, description="Cap rules")
    rules: List[RuleRecord] = Field(default_factory=list, description="Rules inside this profile")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
