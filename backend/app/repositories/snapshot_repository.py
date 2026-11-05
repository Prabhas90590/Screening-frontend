"""Repository for financial_snapshots and estimate_snapshots tables in PostgreSQL."""

from datetime import datetime
import logging
from typing import List, Optional

from app.db.connection import db_manager
from app.models.financial_snapshot import EstimateSnapshotRecord, FinancialSnapshotRecord

logger = logging.getLogger("app.repositories.snapshot")


class SnapshotRepository:
    """Repository for managing financial statement and analyst estimate snapshots in PostgreSQL."""

    def __init__(self):
        db_manager.init_tables()

    # -------------------------------------------------------------
    # FINANCIAL SNAPSHOTS
    # -------------------------------------------------------------

    def save_financial_snapshot(self, record: FinancialSnapshotRecord) -> str:
        """Insert or update a financial statement snapshot."""
        conn = db_manager.get_connection()

        insert_sql = """
            INSERT INTO financial_snapshots (
                id, canonical_company_id, as_of_date, currency,
                ebitda, net_debt, total_debt, cash, revenue,
                operating_income, net_income, free_cash_flow, created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (id) DO UPDATE SET
                ebitda = EXCLUDED.ebitda,
                net_debt = EXCLUDED.net_debt,
                total_debt = EXCLUDED.total_debt,
                cash = EXCLUDED.cash,
                revenue = EXCLUDED.revenue,
                operating_income = EXCLUDED.operating_income,
                net_income = EXCLUDED.net_income,
                free_cash_flow = EXCLUDED.free_cash_flow;
        """

        try:
            cursor = conn.cursor()
            cursor.execute(
                insert_sql,
                (
                    record.id,
                    record.canonical_company_id,
                    record.as_of_date,
                    record.currency,
                    record.ebitda,
                    record.net_debt,
                    record.total_debt,
                    record.cash,
                    record.revenue,
                    record.operating_income,
                    record.net_income,
                    record.free_cash_flow,
                    record.created_at,
                ),
            )
            conn.commit()
            return record.id
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save financial snapshot '{record.id}': {e}")
            raise
        finally:
            conn.close()

    def save_financial_snapshots_batch(self, records: List[FinancialSnapshotRecord]) -> int:
        """Bulk insert financial snapshots with de-duplication using PostgreSQL execute_values."""
        if not records:
            return 0
        conn = db_manager.get_connection()
        deduped = list({r.id: r for r in records}.values())
        try:
            cursor = conn.cursor()
            from psycopg2.extras import execute_values
            pg_sql = """
                INSERT INTO financial_snapshots (
                    id, canonical_company_id, as_of_date, currency,
                    ebitda, net_debt, total_debt, cash, revenue,
                    operating_income, net_income, free_cash_flow, created_at
                ) VALUES %s
                ON CONFLICT (id) DO UPDATE SET
                    ebitda = EXCLUDED.ebitda,
                    net_debt = EXCLUDED.net_debt,
                    total_debt = EXCLUDED.total_debt,
                    cash = EXCLUDED.cash,
                    revenue = EXCLUDED.revenue,
                    operating_income = EXCLUDED.operating_income,
                    net_income = EXCLUDED.net_income,
                    free_cash_flow = EXCLUDED.free_cash_flow;
            """
            tuples = [
                (
                    r.id, r.canonical_company_id, r.as_of_date, r.currency,
                    r.ebitda, r.net_debt, r.total_debt, r.cash, r.revenue,
                    r.operating_income, r.net_income, r.free_cash_flow, r.created_at
                )
                for r in deduped
            ]
            execute_values(cursor, pg_sql, tuples, page_size=1000)
            conn.commit()
            return len(deduped)
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to bulk save financial snapshots: {e}")
            raise
        finally:
            conn.close()

    def save_estimate_snapshots_batch(self, records: List[EstimateSnapshotRecord]) -> int:
        """Bulk insert estimate snapshots with de-duplication using PostgreSQL execute_values."""
        if not records:
            return 0
        conn = db_manager.get_connection()
        deduped = list({r.id: r for r in records}.values())
        try:
            cursor = conn.cursor()
            from psycopg2.extras import execute_values
            pg_sql = """
                INSERT INTO estimate_snapshots (
                    id, canonical_company_id, as_of_date,
                    forward_pe, peg_ratio, eps_growth_fwd, analyst_count,
                    target_price, recommendation_mean, created_at
                ) VALUES %s
                ON CONFLICT (id) DO UPDATE SET
                    forward_pe = EXCLUDED.forward_pe,
                    peg_ratio = EXCLUDED.peg_ratio,
                    eps_growth_fwd = EXCLUDED.eps_growth_fwd,
                    analyst_count = EXCLUDED.analyst_count,
                    target_price = EXCLUDED.target_price,
                    recommendation_mean = EXCLUDED.recommendation_mean;
            """
            tuples = [
                (
                    r.id, r.canonical_company_id, r.as_of_date,
                    r.forward_pe, r.peg_ratio, r.eps_growth_fwd, r.analyst_count,
                    r.target_price, r.recommendation_mean, r.created_at
                )
                for r in deduped
            ]
            execute_values(cursor, pg_sql, tuples, page_size=1000)
            conn.commit()
            return len(deduped)
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to bulk save estimate snapshots: {e}")
            raise
        finally:
            conn.close()

    def get_financial_snapshots_by_company(self, canonical_company_id: str) -> List[FinancialSnapshotRecord]:
        """Fetch all historical financial snapshots for a canonical company."""
        conn = db_manager.get_connection()
        query = "SELECT * FROM financial_snapshots WHERE canonical_company_id = %s ORDER BY as_of_date DESC"

        try:
            cursor = conn.cursor()
            cursor.execute(query, (canonical_company_id,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                results.append(
                    FinancialSnapshotRecord(
                        id=r[0],
                        canonical_company_id=r[1],
                        as_of_date=r[2],
                        currency=r[3],
                        ebitda=r[4],
                        net_debt=r[5],
                        total_debt=r[6],
                        cash=r[7],
                        revenue=r[8],
                        operating_income=r[9],
                        net_income=r[10],
                        free_cash_flow=r[11],
                    )
                )
            return results
        finally:
            conn.close()

    # -------------------------------------------------------------
    # ESTIMATE SNAPSHOTS
    # -------------------------------------------------------------

    def save_estimate_snapshot(self, record: EstimateSnapshotRecord) -> str:
        """Insert or update an analyst estimate snapshot."""
        conn = db_manager.get_connection()

        insert_sql = """
            INSERT INTO estimate_snapshots (
                id, canonical_company_id, as_of_date,
                forward_pe, peg_ratio, eps_growth_fwd, analyst_count,
                target_price, recommendation_mean, created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (id) DO UPDATE SET
                forward_pe = EXCLUDED.forward_pe,
                peg_ratio = EXCLUDED.peg_ratio,
                eps_growth_fwd = EXCLUDED.eps_growth_fwd,
                analyst_count = EXCLUDED.analyst_count,
                target_price = EXCLUDED.target_price,
                recommendation_mean = EXCLUDED.recommendation_mean;
        """

        try:
            cursor = conn.cursor()
            cursor.execute(
                insert_sql,
                (
                    record.id,
                    record.canonical_company_id,
                    record.as_of_date,
                    record.forward_pe,
                    record.peg_ratio,
                    record.eps_growth_fwd,
                    record.analyst_count,
                    record.target_price,
                    record.recommendation_mean,
                    record.created_at,
                ),
            )
            conn.commit()
            return record.id
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save estimate snapshot '{record.id}': {e}")
            raise
        finally:
            conn.close()

    def get_estimate_snapshots_by_company(self, canonical_company_id: str) -> List[EstimateSnapshotRecord]:
        """Fetch all historical estimate snapshots for a canonical company."""
        conn = db_manager.get_connection()
        query = "SELECT * FROM estimate_snapshots WHERE canonical_company_id = %s ORDER BY as_of_date DESC"

        try:
            cursor = conn.cursor()
            cursor.execute(query, (canonical_company_id,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                results.append(
                    EstimateSnapshotRecord(
                        id=r[0],
                        canonical_company_id=r[1],
                        as_of_date=r[2],
                        forward_pe=r[3],
                        peg_ratio=r[4],
                        eps_growth_fwd=r[5],
                        analyst_count=r[6],
                        target_price=r[7],
                        recommendation_mean=r[8],
                    )
                )
            return results
        finally:
            conn.close()


snapshot_repository = SnapshotRepository()
