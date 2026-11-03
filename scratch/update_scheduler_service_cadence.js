const fs = require('fs');

let p = 'backend/app/services/scheduler_service.py';
let content = fs.readFileSync(p, 'utf8').replace(/\r\n/g, '\n');

// 1. Add CADENCE_TABLES constants after imports
const targetImports = `from app.core.config import settings
from app.core.logging import DiagnosticLogger
from app.db.connection import db_manager
from app.schemas.schedule import NextRunItemSchema, ScheduleConfigSchema
from app.schemas.screening import ScreeningRunRequest`;

const newImports = `from app.core.config import settings
from app.core.logging import DiagnosticLogger
from app.db.connection import db_manager
from app.schemas.schedule import NextRunItemSchema, ScheduleConfigSchema
from app.schemas.screening import ScreeningRunRequest

CADENCE_TABLES = {
    "daily": "schedules_daily",
    "weekly": "schedules_weekly",
    "monthly": "schedules_monthly",
    "custom": "schedules_custom",
}
ALL_CADENCE_TABLES = ["schedules_daily", "schedules_weekly", "schedules_monthly", "schedules_custom"]`;

content = content.replace(targetImports, newImports);

// 2. Replace list_schedules, get_schedule, save_schedule, delete_schedule
const targetMethods = `    def list_schedules(self) -> List[ScheduleConfigSchema]:
        """Fetch all saved schedule configurations from PostgreSQL."""
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
                ORDER BY updated_at DESC, time_of_day ASC
                """
            )
            rows = cursor.fetchall()
            if not rows:
                return []

            cols = [
                "schedule_id", "frequency", "day_of_week", "time_of_day", "is_enabled",
                "auto_run", "notify_on_complete", "profile_id", "profile_name",
                "notification_email", "timezone", "daily_type", "active_days",
                "day_of_month", "cron_expression", "skip_holidays", "refresh_data_first",
                "notify_triggers", "last_run_at", "next_run_at", "updated_at"
            ]
            results = []
            for row in rows:
                if hasattr(row, "keys"):
                    d = dict(row)
                else:
                    d = {cols[i]: row[i] for i in range(len(cols))}
                results.append(self._row_to_config(d))
            return results
        except Exception as e:
            logger.warning(f"Could not load schedules from database: {e}")
            return []
        finally:
            conn.close()

    def get_schedule(self, schedule_id: str = "default-schedule") -> ScheduleConfigSchema:
        """Fetch a specific schedule configuration or the first active one."""
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
                WHERE schedule_id = %s
                LIMIT 1
                """,
                (schedule_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            cols = [
                "schedule_id", "frequency", "day_of_week", "time_of_day", "is_enabled",
                "auto_run", "notify_on_complete", "profile_id", "profile_name",
                "notification_email", "timezone", "daily_type", "active_days",
                "day_of_month", "cron_expression", "skip_holidays", "refresh_data_first",
                "notify_triggers", "last_run_at", "next_run_at", "updated_at"
            ]
            d = dict(row) if hasattr(row, "keys") else {cols[i]: row[i] for i in range(len(cols))}
            return self._row_to_config(d)
        except Exception as e:
            logger.warning(f"Could not load schedule '{schedule_id}' from database: {e}")
            return None
        finally:
            conn.close()

    def save_schedule(self, config: ScheduleConfigSchema) -> ScheduleConfigSchema:
        """Persist schedule configuration as an individual distinct schedule entry."""
        conn = db_manager.get_connection()
        try:
            # Deterministic ID if default or empty: e.g. "sched-daily-1111", "sched-daily-1122"
            clean_time = (config.time_of_day or "08:30").replace(":", "")
            clean_freq = (config.frequency or "daily").lower()
            if not config.schedule_id or config.schedule_id == "default-schedule":
                config.schedule_id = f"sched-{clean_freq}-{clean_time}"

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
            logger.info(f"[SCHEDULER:SAVE] Saved distinct schedule '{config.schedule_id}' ({config.frequency} @ {config.time_of_day}). Next run: {next_run}")
            return config
        except Exception as e:
            logger.error(f"[SCHEDULER:SAVE:ERROR] Failed to save schedule: {e}")
            raise
        finally:
            conn.close()

    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete an individual schedule from database."""
        conn = db_manager.get_connection()
        try:
            cursor = conn.cursor()
            is_postgres = hasattr(conn, "info") or "psycopg2" in str(type(conn))
            query = "DELETE FROM schedules WHERE schedule_id = %s" if is_postgres else "DELETE FROM schedules WHERE schedule_id = ?"
            cursor.execute(query, (schedule_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            logger.info(f"[SCHEDULER:DELETE] Deleted schedule '{schedule_id}': {deleted}")
            return deleted
        except Exception as e:
            logger.error(f"[SCHEDULER:DELETE:ERROR] Failed to delete schedule: {e}")
            return False
        finally:
            conn.close()`;

const newMethods = `    def list_schedules(self, cadence: Optional[str] = None) -> List[ScheduleConfigSchema]:
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

            upcoming = self.calculate_next_runs(config, count=1)
            next_run = upcoming[0] if upcoming else None
            config.next_run_at = next_run
            now_utc = datetime.now(timezone.utc)

            cursor = conn.cursor()
            act_days_str = ",".join(config.active_days) if config.active_days else "mon"
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

        return self.save_schedule(config)`;

if (content.includes(targetMethods)) {
  content = content.replace(targetMethods, newMethods);
  console.log('Successfully replaced scheduler_service methods with cadence table support!');
} else {
  console.error('targetMethods not matched in scheduler_service.py');
}

fs.writeFileSync(p, content.replace(/\n/g, '\r\n'), 'utf8');
console.log('scheduler_service.py updated.');

