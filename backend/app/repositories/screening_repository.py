"""Repository for screening runs, funnel metrics, and company results."""

from datetime import datetime
import json
import logging
from typing import Any, Dict, List, Optional

from app.db.connection import db_manager
from app.models.screening_run import (
    FunnelCountRecord,
    ScreeningResultRecord,
    ScreeningRunRecord,
)

logger = logging.getLogger("app.repositories.screening")


class ScreeningRepository:
    """SQL repository for screening_runs, funnel_counts, and screening_results."""

    def __init__(self):
        db_manager.init_tables()

    # -------------------------------------------------------------
    # SCREENING RUNS
    # -------------------------------------------------------------

    def save_run(self, run: ScreeningRunRecord) -> str:
        """Insert or update a screening run record."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        insert_sql = """
            INSERT INTO screening_runs (
                run_id, status, provider, rule_version_id, profile_name,
                display_currency, selected_countries, selected_exchanges,
                rules_snapshot, duration_ms, started_at, completed_at, error_message
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (run_id) DO UPDATE SET
                status = EXCLUDED.status,
                completed_at = EXCLUDED.completed_at,
                duration_ms = EXCLUDED.duration_ms,
                error_message = EXCLUDED.error_message;
        """ if is_postgres else """
            INSERT INTO screening_runs (
                run_id, status, provider, rule_version_id, profile_name,
                display_currency, selected_countries, selected_exchanges,
                rules_snapshot, duration_ms, started_at, completed_at, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (run_id) DO UPDATE SET
                status = excluded.status,
                completed_at = excluded.completed_at,
                duration_ms = excluded.duration_ms,
                error_message = excluded.error_message;
        """

        countries_json = json.dumps(run.selected_countries)
        exchanges_json = json.dumps(run.selected_exchanges)
        rules_json = json.dumps(run.rules_snapshot)

        started_at_val = run.started_at if is_postgres else run.started_at.isoformat()
        completed_at_val = (
            run.completed_at if is_postgres else (run.completed_at.isoformat() if run.completed_at else None)
        )

        values = (
            run.run_id,
            run.status,
            run.provider,
            run.rule_version_id,
            run.profile_name,
            run.display_currency,
            countries_json,
            exchanges_json,
            rules_json,
            run.duration_ms,
            started_at_val,
            completed_at_val,
            run.error_message,
        )

        try:
            cursor = conn.cursor()
            cursor.execute(insert_sql, values)
            conn.commit()
            return run.run_id
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save screening run '{run.run_id}': {e}")
            raise
        finally:
            conn.close()

    def get_run(self, run_id: str) -> Optional[ScreeningRunRecord]:
        """Fetch screening run by ID."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
        query = "SELECT * FROM screening_runs WHERE run_id = %s" if is_postgres else "SELECT * FROM screening_runs WHERE run_id = ?"

        try:
            cursor = conn.cursor()
            cursor.execute(query, (run_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_run(row, is_postgres)
        finally:
            conn.close()

    def list_runs(self, limit: int = 50) -> List[ScreeningRunRecord]:
        """List historical screening runs ordered by start time descending."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
        query = "SELECT * FROM screening_runs ORDER BY started_at DESC LIMIT %s" if is_postgres else "SELECT * FROM screening_runs ORDER BY started_at DESC LIMIT ?"

        try:
            cursor = conn.cursor()
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            return [self._row_to_run(row, is_postgres) for row in rows]
        finally:
            conn.close()

    # -------------------------------------------------------------
    # FUNNEL COUNTS
    # -------------------------------------------------------------

    def save_funnel_counts(self, funnel: FunnelCountRecord) -> str:
        """Insert or update funnel stage progression for a run."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        insert_sql = """
            INSERT INTO funnel_counts (
                id, run_id, universe_count, markets_count, floors_count,
                gates_count, score_count, shortlist_count, selected_count, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (run_id) DO UPDATE SET
                universe_count = EXCLUDED.universe_count,
                markets_count = EXCLUDED.markets_count,
                floors_count = EXCLUDED.floors_count,
                gates_count = EXCLUDED.gates_count,
                score_count = EXCLUDED.score_count,
                shortlist_count = EXCLUDED.shortlist_count,
                selected_count = EXCLUDED.selected_count;
        """ if is_postgres else """
            INSERT INTO funnel_counts (
                id, run_id, universe_count, markets_count, floors_count,
                gates_count, score_count, shortlist_count, selected_count, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (run_id) DO UPDATE SET
                universe_count = excluded.universe_count,
                markets_count = excluded.markets_count,
                floors_count = excluded.floors_count,
                gates_count = excluded.gates_count,
                score_count = excluded.score_count,
                shortlist_count = excluded.shortlist_count,
                selected_count = excluded.selected_count;
        """

        created_at_val = funnel.created_at if is_postgres else funnel.created_at.isoformat()
        values = (
            funnel.id,
            funnel.run_id,
            funnel.universe_count,
            funnel.markets_count,
            funnel.floors_count,
            funnel.gates_count,
            funnel.score_count,
            funnel.shortlist_count,
            funnel.selected_count,
            created_at_val,
        )

        try:
            cursor = conn.cursor()
            cursor.execute(insert_sql, values)
            conn.commit()
            return funnel.id
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save funnel counts for run '{funnel.run_id}': {e}")
            raise
        finally:
            conn.close()

    def get_funnel_counts(self, run_id: str) -> Optional[FunnelCountRecord]:
        """Fetch funnel counts for a specific run."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
        query = "SELECT * FROM funnel_counts WHERE run_id = %s" if is_postgres else "SELECT * FROM funnel_counts WHERE run_id = ?"

        try:
            cursor = conn.cursor()
            cursor.execute(query, (run_id,))
            row = cursor.fetchone()
            if not row:
                return None
            if is_postgres:
                return FunnelCountRecord(
                    id=row[0],
                    run_id=row[1],
                    universe_count=row[2],
                    markets_count=row[3],
                    floors_count=row[4],
                    gates_count=row[5],
                    score_count=row[6],
                    shortlist_count=row[7],
                    selected_count=row[8],
                    created_at=row[9] if isinstance(row[9], datetime) else datetime.fromisoformat(str(row[9])),
                )
            else:
                return FunnelCountRecord(
                    id=row["id"],
                    run_id=row["run_id"],
                    universe_count=row["universe_count"],
                    markets_count=row["markets_count"],
                    floors_count=row["floors_count"],
                    gates_count=row["gates_count"],
                    score_count=row["score_count"],
                    shortlist_count=row["shortlist_count"],
                    selected_count=row["selected_count"],
                    created_at=datetime.fromisoformat(str(row["created_at"])),
                )
        finally:
            conn.close()

    # -------------------------------------------------------------
    # SCREENING RESULTS
    # -------------------------------------------------------------

    def save_results_batch(self, results: List[ScreeningResultRecord]) -> int:
        """Insert a batch of screened securities for a run."""
        if not results:
            return 0

        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        insert_sql = """
            INSERT INTO screening_results (
                id, run_id, canonical_company_id, ticker, company_name,
                country, exchange, sector, rank, score,
                display_price, market_cap_display, display_currency,
                fwd_pe, peg, ev_ebitda, beta, nd_ebitda, yield_pct, eps_growth_pct,
                data_confidence, stage_status, near_miss_status,
                score_breakdown, metric_statuses, created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (id) DO UPDATE SET
                rank = EXCLUDED.rank,
                score = EXCLUDED.score,
                display_price = EXCLUDED.display_price,
                market_cap_display = EXCLUDED.market_cap_display;
        """ if is_postgres else """
            INSERT INTO screening_results (
                id, run_id, canonical_company_id, ticker, company_name,
                country, exchange, sector, rank, score,
                display_price, market_cap_display, display_currency,
                fwd_pe, peg, ev_ebitda, beta, nd_ebitda, yield_pct, eps_growth_pct,
                data_confidence, stage_status, near_miss_status,
                score_breakdown, metric_statuses, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                rank = excluded.rank,
                score = excluded.score,
                display_price = excluded.display_price,
                market_cap_display = excluded.market_cap_display;
        """

        try:
            cursor = conn.cursor()
            for r in results:
                score_json = json.dumps(r.score_breakdown)
                metric_json = json.dumps(r.metric_statuses)
                created_at_val = r.created_at if is_postgres else r.created_at.isoformat()

                values = (
                    r.id,
                    r.run_id,
                    r.canonical_company_id,
                    r.ticker,
                    r.company_name,
                    r.country,
                    r.exchange,
                    r.sector,
                    r.rank,
                    r.score,
                    r.display_price,
                    r.market_cap_display,
                    r.display_currency,
                    r.fwd_pe,
                    r.peg,
                    r.ev_ebitda,
                    r.beta,
                    r.nd_ebitda,
                    r.yield_pct,
                    r.eps_growth_pct,
                    r.data_confidence,
                    r.stage_status,
                    r.near_miss_status,
                    score_json,
                    metric_json,
                    created_at_val,
                )
                cursor.execute(insert_sql, values)
            conn.commit()
            return len(results)
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to batch insert screening results: {e}")
            raise
        finally:
            conn.close()

    def get_results_by_run(
        self,
        run_id: str,
        view: str = "top20",
        sector: Optional[str] = None,
        limit: int = 100,
    ) -> List[ScreeningResultRecord]:
        """Query results for a run filtered by tab view ('top20', 'rank_near_misses', 'rule_near_misses', 'all')."""
        conn = db_manager.get_connection()
        is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        conditions = ["run_id = %s" if is_postgres else "run_id = ?"]
        params: List[Any] = [run_id]

        if view == "top20":
            conditions.append("stage_status = 'passed' AND rank <= 20")
        elif view == "rank_near_misses":
            conditions.append("near_miss_status = 'rank_near_miss'")
        elif view == "rule_near_misses":
            conditions.append("near_miss_status = 'rule_near_miss'")

        if sector and sector != "All":
            conditions.append("sector = %s" if is_postgres else "sector = ?")
            params.append(sector)

        query = f"SELECT * FROM screening_results WHERE {' AND '.join(conditions)} ORDER BY rank ASC LIMIT {limit}"

        try:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [self._row_to_result(row, is_postgres) for row in rows]
        finally:
            conn.close()

    # -------------------------------------------------------------
    # ROW PARSERS
    # -------------------------------------------------------------

    def _row_to_run(self, row: Any, is_postgres: bool) -> ScreeningRunRecord:
        if is_postgres:
            return ScreeningRunRecord(
                run_id=row[0],
                status=row[1],
                provider=row[2],
                rule_version_id=row[3],
                profile_name=row[4],
                display_currency=row[5] or "USD",
                selected_countries=row[6] if isinstance(row[6], list) else json.loads(row[6] or "[]"),
                selected_exchanges=row[7] if isinstance(row[7], list) else json.loads(row[7] or "[]"),
                rules_snapshot=row[8] if isinstance(row[8], list) else json.loads(row[8] or "[]"),
                duration_ms=float(row[9] or 0.0),
                started_at=row[10] if isinstance(row[10], datetime) else datetime.fromisoformat(str(row[10])),
                completed_at=row[11] if (row[11] is None or isinstance(row[11], datetime)) else datetime.fromisoformat(str(row[11])),
                error_message=row[12],
            )
        else:
            return ScreeningRunRecord(
                run_id=row["run_id"],
                status=row["status"],
                provider=row["provider"],
                rule_version_id=row["rule_version_id"],
                profile_name=row["profile_name"],
                display_currency=row["display_currency"] or "USD",
                selected_countries=json.loads(row["selected_countries"] or "[]"),
                selected_exchanges=json.loads(row["selected_exchanges"] or "[]"),
                rules_snapshot=json.loads(row["rules_snapshot"] or "[]"),
                duration_ms=float(row["duration_ms"] or 0.0),
                started_at=datetime.fromisoformat(str(row["started_at"])),
                completed_at=datetime.fromisoformat(str(row["completed_at"])) if row["completed_at"] else None,
                error_message=row["error_message"],
            )

    def _row_to_result(self, row: Any, is_postgres: bool) -> ScreeningResultRecord:
        if is_postgres:
            return ScreeningResultRecord(
                id=row[0],
                run_id=row[1],
                canonical_company_id=row[2],
                ticker=row[3],
                company_name=row[4],
                country=row[5],
                exchange=row[6],
                sector=row[7],
                rank=row[8],
                score=row[9],
                display_price=row[10],
                market_cap_display=row[11],
                display_currency=row[12] or "USD",
                fwd_pe=row[13],
                peg=row[14],
                ev_ebitda=row[15],
                beta=row[16],
                nd_ebitda=row[17],
                yield_pct=row[18],
                eps_growth_pct=row[19],
                data_confidence=row[20] or "High",
                stage_status=row[21] or "passed",
                near_miss_status=row[22] or "none",
                score_breakdown=row[23] if isinstance(row[23], list) else json.loads(row[23] or "[]"),
                metric_statuses=row[24] if isinstance(row[24], dict) else json.loads(row[24] or "{}"),
                created_at=row[25] if isinstance(row[25], datetime) else datetime.fromisoformat(str(row[25])),
            )
        else:
            return ScreeningResultRecord(
                id=row["id"],
                run_id=row["run_id"],
                canonical_company_id=row["canonical_company_id"],
                ticker=row["ticker"],
                company_name=row["company_name"],
                country=row["country"],
                exchange=row["exchange"],
                sector=row["sector"],
                rank=row["rank"],
                score=row["score"],
                display_price=row["display_price"],
                market_cap_display=row["market_cap_display"],
                display_currency=row["display_currency"] or "USD",
                fwd_pe=row["fwd_pe"],
                peg=row["peg"],
                ev_ebitda=row["ev_ebitda"],
                beta=row["beta"],
                nd_ebitda=row["nd_ebitda"],
                yield_pct=row["yield_pct"],
                eps_growth_pct=row["eps_growth_pct"],
                data_confidence=row["data_confidence"] or "High",
                stage_status=row["stage_status"] or "passed",
                near_miss_status=row["near_miss_status"] or "none",
                score_breakdown=json.loads(row["score_breakdown"] or "[]"),
                metric_statuses=json.loads(row["metric_statuses"] or "{}"),
                created_at=datetime.fromisoformat(str(row["created_at"])),
            )


# Global repository instance
screening_repository = ScreeningRepository()
