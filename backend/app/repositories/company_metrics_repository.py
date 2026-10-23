"""Repository for 'company_metrics' table in PostgreSQL (with SQLite fallback).

Stores all 16 calculated metrics alongside core raw financial building blocks
(revenue, ebitda, total debt, cash, net debt) company-wise for immediate
rule evaluation and filtering.
"""

from datetime import datetime
import logging
from typing import Any, List, Optional

from app.db.connection import db_manager
from app.models.company_metrics import CompanyMetricsRecord

logger = logging.getLogger("app.repositories.company_metrics")


class CompanyMetricsRepository:
    """SQL repository for 'company_metrics' table."""

    def __init__(self):
        db_manager.init_tables()

    def save_metrics(self, record: CompanyMetricsRecord) -> str:
        """Insert or update a company's metrics record."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        insert_sql = """
            INSERT INTO company_metrics (
                canonical_company_id, ticker, as_of_date,
                market_cap_usd, price_usd, avg_daily_volume, avg_daily_traded_value,
                forward_pe, pe_vs_benchmark, peg_ratio, ev_ebitda, price_to_sales, price_to_cash_flow,
                revenue_growth_fwd, eps_growth_fwd, beta, net_debt_ebitda, dividend_yield,
                revenue, ebitda, total_debt, cash, net_debt,
                data_confidence, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (canonical_company_id) DO UPDATE SET
                ticker = EXCLUDED.ticker,
                as_of_date = EXCLUDED.as_of_date,
                market_cap_usd = EXCLUDED.market_cap_usd,
                price_usd = EXCLUDED.price_usd,
                avg_daily_volume = EXCLUDED.avg_daily_volume,
                avg_daily_traded_value = EXCLUDED.avg_daily_traded_value,
                forward_pe = EXCLUDED.forward_pe,
                pe_vs_benchmark = EXCLUDED.pe_vs_benchmark,
                peg_ratio = EXCLUDED.peg_ratio,
                ev_ebitda = EXCLUDED.ev_ebitda,
                price_to_sales = EXCLUDED.price_to_sales,
                price_to_cash_flow = EXCLUDED.price_to_cash_flow,
                revenue_growth_fwd = EXCLUDED.revenue_growth_fwd,
                eps_growth_fwd = EXCLUDED.eps_growth_fwd,
                beta = EXCLUDED.beta,
                net_debt_ebitda = EXCLUDED.net_debt_ebitda,
                dividend_yield = EXCLUDED.dividend_yield,
                revenue = EXCLUDED.revenue,
                ebitda = EXCLUDED.ebitda,
                total_debt = EXCLUDED.total_debt,
                cash = EXCLUDED.cash,
                net_debt = EXCLUDED.net_debt,
                data_confidence = EXCLUDED.data_confidence,
                updated_at = EXCLUDED.updated_at;
        """ if is_postgres else """
            INSERT INTO company_metrics (
                canonical_company_id, ticker, as_of_date,
                market_cap_usd, price_usd, avg_daily_volume, avg_daily_traded_value,
                forward_pe, pe_vs_benchmark, peg_ratio, ev_ebitda, price_to_sales, price_to_cash_flow,
                revenue_growth_fwd, eps_growth_fwd, beta, net_debt_ebitda, dividend_yield,
                revenue, ebitda, total_debt, cash, net_debt,
                data_confidence, created_at, updated_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT (canonical_company_id) DO UPDATE SET
                ticker = excluded.ticker,
                as_of_date = excluded.as_of_date,
                market_cap_usd = excluded.market_cap_usd,
                price_usd = excluded.price_usd,
                avg_daily_volume = excluded.avg_daily_volume,
                avg_daily_traded_value = excluded.avg_daily_traded_value,
                forward_pe = excluded.forward_pe,
                pe_vs_benchmark = excluded.pe_vs_benchmark,
                peg_ratio = excluded.peg_ratio,
                ev_ebitda = excluded.ev_ebitda,
                price_to_sales = excluded.price_to_sales,
                price_to_cash_flow = excluded.price_to_cash_flow,
                revenue_growth_fwd = excluded.revenue_growth_fwd,
                eps_growth_fwd = excluded.eps_growth_fwd,
                beta = excluded.beta,
                net_debt_ebitda = excluded.net_debt_ebitda,
                dividend_yield = excluded.dividend_yield,
                revenue = excluded.revenue,
                ebitda = excluded.ebitda,
                total_debt = excluded.total_debt,
                cash = excluded.cash,
                net_debt = excluded.net_debt,
                data_confidence = excluded.data_confidence,
                updated_at = excluded.updated_at;
        """

        created_at_val = record.created_at if is_postgres else record.created_at.isoformat()
        updated_at_val = record.updated_at if is_postgres else record.updated_at.isoformat()

        values = (
            record.canonical_company_id,
            record.ticker,
            record.as_of_date,
            record.market_cap_usd,
            record.price_usd,
            record.avg_daily_volume,
            record.avg_daily_traded_value,
            record.forward_pe,
            record.pe_vs_benchmark,
            record.peg_ratio,
            record.ev_ebitda,
            record.price_to_sales,
            record.price_to_cash_flow,
            record.revenue_growth_fwd,
            record.eps_growth_fwd,
            record.beta,
            record.net_debt_ebitda,
            record.dividend_yield,
            record.revenue,
            record.ebitda,
            record.total_debt,
            record.cash,
            record.net_debt,
            record.data_confidence,
            created_at_val,
            updated_at_val,
        )

        try:
            cursor = conn.cursor()
            cursor.execute(insert_sql, values)
            conn.commit()
            return record.canonical_company_id
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save company metrics for '{record.canonical_company_id}': {e}")
            raise
        finally:
            conn.close()

    def get_metrics(self, canonical_company_id: str) -> Optional[CompanyMetricsRecord]:
        """Fetch calculated metrics for a company by canonical ID."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
        query = "SELECT * FROM company_metrics WHERE canonical_company_id = %s" if is_postgres else "SELECT * FROM company_metrics WHERE canonical_company_id = ?"

        try:
            cursor = conn.cursor()
            cursor.execute(query, (canonical_company_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_model(row, is_postgres)
        finally:
            conn.close()

    def get_metrics_by_ticker(self, ticker: str) -> Optional[CompanyMetricsRecord]:
        """Lookup metrics by ticker symbol."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
        query = "SELECT * FROM company_metrics WHERE LOWER(ticker) = LOWER(%s) LIMIT 1" if is_postgres else "SELECT * FROM company_metrics WHERE LOWER(ticker) = LOWER(?) LIMIT 1"

        try:
            cursor = conn.cursor()
            cursor.execute(query, (ticker.strip(),))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_model(row, is_postgres)
        finally:
            conn.close()

    def list_metrics(self, limit: int = 100) -> List[CompanyMetricsRecord]:
        """List metrics for all companies ordered by market cap descending."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
        query = "SELECT * FROM company_metrics ORDER BY market_cap_usd DESC NULLS LAST LIMIT %s" if is_postgres else "SELECT * FROM company_metrics ORDER BY market_cap_usd DESC LIMIT ?"

        try:
            cursor = conn.cursor()
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            return [self._row_to_model(row, is_postgres) for row in rows]
        finally:
            conn.close()

    def _row_to_model(self, row: Any, is_postgres: bool) -> CompanyMetricsRecord:
        if is_postgres:
            return CompanyMetricsRecord(
                canonical_company_id=row[0],
                ticker=row[1],
                as_of_date=row[2],
                market_cap_usd=row[3],
                price_usd=row[4],
                avg_daily_volume=row[5],
                avg_daily_traded_value=row[6],
                forward_pe=row[7],
                pe_vs_benchmark=row[8],
                peg_ratio=row[9],
                ev_ebitda=row[10],
                price_to_sales=row[11],
                price_to_cash_flow=row[12],
                revenue_growth_fwd=row[13],
                eps_growth_fwd=row[14],
                beta=row[15],
                net_debt_ebitda=row[16],
                dividend_yield=row[17],
                data_confidence=row[18] or "High",
                created_at=row[19] if isinstance(row[19], datetime) else datetime.fromisoformat(str(row[19])),
                updated_at=row[20] if isinstance(row[20], datetime) else datetime.fromisoformat(str(row[20])),
                revenue=row[21] if len(row) > 21 else None,
                ebitda=row[22] if len(row) > 22 else None,
                total_debt=row[23] if len(row) > 23 else None,
                cash=row[24] if len(row) > 24 else None,
                net_debt=row[25] if len(row) > 25 else None,
            )
        else:
            return CompanyMetricsRecord(
                canonical_company_id=row["canonical_company_id"],
                ticker=row["ticker"],
                as_of_date=row["as_of_date"],
                market_cap_usd=row["market_cap_usd"],
                price_usd=row["price_usd"],
                avg_daily_volume=row["avg_daily_volume"],
                avg_daily_traded_value=row["avg_daily_traded_value"],
                forward_pe=row["forward_pe"],
                pe_vs_benchmark=row["pe_vs_benchmark"],
                peg_ratio=row["peg_ratio"],
                ev_ebitda=row["ev_ebitda"],
                price_to_sales=row["price_to_sales"],
                price_to_cash_flow=row["price_to_cash_flow"],
                revenue_growth_fwd=row["revenue_growth_fwd"],
                eps_growth_fwd=row["eps_growth_fwd"],
                beta=row["beta"],
                net_debt_ebitda=row["net_debt_ebitda"],
                dividend_yield=row["dividend_yield"],
                data_confidence=row["data_confidence"] or "High",
                created_at=datetime.fromisoformat(str(row["created_at"])),
                updated_at=datetime.fromisoformat(str(row["updated_at"])),
                revenue=row["revenue"] if "revenue" in row.keys() else None,
                ebitda=row["ebitda"] if "ebitda" in row.keys() else None,
                total_debt=row["total_debt"] if "total_debt" in row.keys() else None,
                cash=row["cash"] if "cash" in row.keys() else None,
                net_debt=row["net_debt"] if "net_debt" in row.keys() else None,
            )


# Global repository instance
company_metrics_repository = CompanyMetricsRepository()
