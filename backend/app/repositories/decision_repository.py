"""Repository for analyst Keep/Drop decisions and portfolio holdings."""

from datetime import datetime
import logging
from typing import Any, List, Optional

from app.db.connection import db_manager
from app.models.decision import DecisionRecord, HoldingRecord

logger = logging.getLogger("app.repositories.decision")


class DecisionRepository:
    """SQL repository for 'decisions' and 'holdings' tables."""

    def __init__(self):
        db_manager.init_tables()

    # -------------------------------------------------------------
    # DECISIONS
    # -------------------------------------------------------------

    DECISION_SELECT_COLS = (
        "decision_id, canonical_company_id, company_name, profile_name, decision, "
        "decision_reason, decision_note, run_id, decided_by, created_at, updated_at"
    )

    def save_decision(self, decision: DecisionRecord) -> str:
        """Insert or update a Keep/Drop analyst decision with company_name and profile_name."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        insert_sql = """
            INSERT INTO decisions (
                decision_id, canonical_company_id, company_name, profile_name, decision,
                decision_reason, decision_note, run_id, decided_by, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (decision_id) DO UPDATE SET
                company_name = COALESCE(EXCLUDED.company_name, decisions.company_name),
                profile_name = COALESCE(EXCLUDED.profile_name, decisions.profile_name),
                decision = EXCLUDED.decision,
                decision_reason = EXCLUDED.decision_reason,
                decision_note = EXCLUDED.decision_note,
                run_id = COALESCE(EXCLUDED.run_id, decisions.run_id),
                updated_at = EXCLUDED.updated_at;
        """ if is_postgres else """
            INSERT INTO decisions (
                decision_id, canonical_company_id, company_name, profile_name, decision,
                decision_reason, decision_note, run_id, decided_by, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (decision_id) DO UPDATE SET
                company_name = COALESCE(excluded.company_name, decisions.company_name),
                profile_name = COALESCE(excluded.profile_name, decisions.profile_name),
                decision = excluded.decision,
                decision_reason = excluded.decision_reason,
                decision_note = excluded.decision_note,
                run_id = COALESCE(excluded.run_id, decisions.run_id),
                updated_at = excluded.updated_at;
        """

        created_at_val = decision.created_at if is_postgres else decision.created_at.isoformat()
        updated_at_val = decision.updated_at if is_postgres else decision.updated_at.isoformat()

        values = (
            decision.decision_id,
            decision.canonical_company_id,
            decision.company_name,
            decision.profile_name,
            decision.decision,
            decision.decision_reason,
            decision.decision_note,
            decision.run_id,
            decision.decided_by,
            created_at_val,
            updated_at_val,
        )

        try:
            cursor = conn.cursor()
            cursor.execute(insert_sql, values)
            conn.commit()
            return decision.decision_id
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save decision for company '{decision.canonical_company_id}': {e}")
            raise
        finally:
            conn.close()

    def save_decisions_batch(self, decisions: List[DecisionRecord]) -> int:
        """Bulk insert or update a list of analyst decisions in a single transaction."""
        if not decisions:
            return 0
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        insert_sql = """
            INSERT INTO decisions (
                decision_id, canonical_company_id, company_name, profile_name, decision,
                decision_reason, decision_note, run_id, decided_by, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (decision_id) DO UPDATE SET
                company_name = COALESCE(EXCLUDED.company_name, decisions.company_name),
                profile_name = COALESCE(EXCLUDED.profile_name, decisions.profile_name),
                decision = EXCLUDED.decision,
                decision_reason = EXCLUDED.decision_reason,
                decision_note = EXCLUDED.decision_note,
                run_id = COALESCE(EXCLUDED.run_id, decisions.run_id),
                updated_at = EXCLUDED.updated_at;
        """ if is_postgres else """
            INSERT INTO decisions (
                decision_id, canonical_company_id, company_name, profile_name, decision,
                decision_reason, decision_note, run_id, decided_by, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (decision_id) DO UPDATE SET
                company_name = COALESCE(excluded.company_name, decisions.company_name),
                profile_name = COALESCE(excluded.profile_name, decisions.profile_name),
                decision = excluded.decision,
                decision_reason = excluded.decision_reason,
                decision_note = excluded.decision_note,
                run_id = COALESCE(excluded.run_id, decisions.run_id),
                updated_at = excluded.updated_at;
        """

        try:
            cursor = conn.cursor()
            for d in decisions:
                created_at_val = d.created_at if is_postgres else d.created_at.isoformat()
                updated_at_val = d.updated_at if is_postgres else d.updated_at.isoformat()
                vals = (
                    d.decision_id,
                    d.canonical_company_id,
                    d.company_name,
                    d.profile_name,
                    d.decision,
                    d.decision_reason,
                    d.decision_note,
                    d.run_id,
                    d.decided_by,
                    created_at_val,
                    updated_at_val,
                )
                cursor.execute(insert_sql, vals)
            conn.commit()
            return len(decisions)
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to batch save decisions: {e}")
            raise
        finally:
            conn.close()

    def get_decision(self, canonical_company_id: str, profile_name: Optional[str] = None) -> Optional[DecisionRecord]:
        """Fetch latest decision for a company, optionally matching profile_name."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        conditions = ["canonical_company_id = %s" if is_postgres else "canonical_company_id = ?"]
        params: list = [canonical_company_id]
        if profile_name:
            conditions.append("profile_name = %s" if is_postgres else "profile_name = ?")
            params.append(profile_name)

        query = f"SELECT {self.DECISION_SELECT_COLS} FROM decisions WHERE {' AND '.join(conditions)} ORDER BY updated_at DESC LIMIT 1"

        try:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_decision(row, is_postgres)
        finally:
            conn.close()

    def list_decisions(self, profile_name: Optional[str] = None, run_id: Optional[str] = None) -> List[DecisionRecord]:
        """Retrieve recorded analyst decisions, optionally filtered by profile_name or run_id."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        conditions = []
        params: list = []
        if profile_name:
            conditions.append("profile_name = %s" if is_postgres else "profile_name = ?")
            params.append(profile_name)
        if run_id:
            conditions.append("run_id = %s" if is_postgres else "run_id = ?")
            params.append(run_id)

        where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"SELECT {self.DECISION_SELECT_COLS} FROM decisions{where_clause} ORDER BY updated_at DESC"

        try:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params) if params else ())
            rows = cursor.fetchall()
            return [self._row_to_decision(row, is_postgres) for row in rows]
        finally:
            conn.close()

    # -------------------------------------------------------------
    # HOLDINGS
    # -------------------------------------------------------------

    def save_holding(self, holding: HoldingRecord) -> str:
        """Insert or update a portfolio holding."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        insert_sql = """
            INSERT INTO holdings (
                holding_id, canonical_company_id, portfolio_name,
                shares, cost_basis, weight_pct, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (holding_id) DO UPDATE SET
                shares = EXCLUDED.shares,
                cost_basis = EXCLUDED.cost_basis,
                weight_pct = EXCLUDED.weight_pct;
        """ if is_postgres else """
            INSERT INTO holdings (
                holding_id, canonical_company_id, portfolio_name,
                shares, cost_basis, weight_pct, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (holding_id) DO UPDATE SET
                shares = excluded.shares,
                cost_basis = excluded.cost_basis,
                weight_pct = excluded.weight_pct;
        """

        created_at_val = holding.created_at if is_postgres else holding.created_at.isoformat()
        values = (
            holding.holding_id,
            holding.canonical_company_id,
            holding.portfolio_name,
            holding.shares,
            holding.cost_basis,
            holding.weight_pct,
            created_at_val,
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

    def list_holdings(self, portfolio_name: Optional[str] = None) -> List[HoldingRecord]:
        """List active fund holdings."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        if portfolio_name:
            query = "SELECT * FROM holdings WHERE portfolio_name = %s" if is_postgres else "SELECT * FROM holdings WHERE portfolio_name = ?"
            params = (portfolio_name,)
        else:
            query = "SELECT * FROM holdings"
            params = ()

        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_holding(row, is_postgres) for row in rows]
        finally:
            conn.close()

    # -------------------------------------------------------------
    # ROW PARSERS
    # -------------------------------------------------------------

    def _row_to_decision(self, row: Any, is_postgres: bool) -> DecisionRecord:
        if isinstance(row, (list, tuple)):
            # Positional mapping from DECISION_SELECT_COLS
            return DecisionRecord(
                decision_id=row[0],
                canonical_company_id=row[1],
                company_name=row[2],
                profile_name=row[3],
                decision=row[4],
                decision_reason=row[5],
                decision_note=row[6],
                run_id=row[7],
                decided_by=row[8] or "Analyst",
                created_at=row[9] if isinstance(row[9], datetime) else datetime.fromisoformat(str(row[9])),
                updated_at=row[10] if isinstance(row[10], datetime) else datetime.fromisoformat(str(row[10])),
            )
        else:
            return DecisionRecord(
                decision_id=row["decision_id"],
                canonical_company_id=row["canonical_company_id"],
                company_name=row.get("company_name"),
                profile_name=row.get("profile_name"),
                decision=row["decision"],
                decision_reason=row.get("decision_reason"),
                decision_note=row.get("decision_note"),
                run_id=row.get("run_id"),
                decided_by=row.get("decided_by") or "Analyst",
                created_at=row["created_at"] if isinstance(row["created_at"], datetime) else datetime.fromisoformat(str(row["created_at"])),
                updated_at=row["updated_at"] if isinstance(row["updated_at"], datetime) else datetime.fromisoformat(str(row["updated_at"])),
            )

    def _row_to_holding(self, row: Any, is_postgres: bool) -> HoldingRecord:
        if is_postgres:
            return HoldingRecord(
                holding_id=row[0],
                canonical_company_id=row[1],
                portfolio_name=row[2],
                shares=float(row[3] or 0.0),
                cost_basis=float(row[4] or 0.0),
                weight_pct=float(row[5] or 0.0),
                created_at=row[6] if isinstance(row[6], datetime) else datetime.fromisoformat(str(row[6])),
            )
        else:
            return HoldingRecord(
                holding_id=row["holding_id"],
                canonical_company_id=row["canonical_company_id"],
                portfolio_name=row["portfolio_name"],
                shares=float(row["shares"] or 0.0),
                cost_basis=float(row["cost_basis"] or 0.0),
                weight_pct=float(row["weight_pct"] or 0.0),
                created_at=datetime.fromisoformat(str(row["created_at"])),
            )


# Global repository instance
decision_repository = DecisionRepository()
