"""Listing entity database model for the Security Master.

Represents an individual exchange-traded instrument (primary shares, dual-listings,
or ADRs) linked directly to a master company entity in the 'companies' table.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ListingRecord(BaseModel):
    """Database model for the 'listings' table."""

    listing_id: str = Field(..., description="Unique listing identifier, e.g. 'list-nse-infy' or 'list-nyse-infy'")
    canonical_company_id: str = Field(..., description="Foreign key to CompanyRecord.canonical_id")
    ticker: str = Field(..., description="Local exchange ticker symbol")
    exchange_id: str = Field(..., description="Normalized exchange identifier (e.g. 'nse', 'nyse')")
    country_id: str = Field(..., description="Country identifier (e.g. 'in', 'us')")
    currency: str = Field(default="USD", description="Quotation currency (e.g. 'INR', 'USD')")
    is_primary: bool = Field(default=True, description="True if primary domestic listing, False for ADRs/cross-listings")
    is_active: bool = Field(default=True, description="True if currently active and trading")
    ric: Optional[str] = Field(None, description="Reuters Instrument Code (if provided by LSEG)")
    sedol: Optional[str] = Field(None, description="SEDOL identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Record creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

