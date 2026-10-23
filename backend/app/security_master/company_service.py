"""Security Master company resolution service.

Resolves incoming security records to a single canonical company legal entity,
preventing duplicate counting of dual-listed stocks (e.g. Infosys on NSE and NYSE,
Equinor in Oslo and New York, TSMC in Taipei and New York).
"""

from datetime import datetime
import logging
from typing import Dict, Optional, Tuple

from app.core.logging import DiagnosticLogger
from app.models.company import CompanyRecord
from app.repositories.company_repository import CompanyRepository, company_repository
from app.schemas.company import NormalizedCompany
from app.security_master.identity import generate_canonical_id, normalize_ticker

logger = DiagnosticLogger("sec_master")

# Cross-border ADR/Dual-listing ISIN mapping: ADR ISIN -> Domestic Primary ISIN
# Allows instant resolution of American Depositary Receipts to their home legal entity
KNOWN_ADR_TO_PRIMARY_ISIN: Dict[str, str] = {
    # Infosys: US ADR -> India Primary
    "US4567881085": "INE009A01021",
    # TSMC: US ADR -> Taiwan Primary
    "US8740391003": "TW0002330008",
    # Alibaba: US ADR -> Hong Kong Primary
    "US01609W1027": "KYG217651051",
    # SAP: US ADR -> Germany Primary
    "US8030542042": "DE0007164600",
    # Novo Nordisk: US ADR -> Denmark Primary
    "US6701002056": "DK0062498333",
    # ASML: US ADR -> Netherlands Primary
    "US00206R1023": "NL0010273215",
    # Equinor: US ADR -> Norway Primary
    "US29446M1027": "NO0010096985",
    # Shell: US ADR -> UK Primary
    "US8425871071": "GB00BP633519",
    # Toyota: US ADR -> Japan Primary
    "US8923313071": "JP3633400001",
    # BHP: US ADR -> Australia Primary
    "US0886061086": "AU000000BHP4",
}


class CompanyService:
    """Service for resolving, matching, and maintaining canonical Company entities."""

    def __init__(self, repository: CompanyRepository = company_repository):
        self.repository = repository

    def resolve_company(
        self,
        ticker: str,
        country: str,
        exchange: str,
        isin: Optional[str] = None,
        figi: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Tuple[Optional[CompanyRecord], Optional[str]]:
        """Identify if an existing canonical company entity exists in the Security Master.

        Hierarchy of resolution:
        1. FIGI (exact global instrument match)
        2. Direct ISIN (exact international identifier match)
        3. Cross-border ADR ISIN mapping (resolves ADRs to parent corporate ISIN)
        4. Ticker + Home Country match
        """
        clean_ticker = normalize_ticker(ticker)

        # 1. Match by FIGI
        if figi and figi.strip():
            existing = self.repository.get_company_by_figi(figi.strip())
            if existing:
                return existing, f"FIGI ({figi})"

        # 2. Match by direct ISIN
        if isin and isin.strip():
            clean_isin = isin.strip().upper()
            existing = self.repository.get_company_by_isin(clean_isin)
            if existing:
                return existing, f"direct ISIN ({clean_isin})"

            # 3. Match via ADR -> Primary ISIN cross-reference
            underlying_isin = KNOWN_ADR_TO_PRIMARY_ISIN.get(clean_isin)
            if underlying_isin:
                existing = self.repository.get_company_by_isin(underlying_isin)
                if existing:
                    return existing, f"ADR cross-reference ({clean_isin} -> {underlying_isin})"

        # 4. Match by primary ticker and country
        existing = self.repository.get_company_by_ticker(clean_ticker, country)
        if existing:
            return existing, f"Primary Ticker + Country ({clean_ticker}, {country})"

        return None, None

    def upsert_company_from_normalized(
        self,
        data: NormalizedCompany,
        is_bank: bool = False,
    ) -> CompanyRecord:
        """Resolve incoming normalized company data to a canonical entity and save it.

        If the company already exists under a dual-listing or secondary exchange,
        it links to the existing entity and avoids double-counting.
        """
        clean_ticker = normalize_ticker(data.ticker)

        # Attempt to resolve existing entity
        existing_company, match_reason = self.resolve_company(
            ticker=clean_ticker,
            country=data.country,
            exchange=data.exchange,
            isin=data.isin,
            figi=data.figi,
            name=data.name,
        )

        now = datetime.utcnow()

        if existing_company:
            logger.sec_master_resolve(
                clean_ticker,
                existing_company.canonical_id,
                match_reason or "security master hierarchy"
            )

            # Update financial attributes if newer or consolidated
            updated = CompanyRecord(
                canonical_id=existing_company.canonical_id,
                name=existing_company.name or data.name,
                primary_ticker=existing_company.primary_ticker,
                country=existing_company.country,
                primary_exchange=existing_company.primary_exchange,
                sector=data.sector if data.sector != "Unclassified" else existing_company.sector,
                industry=data.industry or existing_company.industry,
                market_cap=max(data.market_cap, existing_company.market_cap),
                market_cap_display=max(data.market_cap_display, existing_company.market_cap_display),
                display_currency=data.display_currency,
                currency=existing_company.currency or data.currency,
                isin=existing_company.isin or data.isin,
                figi=existing_company.figi or data.figi,
                is_bank=is_bank or existing_company.is_bank,
                description=data.description or existing_company.description,
                as_of_date=data.as_of_date or existing_company.as_of_date,
                created_at=existing_company.created_at,
                updated_at=now,
            )
            self.repository.save_company(updated)
            return updated
        else:
            # Create a brand new canonical company record
            canonical_id = data.canonical_id or generate_canonical_id(
                country_code=data.country,
                exchange_code=data.exchange,
                ticker=clean_ticker,
                isin=data.isin,
                figi=data.figi,
            )

            new_company = CompanyRecord(
                canonical_id=canonical_id,
                name=data.name,
                primary_ticker=clean_ticker,
                country=data.country,
                primary_exchange=data.exchange,
                sector=data.sector,
                industry=data.industry,
                market_cap=data.market_cap,
                market_cap_display=data.market_cap_display,
                display_currency=data.display_currency,
                currency=data.currency,
                isin=data.isin,
                figi=data.figi,
                is_bank=is_bank,
                description=data.description,
                as_of_date=data.as_of_date,
                created_at=now,
                updated_at=now,
            )
            self.repository.save_company(new_company)
            logger.sec_master_info(
                canonical_id,
                f"Created canonical entity '{data.name}' ({clean_ticker}) in {data.country}"
            )
            return new_company

    def get_company(self, canonical_id: str) -> Optional[CompanyRecord]:
        """Fetch canonical company by ID."""
        return self.repository.get_company_by_id(canonical_id)


# Global company service instance
company_service = CompanyService()

