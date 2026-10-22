-- Migration 001: Create raw_responses table for PostgreSQL
-- Stores 100% unchanged vendor API responses for auditability and point-in-time replay.

CREATE TABLE IF NOT EXISTS raw_responses (
    id VARCHAR(64) PRIMARY KEY,
    run_id VARCHAR(64),
    provider VARCHAR(32) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    request_params JSONB DEFAULT '{}',
    response_body JSONB NOT NULL,
    fingerprint VARCHAR(64) NOT NULL,
    status_code INTEGER DEFAULT 200,
    latency_ms REAL DEFAULT 0.0,
    received_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

-- Fast lookup indexes
CREATE INDEX IF NOT EXISTS idx_raw_responses_run_id ON raw_responses(run_id);
CREATE INDEX IF NOT EXISTS idx_raw_responses_fingerprint ON raw_responses(fingerprint);

