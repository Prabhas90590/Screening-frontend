"""Institutional Automated Scheduler Service (Phase 17).

Provides background recurring screening execution, next-run calculations,
multi-cadence scheduling (Daily, Weekly, Monthly, Custom), and on-demand triggers.
"""

import asyncio
from datetime import date, datetime, time, timedelta, timezone
import json
import logging
from typing import Any, Dict, List, Optional

from app.core.logging import DiagnosticLogger
from app.db.connection import db_manager
from app.schemas.schedule import ScheduleConfigSchema, ScheduleResponse
from app.schemas.screening import ScreeningRunRequest

logger = DiagnosticLogger("scheduler_service")

IST_TZ = timezone(timedelta(hours=5, minutes=30))
UTC_TZ = timezone.utc
DAY_MAP = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def get_tz(tz_name: str) -> timezone:
    """Resolve target timezone with robust fallback."""
    if not tz_name:
        return IST_TZ
    clean = tz_name.strip()
    if clean in ("Asia/Kolkata", "IST", "Asia/Calcutta"):
        return IST_TZ
    if clean in ("America/New_York", "EST", "EDT"):
        return timezone(timedelta(hours=-5))
    if clean in ("UTC", "GMT"):
        return UTC_TZ
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(clean)
    except Exception:
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
            cursor = now.date()
            for _ in range(45):
                dt_cand = datetime.combine(cursor, target_time, tzinfo=tz)
                is_valid = True
                if config.daily_type == "trading_days" and cursor.weekday() >= 5:
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
                    # Bound to valid month length
                    target_day = min(dom, 28)
                    cand_date = date(cursor.year, cursor.month, target_day)
                    dt_cand = datetime.combine(cand_date, target_time, tzinfo=tz)
                    if dt_cand > now and (not runs or runs[-1].month != dt_cand.month):
                        runs.append(dt_cand)
                        if len(runs) >= count:
                            break
                except Exception:
                    pass
                # Step to 1st of next month
                if cursor.month == 12:
                    cursor = date(cursor.year + 1, 1, 1)
                else:
                    cursor = date(cursor.year, cursor.month + 1, 1)

        elif freq == "Custom":
            # For custom, default to weekdays at specified time or every interval
            cursor = now.date()
            for _ in range(45):
                dt_cand = datetime.combine(cursor, target_time, tzinfo=tz)
                if cursor.weekday() < 5 and dt_cand > now:
                    runs.append(dt_cand)
                    if len(runs) >= count:
                        break
                cursor += timedelta(days=1)

        return runs

    def get_schedule(self, schedule_id: str = "default-schedule") -> ScheduleConfigSchema:
        """Fetch the active schedule configuration from database."""
        conn = db_manager.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT schedule_id, frequency, day_of_week, time_of_day, is_enabled,
                       auto_run, notify_on_complete, profile_id, profile_name,
                       notification_email, timezone, daily_type, active_days,
                       day_of_month, cron_expression, skip_holidays, refresh_data_first,
                       notify_triggers, last_run_at, next_run_at, updated_at
                FROM schedules
                WHERE schedule_id = %s OR schedule_id = 'default-schedule'
                LIMIT 1
                """,
                (schedule_id,),
            )
            row = cursor.fetchone()
            if row:
                # Map tuple or dict
                if hasattr(row, "keys"):
                    d = dict(row)
                else:
                    cols = [
                        "schedule_id", "frequency", "day_of_week", "time_of_day", "is_enabled",
                        "auto_run", "notify_on_complete", "profile_id", "profile_name",
                        "notification_email", "timezone", "daily_type", "active_days",
                        "day_of_month", "cron_expression", "skip_holidays", "refresh_data_first",
                        "notify_triggers", "last_run_at", "next_run_at", "updated_at"
                    ]
                    d = {cols[i]: row[i] for i in range(len(cols))}

                # Parse JSON notify_triggers
                trig = d.get("notify_triggers")
                if isinstance(trig, str):
                    try:
                        trig = json.loads(trig)
                    except Exception:
                        trig = {}
                elif not isinstance(trig, dict):
                    trig = {"runCompletes": True, "runFails": True, "dataBlockers": True}

                # Parse active_days
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
            else:
                cfg = ScheduleConfigSchema()

            # Ensure next_run_at is computed
            if not cfg.next_run_at:
                runs = self.calculate_next_runs(cfg, count=1)
                if runs:
                    cfg.next_run_at = runs[0]

            return cfg
        except Exception as e:
            logger.warning(f"Could not load schedule from database: {e}. Returning default config.")
            return ScheduleConfigSchema()
        finally:
            conn.close()

    def save_schedule(self, config: ScheduleConfigSchema) -> ScheduleConfigSchema:
        """Persist schedule configuration and update calculated next run time."""
        conn = db_manager.get_connection()
        try:
            # Recalculate next run
            upcoming = self.calculate_next_runs(config, count=1)
            next_run = upcoming[0] if upcoming else None
            config.next_run_at = next_run
            now_utc = datetime.now(timezone.utc)

            cursor = conn.cursor()
            act_days_str = ",".join(config.active_days) if config.active_days else "mon"
            trig_str = json.dumps(config.notify_triggers)

            is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))

            if is_postgres:
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
                        updated_at = EXCLUDED.updated_at
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
            else:
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

            conn.commit()
            logger.info(f"[SCHEDULER:SAVE] Updated schedule '{config.schedule_id}' ({config.frequency} @ {config.time_of_day}). Next run: {next_run}")
            return config
        except Exception as e:
            logger.error(f"[SCHEDULER:SAVE:ERROR] Failed to save schedule: {e}")
            raise
        finally:
            conn.close()

    async def execute_scheduled_run(self, schedule_id: str = "default-schedule"):
        """Execute a scheduled screening run via the unified screening service."""
        config = self.get_schedule(schedule_id)
        logger.info(f"[SCHEDULER:RUN:START] Triggering scheduled run for profile '{config.profile_name}' (ID: {config.profile_id})")

        from app.services.screening_service import screening_service

        request = ScreeningRunRequest(
            rule_version_id=config.profile_id if config.profile_id else None,
            profile_name=config.profile_name,
            notification_email=config.notification_email,
        )

        try:
            response = await screening_service.initiate_screening_run(request)
            logger.info(f"[SCHEDULER:RUN:SUCCESS] Screening run {response.run_id} completed successfully!")

            # Update last_run_at & compute next_run_at
            now_utc = datetime.now(timezone.utc)
            config.last_run_at = now_utc
            upcoming = self.calculate_next_runs(config, count=1, ref_dt=now_utc)
            config.next_run_at = upcoming[0] if upcoming else None
            self.save_schedule(config)

            return response
        except Exception as e:
            logger.error(f"[SCHEDULER:RUN:FAILED] Error executing scheduled run: {e}")
            raise

    async def _scheduler_loop(self):
        """Background monitoring loop that checks for due runs every 30 seconds."""
        logger.info("[SCHEDULER:WORKER] Background scheduler daemon loop started.")
        while self._running:
            try:
                config = self.get_schedule()
                if config.is_enabled and config.auto_run and config.next_run_at:
                    now_utc = datetime.now(timezone.utc)
                    # Compare in UTC
                    next_dt = config.next_run_at
                    if next_dt.tzinfo is None:
                        next_dt = next_dt.replace(tzinfo=timezone.utc)

                    if now_utc >= next_dt:
                        logger.info(f"[SCHEDULER:TRIGGER] Scheduled time reached for '{config.schedule_id}'. Firing pipeline...")
                        await self.execute_scheduled_run(config.schedule_id)

            except Exception as e:
                logger.warning(f"[SCHEDULER:WORKER:ERROR] Exception in scheduler loop: {e}")

            # Sleep 30 seconds
            await asyncio.sleep(30)

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


# Global singleton instance
scheduler_service = SchedulerService()
