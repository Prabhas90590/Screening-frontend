"""Company entity database model for the Security Master.

Represents a single unique legal corporate entity, regardless of how many
international exchanges or currencies it trades on (e.g., Infosys trades on
NSE in INR and NYSE as an ADR in USD, but is one legal company).
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CompanyRecord(BaseModel):
    """Database model for the 'companies' master table."""

    canonical_id: str = Field(..., description="Deterministic global entity ID (e.g. 'comp-isin-ine009a01021')")
    name: str = Field(..., description="Official legal name of the company")
    primary_ticker: str = Field(..., description="Primary trading symbol (e.g. 'INFY')")
    country: str = Field(..., description="Primary home country code (e.g. 'IN')")
    primary_exchange: str = Field(..., description="Primary stock exchange code (e.g. 'NSE')")
    sector: str = Field(default="Unclassified", description="GICS or equivalent sector")
    industry: Optional[str] = Field(None, description="Detailed sub-industry classification")
    market_cap: float = Field(default=0.0, description="Consolidated market capitalization in USD ($)")
    market_cap_display: float = Field(default=0.0, description="Consolidated market cap converted to user's display currency")
    display_currency: str = Field(default="USD", description="Currency specified for display (default 'USD' / '$')")
    currency: str = Field(default="USD", description="Original company financial reporting currency code")
    isin: Optional[str] = Field(None, description="International Securities Identification Number")
    figi: Optional[str] = Field(None, description="Financial Instrument Global Identifier")
    is_bank: bool = Field(default=False, description="Flag for banks/financials where debt metrics are handled differently")
    description: Optional[str] = Field(None, description="Business summary description")
    as_of_date: Optional[str] = Field(None, description="Data date / freshness stamp")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Record creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
