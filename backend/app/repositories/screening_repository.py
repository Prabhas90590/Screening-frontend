"""Repository for screening runs, funnel metrics, and company results in PostgreSQL."""

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
    """SQL repository for screening_runs, funnel_counts, and screening_results in PostgreSQL."""

    def __init__(self):
        db_manager.init_tables()

    # -------------------------------------------------------------
    # SCREENING RUNS
    # -------------------------------------------------------------

    def save_run(self, run: ScreeningRunRecord) -> str:
        """Insert or update a screening run record."""
        conn = db_manager.get_connection()

        insert_sql = """
            INSERT INTO screening_runs (
                run_id, status, provider, rule_version_id, profile_name,
                display_currency, selected_countries, selected_exchanges,
                rules_snapshot, duration_ms, started_at, completed_at, error_message, trigger_type, notification_email, owner_email
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (run_id) DO UPDATE SET
                status = EXCLUDED.status,
                completed_at = EXCLUDED.completed_at,
                duration_ms = EXCLUDED.duration_ms,
                error_message = EXCLUDED.error_message,
                trigger_type = EXCLUDED.trigger_type,
                notification_email = EXCLUDED.notification_email,
                owner_email = COALESCE(EXCLUDED.owner_email, screening_runs.owner_email);
        """

        countries_json = json.dumps(run.selected_countries)
        exchanges_json = json.dumps(run.selected_exchanges)
        rules_json = json.dumps(run.rules_snapshot)

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
            run.started_at,
            run.completed_at,
            run.error_message,
            run.trigger_type or "instant",
            run.notification_email,
            run.owner_email,
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
        """Fetch screening run by ID with joined funnel counts."""
        conn = db_manager.get_connection()
        query = """
            SELECT 
                r.run_id, r.status, r.provider, r.rule_version_id, r.profile_name,
                r.display_currency, r.selected_countries, r.selected_exchanges,
                r.rules_snapshot, r.duration_ms, r.started_at, r.completed_at,
                r.error_message,
                COALESCE(f.universe_count, 0) as universe_count,
                COALESCE(f.selected_count, 0) as selected_count,
                COALESCE(r.trigger_type, 'instant') as trigger_type,
                r.notification_email,
                r.owner_email
            FROM screening_runs r
            LEFT JOIN funnel_counts f ON r.run_id = f.run_id
            WHERE r.run_id = %s
        """

        try:
            cursor = conn.cursor()
            cursor.execute(query, (run_id,))
            row = cursor.fetchone()
            if not row:
                return None
            col_names = [desc[0] for desc in cursor.description]
            row_dict = dict(zip(col_names, row))
            return self._row_to_run(row_dict)
        finally:
            conn.close()

    def list_runs(self, limit: int = 50, owner_email: Optional[str] = None) -> List[ScreeningRunRecord]:
        """List historical screening runs ordered by start time descending."""
        if not owner_email:
            return []

        conn = db_manager.get_connection()
        where_clause = "WHERE LOWER(r.owner_email) = LOWER(%s)"
        params: list = [owner_email, limit]

        query = f"""
            SELECT 
                r.run_id, r.status, r.provider, r.rule_version_id, r.profile_name,
                r.display_currency, r.selected_countries, r.selected_exchanges,
                r.rules_snapshot, r.duration_ms, r.started_at, r.completed_at,
                r.error_message,
                COALESCE(f.universe_count, 0) as universe_count,
                COALESCE(f.selected_count, 0) as selected_count,
                COALESCE(r.trigger_type, 'instant') as trigger_type,
                r.notification_email,
                r.owner_email
            FROM screening_runs r
            LEFT JOIN funnel_counts f ON r.run_id = f.run_id
            {where_clause}
            ORDER BY r.started_at DESC
            LIMIT %s
        """

        try:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            col_names = [desc[0] for desc in cursor.description]
            rows = [dict(zip(col_names, r)) for r in cursor.fetchall()]
            return [self._row_to_run(row) for row in rows]
        finally:
            conn.close()

    def delete_run(self, run_id: str) -> bool:
        """Permanently delete a single screening run and its associated records."""
        conn = db_manager.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM screening_results WHERE run_id = %s", (run_id,))
            cursor.execute("DELETE FROM funnel_counts WHERE run_id = %s", (run_id,))
            cursor.execute("DELETE FROM raw_responses WHERE run_id = %s", (run_id,))
            cursor.execute("DELETE FROM decisions WHERE run_id = %s", (run_id,))
            cursor.execute("DELETE FROM screening_runs WHERE run_id = %s", (run_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            logger.info(f"[REPOSITORY:DELETE_RUN] Successfully deleted run '{run_id}' (affected: {deleted})")
            return deleted
        except Exception as e:
            conn.rollback()
            logger.error(f"[REPOSITORY:DELETE_RUN:ERROR] Could not delete run '{run_id}': {e}")
            raise
        finally:
            conn.close()

    def clear_all_runs(self) -> int:
        """Permanently delete all screening runs and their results."""
        conn = db_manager.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM screening_results")
            cursor.execute("DELETE FROM funnel_counts")
            cursor.execute("DELETE FROM raw_responses")
            cursor.execute("DELETE FROM decisions")
            cursor.execute("DELETE FROM screening_runs")
            count = cursor.rowcount
            conn.commit()
            logger.info("[REPOSITORY:CLEAR_RUNS] Successfully cleared all screening runs")
            return count
        except Exception as e:
            conn.rollback()
            logger.error(f"[REPOSITORY:CLEAR_RUNS:ERROR] Could not clear screening runs: {e}")
            raise
        finally:
            conn.close()

    # -------------------------------------------------------------
    # FUNNEL COUNTS
    # -------------------------------------------------------------

    def save_funnel_counts(self, funnel: FunnelCountRecord) -> str:
        """Insert or update funnel stage progression for a run."""
        conn = db_manager.get_connection()

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
        """

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
            funnel.created_at,
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
        query = "SELECT * FROM funnel_counts WHERE run_id = %s"

        try:
            cursor = conn.cursor()
            cursor.execute(query, (run_id,))
            row = cursor.fetchone()
            if not row:
                return None
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
        finally:
            conn.close()

    # -------------------------------------------------------------
    # SCREENING RESULTS
    # -------------------------------------------------------------

    def save_results_batch(self, results: List[ScreeningResultRecord]) -> int:
        """Insert a batch of screened securities for a run using fast PostgreSQL execute_values."""
        if not results:
            return 0

        conn = db_manager.get_connection()
        deduped_results = list({r.id: r for r in results}.values())

        try:
            cursor = conn.cursor()
            from psycopg2.extras import execute_values
            pg_insert_sql = """
                INSERT INTO screening_results (
                    id, run_id, canonical_company_id, ticker, company_name,
                    country, exchange, sector, rank, score,
                    display_price, market_cap_display, display_currency,
                    fwd_pe, peg, ev_ebitda, beta, nd_ebitda, yield_pct, eps_growth_pct,
                    pe_vs_benchmark, price_to_sales, price_to_cash_flow, revenue_growth_fwd, avg_daily_volume, avg_daily_traded_value,
                    data_confidence, stage_status, near_miss_status,
                    score_breakdown, metric_statuses, created_at
                ) VALUES %s
                ON CONFLICT (id) DO UPDATE SET
                    rank = EXCLUDED.rank,
                    score = EXCLUDED.score,
                    display_price = EXCLUDED.display_price,
                    market_cap_display = EXCLUDED.market_cap_display;
            """
            value_tuples = [
                (
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
                    r.pe_vs_benchmark,
                    r.price_to_sales,
                    r.price_to_cash_flow,
                    r.revenue_growth_fwd,
                    r.avg_daily_volume,
                    r.avg_daily_traded_value,
                    r.data_confidence,
                    r.stage_status,
                    r.near_miss_status,
                    json.dumps(r.score_breakdown),
                    json.dumps(r.metric_statuses),
                    r.created_at,
                )
                for r in deduped_results
            ]
            execute_values(cursor, pg_insert_sql, value_tuples, page_size=1000)
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

        conditions = ["run_id = %s"]
        params: List[Any] = [run_id]

        if view == "top20":
            conditions.append("stage_status = 'passed' AND rank <= 20")
        elif view == "rank_near_misses":
            conditions.append("near_miss_status = 'rank_near_miss'")
        elif view == "rule_near_misses":
            conditions.append("near_miss_status = 'rule_near_miss'")

        if sector and sector != "All":
            conditions.append("sector = %s")
            params.append(sector)

        query = f"SELECT * FROM screening_results WHERE {' AND '.join(conditions)} ORDER BY rank ASC LIMIT {limit}"

        try:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            col_names = [desc[0] for desc in cursor.description]
            rows = [dict(zip(col_names, r)) for r in cursor.fetchall()]
            return [self._row_to_result(row) for row in rows]
        finally:
            conn.close()

    # -------------------------------------------------------------
    # ROW PARSERS
    # -------------------------------------------------------------

    def _row_to_run(self, row: Any) -> ScreeningRunRecord:
        if isinstance(row, dict):
            countries = row.get("selected_countries")
            if isinstance(countries, str):
                countries = json.loads(countries or "[]")
            elif not isinstance(countries, list):
                countries = []

            exchanges = row.get("selected_exchanges")
            if isinstance(exchanges, str):
                exchanges = json.loads(exchanges or "[]")
            elif not isinstance(exchanges, list):
                exchanges = []

            rules_snap = row.get("rules_snapshot")
            if isinstance(rules_snap, str):
                rules_snap = json.loads(rules_snap or "[]")
            elif not isinstance(rules_snap, list):
                rules_snap = []

            started = row.get("started_at")
            if not isinstance(started, datetime):
                started = datetime.fromisoformat(str(started)) if started else datetime.utcnow()

            completed = row.get("completed_at")
            if completed and not isinstance(completed, datetime):
                completed = datetime.fromisoformat(str(completed))

            return ScreeningRunRecord(
                run_id=row.get("run_id", ""),
                status=row.get("status", "succeeded"),
                provider=row.get("provider", "mock"),
                rule_version_id=row.get("rule_version_id"),
                profile_name=row.get("profile_name"),
                display_currency=row.get("display_currency") or "USD",
                selected_countries=countries,
                selected_exchanges=exchanges,
                rules_snapshot=rules_snap,
                duration_ms=float(row.get("duration_ms") or 0.0),
                started_at=started,
                completed_at=completed,
                error_message=row.get("error_message"),
                universe_count=int(row.get("universe_count") or 0),
                selected_count=int(row.get("selected_count") or 0),
                trigger_type=row.get("trigger_type") or "instant",
                notification_email=row.get("notification_email"),
                owner_email=row.get("owner_email"),
            )
        else:
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
                universe_count=int(row[13]) if len(row) > 13 and row[13] is not None and str(row[13]).isdigit() else 0,
                selected_count=int(row[14]) if len(row) > 14 and row[14] is not None and str(row[14]).isdigit() else 0,
                trigger_type=row[15] if len(row) > 15 and row[15] is not None else "instant",
                notification_email=row[16] if len(row) > 16 else None,
                owner_email=row[17] if len(row) > 17 else None,
            )

    def _row_to_result(self, row: Any) -> ScreeningResultRecord:
        if isinstance(row, dict):
            score_b = row.get("score_breakdown")
            if isinstance(score_b, str):
                score_b = json.loads(score_b or "[]")
            elif not isinstance(score_b, list):
                score_b = []

            metrics_s = row.get("metric_statuses")
            if isinstance(metrics_s, str):
                metrics_s = json.loads(metrics_s or "{}")
            elif not isinstance(metrics_s, dict):
                metrics_s = {}

            created = row.get("created_at")
            if not isinstance(created, datetime):
                created = datetime.fromisoformat(str(created)) if created else datetime.utcnow()

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
                display_price=row.get("display_price"),
                market_cap_display=row.get("market_cap_display"),
                display_currency=row.get("display_currency") or "USD",
                fwd_pe=row.get("fwd_pe"),
                peg=row.get("peg"),
                ev_ebitda=row.get("ev_ebitda"),
                beta=row.get("beta"),
                nd_ebitda=row.get("nd_ebitda"),
                yield_pct=row.get("yield_pct"),
                eps_growth_pct=row.get("eps_growth_pct"),
                pe_vs_benchmark=row.get("pe_vs_benchmark"),
                price_to_sales=row.get("price_to_sales"),
                price_to_cash_flow=row.get("price_to_cash_flow"),
                revenue_growth_fwd=row.get("revenue_growth_fwd"),
                avg_daily_volume=row.get("avg_daily_volume"),
                avg_daily_traded_value=row.get("avg_daily_traded_value"),
                data_confidence=row.get("data_confidence") or "High",
                stage_status=row.get("stage_status") or "passed",
                near_miss_status=row.get("near_miss_status") or "none",
                score_breakdown=score_b,
                metric_statuses=metrics_s,
                created_at=created,
            )
        else:
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
                pe_vs_benchmark=row[20],
                price_to_sales=row[21],
                price_to_cash_flow=row[22],
                revenue_growth_fwd=row[23],
                avg_daily_volume=row[24],
                avg_daily_traded_value=row[25],
                data_confidence=row[26] or "High",
                stage_status=row[27] or "passed",
                near_miss_status=row[28] or "none",
                score_breakdown=row[29] if isinstance(row[29], list) else json.loads(row[29] or "[]"),
                metric_statuses=row[30] if isinstance(row[30], dict) else json.loads(row[30] or "{}"),
                created_at=row[31] if isinstance(row[31], datetime) else datetime.fromisoformat(str(row[31])),
            )


# Global repository instance
screening_repository = ScreeningRepository()
