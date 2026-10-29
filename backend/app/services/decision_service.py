"""Analyst Decision Service (Phase 16).

Manages Keep/Drop analyst decisions, linking screening outputs, portfolio holdings,
and human investment decisions with full auditability and persistence.
"""

from datetime import datetime
import logging
import re
from typing import List, Optional

from app.db.connection import db_manager
from app.models.decision import DecisionRecord
from app.repositories.decision_repository import decision_repository
from app.schemas.decision import DecisionUpdateRequest, DecisionBulkSyncRequest, DecisionResponse

logger = logging.getLogger("app.services.decision")


class DecisionService:
    """Business logic for recording, querying, and bulk-syncing analyst Keep/Drop decisions."""

    def __init__(self, repository=None):
        self.repo = repository or decision_repository

    def _clean_slug(self, text: Optional[str]) -> str:
        """Create a clean alphanumeric slug for IDs."""
        if not text:
            return "default"
        cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", text.strip().lower())
        return cleaned.strip("-") or "default"

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

    def _resolve_company_name(self, canonical_id: str, provided_name: Optional[str] = None) -> str:
        """Determine company name from parameter, companies master, or screening_results."""
        if provided_name and provided_name.strip():
            return provided_name.strip()

        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        try:
            cursor = conn.cursor()
            query1 = "SELECT name FROM companies WHERE canonical_id = %s" if is_postgres else "SELECT name FROM companies WHERE canonical_id = ?"
            cursor.execute(query1, (canonical_id,))
            row = cursor.fetchone()
            if row and row[0]:
                return row[0] if isinstance(row, tuple) else row["name"]

            query2 = "SELECT company_name FROM screening_results WHERE canonical_company_id = %s LIMIT 1" if is_postgres else "SELECT company_name FROM screening_results WHERE canonical_company_id = ? LIMIT 1"
            cursor.execute(query2, (canonical_id,))
            row2 = cursor.fetchone()
            if row2 and row2[0]:
                return row2[0] if isinstance(row2, tuple) else row2["company_name"]
        except Exception as e:
            logger.warning(f"[DecisionService] Could not lookup company name for '{canonical_id}': {e}")
        finally:
            conn.close()

        return canonical_id.replace("comp-", "").replace("-", " ").title()

    def _compute_decision_id(self, canonical_id: str, profile_name: Optional[str], run_id: Optional[str]) -> str:
        """Generate consistent decision ID so updating the same profile/company replaces the record."""
        if profile_name and profile_name.strip():
            slug = self._clean_slug(profile_name)
            return f"dec-{slug}-{canonical_id}"
        if run_id and run_id.strip():
            return f"dec-{run_id.strip()}-{canonical_id}"
        return f"dec-{canonical_id}"

    def record_decision(self, req: DecisionUpdateRequest) -> DecisionResponse:
        """Create or update an analyst decision for a security."""
        now = datetime.utcnow()
        canonical_id = self._resolve_canonical_company_id(req.canonical_company_id)
        comp_name = self._resolve_company_name(canonical_id, req.company_name)
        dec_id = self._compute_decision_id(canonical_id, req.profile_name, req.run_id)

        dec_record = DecisionRecord(
            decision_id=dec_id,
            canonical_company_id=canonical_id,
            company_name=comp_name,
            profile_name=req.profile_name,
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
            f"[DecisionService] Saved decision for {comp_name} ({canonical_id}) under profile '{req.profile_name}': {req.decision.upper()}"
        )

        return DecisionResponse(
            decision_id=dec_record.decision_id,
            canonical_company_id=dec_record.canonical_company_id,
            company_name=dec_record.company_name,
            profile_name=dec_record.profile_name,
            decision=dec_record.decision,
            decision_reason=dec_record.decision_reason,
            decision_note=dec_record.decision_note,
            run_id=dec_record.run_id,
            decided_by=dec_record.decided_by,
            updated_at=dec_record.updated_at,
        )

    def bulk_sync_decisions(self, bulk_req: DecisionBulkSyncRequest) -> List[DecisionResponse]:
        """Bulk upsert all Keep/Drop decisions when user exports results for a profile."""
        now = datetime.utcnow()
        records_to_save: List[DecisionRecord] = []
        responses: List[DecisionResponse] = []

        for item in bulk_req.decisions:
            if not item.decision:
                continue
            canonical_id = self._resolve_canonical_company_id(item.canonical_company_id)
            comp_name = self._resolve_company_name(canonical_id, item.company_name)
            prof_name = item.profile_name or bulk_req.profile_name
            r_id = item.run_id or bulk_req.run_id

            dec_id = self._compute_decision_id(canonical_id, prof_name, r_id)

            rec = DecisionRecord(
                decision_id=dec_id,
                canonical_company_id=canonical_id,
                company_name=comp_name,
                profile_name=prof_name,
                decision=item.decision,
                decision_reason=item.decision_reason,
                decision_note=item.decision_note,
                run_id=r_id,
                decided_by=item.decided_by or "Analyst",
                created_at=now,
                updated_at=now,
            )
            records_to_save.append(rec)
            responses.append(
                DecisionResponse(
                    decision_id=rec.decision_id,
                    canonical_company_id=rec.canonical_company_id,
                    company_name=rec.company_name,
                    profile_name=rec.profile_name,
                    decision=rec.decision,
                    decision_reason=rec.decision_reason,
                    decision_note=rec.decision_note,
                    run_id=rec.run_id,
                    decided_by=rec.decided_by,
                    updated_at=rec.updated_at,
                )
            )

        if records_to_save:
            self.repo.save_decisions_batch(records_to_save)
            logger.info(
                f"[DecisionService] Bulk-synced {len(records_to_save)} decisions for profile '{bulk_req.profile_name}'"
            )

        return responses

    def get_decision(self, canonical_company_id: str, profile_name: Optional[str] = None) -> Optional[DecisionResponse]:
        """Fetch the most recent decision for a security."""
        canonical_id = self._resolve_canonical_company_id(canonical_company_id)
        rec = self.repo.get_decision(canonical_id, profile_name=profile_name)
        if not rec:
            return None
        return DecisionResponse(
            decision_id=rec.decision_id,
            canonical_company_id=rec.canonical_company_id,
            company_name=rec.company_name,
            profile_name=rec.profile_name,
            decision=rec.decision,
            decision_reason=rec.decision_reason,
            decision_note=rec.decision_note,
            run_id=rec.run_id,
            decided_by=rec.decided_by,
            updated_at=rec.updated_at,
        )

    def list_decisions(
        self, profile_name: Optional[str] = None, run_id: Optional[str] = None
    ) -> List[DecisionResponse]:
        """Fetch decisions, optionally filtered by profile_name or run_id."""
        records = self.repo.list_decisions(profile_name=profile_name, run_id=run_id)

        return [
            DecisionResponse(
                decision_id=r.decision_id,
                canonical_company_id=r.canonical_company_id,
                company_name=r.company_name,
                profile_name=r.profile_name,
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
