const fs = require('fs');
let content = fs.readFileSync('backend/app/services/scheduler_service.py', 'utf8');
content = content.replace(/\r\n/g, '\n');

const target = `            if not config.schedule_id or config.schedule_id == "default-schedule":
                config.schedule_id = f"sched-{clean_freq}-{clean_time}"`;

const replacement = `            if not config.schedule_id or config.schedule_id == "default-schedule":
                config.schedule_id = f"sched-{clean_freq}-{clean_time}"

            if clean_freq == "daily":
                if not config.active_days:
                    config.active_days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] if config.daily_type == "all_days" else ["mon", "tue", "wed", "thu", "fri"]`;

if (content.includes(target)) {
  content = content.replace(target, replacement);
  fs.writeFileSync('backend/app/services/scheduler_service.py', content, 'utf8');
  console.log('Successfully updated scheduler_service.py');
} else {
  console.log('Target not found in scheduler_service.py');
}

