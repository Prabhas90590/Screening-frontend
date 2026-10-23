"""Repository for financial_snapshots and estimate_snapshots tables in PostgreSQL."""

from datetime import datetime
import logging
from typing import List, Optional

from app.db.connection import db_manager
from app.models.financial_snapshot import EstimateSnapshotRecord, FinancialSnapshotRecord

logger = logging.getLogger("app.repositories.snapshot")


class SnapshotRepository:
    """Repository for managing financial statement and analyst estimate snapshots."""

    def __init__(self):
        db_manager.init_tables()

    # -------------------------------------------------------------
    # FINANCIAL SNAPSHOTS
    # -------------------------------------------------------------

    def save_financial_snapshot(self, record: FinancialSnapshotRecord) -> str:
        """Insert or update a financial statement snapshot."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

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
        """ if is_postgres else """
            INSERT INTO financial_snapshots (
                id, canonical_company_id, as_of_date, currency,
                ebitda, net_debt, total_debt, cash, revenue,
                operating_income, net_income, free_cash_flow, created_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT (id) DO UPDATE SET
                ebitda = excluded.ebitda,
                net_debt = excluded.net_debt,
                total_debt = excluded.total_debt,
                cash = excluded.cash,
                revenue = excluded.revenue,
                operating_income = excluded.operating_income,
                net_income = excluded.net_income,
                free_cash_flow = excluded.free_cash_flow;
        """

        created_at_val = record.created_at if is_postgres else record.created_at.isoformat()

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
                    created_at_val,
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

    def get_financial_snapshots_by_company(self, canonical_company_id: str) -> List[FinancialSnapshotRecord]:
        """Fetch all historical financial snapshots for a canonical company."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
        query = "SELECT * FROM financial_snapshots WHERE canonical_company_id = %s ORDER BY as_of_date DESC" if is_postgres else "SELECT * FROM financial_snapshots WHERE canonical_company_id = ? ORDER BY as_of_date DESC"

        try:
            cursor = conn.cursor()
            cursor.execute(query, (canonical_company_id,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                results.append(
                    FinancialSnapshotRecord(
                        id=r[0] if is_postgres else r["id"],
                        canonical_company_id=r[1] if is_postgres else r["canonical_company_id"],
                        as_of_date=r[2] if is_postgres else r["as_of_date"],
                        currency=r[3] if is_postgres else r["currency"],
                        ebitda=r[4] if is_postgres else r["ebitda"],
                        net_debt=r[5] if is_postgres else r["net_debt"],
                        total_debt=r[6] if is_postgres else r["total_debt"],
                        cash=r[7] if is_postgres else r["cash"],
                        revenue=r[8] if is_postgres else r["revenue"],
                        operating_income=r[9] if is_postgres else r["operating_income"],
                        net_income=r[10] if is_postgres else r["net_income"],
                        free_cash_flow=r[11] if is_postgres else r["free_cash_flow"],
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
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

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
        """ if is_postgres else """
            INSERT INTO estimate_snapshots (
                id, canonical_company_id, as_of_date,
                forward_pe, peg_ratio, eps_growth_fwd, analyst_count,
                target_price, recommendation_mean, created_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT (id) DO UPDATE SET
                forward_pe = excluded.forward_pe,
                peg_ratio = excluded.peg_ratio,
                eps_growth_fwd = excluded.eps_growth_fwd,
                analyst_count = excluded.analyst_count,
                target_price = excluded.target_price,
                recommendation_mean = excluded.recommendation_mean;
        """

        created_at_val = record.created_at if is_postgres else record.created_at.isoformat()

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
                    created_at_val,
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
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
        query = "SELECT * FROM estimate_snapshots WHERE canonical_company_id = %s ORDER BY as_of_date DESC" if is_postgres else "SELECT * FROM estimate_snapshots WHERE canonical_company_id = ? ORDER BY as_of_date DESC"

        try:
            cursor = conn.cursor()
            cursor.execute(query, (canonical_company_id,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                results.append(
                    EstimateSnapshotRecord(
                        id=r[0] if is_postgres else r["id"],
                        canonical_company_id=r[1] if is_postgres else r["canonical_company_id"],
                        as_of_date=r[2] if is_postgres else r["as_of_date"],
                        forward_pe=r[3] if is_postgres else r["forward_pe"],
                        peg_ratio=r[4] if is_postgres else r["peg_ratio"],
                        eps_growth_fwd=r[5] if is_postgres else r["eps_growth_fwd"],
                        analyst_count=r[6] if is_postgres else r["analyst_count"],
                        target_price=r[7] if is_postgres else r["target_price"],
                        recommendation_mean=r[8] if is_postgres else r["recommendation_mean"],
                    )
                )
            return results
        finally:
            conn.close()


snapshot_repository = SnapshotRepository()

