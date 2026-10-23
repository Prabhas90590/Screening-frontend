"""Verification script for Phase 6 Security Master.

Demonstrates:
1. Automated schema creation for 'companies' and 'listings' tables in PostgreSQL.
2. Ingesting primary domestic securities and secondary ADR/dual-listings.
3. De-duplication and resolution ensuring dual-listings map to ONE legal entity.
4. Database querying and diagnostic log verification.
"""

from datetime import datetime, timezone
from pathlib import Path
import sys

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.logging import configure_logging
from app.db.connection import db_manager
from app.models.company import CompanyRecord
from app.repositories.company_repository import company_repository
from app.schemas.company import NormalizedCompany
from app.schemas.listing import NormalizedListing
from app.security_master.company_service import company_service
from app.security_master.listing_service import listing_service


def main():
    configure_logging(debug=True)
    print("=" * 70)
    print("PHASE 6: SECURITY MASTER & DUAL-LISTING RESOLUTION VERIFICATION")
    print("=" * 70)

    # 1. Initialize tables in PostgreSQL
    print("\n1. Initializing Security Master database tables (companies, listings)...")
    db_manager.init_tables()

    # 2. Test Case 1: Primary Listing for Infosys (NSE India, INR)
    print("\n2. Ingesting Primary Listing: Infosys Ltd on NSE (India)...")
    infy_primary_company = NormalizedCompany(
        canonical_id="comp-isin-ine009a01021",
        name="Infosys Limited",
        ticker="INFY",
        country="IN",
        exchange="NSE",
        sector="Information Technology",
        industry="IT Services & Consulting",
        market_cap=77500000000.0,  # $77.5B USD
        market_cap_display=77500000000.0,
        display_currency="USD",
        currency="INR",
        isin="INE009A01021",
        as_of_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    )
    saved_infy = company_service.upsert_company_from_normalized(infy_primary_company)
    print(f"   -> Canonical Company ID: {saved_infy.canonical_id}")
    print(f"   -> Name:                 {saved_infy.name}")
    print(f"   -> Primary Exchange:     {saved_infy.primary_exchange}")

    # Register NSE listing
    infy_nse_listing = NormalizedListing(
        listing_id="list-nse-infy",
        canonical_company_id=saved_infy.canonical_id,
        ticker="INFY",
        exchange_id="nse",
        country_id="in",
        currency="INR",
        is_primary=True,
    )
    listing_service.register_listing(infy_nse_listing, saved_infy.canonical_id)
    print("   -> Registered NSE Listing: list-nse-infy (Primary=True, Currency=INR)")

    # 3. Test Case 2: Cross-Listing / ADR for Infosys (NYSE, USD)
    print("\n3. Ingesting Cross-Listing: Infosys ADR on NYSE (United States)...")
    infy_adr_company = NormalizedCompany(
        canonical_id="comp-us-nyse-infy",  # Secondary identifier provided by vendor
        name="Infosys Limited ADR",
        ticker="INFY",
        country="US",
        exchange="NYSE",
        sector="Information Technology",
        market_cap=77500000000.0,
        display_currency="USD",
        currency="USD",
        isin="US4567881085",  # US ADR ISIN (maps to INE009A01021)
        as_of_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    )
    resolved_infy_adr = company_service.upsert_company_from_normalized(infy_adr_company)
    print(f"   -> Resolved to Canonical ID: {resolved_infy_adr.canonical_id}")

    # Register NYSE listing
    infy_nyse_listing = NormalizedListing(
        listing_id="list-nyse-infy",
        canonical_company_id=resolved_infy_adr.canonical_id,
        ticker="INFY",
        exchange_id="nyse",
        country_id="us",
        currency="USD",
        is_primary=False,
    )
    listing_service.register_listing(infy_nyse_listing, resolved_infy_adr.canonical_id)
    print("   -> Registered NYSE Listing: list-nyse-infy (Primary=False, Currency=USD)")

    # Assert that both resolved to the same entity
    assert saved_infy.canonical_id == resolved_infy_adr.canonical_id, (
        "Dual-listing resolution failed: IDs do not match!"
    )
    print("   [PASS] Both listings correctly resolved to the SAME legal entity without double-counting!")

    # 4. Test Case 3: Equinor ASA (Oslo Børs, NOK) + NYSE ADR (USD)
    print("\n4. Ingesting Dual-Listed Equinor ASA (OSE Norway + NYSE US)...")
    eqnr_primary = NormalizedCompany(
        canonical_id="comp-isin-no0010096985",
        name="Equinor ASA",
        ticker="EQNR",
        country="NO",
        exchange="OSE",
        sector="Energy",
        market_cap=82000000000.0,
        currency="NOK",
        isin="NO0010096985",
        as_of_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    )
    saved_eqnr = company_service.upsert_company_from_normalized(eqnr_primary)
    listing_service.register_listing(
        NormalizedListing(
            listing_id="list-ose-eqnr",
            canonical_company_id=saved_eqnr.canonical_id,
            ticker="EQNR",
            exchange_id="ose",
            country_id="no",
            currency="NOK",
            is_primary=True,
        ),
        saved_eqnr.canonical_id,
    )

    eqnr_adr = NormalizedCompany(
        canonical_id="comp-us-nyse-eqnr",
        name="Equinor ASA ADR",
        ticker="EQNR",
        country="US",
        exchange="NYSE",
        sector="Energy",
        market_cap=82000000000.0,
        currency="USD",
        isin="US29446M1027",  # ADR ISIN
    )
    resolved_eqnr_adr = company_service.upsert_company_from_normalized(eqnr_adr)
    listing_service.register_listing(
        NormalizedListing(
            listing_id="list-nyse-eqnr",
            canonical_company_id=resolved_eqnr_adr.canonical_id,
            ticker="EQNR",
            exchange_id="nyse",
            country_id="us",
            currency="USD",
            is_primary=False,
        ),
        resolved_eqnr_adr.canonical_id,
    )
    assert saved_eqnr.canonical_id == resolved_eqnr_adr.canonical_id
    print("   [PASS] Equinor ASA OSE + NYSE ADR resolved to ONE legal entity!")

    # 5. Database Verification
    print("\n5. Verifying Database Records in PostgreSQL...")
    total_companies = company_repository.count_companies()
    total_listings = company_repository.count_listings()
    print(f"   -> Total Canonical Companies: {total_companies}")
    print(f"   -> Total Exchange Listings:   {total_listings}")

    # Inspect all listings for Infosys
    infy_listings = listing_service.get_listings_for_company(saved_infy.canonical_id)
    print(f"\n   Listings linked to Infosys ({saved_infy.canonical_id}):")
    for l in infy_listings:
        print(f"     * Listing: {l.listing_id} | Exchange: {l.exchange_id.upper()} | Currency: {l.currency} | Primary: {l.is_primary}")

    print("\n" + "=" * 70)
    print("PHASE 6 VERIFICATION COMPLETE: ALL CHECKS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()
