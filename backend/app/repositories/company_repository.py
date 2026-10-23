"""Repository for Security Master entities (companies and listings).

Supports PostgreSQL with SQLite fallback, handling upserts, identifier index lookups,
and dual-listing queries.
"""

from datetime import datetime
import logging
from typing import Any, List, Optional

from app.db.connection import db_manager
from app.models.company import CompanyRecord
from app.models.listing import ListingRecord

logger = logging.getLogger("app.repositories.company")


class CompanyRepository:
    """SQL repository for 'companies' and 'listings' master tables."""

    def __init__(self):
        db_manager.init_tables()

    # ---------------------------------------------------------
    # COMPANY OPERATIONS
    # ---------------------------------------------------------

    def save_company(self, company: CompanyRecord) -> str:
        """Insert or update a company record in the master table."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        insert_sql = """
            INSERT INTO companies (
                canonical_id, name, primary_ticker, country, primary_exchange,
                sector, industry, market_cap, market_cap_display, display_currency,
                currency, isin, figi, is_bank, description, as_of_date, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (canonical_id) DO UPDATE SET
                name = EXCLUDED.name,
                primary_ticker = EXCLUDED.primary_ticker,
                country = EXCLUDED.country,
                primary_exchange = EXCLUDED.primary_exchange,
                sector = EXCLUDED.sector,
                industry = EXCLUDED.industry,
                market_cap = EXCLUDED.market_cap,
                market_cap_display = EXCLUDED.market_cap_display,
                display_currency = EXCLUDED.display_currency,
                currency = EXCLUDED.currency,
                isin = COALESCE(EXCLUDED.isin, companies.isin),
                figi = COALESCE(EXCLUDED.figi, companies.figi),
                is_bank = EXCLUDED.is_bank,
                description = COALESCE(EXCLUDED.description, companies.description),
                as_of_date = EXCLUDED.as_of_date,
                updated_at = EXCLUDED.updated_at;
        """ if is_postgres else """
            INSERT INTO companies (
                canonical_id, name, primary_ticker, country, primary_exchange,
                sector, industry, market_cap, market_cap_display, display_currency,
                currency, isin, figi, is_bank, description, as_of_date, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (canonical_id) DO UPDATE SET
                name = excluded.name,
                primary_ticker = excluded.primary_ticker,
                country = excluded.country,
                primary_exchange = excluded.primary_exchange,
                sector = excluded.sector,
                industry = excluded.industry,
                market_cap = excluded.market_cap,
                market_cap_display = excluded.market_cap_display,
                display_currency = excluded.display_currency,
                currency = excluded.currency,
                isin = COALESCE(excluded.isin, companies.isin),
                figi = COALESCE(excluded.figi, companies.figi),
                is_bank = excluded.is_bank,
                description = COALESCE(excluded.description, companies.description),
                as_of_date = excluded.as_of_date,
                updated_at = excluded.updated_at;
        """

        created_at_val = company.created_at if is_postgres else company.created_at.isoformat()
        updated_at_val = company.updated_at if is_postgres else company.updated_at.isoformat()
        is_bank_val = company.is_bank if is_postgres else (1 if company.is_bank else 0)

        values = (
            company.canonical_id,
            company.name,
            company.primary_ticker,
            company.country,
            company.primary_exchange,
            company.sector,
            company.industry,
            company.market_cap,
            company.market_cap_display,
            company.display_currency,
            company.currency,
            company.isin,
            company.figi,
            is_bank_val,
            company.description,
            company.as_of_date,
            created_at_val,
            updated_at_val,
        )

        try:
            cursor = conn.cursor()
            cursor.execute(insert_sql, values)
            conn.commit()
            return company.canonical_id
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save company '{company.canonical_id}': {e}")
            raise
        finally:
            conn.close()

    def get_company_by_id(self, canonical_id: str) -> Optional[CompanyRecord]:
        """Lookup company by canonical ID."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
        query = "SELECT * FROM companies WHERE canonical_id = %s" if is_postgres else "SELECT * FROM companies WHERE canonical_id = ?"

        try:
            cursor = conn.cursor()
            cursor.execute(query, (canonical_id,))
            row = cursor.fetchone()
            return self._row_to_company(row, is_postgres) if row else None
        finally:
            conn.close()

    def get_company_by_isin(self, isin: str) -> Optional[CompanyRecord]:
        """Lookup existing company by international ISIN."""
        if not isin or not isin.strip():
            return None
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
        query = "SELECT * FROM companies WHERE LOWER(isin) = LOWER(%s) LIMIT 1" if is_postgres else "SELECT * FROM companies WHERE LOWER(isin) = LOWER(?) LIMIT 1"

        try:
            cursor = conn.cursor()
            cursor.execute(query, (isin.strip(),))
            row = cursor.fetchone()
            return self._row_to_company(row, is_postgres) if row else None
        finally:
            conn.close()

    def get_company_by_figi(self, figi: str) -> Optional[CompanyRecord]:
        """Lookup existing company by global FIGI."""
        if not figi or not figi.strip():
            return None
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
        query = "SELECT * FROM companies WHERE LOWER(figi) = LOWER(%s) LIMIT 1" if is_postgres else "SELECT * FROM companies WHERE LOWER(figi) = LOWER(?) LIMIT 1"

        try:
            cursor = conn.cursor()
            cursor.execute(query, (figi.strip(),))
            row = cursor.fetchone()
            return self._row_to_company(row, is_postgres) if row else None
        finally:
            conn.close()

    def get_company_by_ticker(self, ticker: str, country: Optional[str] = None) -> Optional[CompanyRecord]:
        """Lookup company by primary ticker, optionally disambiguated by country."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        if country:
            query = (
                "SELECT * FROM companies WHERE LOWER(primary_ticker) = LOWER(%s) AND LOWER(country) = LOWER(%s) LIMIT 1"
                if is_postgres else
                "SELECT * FROM companies WHERE LOWER(primary_ticker) = LOWER(?) AND LOWER(country) = LOWER(?) LIMIT 1"
            )
            params = (ticker.strip(), country.strip())
        else:
            query = (
                "SELECT * FROM companies WHERE LOWER(primary_ticker) = LOWER(%s) LIMIT 1"
                if is_postgres else
                "SELECT * FROM companies WHERE LOWER(primary_ticker) = LOWER(?) LIMIT 1"
            )
            params = (ticker.strip(),)

        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return self._row_to_company(row, is_postgres) if row else None
        finally:
            conn.close()

    # ---------------------------------------------------------
    # LISTING OPERATIONS
    # ---------------------------------------------------------

    def save_listing(self, listing: ListingRecord) -> str:
        """Insert or update an exchange listing linked to a canonical company."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        insert_sql = """
            INSERT INTO listings (
                listing_id, canonical_company_id, ticker, exchange_id, country_id,
                currency, is_primary, is_active, ric, sedol, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (listing_id) DO UPDATE SET
                canonical_company_id = EXCLUDED.canonical_company_id,
                ticker = EXCLUDED.ticker,
                exchange_id = EXCLUDED.exchange_id,
                country_id = EXCLUDED.country_id,
                currency = EXCLUDED.currency,
                is_primary = EXCLUDED.is_primary,
                is_active = EXCLUDED.is_active,
                ric = COALESCE(EXCLUDED.ric, listings.ric),
                sedol = COALESCE(EXCLUDED.sedol, listings.sedol),
                updated_at = EXCLUDED.updated_at;
        """ if is_postgres else """
            INSERT INTO listings (
                listing_id, canonical_company_id, ticker, exchange_id, country_id,
                currency, is_primary, is_active, ric, sedol, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (listing_id) DO UPDATE SET
                canonical_company_id = excluded.canonical_company_id,
                ticker = excluded.ticker,
                exchange_id = excluded.exchange_id,
                country_id = excluded.country_id,
                currency = excluded.currency,
                is_primary = excluded.is_primary,
                is_active = excluded.is_active,
                ric = COALESCE(excluded.ric, listings.ric),
                sedol = COALESCE(excluded.sedol, listings.sedol),
                updated_at = excluded.updated_at;
        """

        created_at_val = listing.created_at if is_postgres else listing.created_at.isoformat()
        updated_at_val = listing.updated_at if is_postgres else listing.updated_at.isoformat()
        is_primary_val = listing.is_primary if is_postgres else (1 if listing.is_primary else 0)
        is_active_val = listing.is_active if is_postgres else (1 if listing.is_active else 0)

        values = (
            listing.listing_id,
            listing.canonical_company_id,
            listing.ticker,
            listing.exchange_id,
            listing.country_id,
            listing.currency,
            is_primary_val,
            is_active_val,
            listing.ric,
            listing.sedol,
            created_at_val,
            updated_at_val,
        )

        try:
            cursor = conn.cursor()
            cursor.execute(insert_sql, values)
            conn.commit()
            return listing.listing_id
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save listing '{listing.listing_id}': {e}")
            raise
        finally:
            conn.close()

    def get_listing_by_id(self, listing_id: str) -> Optional[ListingRecord]:
        """Retrieve listing by ID."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
        query = "SELECT * FROM listings WHERE listing_id = %s" if is_postgres else "SELECT * FROM listings WHERE listing_id = ?"

        try:
            cursor = conn.cursor()
            cursor.execute(query, (listing_id,))
            row = cursor.fetchone()
            return self._row_to_listing(row, is_postgres) if row else None
        finally:
            conn.close()

    def get_listing(self, exchange_id: str, ticker: str) -> Optional[ListingRecord]:
        """Lookup listing by exchange and ticker."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
        query = (
            "SELECT * FROM listings WHERE LOWER(exchange_id) = LOWER(%s) AND LOWER(ticker) = LOWER(%s) LIMIT 1"
            if is_postgres else
            "SELECT * FROM listings WHERE LOWER(exchange_id) = LOWER(?) AND LOWER(ticker) = LOWER(?) LIMIT 1"
        )

        try:
            cursor = conn.cursor()
            cursor.execute(query, (exchange_id.strip(), ticker.strip()))
            row = cursor.fetchone()
            return self._row_to_listing(row, is_postgres) if row else None
        finally:
            conn.close()

    def get_listings_by_company(self, canonical_company_id: str) -> List[ListingRecord]:
        """Get all international listings associated with a canonical company ID."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
        query = (
            "SELECT * FROM listings WHERE canonical_company_id = %s ORDER BY is_primary DESC, created_at ASC"
            if is_postgres else
            "SELECT * FROM listings WHERE canonical_company_id = ? ORDER BY is_primary DESC, created_at ASC"
        )

        try:
            cursor = conn.cursor()
            cursor.execute(query, (canonical_company_id,))
            rows = cursor.fetchall()
            return [self._row_to_listing(row, is_postgres) for row in rows]
        finally:
            conn.close()

    def list_companies(self, limit: int = 100, offset: int = 0) -> List[CompanyRecord]:
        """List companies with pagination."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
        query = (
            "SELECT * FROM companies ORDER BY market_cap DESC LIMIT %s OFFSET %s"
            if is_postgres else
            "SELECT * FROM companies ORDER BY market_cap DESC LIMIT ? OFFSET ?"
        )

        try:
            cursor = conn.cursor()
            cursor.execute(query, (limit, offset))
            rows = cursor.fetchall()
            return [self._row_to_company(row, is_postgres) for row in rows]
        finally:
            conn.close()

    def count_companies(self) -> int:
        """Count total companies stored."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM companies")
            row = cursor.fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    def count_listings(self) -> int:
        """Count total listings stored."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM listings")
            row = cursor.fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    def list_listings(self, limit: int = 100, offset: int = 0) -> List[ListingRecord]:
        """Fetch listings with pagination."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
        query = "SELECT * FROM listings ORDER BY created_at DESC LIMIT %s OFFSET %s" if is_postgres else "SELECT * FROM listings ORDER BY created_at DESC LIMIT ? OFFSET ?"

        try:
            cursor = conn.cursor()
            cursor.execute(query, (limit, offset))
            rows = cursor.fetchall()
            return [self._row_to_listing(row, is_postgres) for row in rows]
        finally:
            conn.close()

    # ---------------------------------------------------------
    # ROW PARSERS
    # ---------------------------------------------------------

    def _row_to_company(self, row: Any, is_postgres: bool) -> CompanyRecord:
        if is_postgres:
            return CompanyRecord(
                canonical_id=row[0],
                name=row[1],
                primary_ticker=row[2],
                country=row[3],
                primary_exchange=row[4],
                sector=row[5],
                industry=row[6],
                market_cap=float(row[7] or 0.0),
                market_cap_display=float(row[8] or 0.0),
                display_currency=row[9] or "USD",
                currency=row[10] or "USD",
                isin=row[11],
                figi=row[12],
                is_bank=bool(row[13]),
                description=row[14],
                as_of_date=row[15],
                created_at=row[16] if isinstance(row[16], datetime) else datetime.fromisoformat(str(row[16])),
                updated_at=row[17] if isinstance(row[17], datetime) else datetime.fromisoformat(str(row[17])),
            )
        else:
            return CompanyRecord(
                canonical_id=row["canonical_id"],
                name=row["name"],
                primary_ticker=row["primary_ticker"],
                country=row["country"],
                primary_exchange=row["primary_exchange"],
                sector=row["sector"],
                industry=row["industry"],
                market_cap=float(row["market_cap"] or 0.0),
                market_cap_display=float(row["market_cap_display"] or 0.0),
                display_currency=row["display_currency"] or "USD",
                currency=row["currency"] or "USD",
                isin=row["isin"],
                figi=row["figi"],
                is_bank=bool(row["is_bank"]),
                description=row["description"],
                as_of_date=row["as_of_date"],
                created_at=datetime.fromisoformat(str(row["created_at"])),
                updated_at=datetime.fromisoformat(str(row["updated_at"])),
            )

    def _row_to_listing(self, row: Any, is_postgres: bool) -> ListingRecord:
        if is_postgres:
            return ListingRecord(
                listing_id=row[0],
                canonical_company_id=row[1],
                ticker=row[2],
                exchange_id=row[3],
                country_id=row[4],
                currency=row[5] or "USD",
                is_primary=bool(row[6]),
                is_active=bool(row[7]),
                ric=row[8],
                sedol=row[9],
                created_at=row[10] if isinstance(row[10], datetime) else datetime.fromisoformat(str(row[10])),
                updated_at=row[11] if isinstance(row[11], datetime) else datetime.fromisoformat(str(row[11])),
            )
        else:
            return ListingRecord(
                listing_id=row["listing_id"],
                canonical_company_id=row["canonical_company_id"],
                ticker=row["ticker"],
                exchange_id=row["exchange_id"],
                country_id=row["country_id"],
                currency=row["currency"] or "USD",
                is_primary=bool(row["is_primary"]),
                is_active=bool(row["is_active"]),
                ric=row["ric"],
                sedol=row["sedol"],
                created_at=datetime.fromisoformat(str(row["created_at"])),
                updated_at=datetime.fromisoformat(str(row["updated_at"])),
            )


# Global repository instance
company_repository = CompanyRepository()

