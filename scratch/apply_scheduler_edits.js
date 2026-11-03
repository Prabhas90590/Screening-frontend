const fs = require('fs');

// 1. backend/app/schemas/schedule.py
let p1 = 'backend/app/schemas/schedule.py';
let c1 = fs.readFileSync(p1, 'utf8').replace(/\r\n/g, '\n');
c1 = c1.replace(
  'schedule: ScheduleConfigSchema',
  'schedule: Optional[ScheduleConfigSchema] = None'
);
fs.writeFileSync(p1, c1.replace(/\n/g, '\r\n'), 'utf8');
console.log('Updated schedule.py');

// 2. backend/app/api/routes/schedules.py
let p2 = 'backend/app/api/routes/schedules.py';
let c2 = fs.readFileSync(p2, 'utf8').replace(/\r\n/g, '\n');
// In get_schedules:
// active = schedules[0] if schedules else scheduler_service.get_schedule()
// Replace with:
// active = schedules[0] if schedules else None
c2 = c2.replace(
  'active = schedules[0] if schedules else scheduler_service.get_schedule()',
  'active = schedules[0] if schedules else None'
);
// In delete_schedule:
// active = schedules[0] if schedules else scheduler_service.get_schedule()
// Replace with:
// active = schedules[0] if schedules else None
c2 = c2.replace(
  'active = schedules[0] if schedules else scheduler_service.get_schedule()',
  'active = schedules[0] if schedules else None'
);
fs.writeFileSync(p2, c2.replace(/\n/g, '\r\n'), 'utf8');
console.log('Updated routes/schedules.py');

// 3. backend/app/services/scheduler_service.py
// In get_schedule:
// Do not return fallback row or dummy ScheduleConfigSchema when schedule is not found
let p3 = 'backend/app/services/scheduler_service.py';
let c3 = fs.readFileSync(p3, 'utf8').replace(/\r\n/g, '\n');

const oldGetSched = `            cursor.execute(
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
                cursor.execute(
                    """
                    SELECT schedule_id, frequency, day_of_week, time_of_day, is_enabled,
                           auto_run, notify_on_complete, profile_id, profile_name,
                           notification_email, timezone, daily_type, active_days,
                           day_of_month, cron_expression, skip_holidays, refresh_data_first,
                           notify_triggers, last_run_at, next_run_at, updated_at
                    FROM schedules
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """
                )
                row = cursor.fetchone()

            if row:
                cols = [
                    "schedule_id", "frequency", "day_of_week", "time_of_day", "is_enabled",
                    "auto_run", "notify_on_complete", "profile_id", "profile_name",
                    "notification_email", "timezone", "daily_type", "active_days",
                    "day_of_month", "cron_expression", "skip_holidays", "refresh_data_first",
                    "notify_triggers", "last_run_at", "next_run_at", "updated_at"
                ]
                d = dict(row) if hasattr(row, "keys") else {cols[i]: row[i] for i in range(len(cols))}
                return self._row_to_config(d)
            return ScheduleConfigSchema()
        except Exception as e:
            logger.warning(f"Could not load schedule from database: {e}. Returning default config.")
            return ScheduleConfigSchema()`;

const newGetSched = `            cursor.execute(
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
            return None`;

if (c3.includes(oldGetSched)) {
  c3 = c3.replace(oldGetSched, newGetSched);
  console.log('Updated get_schedule in scheduler_service.py');
} else {
  console.error('oldGetSched not matched');
}

// In execute_scheduled_run:
// If config is None or not is_enabled, abort immediately so deleted schedule NEVER runs!
const oldExec = `    async def execute_scheduled_run(self, schedule_id: str):
        """Execute a scheduled screening run via the unified screening service."""
        config = self.get_schedule(schedule_id)
        logger.info(f"[SCHEDULER:RUN:START] Triggering scheduled run for profile '{config.profile_name}' (Schedule: {schedule_id})")`;

const newExec = `    async def execute_scheduled_run(self, schedule_id: str):
        """Execute a scheduled screening run via the unified screening service."""
        config = self.get_schedule(schedule_id)
        if not config:
            logger.warning(f"[SCHEDULER:ABORT] Schedule '{schedule_id}' does not exist (may have been deleted). Aborting execution.")
            return None
        if not config.is_enabled:
            logger.info(f"[SCHEDULER:SKIP] Schedule '{schedule_id}' is paused/disabled. Skipping execution.")
            return None
        logger.info(f"[SCHEDULER:RUN:START] Triggering scheduled run for profile '{config.profile_name}' (Schedule: {schedule_id})")`;

if (c3.includes(oldExec)) {
  c3 = c3.replace(oldExec, newExec);
  console.log('Updated execute_scheduled_run in scheduler_service.py');
} else {
  console.error('oldExec not matched');
}

fs.writeFileSync(p3, c3.replace(/\n/g, '\r\n'), 'utf8');

