const fs = require('fs');
let p = 'backend/app/services/scheduler_service.py';
let txt = fs.readFileSync(p, 'utf8');

const target = 'DAY_MAP = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}';
const addition = `DAY_MAP = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

CADENCE_TABLES = {
    "daily": "schedules_daily",
    "weekly": "schedules_weekly",
    "monthly": "schedules_monthly",
    "custom": "schedules_custom",
}
ALL_CADENCE_TABLES = ["schedules_daily", "schedules_weekly", "schedules_monthly", "schedules_custom"]`;

txt = txt.replace(target, addition);
fs.writeFileSync(p, txt, 'utf8');
console.log('Added CADENCE_TABLES successfully.');

