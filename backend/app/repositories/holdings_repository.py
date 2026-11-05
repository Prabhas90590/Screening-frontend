"""Phase 15: Holdings Repository for Portfolio Storage in PostgreSQL."""

from datetime import datetime
import logging
from typing import Any, List, Optional
import psycopg2.extras

from app.db.connection import db_manager
from app.models.holding import HoldingRecord, HoldingWithDetails

logger = logging.getLogger("app.repositories.holdings")


class HoldingsRepository:
    """SQL repository for 'holdings' table in PostgreSQL supporting high-speed bulk batching."""

    def __init__(self):
        db_manager.init_tables()

    def save_holding(self, holding: HoldingRecord) -> str:
        """Insert or update a single portfolio holding."""
        conn = db_manager.get_connection()

        insert_sql = """
            INSERT INTO holdings (
                holding_id, canonical_company_id, portfolio_name,
                shares, cost_basis, weight_pct, holding_rank, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (holding_id) DO UPDATE SET
                shares = EXCLUDED.shares,
                cost_basis = EXCLUDED.cost_basis,
                weight_pct = EXCLUDED.weight_pct,
                holding_rank = EXCLUDED.holding_rank;
        """

        values = (
            holding.holding_id,
            holding.canonical_company_id,
            holding.portfolio_name,
            holding.shares,
            holding.cost_basis,
            holding.weight_pct,
            holding.holding_rank,
            holding.created_at,
        )

        try:
            cursor = conn.cursor()
            cursor.execute(insert_sql, values)
            conn.commit()
            return holding.holding_id
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save holding '{holding.holding_id}': {e}")
            raise
        finally:
            conn.close()

    def save_holdings_batch(self, holdings: List[HoldingRecord]) -> int:
        """Bulk batch write portfolio holdings using psycopg2.extras.execute_values."""
        if not holdings:
            return 0

        deduped = list({h.holding_id: h for h in holdings}.values())
        conn = db_manager.get_connection()

        sql = """
            INSERT INTO holdings (
                holding_id, canonical_company_id, portfolio_name,
                shares, cost_basis, weight_pct, holding_rank, created_at
            ) VALUES %s
            ON CONFLICT (holding_id) DO UPDATE SET
                shares = EXCLUDED.shares,
                cost_basis = EXCLUDED.cost_basis,
                weight_pct = EXCLUDED.weight_pct,
                holding_rank = EXCLUDED.holding_rank;
        """
        values_list = [
            (
                h.holding_id,
                h.canonical_company_id,
                h.portfolio_name,
                h.shares,
                h.cost_basis,
                h.weight_pct,
                h.holding_rank,
                h.created_at,
            )
            for h in deduped
        ]
        try:
            cursor = conn.cursor()
            psycopg2.extras.execute_values(cursor, sql, values_list, page_size=1000)
            conn.commit()
            return len(deduped)
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to bulk save holdings batch: {e}")
            raise
        finally:
            conn.close()

    def list_holdings(self, portfolio_name: Optional[str] = None) -> List[HoldingRecord]:
        """List active fund holdings."""
        conn = db_manager.get_connection()

        if portfolio_name:
            query = "SELECT * FROM holdings WHERE portfolio_name = %s ORDER BY COALESCE(holding_rank, 999999) ASC, weight_pct DESC"
            params = (portfolio_name,)
        else:
            query = "SELECT * FROM holdings ORDER BY COALESCE(holding_rank, 999999) ASC, weight_pct DESC"
            params = ()

        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_holding(row) for row in rows]
        finally:
            conn.close()

    def get_holdings_with_details(self, portfolio_name: Optional[str] = None) -> List[HoldingWithDetails]:
        """Fetch holdings joined with Security Master company details."""
        conn = db_manager.get_connection()

        query = """
            SELECT 
                h.holding_id,
                h.canonical_company_id,
                h.portfolio_name,
                h.shares,
                h.cost_basis,
                h.weight_pct,
                h.created_at,
                COALESCE(c.primary_ticker, 'UNKNOWN') AS ticker,
                COALESCE(c.name, 'Unknown Company') AS company_name,
                COALESCE(c.country, 'US') AS country,
                COALESCE(c.primary_exchange, 'NYSE') AS exchange,
                COALESCE(c.sector, 'Unclassified') AS sector,
                c.market_cap_display,
                c.market_cap,
                h.holding_rank
            FROM holdings h
            LEFT JOIN companies c ON h.canonical_company_id = c.canonical_id
        """
        if portfolio_name:
            query += " WHERE h.portfolio_name = %s ORDER BY COALESCE(h.holding_rank, 999999) ASC, h.weight_pct DESC"
            params = (portfolio_name,)
        else:
            query += " ORDER BY COALESCE(h.holding_rank, 999999) ASC, h.weight_pct DESC"
            params = ()

        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            results: List[HoldingWithDetails] = []
            for row in rows:
                results.append(
                    HoldingWithDetails(
                        holding_id=row[0],
                        canonical_company_id=row[1],
                        portfolio_name=row[2],
                        shares=float(row[3] or 0.0),
                        cost_basis=float(row[4] or 0.0),
                        weight_pct=float(row[5] or 0.0),
                        created_at=row[6] if isinstance(row[6], datetime) else datetime.fromisoformat(str(row[6])),
                        ticker=row[7],
                        company_name=row[8],
                        country=row[9],
                        exchange=row[10],
                        sector=row[11],
                        market_cap_display=float(row[12]) if row[12] is not None else None,
                        holding_rank=int(row[14]) if (len(row) > 14 and row[14] is not None) else None,
                    )
                )
            return results
        finally:
            conn.close()

    def delete_holding(self, holding_id: str) -> bool:
        """Delete a single holding by ID."""
        conn = db_manager.get_connection()
        query = "DELETE FROM holdings WHERE holding_id = %s"

        try:
            cursor = conn.cursor()
            cursor.execute(query, (holding_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def clear_holdings(self, portfolio_name: Optional[str] = None) -> int:
        """Delete all holdings for a given portfolio (or entire table)."""
        conn = db_manager.get_connection()

        if portfolio_name:
            query = "DELETE FROM holdings WHERE portfolio_name = %s"
            params = (portfolio_name,)
        else:
            query = "DELETE FROM holdings"
            params = ()

        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            deleted = cursor.rowcount
            conn.commit()
            return deleted
        finally:
            conn.close()

    def _row_to_holding(self, row: Any) -> HoldingRecord:
        return HoldingRecord(
            holding_id=row[0],
            canonical_company_id=row[1],
            portfolio_name=row[2],
            shares=float(row[3] or 0.0),
            cost_basis=float(row[4] or 0.0),
            weight_pct=float(row[5] or 0.0),
            holding_rank=int(row[6]) if (len(row) > 7 and row[6] is not None) else None,
            created_at=row[7] if (len(row) > 7 and isinstance(row[7], datetime)) else (row[6] if isinstance(row[6], datetime) else datetime.utcnow()),
        )


holdings_repository = HoldingsRepository()
