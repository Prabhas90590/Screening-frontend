"""Security Master listing service.

Manages international exchange listings, connecting tickers and exchanges
to their canonical parent company entity in PostgreSQL.
"""

from datetime import datetime
import logging
from typing import List, Optional

from app.core.logging import DiagnosticLogger
from app.models.listing import ListingRecord
from app.repositories.company_repository import CompanyRepository, company_repository
from app.schemas.listing import NormalizedListing
from app.security_master.identity import generate_listing_id, normalize_ticker

logger = DiagnosticLogger("sec_master")


class ListingService:
    """Service for managing exchange listings and dual-listing links."""

    def __init__(self, repository: CompanyRepository = company_repository):
        self.repository = repository

    def register_listing(
        self,
        listing_data: NormalizedListing,
        canonical_company_id: str,
        is_home_country: bool = True,
    ) -> ListingRecord:
        """Register or update an exchange listing linked to a canonical company ID.

        Automatically determines if this listing is primary or secondary based on
        existing listings already associated with this company.
        """
        clean_ticker = normalize_ticker(listing_data.ticker)
        listing_id = listing_data.listing_id or generate_listing_id(
            listing_data.exchange_id,
            clean_ticker
        )

        existing_listings = self.repository.get_listings_by_company(canonical_company_id)
        has_primary = any(l.is_primary for l in existing_listings if l.listing_id != listing_id)

        # If company already has a primary listing, subsequent cross-listings/ADRs are secondary
        is_primary = listing_data.is_primary if not has_primary else False

        now = datetime.utcnow()

        listing_record = ListingRecord(
            listing_id=listing_id,
            canonical_company_id=canonical_company_id,
            ticker=clean_ticker,
            exchange_id=listing_data.exchange_id.lower(),
            country_id=listing_data.country_id.lower(),
            currency=listing_data.currency.upper(),
            is_primary=is_primary,
            is_active=listing_data.is_active,
            ric=listing_data.ric,
            sedol=listing_data.sedol,
            created_at=now,
            updated_at=now,
        )

        self.repository.save_listing(listing_record)

        logger.sec_master_info(
            canonical_company_id,
            f"Linked listing '{listing_id}' ({clean_ticker}.{listing_data.exchange_id.upper()}) "
            f"[Primary={is_primary}]"
        )

        return listing_record

    def get_listings_for_company(self, canonical_company_id: str) -> List[ListingRecord]:
        """Fetch all exchange listings (primary + cross-listings/ADRs) for a company."""
        return self.repository.get_listings_by_company(canonical_company_id)

    def get_listing(self, exchange_id: str, ticker: str) -> Optional[ListingRecord]:
        """Retrieve a listing record by exchange and ticker."""
        clean_ticker = normalize_ticker(ticker)
        return self.repository.get_listing(exchange_id, clean_ticker)


# Global listing service instance
listing_service = ListingService()

