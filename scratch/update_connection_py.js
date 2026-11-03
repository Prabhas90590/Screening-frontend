const fs = require('fs');

let p = 'backend/app/db/connection.py';
let content = fs.readFileSync(p, 'utf8').replace(/\r\n/g, '\n');

const postgresCadenceSQL = `CREATE TABLE IF NOT EXISTS schedules (
    schedule_id VARCHAR(64) PRIMARY KEY,
    frequency VARCHAR(32) NOT NULL DEFAULT 'Weekly',
    day_of_week VARCHAR(16) DEFAULT 'Monday',
    time_of_day VARCHAR(16) DEFAULT '09:00',
    is_enabled BOOLEAN DEFAULT FALSE,
    auto_run BOOLEAN DEFAULT TRUE,
    notify_on_complete BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Dedicated Cadence Tables (Phase 18)
CREATE TABLE IF NOT EXISTS schedules_daily (
    schedule_id VARCHAR(64) PRIMARY KEY,
    frequency VARCHAR(32) NOT NULL DEFAULT 'Daily',
    day_of_week VARCHAR(16) DEFAULT 'Monday',
    time_of_day VARCHAR(16) DEFAULT '08:30',
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
    notify_triggers JSONB DEFAULT '{"runFails": true, "dataBlockers": true, "runCompletes": true}'::jsonb,
    last_run_at TIMESTAMP WITH TIME ZONE,
    next_run_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schedules_weekly (
    schedule_id VARCHAR(64) PRIMARY KEY,
    frequency VARCHAR(32) NOT NULL DEFAULT 'Weekly',
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
    active_days VARCHAR(128) DEFAULT 'mon',
    day_of_month INTEGER DEFAULT 1,
    cron_expression VARCHAR(64) DEFAULT '0 9 * * 1-5',
    skip_holidays BOOLEAN DEFAULT TRUE,
    refresh_data_first BOOLEAN DEFAULT TRUE,
    notify_triggers JSONB DEFAULT '{"runFails": true, "dataBlockers": true, "runCompletes": true}'::jsonb,
    last_run_at TIMESTAMP WITH TIME ZONE,
    next_run_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schedules_monthly (
    schedule_id VARCHAR(64) PRIMARY KEY,
    frequency VARCHAR(32) NOT NULL DEFAULT 'Monthly',
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
    active_days VARCHAR(128) DEFAULT 'mon',
    day_of_month INTEGER DEFAULT 1,
    cron_expression VARCHAR(64) DEFAULT '0 9 * * 1-5',
    skip_holidays BOOLEAN DEFAULT TRUE,
    refresh_data_first BOOLEAN DEFAULT TRUE,
    notify_triggers JSONB DEFAULT '{"runFails": true, "dataBlockers": true, "runCompletes": true}'::jsonb,
    last_run_at TIMESTAMP WITH TIME ZONE,
    next_run_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schedules_custom (
    schedule_id VARCHAR(64) PRIMARY KEY,
    frequency VARCHAR(32) NOT NULL DEFAULT 'Custom',
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
    notify_triggers JSONB DEFAULT '{"runFails": true, "dataBlockers": true, "runCompletes": true}'::jsonb,
    last_run_at TIMESTAMP WITH TIME ZONE,
    next_run_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);`;

const sqliteCadenceSQL = `CREATE TABLE IF NOT EXISTS schedules (
    schedule_id TEXT PRIMARY KEY,
    frequency TEXT NOT NULL DEFAULT 'Weekly',
    day_of_week TEXT DEFAULT 'Monday',
    time_of_day TEXT DEFAULT '09:00',
    is_enabled INTEGER DEFAULT 0,
    auto_run INTEGER DEFAULT 1,
    notify_on_complete INTEGER DEFAULT 1,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schedules_daily (
    schedule_id TEXT PRIMARY KEY,
    frequency TEXT NOT NULL DEFAULT 'Daily',
    day_of_week TEXT DEFAULT 'Monday',
    time_of_day TEXT DEFAULT '08:30',
    is_enabled INTEGER DEFAULT 1,
    auto_run INTEGER DEFAULT 1,
    notify_on_complete INTEGER DEFAULT 1,
    profile_id TEXT,
    profile_name TEXT,
    notification_email TEXT,
    timezone TEXT DEFAULT 'Asia/Kolkata',
    daily_type TEXT DEFAULT 'trading_days',
    active_days TEXT DEFAULT 'mon,tue,wed,thu,fri',
    day_of_month INTEGER DEFAULT 1,
    cron_expression TEXT DEFAULT '0 9 * * 1-5',
    skip_holidays INTEGER DEFAULT 1,
    refresh_data_first INTEGER DEFAULT 1,
    notify_triggers TEXT DEFAULT '{"runFails": true, "dataBlockers": true, "runCompletes": true}',
    last_run_at TEXT,
    next_run_at TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schedules_weekly (
    schedule_id TEXT PRIMARY KEY,
    frequency TEXT NOT NULL DEFAULT 'Weekly',
    day_of_week TEXT DEFAULT 'Monday',
    time_of_day TEXT DEFAULT '09:00',
    is_enabled INTEGER DEFAULT 1,
    auto_run INTEGER DEFAULT 1,
    notify_on_complete INTEGER DEFAULT 1,
    profile_id TEXT,
    profile_name TEXT,
    notification_email TEXT,
    timezone TEXT DEFAULT 'Asia/Kolkata',
    daily_type TEXT DEFAULT 'trading_days',
    active_days TEXT DEFAULT 'mon',
    day_of_month INTEGER DEFAULT 1,
    cron_expression TEXT DEFAULT '0 9 * * 1-5',
    skip_holidays INTEGER DEFAULT 1,
    refresh_data_first INTEGER DEFAULT 1,
    notify_triggers TEXT DEFAULT '{"runFails": true, "dataBlockers": true, "runCompletes": true}',
    last_run_at TEXT,
    next_run_at TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schedules_monthly (
    schedule_id TEXT PRIMARY KEY,
    frequency TEXT NOT NULL DEFAULT 'Monthly',
    day_of_week TEXT DEFAULT 'Monday',
    time_of_day TEXT DEFAULT '09:00',
    is_enabled INTEGER DEFAULT 1,
    auto_run INTEGER DEFAULT 1,
    notify_on_complete INTEGER DEFAULT 1,
    profile_id TEXT,
    profile_name TEXT,
    notification_email TEXT,
    timezone TEXT DEFAULT 'Asia/Kolkata',
    daily_type TEXT DEFAULT 'trading_days',
    active_days TEXT DEFAULT 'mon',
    day_of_month INTEGER DEFAULT 1,
    cron_expression TEXT DEFAULT '0 9 * * 1-5',
    skip_holidays INTEGER DEFAULT 1,
    refresh_data_first INTEGER DEFAULT 1,
    notify_triggers TEXT DEFAULT '{"runFails": true, "dataBlockers": true, "runCompletes": true}',
    last_run_at TEXT,
    next_run_at TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schedules_custom (
    schedule_id TEXT PRIMARY KEY,
    frequency TEXT NOT NULL DEFAULT 'Custom',
    day_of_week TEXT DEFAULT 'Monday',
    time_of_day TEXT DEFAULT '09:00',
    is_enabled INTEGER DEFAULT 1,
    auto_run INTEGER DEFAULT 1,
    notify_on_complete INTEGER DEFAULT 1,
    profile_id TEXT,
    profile_name TEXT,
    notification_email TEXT,
    timezone TEXT DEFAULT 'Asia/Kolkata',
    daily_type TEXT DEFAULT 'trading_days',
    active_days TEXT DEFAULT 'mon,tue,wed,thu,fri',
    day_of_month INTEGER DEFAULT 1,
    cron_expression TEXT DEFAULT '0 9 * * 1-5',
    skip_holidays INTEGER DEFAULT 1,
    refresh_data_first INTEGER DEFAULT 1,
    notify_triggers TEXT DEFAULT '{"runFails": true, "dataBlockers": true, "runCompletes": true}',
    last_run_at TEXT,
    next_run_at TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);`;

// Replace in POSTGRES_SCHEMA_SQL (first occurrence)
const targetPostgres = `CREATE TABLE IF NOT EXISTS schedules (
    schedule_id VARCHAR(64) PRIMARY KEY,
    frequency VARCHAR(32) NOT NULL DEFAULT 'Weekly',
    day_of_week VARCHAR(16) DEFAULT 'Monday',
    time_of_day VARCHAR(16) DEFAULT '09:00',
    is_enabled BOOLEAN DEFAULT FALSE,
    auto_run BOOLEAN DEFAULT TRUE,
    notify_on_complete BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);`;

// Replace in SQLITE_SCHEMA_SQL (second occurrence)
const idx1 = content.indexOf(targetPostgres);
if (idx1 !== -1) {
  content = content.slice(0, idx1) + postgresCadenceSQL + content.slice(idx1 + targetPostgres.length);
  console.log('Updated POSTGRES_SCHEMA_SQL with 4 cadence tables.');
}

const idx2 = content.indexOf(targetPostgres);
if (idx2 !== -1) {
  content = content.slice(0, idx2) + sqliteCadenceSQL + content.slice(idx2 + targetPostgres.length);
  console.log('Updated SQLITE_SCHEMA_SQL with 4 cadence tables.');
}

fs.writeFileSync(p, content.replace(/\n/g, '\r\n'), 'utf8');
console.log('connection.py updated successfully.');

