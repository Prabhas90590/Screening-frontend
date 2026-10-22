"""Canonical listing schema.

Represents a security's listing on a specific stock exchange.
"""

from typing import Optional
from pydantic import BaseModel, Field


class NormalizedListing(BaseModel):
    """Canonical listing record linking a ticker on an exchange to a canonical company."""
    listing_id: str = Field(..., description="Unique listing identifier, e.g. 'list-us-nasdaq-hmp'")
    canonical_company_id: str = Field(..., description="Foreign key to NormalizedCompany.canonical_id")
    ticker: str = Field(..., description="Exchange trading symbol, e.g. 'HMP' or '6501-TO'")
    exchange_id: str = Field(..., description="Exchange identifier, e.g. 'nasdaq', 'tse'")
    country_id: str = Field(..., description="Country identifier, e.g. 'us', 'jp'")
    currency: str = Field(default="USD", description="Quotation currency, e.g. 'USD', 'JPY'")
    is_primary: bool = Field(default=True, description="True if primary listing")
    is_active: bool = Field(default=True, description="True if actively trading")
    ric: Optional[str] = Field(None, description="Reuters Instrument Code (if provided by LSEG)")
    sedol: Optional[str] = Field(None, description="SEDOL identifier (if provided)")

