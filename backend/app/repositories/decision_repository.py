"""Repository for analyst Keep/Drop decisions and portfolio holdings in PostgreSQL."""

from datetime import datetime
import logging
from typing import Any, List, Optional

from app.db.connection import db_manager
from app.models.decision import DecisionRecord, HoldingRecord

logger = logging.getLogger("app.repositories.decision")


class DecisionRepository:
    """SQL repository for 'decisions' and 'holdings' tables in PostgreSQL."""

    def __init__(self):
        db_manager.init_tables()

    # -------------------------------------------------------------
    # DECISIONS
    # -------------------------------------------------------------

    DECISION_SELECT_COLS = (
        "decision_id, canonical_company_id, company_name, profile_name, decision, "
        "decision_reason, decision_note, run_id, decided_by, owner_email, created_at, updated_at"
    )

    def save_decision(self, decision: DecisionRecord) -> str:
        """Insert or update a Keep/Drop analyst decision with company_name and profile_name."""
        conn = db_manager.get_connection()

        insert_sql = """
            INSERT INTO decisions (
                decision_id, canonical_company_id, company_name, profile_name, decision,
                decision_reason, decision_note, run_id, decided_by, owner_email, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (decision_id) DO UPDATE SET
                company_name = COALESCE(EXCLUDED.company_name, decisions.company_name),
                profile_name = COALESCE(EXCLUDED.profile_name, decisions.profile_name),
                decision = EXCLUDED.decision,
                decision_reason = EXCLUDED.decision_reason,
                decision_note = EXCLUDED.decision_note,
                run_id = COALESCE(EXCLUDED.run_id, decisions.run_id),
                owner_email = COALESCE(EXCLUDED.owner_email, decisions.owner_email),
                updated_at = EXCLUDED.updated_at;
        """

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
            decision.owner_email,
            decision.created_at,
            decision.updated_at,
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

        insert_sql = """
            INSERT INTO decisions (
                decision_id, canonical_company_id, company_name, profile_name, decision,
                decision_reason, decision_note, run_id, decided_by, owner_email, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (decision_id) DO UPDATE SET
                company_name = COALESCE(EXCLUDED.company_name, decisions.company_name),
                profile_name = COALESCE(EXCLUDED.profile_name, decisions.profile_name),
                decision = EXCLUDED.decision,
                decision_reason = EXCLUDED.decision_reason,
                decision_note = EXCLUDED.decision_note,
                run_id = COALESCE(EXCLUDED.run_id, decisions.run_id),
                owner_email = COALESCE(EXCLUDED.owner_email, decisions.owner_email),
                updated_at = EXCLUDED.updated_at;
        """

        try:
            cursor = conn.cursor()
            for d in decisions:
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
                    d.owner_email,
                    d.created_at,
                    d.updated_at,
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

    def get_decision(
        self,
        canonical_company_id: str,
        profile_name: Optional[str] = None,
        owner_email: Optional[str] = None,
    ) -> Optional[DecisionRecord]:
        """Fetch latest decision for a company, optionally matching profile_name and owner_email."""
        conn = db_manager.get_connection()

        conditions = ["canonical_company_id = %s"]
        params: list = [canonical_company_id]
        if profile_name:
            conditions.append("profile_name = %s")
            params.append(profile_name)
        if owner_email:
            conditions.append("LOWER(owner_email) = LOWER(%s)")
            params.append(owner_email)

        query = f"SELECT {self.DECISION_SELECT_COLS} FROM decisions WHERE {' AND '.join(conditions)} ORDER BY updated_at DESC LIMIT 1"

        try:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_decision(row)
        finally:
            conn.close()

    def list_decisions(
        self,
        profile_name: Optional[str] = None,
        run_id: Optional[str] = None,
        owner_email: Optional[str] = None,
    ) -> List[DecisionRecord]:
        """Retrieve recorded analyst decisions, optionally filtered by profile_name, run_id, or owner_email."""
        conn = db_manager.get_connection()

        conditions = []
        params: list = []
        if profile_name:
            conditions.append("profile_name = %s")
            params.append(profile_name)
        if run_id:
            conditions.append("run_id = %s")
            params.append(run_id)
        if owner_email:
            conditions.append("LOWER(owner_email) = LOWER(%s)")
            params.append(owner_email)

        where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"SELECT {self.DECISION_SELECT_COLS} FROM decisions{where_clause} ORDER BY updated_at DESC"

        try:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params) if params else ())
            rows = cursor.fetchall()
            return [self._row_to_decision(row) for row in rows]
        finally:
            conn.close()

    # -------------------------------------------------------------
    # HOLDINGS
    # -------------------------------------------------------------

    def save_holding(self, holding: HoldingRecord) -> str:
        """Insert or update a portfolio holding."""
        conn = db_manager.get_connection()

        insert_sql = """
            INSERT INTO holdings (
                holding_id, canonical_company_id, portfolio_name,
                shares, cost_basis, weight_pct, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (holding_id) DO UPDATE SET
                shares = EXCLUDED.shares,
                cost_basis = EXCLUDED.cost_basis,
                weight_pct = EXCLUDED.weight_pct;
        """

        values = (
            holding.holding_id,
            holding.canonical_company_id,
            holding.portfolio_name,
            holding.shares,
            holding.cost_basis,
            holding.weight_pct,
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

    def list_holdings(self, portfolio_name: Optional[str] = None) -> List[HoldingRecord]:
        """List active fund holdings."""
        conn = db_manager.get_connection()

        if portfolio_name:
            query = "SELECT * FROM holdings WHERE portfolio_name = %s"
            params = (portfolio_name,)
        else:
            query = "SELECT * FROM holdings"
            params = ()

        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_holding(row) for row in rows]
        finally:
            conn.close()

    # -------------------------------------------------------------
    # ROW PARSERS
    # -------------------------------------------------------------

    def _row_to_decision(self, row: Any) -> DecisionRecord:
        if isinstance(row, (list, tuple)):
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
                owner_email=row[9],
                created_at=row[10] if isinstance(row[10], datetime) else datetime.fromisoformat(str(row[10])),
                updated_at=row[11] if isinstance(row[11], datetime) else datetime.fromisoformat(str(row[11])),
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
                owner_email=row.get("owner_email"),
                created_at=row["created_at"] if isinstance(row["created_at"], datetime) else datetime.fromisoformat(str(row["created_at"])),
                updated_at=row["updated_at"] if isinstance(row["updated_at"], datetime) else datetime.fromisoformat(str(row["updated_at"])),
            )

    def _row_to_holding(self, row: Any) -> HoldingRecord:
        return HoldingRecord(
            holding_id=row[0],
            canonical_company_id=row[1],
            portfolio_name=row[2],
            shares=float(row[3] or 0.0),
            cost_basis=float(row[4] or 0.0),
            weight_pct=float(row[5] or 0.0),
            created_at=row[6] if isinstance(row[6], datetime) else datetime.fromisoformat(str(row[6])),
        )


# Global repository instance
decision_repository = DecisionRepository()
