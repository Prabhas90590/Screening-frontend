import psycopg2
import json

conn = psycopg2.connect('postgresql://postgres:prabhas123@localhost:5432/screening_db')
cur = conn.cursor()

tables = ['schedules_daily', 'schedules_weekly', 'schedules_monthly', 'schedules_custom']

for tbl in tables:
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {tbl} (
        schedule_id VARCHAR(64) PRIMARY KEY,
        frequency VARCHAR(32) NOT NULL,
        day_of_week VARCHAR(16) DEFAULT 'Monday',
        time_of_day VARCHAR(16) DEFAULT '09:00',
        is_enabled BOOLEAN DEFAULT TRUE,
        auto_run BOOLEAN DEFAULT TRUE,
        notify_on_complete BOOLEAN DEFAULT TRUE,
        profile_id VARCHAR(64),
        profile_name VARCHAR(128),
        notification_email TEXT,
        timezone VARCHAR(64) DEFAULT 'Asia/Kolkata',
        daily_type VARCHAR(32) DEFAULT 'trading_days',
        active_days VARCHAR(128) DEFAULT 'mon,tue,wed,thu,fri',
        day_of_month INTEGER DEFAULT 1,
        cron_expression VARCHAR(64) DEFAULT '0 9 * * 1-5',
        skip_holidays BOOLEAN DEFAULT TRUE,
        refresh_data_first BOOLEAN DEFAULT TRUE,
        notify_triggers JSONB DEFAULT '{{"runFails": true, "dataBlockers": true, "runCompletes": true}}'::jsonb,
        last_run_at TIMESTAMP WITH TIME ZONE,
        next_run_at TIMESTAMP WITH TIME ZONE,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """)
    print(f'Created table: {tbl}')

cur.execute("""
SELECT schedule_id, frequency, day_of_week, time_of_day, is_enabled,
       auto_run, notify_on_complete, profile_id, profile_name,
       notification_email, timezone, daily_type, active_days,
       day_of_month, cron_expression, skip_holidays, refresh_data_first,
       notify_triggers, last_run_at, next_run_at, updated_at
FROM schedules;
""")
rows = cur.fetchall()
cols = [
    'schedule_id', 'frequency', 'day_of_week', 'time_of_day', 'is_enabled',
    'auto_run', 'notify_on_complete', 'profile_id', 'profile_name',
    'notification_email', 'timezone', 'daily_type', 'active_days',
    'day_of_month', 'cron_expression', 'skip_holidays', 'refresh_data_first',
    'notify_triggers', 'last_run_at', 'next_run_at', 'updated_at'
]
placeholders = ', '.join(['%s'] * len(cols))
col_names = ', '.join(cols)

for r in rows:
    d = dict(zip(cols, r))
    freq = (d['frequency'] or 'Daily').lower()
    target_tbl = f'schedules_{freq}' if f'schedules_{freq}' in tables else 'schedules_custom'
    
    val_list = list(r)
    # If notify_triggers is dict, serialize to json string
    trig_idx = cols.index('notify_triggers')
    if isinstance(val_list[trig_idx], dict):
        val_list[trig_idx] = json.dumps(val_list[trig_idx])
    
    cur.execute(f"""
    INSERT INTO {target_tbl} ({col_names})
    VALUES ({placeholders})
    ON CONFLICT (schedule_id) DO UPDATE SET
        frequency = EXCLUDED.frequency,
        time_of_day = EXCLUDED.time_of_day,
        is_enabled = EXCLUDED.is_enabled,
        active_days = EXCLUDED.active_days,
        updated_at = EXCLUDED.updated_at;
    """, tuple(val_list))
    print(f'Migrated {d["schedule_id"]} ({freq}) -> {target_tbl}')

conn.commit()
conn.close()
print('All 4 cadence tables created and data migrated successfully!')
