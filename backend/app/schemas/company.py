"""Canonical company schema.

Decouples internal company representations from vendor-specific payloads,
supporting client-specified display currencies (defaulting to USD / $).
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class NormalizedCompany(BaseModel):
    """Canonical representation of an equity issuer (company)."""
    canonical_id: str = Field(..., description="Stable internal company identifier, e.g. 'comp-us-hmp'")
    name: str = Field(..., description="Legal or trade name of the company")
    ticker: str = Field(..., description="Primary ticker symbol, e.g. 'HMP'")
    country: str = Field(..., description="Country code (e.g. 'US') or country name")
    exchange: str = Field(..., description="Primary listing exchange code, e.g. 'NASDAQ'")
    sector: str = Field(..., description="Sector name, e.g. 'Energy', 'Info Tech', 'Financials'")
    industry: Optional[str] = Field(None, description="Detailed sub-industry classification")
    market_cap: float = Field(default=0.0, description="Market capitalization in USD ($)")
    market_cap_display: float = Field(default=0.0, description="Market cap converted to client's display currency")
    display_currency: str = Field(default="USD", description="Currency specified by the client for display (default '$' / 'USD')")
    currency: str = Field(default="USD", description="Original company financial reporting currency code")
    isin: Optional[str] = Field(None, description="International Securities Identification Number")
    figi: Optional[str] = Field(None, description="Financial Instrument Global Identifier")
    description: Optional[str] = Field(None, description="Business summary description")
    as_of_date: Optional[str] = Field(None, description="Data date / freshness stamp")


class CompanySearchResult(BaseModel):
    canonical_id: str
    name: str
    ticker: str
    country: str
    exchange: str
    sector: str
