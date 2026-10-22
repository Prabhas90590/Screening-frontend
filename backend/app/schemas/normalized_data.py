"""Composite normalized data container for a security.

Aggregates company identity, listing details, prices, fundamentals, estimates,
and data quality confidence into a unified entity ready for the metrics and rules engines.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from app.schemas.company import NormalizedCompany
from app.schemas.listing import NormalizedListing
from app.schemas.price import NormalizedPrice
from app.schemas.financials import NormalizedFinancials
from app.schemas.estimates import NormalizedEstimates


DataConfidenceLevel = Literal["High", "Medium", "Low"]


class ConfidenceDetails(BaseModel):
    """Detailed transparency notes regarding estimate spread and data freshness."""
    estimate_note: Optional[str] = Field(None, description="Note on estimate dispersion or provider consensus")
    freshness_note: Optional[str] = Field(None, description="Fundamentals reporting date and price close date")
    missing_fields: List[str] = Field(default_factory=list, description="Fields absent in the vendor payload")


class NormalizedSecurityData(BaseModel):
    """Unified canonical representation of a security across all data dimensions."""
    canonical_id: str = Field(..., description="Stable internal security identifier")
    company: NormalizedCompany
    listing: NormalizedListing
    price: NormalizedPrice
    financials: NormalizedFinancials
    estimates: NormalizedEstimates
    data_confidence: DataConfidenceLevel = Field(
        default="High", description="Quality confidence grade based on completeness & freshness"
    )
    confidence_details: ConfidenceDetails = Field(
        default_factory=ConfidenceDetails, description="Human-readable confidence disclosures"
    )
    raw_payload_ref: Optional[str] = Field(None, description="Reference to raw response store ID")

