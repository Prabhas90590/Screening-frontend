"""Institutional Automated Scheduler Service (Phase 17).

Provides background recurring screening execution, next-run calculations,
multi-cadence scheduling (Daily, Weekly, Monthly, Custom), and multi-schedule persistence.
"""

import asyncio
from datetime import date, datetime, time, timedelta, timezone
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import DiagnosticLogger
from app.db.connection import db_manager
from app.db.ownership import build_owner_filter, is_record_owned_by, resolve_user_identity
from app.schemas.schedule import NextRunItemSchema, ScheduleConfigSchema, ScheduleResponse
from app.schemas.screening import ScreeningRunRequest

logger = DiagnosticLogger("scheduler_service")

IST_TZ = timezone(timedelta(hours=5, minutes=30))
UTC_TZ = timezone.utc
DAY_MAP = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

CADENCE_TABLES = {
    "daily": "schedules_daily",
    "weekly": "schedules_weekly",
    "monthly": "schedules_monthly",
    "custom": "schedules_custom",
}
ALL_CADENCE_TABLES = ["schedules_daily", "schedules_weekly", "schedules_monthly", "schedules_custom"]
_SCHEDULE_COLS = [
    "schedule_id", "frequency", "day_of_week", "time_of_day", "is_enabled",
    "auto_run", "notify_on_complete", "profile_id", "profile_name",
    "notification_email", "timezone", "daily_type", "active_days",
    "day_of_month", "cron_expression", "skip_holidays", "refresh_data_first",
    "notify_triggers", "last_run_at", "next_run_at", "updated_at",
    "owner_email", "user_id",
]
_SCHEDULE_SELECT_SQL = ", ".join(_SCHEDULE_COLS)


def get_tz(tz_name: str):
    """Resolve target timezone using Python standard zoneinfo with robust fallback."""
    if not tz_name:
        return IST_TZ
    clean = tz_name.strip()
    try:
        from zoneinfo import ZoneInfo
        alias_map = {
            "IST": "Asia/Kolkata",
            "EST": "America/New_York",
            "EDT": "America/New_York",
            "CST": "America/Chicago",
            "CDT": "America/Chicago",
            "PST": "America/Los_Angeles",
            "PDT": "America/Los_Angeles",
            "GMT": "Europe/London",
            "BST": "Europe/London",
            "JST": "Asia/Tokyo",
            "SGT": "Asia/Singapore",
            "HKT": "Asia/Hong_Kong",
        }
        target = alias_map.get(clean.upper(), clean)
        return ZoneInfo(target)
    except Exception:
        if clean in ("Asia/Kolkata", "IST", "Asia/Calcutta"):
            return IST_TZ
        if clean in ("UTC", "GMT"):
            return UTC_TZ
        return IST_TZ


class SchedulerService:
    """Manages automated screening schedules and executes background runs."""

    def __init__(self):
        self._loop_task: Optional[asyncio.Task] = None
        self._running: bool = False

    def calculate_next_runs(
        self,
        config: ScheduleConfigSchema,
        count: int = 3,
        ref_dt: Optional[datetime] = None,
    ) -> List[datetime]:
        """Calculate the next upcoming execution datetimes based on schedule configuration."""
        tz = get_tz(config.timezone)
        now = ref_dt or datetime.now(tz)
        if now.tzinfo is None:
            now = now.replace(tzinfo=tz)
        else:
            # Always evaluate calendar date and clock comparisons in the schedule's configured timezone.
            now = now.astimezone(tz)

        # Parse time of day
        try:
            parts = config.time_of_day.strip().split(":")
            h, m = int(parts[0]), int(parts[1])
            target_time = time(h, m)
        except Exception:
            target_time = time(8, 30)

        runs: List[datetime] = []
        freq = (config.frequency or "Daily").capitalize()

        if freq == "Daily":
            active_days = config.active_days if config.active_days is not None else ["mon", "tue", "wed", "thu", "fri"]
            target_weekdays = set(DAY_MAP.get(d.lower()[:3], 0) for d in active_days if d)
            cursor = now.date()
            for _ in range(45):
                dt_cand = datetime.combine(cursor, target_time, tzinfo=tz)
                is_valid = True
                if config.daily_type == "trading_days" and cursor.weekday() >= 5:
                    is_valid = False
                if cursor.weekday() not in target_weekdays:
                    is_valid = False

                if is_valid and dt_cand > now:
                    runs.append(dt_cand)
                    if len(runs) >= count:
                        break
                cursor += timedelta(days=1)

        elif freq == "Weekly":
            active_days = config.active_days or ["mon"]
            target_weekdays = set(DAY_MAP.get(d.lower(), 0) for d in active_days) or {0}
            cursor = now.date()
            for _ in range(90):
                dt_cand = datetime.combine(cursor, target_time, tzinfo=tz)
                if cursor.weekday() in target_weekdays and dt_cand > now:
                    runs.append(dt_cand)
                    if len(runs) >= count:
                        break
                cursor += timedelta(days=1)

        elif freq == "Monthly":
            dom = max(1, min(config.day_of_month or 1, 31))
            cursor = now.date()
            for _ in range(120):
                try:
                    target_day = min(dom, 28)
                    cand_date = date(cursor.year, cursor.month, target_day)
                    dt_cand = datetime.combine(cand_date, target_time, tzinfo=tz)
                    if dt_cand > now and (not runs or runs[-1].month != dt_cand.month):
                        runs.append(dt_cand)
                        if len(runs) >= count:
                            break
                except Exception:
                    pass
                if cursor.month == 12:
                    cursor = date(cursor.year + 1, 1, 1)
                else:
                    cursor = date(cursor.year, cursor.month + 1, 1)

        elif freq == "Custom":
            cursor = now.date()
            for _ in range(45):
                dt_cand = datetime.combine(cursor, target_time, tzinfo=tz)
                if cursor.weekday() < 5 and dt_cand > now:
                    runs.append(dt_cand)
                    if len(runs) >= count:
                        break
                cursor += timedelta(days=1)

        return runs

    @staticmethod
    def _clean_profile_name(raw_name: Optional[str]) -> Optional[str]:
        if raw_name is None:
            return None
        cleaned = str(raw_name).strip()
        if not cleaned or cleaned.lower() in ("none", "null"):
            return None
        return cleaned

    @staticmethod
    def _build_schedule_where(
        schedule_id: Optional[str] = None,
        owner_email: Optional[str] = None,
        user_id: Optional[str] = None,
        allow_unscoped: bool = False,
    ) -> Tuple[str, Tuple[Any, ...]]:
        """Build parameterized WHERE clause for schedule tables with optional owner scoping."""
        clauses: List[str] = []
        params: List[Any] = []
        if schedule_id is not None:
            clauses.append("schedule_id = %s")
            params.append(schedule_id)
        if owner_email or user_id:
            owner_clause, owner_params = build_owner_filter(user_id=user_id, owner_email=owner_email)
            clauses.append(owner_clause)
            params.extend(owner_params)
        elif not allow_unscoped:
            clauses.append("1 = 0")
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        return where_sql, tuple(params)

    def _resolve_schedule_owner(
        self, config: ScheduleConfigSchema, prof: Any = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """Resolve the owning account email and user ID for background run execution."""
        owner_email = config.owner_email or (getattr(prof, "owner_email", None) if prof else None)
        user_id = config.user_id or (getattr(prof, "user_id", None) if prof else None)
        if owner_email or user_id:
            resolved_uid, resolved_email = resolve_user_identity(user_id=user_id, owner_email=owner_email)
            return resolved_email or owner_email, resolved_uid or user_id

        if config.notification_email:
            for candidate in str(config.notification_email).split(","):
                addr = candidate.strip()
                if addr:
                    resolved_uid, resolved_email = resolve_user_identity(owner_email=addr)
                    if resolved_uid and resolved_email:
                        return resolved_email, resolved_uid

        return None, None

    def _row_to_config(self, d: Dict[str, Any]) -> ScheduleConfigSchema:
        trig = d.get("notify_triggers")
        if isinstance(trig, str):
            try:
                trig = json.loads(trig)
            except Exception:
                trig = {}
        elif not isinstance(trig, dict):
            trig = {"runCompletes": True, "runFails": True, "dataBlockers": True}

        raw_days = d.get("active_days")
        if isinstance(raw_days, str):
            act_days = [x.strip() for x in raw_days.split(",") if x.strip()]
        elif isinstance(raw_days, list):
            act_days = raw_days
        else:
            act_days = ["mon", "tue", "wed", "thu", "fri"]

        cfg = ScheduleConfigSchema(
            schedule_id=d.get("schedule_id") or "default-schedule",
            profile_id=d.get("profile_id"),
            profile_name=self._clean_profile_name(d.get("profile_name")) or "Default Strategy",
            frequency=d.get("frequency") or "Daily",
            daily_type=d.get("daily_type") or "trading_days",
            active_days=act_days,
            day_of_month=d.get("day_of_month") or 1,
            time_of_day=d.get("time_of_day") or "08:30",
            timezone=d.get("timezone") or "Asia/Kolkata",
            cron_expression=d.get("cron_expression") or "0 9 * * 1-5",
            is_enabled=bool(d.get("is_enabled", True)),
            auto_run=bool(d.get("auto_run", True)),
            refresh_data_first=bool(d.get("refresh_data_first", True)),
            skip_holidays=bool(d.get("skip_holidays", True)),
            notify_on_complete=bool(d.get("notify_on_complete", True)),
            notification_email=d.get("notification_email"),
            notify_triggers=trig,
            last_run_at=d.get("last_run_at"),
            next_run_at=d.get("next_run_at"),
            owner_email=d.get("owner_email"),
            user_id=d.get("user_id"),
            updated_at=d.get("updated_at"),
        )
        if not cfg.next_run_at:
            runs = self.calculate_next_runs(cfg, count=1)
            if runs:
                cfg.next_run_at = runs[0]
        return cfg

    def list_schedules(
        self,
        cadence: Optional[str] = None,
        owner_email: Optional[str] = None,
        user_id: Optional[str] = None,
        include_all: bool = False,
    ) -> List[ScheduleConfigSchema]:
        """Fetch saved schedule configurations from cadence-specific tables (Daily, Weekly, Monthly, Custom)."""
        if not include_all and not owner_email and not user_id:
            return []

        db_manager.init_tables()
        conn = db_manager.get_connection()
        cols = _SCHEDULE_COLS

        target_tables = [CADENCE_TABLES[cadence.lower()]] if cadence and cadence.lower() in CADENCE_TABLES else ALL_CADENCE_TABLES
        results_map: Dict[str, ScheduleConfigSchema] = {}
        where_sql, where_params = self._build_schedule_where(
            owner_email=owner_email,
            user_id=user_id,
            allow_unscoped=include_all,
        )

        try:
            cursor = conn.cursor()
            for tbl in target_tables:
                try:
                    cursor.execute(
                        f"""
                        SELECT {_SCHEDULE_SELECT_SQL}
                        FROM {tbl}
                        {where_sql}
                        ORDER BY updated_at DESC, time_of_day ASC
                        """,
                        where_params,
                    )
                    rows = cursor.fetchall()
                    for row in rows:
                        d = dict(row) if hasattr(row, "keys") else {cols[i]: row[i] for i in range(len(cols))}
                        cfg = self._row_to_config(d)
                        if cfg.schedule_id not in results_map:
                            results_map[cfg.schedule_id] = cfg
                except Exception as table_err:
                    logger.debug(f"Table {tbl} read notice: {table_err}")

            # If cadence-specific tables had no records, fallback to unified schedules table
            if not results_map and not cadence:
                try:
                    cursor.execute(
                        f"""
                        SELECT {_SCHEDULE_SELECT_SQL}
                        FROM schedules
                        {where_sql}
                        ORDER BY updated_at DESC, time_of_day ASC
                        """,
                        where_params,
                    )
                    for row in cursor.fetchall():
                        d = dict(row) if hasattr(row, "keys") else {cols[i]: row[i] for i in range(len(cols))}
                        cfg = self._row_to_config(d)
                        if cfg.schedule_id not in results_map:
                            results_map[cfg.schedule_id] = cfg
                except Exception:
                    pass

            sorted_list = sorted(
                results_map.values(),
                key=lambda x: str(x.updated_at or ""),
                reverse=True
            )
            return sorted_list
        except Exception as e:
            logger.warning(f"Could not load schedules from database: {e}")
            return []
        finally:
            conn.close()

    def get_schedule(
        self,
        schedule_id: str = "default-schedule",
        owner_email: Optional[str] = None,
        user_id: Optional[str] = None,
        allow_unscoped: bool = False,
    ) -> Optional[ScheduleConfigSchema]:
        """Fetch a specific schedule configuration across all cadence tables."""
        if not allow_unscoped and not owner_email and not user_id:
            return None

        db_manager.init_tables()
        conn = db_manager.get_connection()
        cols = _SCHEDULE_COLS
        where_sql, params = self._build_schedule_where(
            schedule_id=schedule_id,
            owner_email=owner_email,
            user_id=user_id,
            allow_unscoped=allow_unscoped,
        )
        try:
            cursor = conn.cursor()

            # Search across dedicated cadence tables first
            for tbl in ALL_CADENCE_TABLES:
                try:
                    cursor.execute(
                        f"""
                        SELECT {_SCHEDULE_SELECT_SQL}
                        FROM {tbl}
                        {where_sql}
                        LIMIT 1
                        """,
                        params,
                    )
                    row = cursor.fetchone()
                    if row:
                        d = dict(row) if hasattr(row, "keys") else {cols[i]: row[i] for i in range(len(cols))}
                        return self._row_to_config(d)
                except Exception:
                    pass

            # Fallback to schedules table
            cursor.execute(
                f"""
                SELECT {_SCHEDULE_SELECT_SQL}
                FROM schedules
                {where_sql}
                LIMIT 1
                """,
                params,
            )
            row = cursor.fetchone()
            if row:
                d = dict(row) if hasattr(row, "keys") else {cols[i]: row[i] for i in range(len(cols))}
                return self._row_to_config(d)

            return None
        except Exception as e:
            logger.warning(f"Could not load schedule '{schedule_id}' from database: {e}")
            return None
        finally:
            conn.close()

    def save_schedule(self, config: ScheduleConfigSchema) -> ScheduleConfigSchema:
        """Persist schedule into its dedicated cadence table (schedules_daily, schedules_weekly, etc.)."""
        db_manager.init_tables()
        config.profile_name = self._clean_profile_name(config.profile_name) or "Default Strategy"
        resolved_uid, resolved_email = resolve_user_identity(
            user_id=config.user_id,
            owner_email=config.owner_email,
        )
        config.user_id = resolved_uid
        config.owner_email = resolved_email

        clean_time = (config.time_of_day or "08:30").replace(":", "")
        clean_freq = (config.frequency or "daily").lower()
        if not config.schedule_id or config.schedule_id == "default-schedule":
            uid_suffix = (resolved_uid or "").replace("-", "")[:6]
            config.schedule_id = (
                f"sched-{clean_freq}-{clean_time}-{uid_suffix}"
                if uid_suffix
                else f"sched-{clean_freq}-{clean_time}"
            )

        existing = self.get_schedule(config.schedule_id, allow_unscoped=True)
        if existing and (existing.user_id or existing.owner_email):
            if not is_record_owned_by(
                record_user_id=existing.user_id,
                record_owner_email=existing.owner_email,
                current_user_id=resolved_uid,
                current_user_email=resolved_email,
            ):
                raise PermissionError(f"Schedule '{config.schedule_id}' belongs to another user account.")

        conn = db_manager.get_connection()
        try:
            if clean_freq == "daily":
                if not config.active_days:
                    config.active_days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] if config.daily_type == "all_days" else ["mon", "tue", "wed", "thu", "fri"]

            upcoming = self.calculate_next_runs(config, count=1)
            next_run = upcoming[0] if upcoming else None
            config.next_run_at = next_run
            now_utc = datetime.now(timezone.utc)

            cursor = conn.cursor()
            act_days_str = ",".join(config.active_days) if config.active_days is not None else "mon,tue,wed,thu,fri"
            trig_str = json.dumps(config.notify_triggers)

            target_table = CADENCE_TABLES.get(clean_freq, "schedules_daily")
            cleanup_where, cleanup_params = self._build_schedule_where(
                schedule_id=config.schedule_id,
                owner_email=resolved_email,
                user_id=resolved_uid,
                allow_unscoped=True,
            )

            # Remove from any other cadence tables in case frequency was changed
            for other_tbl in ALL_CADENCE_TABLES:
                if other_tbl != target_table:
                    try:
                        cursor.execute(f"DELETE FROM {other_tbl} {cleanup_where}", cleanup_params)
                    except Exception:
                        pass

            # Upsert into dedicated cadence table (and unified schedules table)
            upsert_values = (
                config.schedule_id, config.profile_id, config.profile_name,
                config.frequency, config.daily_type, act_days_str,
                config.day_of_month, config.time_of_day, config.timezone,
                config.cron_expression, config.is_enabled, config.auto_run,
                config.refresh_data_first, config.skip_holidays,
                config.notify_on_complete, config.notification_email,
                trig_str, config.last_run_at, next_run, config.owner_email,
                config.user_id, now_utc,
            )

            def _upsert_sql(table_name: str) -> str:
                return f"""
                    INSERT INTO {table_name} (
                        schedule_id, profile_id, profile_name, frequency, daily_type,
                        active_days, day_of_month, time_of_day, timezone, cron_expression,
                        is_enabled, auto_run, refresh_data_first, skip_holidays,
                        notify_on_complete, notification_email, notify_triggers,
                        last_run_at, next_run_at, owner_email, user_id, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (schedule_id) DO UPDATE SET
                        profile_id = EXCLUDED.profile_id,
                        profile_name = EXCLUDED.profile_name,
                        frequency = EXCLUDED.frequency,
                        daily_type = EXCLUDED.daily_type,
                        active_days = EXCLUDED.active_days,
                        day_of_month = EXCLUDED.day_of_month,
                        time_of_day = EXCLUDED.time_of_day,
                        timezone = EXCLUDED.timezone,
                        cron_expression = EXCLUDED.cron_expression,
                        is_enabled = EXCLUDED.is_enabled,
                        auto_run = EXCLUDED.auto_run,
                        refresh_data_first = EXCLUDED.refresh_data_first,
                        skip_holidays = EXCLUDED.skip_holidays,
                        notify_on_complete = EXCLUDED.notify_on_complete,
                        notification_email = EXCLUDED.notification_email,
                        notify_triggers = EXCLUDED.notify_triggers,
                        last_run_at = COALESCE(EXCLUDED.last_run_at, {table_name}.last_run_at),
                        next_run_at = EXCLUDED.next_run_at,
                        owner_email = COALESCE(EXCLUDED.owner_email, {table_name}.owner_email),
                        user_id = COALESCE(EXCLUDED.user_id, {table_name}.user_id),
                        updated_at = EXCLUDED.updated_at;
                """

            cursor.execute(_upsert_sql(target_table), upsert_values)
            try:
                cursor.execute(_upsert_sql("schedules"), upsert_values)
            except Exception as sync_err:
                logger.debug(f"Unified schedules sync notice: {sync_err}")


            conn.commit()
            logger.info(f"[SCHEDULER:SAVE] Saved distinct schedule '{config.schedule_id}' into table '{target_table}' ({config.frequency} @ {config.time_of_day}). Next run: {next_run}")
            return config
        except Exception as e:
            logger.error(f"[SCHEDULER:SAVE:ERROR] Failed to save schedule: {e}")
            raise
        finally:
            conn.close()

    def delete_schedule(
        self,
        schedule_id: str,
        owner_email: Optional[str] = None,
        user_id: Optional[str] = None,
        allow_unscoped: bool = False,
    ) -> bool:
        """Delete an individual schedule from all cadence tables."""
        if not allow_unscoped and not owner_email and not user_id:
            return False

        conn = db_manager.get_connection()
        try:
            cursor = conn.cursor()
            deleted_any = False
            where_sql, params = self._build_schedule_where(
                schedule_id=schedule_id,
                owner_email=owner_email,
                user_id=user_id,
                allow_unscoped=allow_unscoped,
            )

            for tbl in ALL_CADENCE_TABLES + ["schedules"]:
                try:
                    cursor.execute(f"DELETE FROM {tbl} {where_sql}", params)
                    if cursor.rowcount > 0:
                        deleted_any = True
                except Exception:
                    pass

            conn.commit()
            logger.info(f"[SCHEDULER:DELETE] Deleted schedule '{schedule_id}' across cadence tables: {deleted_any}")
            return deleted_any
        except Exception as e:
            logger.error(f"[SCHEDULER:DELETE:ERROR] Failed to delete schedule: {e}")
            return False
        finally:
            conn.close()

    def remove_day_from_schedule(
        self,
        schedule_id: str,
        day: str,
        owner_email: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[ScheduleConfigSchema]:
        """Remove a single specific day (e.g. 'wed') from a schedule's active_days list."""
        config = self.get_schedule(schedule_id, owner_email=owner_email, user_id=user_id)
        if not config:
            logger.warning(f"[SCHEDULER:REMOVE_DAY] Schedule '{schedule_id}' not found.")
            return None

        day_norm = day.strip().lower()[:3]
        current_days = [d.strip().lower()[:3] for d in (config.active_days or []) if d]
        updated_days = [d for d in current_days if d != day_norm]

        logger.info(f"[SCHEDULER:REMOVE_DAY] Schedule '{schedule_id}': removing day '{day_norm}' ({current_days} -> {updated_days})")
        config.active_days = updated_days

        if not updated_days:
            # If all active days were removed, pause the schedule
            config.is_enabled = False
            config.next_run_at = None
        else:
            upcoming = self.calculate_next_runs(config, count=1)
            config.next_run_at = upcoming[0] if upcoming else None

        return self.save_schedule(config)

    def calculate_all_next_runs(
        self,
        count_per_schedule: int = 5,
        cadence: Optional[str] = None,
        owner_email: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Tuple[List[str], List[NextRunItemSchema], Dict[str, List[str]]]:
        """Aggregate and sort next runs across enabled schedules, optionally filtered by cadence."""
        schedules = (
            self.list_schedules(cadence=cadence, owner_email=owner_email, user_id=user_id)
            if cadence and cadence.lower() != 'all'
            else self.list_schedules(owner_email=owner_email, user_id=user_id)
        )
        if not schedules:
            return [], [], {"Daily": [], "Weekly": [], "Monthly": [], "Custom": []}

        all_detailed: List[Tuple[datetime, NextRunItemSchema]] = []
        by_freq: Dict[str, List[str]] = {"Daily": [], "Weekly": [], "Monthly": [], "Custom": []}

        for s in schedules:
            if not s.is_enabled:
                continue
            dt_list = self.calculate_next_runs(s, count=count_per_schedule)
            freq_key = (s.frequency or "Daily").capitalize()
            for dt in dt_list:
                iso_str = dt.isoformat()
                if freq_key in by_freq:
                    by_freq[freq_key].append(iso_str)
                else:
                    by_freq["Custom"].append(iso_str)

                tz_val = s.timezone or "Asia/Kolkata"
                tz_short = "IST" if "Kolkata" in tz_val else ("EST" if "New_York" in tz_val else tz_val.split("/")[-1])
                label = f"{s.frequency} @ {s.time_of_day} {tz_short} ({s.profile_name or 'Strategy'})"
                item = NextRunItemSchema(
                    datetime=iso_str,
                    schedule_id=s.schedule_id,
                    frequency=s.frequency,
                    time_of_day=s.time_of_day,
                    profile_name=s.profile_name or "Default Strategy",
                    label=label,
                    notification_email=s.notification_email,
                    timezone=tz_val,
                )
                all_detailed.append((dt, item))

        all_detailed.sort(key=lambda x: x[0])
        for k in by_freq:
            by_freq[k].sort()

        flat_iso_list = [x[0].isoformat() for x in all_detailed]
        detailed_list = [x[1] for x in all_detailed]

        return flat_iso_list, detailed_list, by_freq

    async def execute_scheduled_run(self, schedule_id: str):
        """Execute a scheduled screening run via the unified screening service."""
        config = self.get_schedule(schedule_id, allow_unscoped=True)
        if not config:
            logger.warning(f"[SCHEDULER:ABORT] Schedule '{schedule_id}' does not exist (may have been deleted). Aborting execution.")
            return None
        if not config.is_enabled:
            logger.info(f"[SCHEDULER:SKIP] Schedule '{schedule_id}' is paused/disabled. Skipping execution.")
            return None

        from app.services.screening_service import screening_service
        from app.repositories.rule_repository import rule_repository

        target_countries = None
        target_exchanges = None
        target_prof_id = config.profile_id
        clean_prof_name = self._clean_profile_name(config.profile_name)
        exec_owner_email, exec_user_id = self._resolve_schedule_owner(config)
        prof = None
        if target_prof_id:
            if exec_owner_email or exec_user_id:
                prof = rule_repository.get_version_by_id(
                    target_prof_id,
                    owner_email=exec_owner_email,
                    user_id=exec_user_id,
                )
            else:
                prof = rule_repository.get_version_by_id(target_prof_id, allow_unscoped=True)
                exec_owner_email, exec_user_id = self._resolve_schedule_owner(config, prof=prof)

        if not exec_owner_email and not exec_user_id:
            logger.warning(
                f"[SCHEDULER:ABORT] Schedule '{schedule_id}' has no resolved owner; skipping unowned execution."
            )
            return None

        if not prof and clean_prof_name and clean_prof_name.lower() != "default strategy":
            all_profs = rule_repository.list_versions(owner_email=exec_owner_email, user_id=exec_user_id)
            for p in all_profs:
                v_num = getattr(p, "version_number", "1.0")
                if (
                    p.profile_name.strip().lower() == clean_prof_name.lower()
                    or f"{p.profile_name} - Version {v_num}".strip().lower() == clean_prof_name.lower()
                    or f"{p.profile_name} v{v_num}".strip().lower() == clean_prof_name.lower()
                ):
                    prof = p
                    target_prof_id = p.version_id
                    break

        if not prof and (exec_owner_email or exec_user_id):
            prof = rule_repository.get_active_version(owner_email=exec_owner_email, user_id=exec_user_id)
            if prof:
                target_prof_id = prof.version_id

        resolved_prof_name = clean_prof_name
        if prof and (not resolved_prof_name or resolved_prof_name.lower() == "default strategy"):
            v_num = getattr(prof, "version_number", "1.0")
            resolved_prof_name = f"{prof.profile_name} - Version {v_num}"

        logger.info(
            f"[SCHEDULER:RUN:START] Triggering scheduled run for profile '{resolved_prof_name or 'Active Strategy'}' "
            f"(Schedule: {schedule_id}, Owner: {exec_owner_email})"
        )

        if prof:
            div_rules = getattr(prof, "diversification_rules", None) or {}
            snapshot = div_rules.get("snapshot", {}) if isinstance(div_rules, dict) else {}
            if snapshot:
                saved_c = [c["id"].lower() for c in snapshot.get("countries", []) if c.get("selected")]
                saved_e = [e["id"].lower() for e in snapshot.get("exchanges", []) if e.get("selected")]
                if saved_c:
                    target_countries = saved_c
                if saved_e:
                    target_exchanges = saved_e

        request = ScreeningRunRequest(
            rule_version_id=target_prof_id if target_prof_id else None,
            profile_name=resolved_prof_name,
            notification_email=config.notification_email,
            trigger_type="scheduled",
            countries=target_countries,
            exchanges=target_exchanges,
        )

        now_utc = datetime.now(timezone.utc)
        try:
            response = await screening_service.initiate_screening_run(
                request,
                owner_email=exec_owner_email,
                user_id=exec_user_id,
            )
            logger.info(
                f"[SCHEDULER:RUN:COMPLETE] Scheduled run {response.run_id} finished with status='{response.status}'."
            )

            config.last_run_at = now_utc
            if exec_owner_email and not config.owner_email:
                config.owner_email = exec_owner_email
            if exec_user_id and not config.user_id:
                config.user_id = exec_user_id
            upcoming = self.calculate_next_runs(config, count=1, ref_dt=now_utc)
            config.next_run_at = upcoming[0] if upcoming else None
            self.save_schedule(config)

            return response
        except Exception as e:
            logger.error(f"[SCHEDULER:RUN:FAILED] Error executing scheduled run for '{schedule_id}': {e}")
            # Roll forward next_run_at so a failed run never traps the worker in a 10-second infinite retry loop.
            try:
                upcoming = self.calculate_next_runs(config, count=1, ref_dt=datetime.now(timezone.utc))
                config.next_run_at = upcoming[0] if upcoming else None
                self.save_schedule(config)
            except Exception as save_err:
                logger.warning(f"[SCHEDULER:ROLLFORWARD:ERROR] Could not advance next_run_at for '{schedule_id}': {save_err}")
            raise

    async def _scheduler_loop(self):
        """Background monitoring loop that checks for due runs across all schedules every 10s."""
        logger.info("[SCHEDULER:WORKER] Background scheduler daemon loop started.")
        while self._running:
            try:
                schedules = self.list_schedules(include_all=True)
                now_utc = datetime.now(timezone.utc)
                for config in schedules:
                    if config.is_enabled and config.auto_run and config.next_run_at:
                        next_dt = config.next_run_at
                        if next_dt.tzinfo is None:
                            next_dt = next_dt.replace(tzinfo=timezone.utc)

                        if now_utc >= next_dt:
                            logger.info(f"[SCHEDULER:TRIGGER] Scheduled time reached for '{config.schedule_id}' ({config.frequency} @ {config.time_of_day}). Firing pipeline...")
                            try:
                                await self.execute_scheduled_run(config.schedule_id)
                            except Exception as sched_err:
                                logger.warning(f"[SCHEDULER:WORKER:ERROR] Schedule '{config.schedule_id}' execution error: {sched_err}")

            except Exception as e:
                logger.warning(f"[SCHEDULER:WORKER:ERROR] Exception in scheduler loop: {e}")

            await asyncio.sleep(10)

    def start(self):
        """Start the background scheduler worker."""
        if not self._running:
            self._running = True
            try:
                loop = asyncio.get_running_loop()
                self._loop_task = loop.create_task(self._scheduler_loop())
                logger.info("[SCHEDULER] Background scheduler worker spawned.")
            except RuntimeError:
                logger.warning("[SCHEDULER] No running event loop to start background scheduler.")

    def stop(self):
        """Stop the background scheduler worker."""
        if self._running:
            self._running = False
            if self._loop_task and not self._loop_task.done():
                self._loop_task.cancel()
            logger.info("[SCHEDULER] Background scheduler worker stopped.")


scheduler_service = SchedulerService()
