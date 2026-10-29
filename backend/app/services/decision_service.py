"""Analyst Decision Service (Phase 16).

Manages Keep/Drop analyst decisions, linking screening outputs, portfolio holdings,
and human investment decisions with full auditability and persistence.
"""

from datetime import datetime
import logging
from typing import List, Optional

from app.db.connection import db_manager
from app.models.decision import DecisionRecord
from app.repositories.decision_repository import decision_repository
from app.schemas.decision import DecisionUpdateRequest, DecisionResponse

logger = logging.getLogger("app.services.decision")


class DecisionService:
    """Business logic for recording and querying analyst Keep/Drop decisions."""

    def __init__(self, repository=None):
        self.repo = repository or decision_repository

    def _resolve_canonical_company_id(self, identifier: str) -> str:
        """Resolve identifier (canonical_id or ticker) against companies table, inserting a minimal company stub if needed."""
        if not identifier:
            return "comp-unknown"

        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        try:
            cursor = conn.cursor()
            # 1. Exact match by canonical_id
            query1 = "SELECT canonical_id FROM companies WHERE canonical_id = %s" if is_postgres else "SELECT canonical_id FROM companies WHERE canonical_id = ?"
            cursor.execute(query1, (identifier,))
            row = cursor.fetchone()
            if row:
                return row[0] if isinstance(row, tuple) else row["canonical_id"]

            # 2. Case-insensitive match by primary_ticker
            query2 = "SELECT canonical_id FROM companies WHERE UPPER(primary_ticker) = UPPER(%s) LIMIT 1" if is_postgres else "SELECT canonical_id FROM companies WHERE UPPER(primary_ticker) = UPPER(?) LIMIT 1"
            cursor.execute(query2, (identifier,))
            row = cursor.fetchone()
            if row:
                return row[0] if isinstance(row, tuple) else row["canonical_id"]

            # 3. If neither matched, generate canonical ID and ensure record in companies table
            clean_id = f"comp-{identifier.lower().replace(' ', '-')}"
            insert_company = """
                INSERT INTO companies (canonical_id, primary_ticker, name, country, sector)
                VALUES (%s, %s, %s, 'GLOBAL', 'General')
                ON CONFLICT (canonical_id) DO NOTHING;
            """ if is_postgres else """
                INSERT OR IGNORE INTO companies (canonical_id, primary_ticker, name, country, sector)
                VALUES (?, ?, ?, 'GLOBAL', 'General');
            """
            cursor.execute(insert_company, (clean_id, identifier.upper(), f"{identifier} Ltd"))
            conn.commit()
            return clean_id
        except Exception as e:
            logger.warning(f"[DecisionService] Could not resolve canonical_id for '{identifier}': {e}")
            return identifier
        finally:
            conn.close()

    def record_decision(self, req: DecisionUpdateRequest) -> DecisionResponse:
        """Create or update an analyst decision for a security."""
        now = datetime.utcnow()
        canonical_id = self._resolve_canonical_company_id(req.canonical_company_id)

        # Canonical decision ID per company/run to enable seamless upserting
        if req.run_id:
            dec_id = f"dec-{req.run_id}-{canonical_id}"
        else:
            dec_id = f"dec-{canonical_id}"

        dec_record = DecisionRecord(
            decision_id=dec_id,
            canonical_company_id=canonical_id,
            decision=req.decision,
            decision_reason=req.decision_reason,
            decision_note=req.decision_note,
            run_id=req.run_id,
            decided_by=getattr(req, "decided_by", "Analyst") or "Analyst",
            created_at=now,
            updated_at=now,
        )

        self.repo.save_decision(dec_record)
        logger.info(
            f"[DecisionService] Recorded decision: {req.decision.upper()} for company '{canonical_id}' (Reason: {req.decision_reason})"
        )

        return DecisionResponse(
            decision_id=dec_record.decision_id,
            canonical_company_id=dec_record.canonical_company_id,
            decision=dec_record.decision,
            decision_reason=dec_record.decision_reason,
            decision_note=dec_record.decision_note,
            run_id=dec_record.run_id,
            decided_by=dec_record.decided_by,
            updated_at=dec_record.updated_at,
        )

    def get_decision(self, canonical_company_id: str) -> Optional[DecisionResponse]:
        """Fetch the most recent decision for a security."""
        canonical_id = self._resolve_canonical_company_id(canonical_company_id)
        rec = self.repo.get_decision(canonical_id)
        if not rec:
            return None
        return DecisionResponse(
            decision_id=rec.decision_id,
            canonical_company_id=rec.canonical_company_id,
            decision=rec.decision,
            decision_reason=rec.decision_reason,
            decision_note=rec.decision_note,
            run_id=rec.run_id,
            decided_by=rec.decided_by,
            updated_at=rec.updated_at,
        )

    def list_decisions(self, run_id: Optional[str] = None) -> List[DecisionResponse]:
        """Fetch all decisions, optionally filtered by run ID."""
        records = self.repo.list_decisions()
        if run_id:
            records = [r for r in records if r.run_id == run_id]

        return [
            DecisionResponse(
                decision_id=r.decision_id,
                canonical_company_id=r.canonical_company_id,
                decision=r.decision,
                decision_reason=r.decision_reason,
                decision_note=r.decision_note,
                run_id=r.run_id,
                decided_by=r.decided_by,
                updated_at=r.updated_at,
            )
            for r in records
        ]


decision_service = DecisionService()
