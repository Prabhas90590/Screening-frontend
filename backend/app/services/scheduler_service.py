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
            profile_name=d.get("profile_name") or "Default Strategy",
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
            updated_at=d.get("updated_at"),
        )
        if not cfg.next_run_at:
            runs = self.calculate_next_runs(cfg, count=1)
            if runs:
                cfg.next_run_at = runs[0]
        return cfg

    def list_schedules(self, cadence: Optional[str] = None) -> List[ScheduleConfigSchema]:
        """Fetch saved schedule configurations from cadence-specific tables (Daily, Weekly, Monthly, Custom)."""
        conn = db_manager.get_connection()
        cols = [
            "schedule_id", "frequency", "day_of_week", "time_of_day", "is_enabled",
            "auto_run", "notify_on_complete", "profile_id", "profile_name",
            "notification_email", "timezone", "daily_type", "active_days",
            "day_of_month", "cron_expression", "skip_holidays", "refresh_data_first",
            "notify_triggers", "last_run_at", "next_run_at", "updated_at"
        ]
        
        target_tables = [CADENCE_TABLES[cadence.lower()]] if cadence and cadence.lower() in CADENCE_TABLES else ALL_CADENCE_TABLES
        results_map: Dict[str, ScheduleConfigSchema] = {}

        try:
            cursor = conn.cursor()
            for tbl in target_tables:
                try:
                    cursor.execute(
                        f"""
                        SELECT schedule_id, frequency, day_of_week, time_of_day, is_enabled,
                               auto_run, notify_on_complete, profile_id, profile_name,
                               notification_email, timezone, daily_type, active_days,
                               day_of_month, cron_expression, skip_holidays, refresh_data_first,
                               notify_triggers, last_run_at, next_run_at, updated_at
                        FROM {tbl}
                        ORDER BY updated_at DESC, time_of_day ASC
                        """
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
                        """
                        SELECT schedule_id, frequency, day_of_week, time_of_day, is_enabled,
                               auto_run, notify_on_complete, profile_id, profile_name,
                               notification_email, timezone, daily_type, active_days,
                               day_of_month, cron_expression, skip_holidays, refresh_data_first,
                               notify_triggers, last_run_at, next_run_at, updated_at
                        FROM schedules
                        ORDER BY updated_at DESC, time_of_day ASC
                        """
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

    def get_schedule(self, schedule_id: str = "default-schedule") -> Optional[ScheduleConfigSchema]:
        """Fetch a specific schedule configuration across all cadence tables."""
        conn = db_manager.get_connection()
        cols = [
            "schedule_id", "frequency", "day_of_week", "time_of_day", "is_enabled",
            "auto_run", "notify_on_complete", "profile_id", "profile_name",
            "notification_email", "timezone", "daily_type", "active_days",
            "day_of_month", "cron_expression", "skip_holidays", "refresh_data_first",
            "notify_triggers", "last_run_at", "next_run_at", "updated_at"
        ]
        try:
            cursor = conn.cursor()
            is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
            param = "%s" if is_postgres else "?"

            # Search across dedicated cadence tables first
            for tbl in ALL_CADENCE_TABLES:
                try:
                    cursor.execute(
                        f"""
                        SELECT schedule_id, frequency, day_of_week, time_of_day, is_enabled,
                               auto_run, notify_on_complete, profile_id, profile_name,
                               notification_email, timezone, daily_type, active_days,
                               day_of_month, cron_expression, skip_holidays, refresh_data_first,
                               notify_triggers, last_run_at, next_run_at, updated_at
                        FROM {tbl}
                        WHERE schedule_id = {param}
                        LIMIT 1
                        """,
                        (schedule_id,),
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
                SELECT schedule_id, frequency, day_of_week, time_of_day, is_enabled,
                       auto_run, notify_on_complete, profile_id, profile_name,
                       notification_email, timezone, daily_type, active_days,
                       day_of_month, cron_expression, skip_holidays, refresh_data_first,
                       notify_triggers, last_run_at, next_run_at, updated_at
                FROM schedules
                WHERE schedule_id = {param}
                LIMIT 1
                """,
                (schedule_id,),
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
        conn = db_manager.get_connection()
        try:
            clean_time = (config.time_of_day or "08:30").replace(":", "")
            clean_freq = (config.frequency or "daily").lower()
            if not config.schedule_id or config.schedule_id == "default-schedule":
                config.schedule_id = f"sched-{clean_freq}-{clean_time}"

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
            is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
            param = "%s" if is_postgres else "?"

            target_table = CADENCE_TABLES.get(clean_freq, "schedules_daily")

            # Remove from any other cadence tables in case frequency was changed
            for other_tbl in ALL_CADENCE_TABLES:
                if other_tbl != target_table:
                    try:
                        cursor.execute(f"DELETE FROM {other_tbl} WHERE schedule_id = {param}", (config.schedule_id,))
                    except Exception:
                        pass

            # Upsert into dedicated cadence table
            if is_postgres:
                cursor.execute(
                    f"""
                    INSERT INTO {target_table} (
                        schedule_id, profile_id, profile_name, frequency, daily_type,
                        active_days, day_of_month, time_of_day, timezone, cron_expression,
                        is_enabled, auto_run, refresh_data_first, skip_holidays,
                        notify_on_complete, notification_email, notify_triggers,
                        next_run_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
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
                        next_run_at = EXCLUDED.next_run_at,
                        updated_at = EXCLUDED.updated_at;
                    """,
                    (
                        config.schedule_id, config.profile_id, config.profile_name,
                        config.frequency, config.daily_type, act_days_str,
                        config.day_of_month, config.time_of_day, config.timezone,
                        config.cron_expression, config.is_enabled, config.auto_run,
                        config.refresh_data_first, config.skip_holidays,
                        config.notify_on_complete, config.notification_email,
                        trig_str, next_run, now_utc,
                    ),
                )
                # Also sync unified schedules table
                try:
                    cursor.execute(
                        """
                        INSERT INTO schedules (
                            schedule_id, profile_id, profile_name, frequency, daily_type,
                            active_days, day_of_month, time_of_day, timezone, cron_expression,
                            is_enabled, auto_run, refresh_data_first, skip_holidays,
                            notify_on_complete, notification_email, notify_triggers,
                            next_run_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
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
                            next_run_at = EXCLUDED.next_run_at,
                            updated_at = EXCLUDED.updated_at;
                        """,
                        (
                            config.schedule_id, config.profile_id, config.profile_name,
                            config.frequency, config.daily_type, act_days_str,
                            config.day_of_month, config.time_of_day, config.timezone,
                            config.cron_expression, config.is_enabled, config.auto_run,
                            config.refresh_data_first, config.skip_holidays,
                            config.notify_on_complete, config.notification_email,
                            trig_str, next_run, now_utc,
                        ),
                    )
                except Exception:
                    pass
            else:
                cursor.execute(
                    f"""
                    INSERT OR REPLACE INTO {target_table} (
                        schedule_id, profile_id, profile_name, frequency, daily_type,
                        active_days, day_of_month, time_of_day, timezone, cron_expression,
                        is_enabled, auto_run, refresh_data_first, skip_holidays,
                        notify_on_complete, notification_email, notify_triggers,
                        next_run_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        config.schedule_id, config.profile_id, config.profile_name,
                        config.frequency, config.daily_type, act_days_str,
                        config.day_of_month, config.time_of_day, config.timezone,
                        config.cron_expression, int(config.is_enabled), int(config.auto_run),
                        int(config.refresh_data_first), int(config.skip_holidays),
                        int(config.notify_on_complete), config.notification_email,
                        trig_str, str(next_run) if next_run else None, str(now_utc),
                    ),
                )
                try:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO schedules (
                            schedule_id, profile_id, profile_name, frequency, daily_type,
                            active_days, day_of_month, time_of_day, timezone, cron_expression,
                            is_enabled, auto_run, refresh_data_first, skip_holidays,
                            notify_on_complete, notification_email, notify_triggers,
                            next_run_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            config.schedule_id, config.profile_id, config.profile_name,
                            config.frequency, config.daily_type, act_days_str,
                            config.day_of_month, config.time_of_day, config.timezone,
                            config.cron_expression, int(config.is_enabled), int(config.auto_run),
                            int(config.refresh_data_first), int(config.skip_holidays),
                            int(config.notify_on_complete), config.notification_email,
                            trig_str, str(next_run) if next_run else None, str(now_utc),
                        ),
                    )
                except Exception:
                    pass

            conn.commit()
            logger.info(f"[SCHEDULER:SAVE] Saved distinct schedule '{config.schedule_id}' into table '{target_table}' ({config.frequency} @ {config.time_of_day}). Next run: {next_run}")
            return config
        except Exception as e:
            logger.error(f"[SCHEDULER:SAVE:ERROR] Failed to save schedule: {e}")
            raise
        finally:
            conn.close()

    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete an individual schedule from all cadence tables."""
        conn = db_manager.get_connection()
        try:
            cursor = conn.cursor()
            is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
            param = "%s" if is_postgres else "?"
            deleted_any = False

            for tbl in ALL_CADENCE_TABLES + ["schedules"]:
                try:
                    cursor.execute(f"DELETE FROM {tbl} WHERE schedule_id = {param}", (schedule_id,))
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

    def remove_day_from_schedule(self, schedule_id: str, day: str) -> Optional[ScheduleConfigSchema]:
        """Remove a single specific day (e.g. 'wed') from a schedule's active_days list."""
        config = self.get_schedule(schedule_id)
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
        self, count_per_schedule: int = 5, cadence: Optional[str] = None
    ) -> Tuple[List[str], List[NextRunItemSchema], Dict[str, List[str]]]:
        """Aggregate and sort next runs across enabled schedules, optionally filtered by cadence."""
        schedules = self.list_schedules(cadence=cadence) if cadence and cadence.lower() != 'all' else self.list_schedules()
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
        config = self.get_schedule(schedule_id)
        if not config:
            logger.warning(f"[SCHEDULER:ABORT] Schedule '{schedule_id}' does not exist (may have been deleted). Aborting execution.")
            return None
        if not config.is_enabled:
            logger.info(f"[SCHEDULER:SKIP] Schedule '{schedule_id}' is paused/disabled. Skipping execution.")
            return None
        logger.info(f"[SCHEDULER:RUN:START] Triggering scheduled run for profile '{config.profile_name}' (Schedule: {schedule_id})")

        from app.services.screening_service import screening_service

        request = ScreeningRunRequest(
            rule_version_id=config.profile_id if config.profile_id else None,
            profile_name=config.profile_name,
            notification_email=config.notification_email,
            trigger_type="scheduled",
        )

        try:
            response = await screening_service.initiate_screening_run(request)
            logger.info(f"[SCHEDULER:RUN:SUCCESS] Screening run {response.run_id} completed successfully!")

            now_utc = datetime.now(timezone.utc)
            config.last_run_at = now_utc
            upcoming = self.calculate_next_runs(config, count=1, ref_dt=now_utc)
            config.next_run_at = upcoming[0] if upcoming else None
            self.save_schedule(config)

            return response
        except Exception as e:
            logger.error(f"[SCHEDULER:RUN:FAILED] Error executing scheduled run for '{schedule_id}': {e}")
            raise

    async def _scheduler_loop(self):
        """Background monitoring loop that checks for due runs across all schedules every 10s."""
        logger.info("[SCHEDULER:WORKER] Background scheduler daemon loop started.")
        while self._running:
            try:
                schedules = self.list_schedules()
                now_utc = datetime.now(timezone.utc)
                for config in schedules:
                    if config.is_enabled and config.auto_run and config.next_run_at:
                        next_dt = config.next_run_at
                        if next_dt.tzinfo is None:
                            next_dt = next_dt.replace(tzinfo=timezone.utc)

                        if now_utc >= next_dt:
                            logger.info(f"[SCHEDULER:TRIGGER] Scheduled time reached for '{config.schedule_id}' ({config.frequency} @ {config.time_of_day}). Firing pipeline...")
                            await self.execute_scheduled_run(config.schedule_id)

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
