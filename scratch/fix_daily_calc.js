const fs = require('fs');

let p = 'backend/app/services/scheduler_service.py';
let content = fs.readFileSync(p, 'utf8').replace(/\r\n/g, '\n');

// Fix calculate_next_runs for Daily
const oldDailyBlock = `        if freq == "Daily":
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
                cursor += timedelta(days=1)`;

const newDailyBlock = `        if freq == "Daily":
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
                cursor += timedelta(days=1)`;

content = content.replace(oldDailyBlock, newDailyBlock);

// Fix act_days_str in save_schedule
content = content.replace(
  'act_days_str = ",".join(config.active_days) if config.active_days else "mon"',
  'act_days_str = ",".join(config.active_days) if config.active_days is not None else "mon,tue,wed,thu,fri"'
);

// Update calculate_all_next_runs to accept cadence parameter
const oldCalcAll = `    def calculate_all_next_runs(
        self, count_per_schedule: int = 5
    ) -> Tuple[List[str], List[NextRunItemSchema], Dict[str, List[str]]]:
        """Aggregate and sort next runs across all enabled schedules, grouped by frequency."""
        schedules = self.list_schedules()`;

const newCalcAll = `    def calculate_all_next_runs(
        self, count_per_schedule: int = 5, cadence: Optional[str] = None
    ) -> Tuple[List[str], List[NextRunItemSchema], Dict[str, List[str]]]:
        """Aggregate and sort next runs across enabled schedules, optionally filtered by cadence."""
        schedules = self.list_schedules(cadence=cadence) if cadence and cadence.lower() != 'all' else self.list_schedules()`;

content = content.replace(oldCalcAll, newCalcAll);

fs.writeFileSync(p, content.replace(/\n/g, '\r\n'), 'utf8');
console.log('Fixed calculate_next_runs and calculate_all_next_runs in scheduler_service.py');

