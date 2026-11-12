"""Repository for analyst Keep/Drop decisions and portfolio holdings in PostgreSQL."""

from datetime import datetime
import logging
from typing import Any, List, Optional

from app.db.connection import db_manager
from app.db.ownership import build_owner_filter
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
        "decision_reason, decision_note, run_id, decided_by, owner_email, user_id, created_at, updated_at"
    )

    def save_decision(self, decision: DecisionRecord) -> str:
        """Insert or update a Keep/Drop analyst decision with company_name and profile_name."""
        return self.save_decisions_batch([decision]) and decision.decision_id

    def save_decisions_batch(self, decisions: List[DecisionRecord]) -> int:
        """Bulk insert or update a list of analyst decisions in a single transaction."""
        if not decisions:
            return 0
        conn = db_manager.get_connection()

        insert_sql = """
            INSERT INTO decisions (
                decision_id, canonical_company_id, company_name, profile_name, decision,
                decision_reason, decision_note, run_id, decided_by, owner_email, user_id, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (decision_id) DO UPDATE SET
                company_name = COALESCE(EXCLUDED.company_name, decisions.company_name),
                profile_name = COALESCE(EXCLUDED.profile_name, decisions.profile_name),
                decision = EXCLUDED.decision,
                decision_reason = EXCLUDED.decision_reason,
                decision_note = EXCLUDED.decision_note,
                run_id = COALESCE(EXCLUDED.run_id, decisions.run_id),
                owner_email = COALESCE(EXCLUDED.owner_email, decisions.owner_email),
                user_id = COALESCE(EXCLUDED.user_id, decisions.user_id),
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
                    d.user_id,
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
        user_id: Optional[str] = None,
    ) -> Optional[DecisionRecord]:
        """Fetch latest decision for a company owned by caller."""
        if not owner_email and not user_id:
            return None

        conn = db_manager.get_connection()

        owner_clause, owner_params = build_owner_filter(user_id=user_id, owner_email=owner_email)
        conditions = ["canonical_company_id = %s", owner_clause]
        params: list = [canonical_company_id, *owner_params]
        if profile_name:
            conditions.append("profile_name = %s")
            params.append(profile_name)

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
        user_id: Optional[str] = None,
    ) -> List[DecisionRecord]:
        """Retrieve recorded analyst decisions strictly scoped to caller."""
        if not owner_email and not user_id:
            return []

        conn = db_manager.get_connection()

        owner_clause, owner_params = build_owner_filter(user_id=user_id, owner_email=owner_email)
        conditions = [owner_clause]
        params: list = [*owner_params]
        if profile_name:
            conditions.append("profile_name = %s")
            params.append(profile_name)
        if run_id:
            conditions.append("run_id = %s")
            params.append(run_id)

        query = f"SELECT {self.DECISION_SELECT_COLS} FROM decisions WHERE {' AND '.join(conditions)} ORDER BY updated_at DESC"

        try:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
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
                user_id=row[10],
                created_at=row[11] if isinstance(row[11], datetime) else datetime.fromisoformat(str(row[11])),
                updated_at=row[12] if isinstance(row[12], datetime) else datetime.fromisoformat(str(row[12])),
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
                user_id=row.get("user_id"),
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
