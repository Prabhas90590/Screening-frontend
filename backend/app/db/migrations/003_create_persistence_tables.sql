-- Migration 003: Create Full Persistence Tables for PostgreSQL
-- Establishes storage for financial snapshots, rules, screening runs, results, funnel counts, decisions, and audit events.

-- 1. Financial Snapshots
CREATE TABLE IF NOT EXISTS financial_snapshots (
    id VARCHAR(64) PRIMARY KEY,
    canonical_company_id VARCHAR(64) NOT NULL REFERENCES companies(canonical_id) ON DELETE CASCADE,
    as_of_date VARCHAR(32) NOT NULL,
    currency VARCHAR(8) DEFAULT 'USD',
    ebitda DOUBLE PRECISION,
    net_debt DOUBLE PRECISION,
    total_debt DOUBLE PRECISION,
    cash DOUBLE PRECISION,
    revenue DOUBLE PRECISION,
    operating_income DOUBLE PRECISION,
    net_income DOUBLE PRECISION,
    free_cash_flow DOUBLE PRECISION,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_financial_snapshots_company ON financial_snapshots(canonical_company_id, as_of_date);

-- 2. Estimate Snapshots
CREATE TABLE IF NOT EXISTS estimate_snapshots (
    id VARCHAR(64) PRIMARY KEY,
    canonical_company_id VARCHAR(64) NOT NULL REFERENCES companies(canonical_id) ON DELETE CASCADE,
    as_of_date VARCHAR(32) NOT NULL,
    forward_pe DOUBLE PRECISION,
    peg_ratio DOUBLE PRECISION,
    eps_growth_fwd DOUBLE PRECISION,
    analyst_count INTEGER,
    target_price DOUBLE PRECISION,
    recommendation_mean DOUBLE PRECISION,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_estimate_snapshots_company ON estimate_snapshots(canonical_company_id, as_of_date);

-- 3. Consolidated Company Metrics (Stores all 16 calculated metrics per company)
CREATE TABLE IF NOT EXISTS company_metrics (
    canonical_company_id VARCHAR(64) PRIMARY KEY REFERENCES companies(canonical_id) ON DELETE CASCADE,
    ticker VARCHAR(32) NOT NULL,
    as_of_date VARCHAR(32) NOT NULL,
    -- Size & Liquidity
    market_cap_usd DOUBLE PRECISION,
    price_usd DOUBLE PRECISION,
    avg_daily_volume DOUBLE PRECISION,
    avg_daily_traded_value DOUBLE PRECISION,
    -- Valuation
    forward_pe DOUBLE PRECISION,
    pe_vs_benchmark DOUBLE PRECISION,
    peg_ratio DOUBLE PRECISION,
    ev_ebitda DOUBLE PRECISION,
    price_to_sales DOUBLE PRECISION,
    price_to_cash_flow DOUBLE PRECISION,
    -- Growth, Leverage & Income
    revenue_growth_fwd DOUBLE PRECISION,
    eps_growth_fwd DOUBLE PRECISION,
    beta DOUBLE PRECISION,
    net_debt_ebitda DOUBLE PRECISION,
    dividend_yield DOUBLE PRECISION,
    -- Quality & Audit
    data_confidence VARCHAR(16) DEFAULT 'High',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_company_metrics_ticker ON company_metrics(ticker);
CREATE INDEX IF NOT EXISTS idx_company_metrics_forward_pe ON company_metrics(forward_pe);
CREATE INDEX IF NOT EXISTS idx_company_metrics_ev_ebitda ON company_metrics(ev_ebitda);
CREATE INDEX IF NOT EXISTS idx_company_metrics_nd_ebitda ON company_metrics(net_debt_ebitda);

-- 4. Rule Versions (Profiles)
CREATE TABLE IF NOT EXISTS rule_versions (
    version_id VARCHAR(64) PRIMARY KEY,
    profile_name VARCHAR(128) NOT NULL,
    version_number VARCHAR(16) NOT NULL DEFAULT '1.0',
    is_active BOOLEAN DEFAULT TRUE,
    description TEXT,
    sector_limits JSONB DEFAULT '{}',
    diversification_rules JSONB DEFAULT '{}',
    changes JSONB DEFAULT '[]',
    selected_countries JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Rules (Individual Criteria within a Profile)
CREATE TABLE IF NOT EXISTS rules (
    rule_id VARCHAR(64) PRIMARY KEY,
    version_id VARCHAR(64) NOT NULL REFERENCES rule_versions(version_id) ON DELETE CASCADE,
    metric_name VARCHAR(64) NOT NULL,
    label VARCHAR(128) NOT NULL,
    category VARCHAR(64) NOT NULL DEFAULT 'Valuation',
    condition VARCHAR(16) NOT NULL DEFAULT '>=',
    threshold_value DOUBLE PRECISION NOT NULL,
    threshold_display VARCHAR(32) NOT NULL DEFAULT '',
    mode VARCHAR(16) NOT NULL DEFAULT 'Both',
    weight DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_rules_version ON rules(version_id, metric_name);

-- 5. Screening Runs (Audit trail of executions)
CREATE TABLE IF NOT EXISTS screening_runs (
    run_id VARCHAR(64) PRIMARY KEY,
    status VARCHAR(32) NOT NULL DEFAULT 'succeeded',
    provider VARCHAR(32) NOT NULL DEFAULT 'mock',
    rule_version_id VARCHAR(64),
    profile_name VARCHAR(128),
    display_currency VARCHAR(8) DEFAULT 'USD',
    selected_countries JSONB DEFAULT '[]',
    selected_exchanges JSONB DEFAULT '[]',
    selected_countries JSONB DEFAULT '[]',
    rules_snapshot JSONB DEFAULT '[]',
    duration_ms DOUBLE PRECISION DEFAULT 0.0,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_screening_runs_status ON screening_runs(status);
CREATE INDEX IF NOT EXISTS idx_screening_runs_started ON screening_runs(started_at DESC);

-- 6. Funnel Counts (Stage-by-stage counts)
CREATE TABLE IF NOT EXISTS funnel_counts (
    id VARCHAR(64) PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL REFERENCES screening_runs(run_id) ON DELETE CASCADE UNIQUE,
    universe_count INTEGER NOT NULL DEFAULT 0,
    markets_count INTEGER NOT NULL DEFAULT 0,
    floors_count INTEGER NOT NULL DEFAULT 0,
    gates_count INTEGER NOT NULL DEFAULT 0,
    score_count INTEGER NOT NULL DEFAULT 0,
    shortlist_count INTEGER NOT NULL DEFAULT 0,
    selected_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Screening Results (Leaderboard and Near-Misses)
CREATE TABLE IF NOT EXISTS screening_results (
    id VARCHAR(64) PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL REFERENCES screening_runs(run_id) ON DELETE CASCADE,
    canonical_company_id VARCHAR(64) NOT NULL REFERENCES companies(canonical_id) ON DELETE CASCADE,
    ticker VARCHAR(32) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    country VARCHAR(16) NOT NULL,
    exchange VARCHAR(32) NOT NULL,
    sector VARCHAR(64) NOT NULL,
    rank INTEGER NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    display_price DOUBLE PRECISION,
    market_cap_display DOUBLE PRECISION,
    display_currency VARCHAR(8) DEFAULT 'USD',
    fwd_pe DOUBLE PRECISION,
    peg DOUBLE PRECISION,
    ev_ebitda DOUBLE PRECISION,
    beta DOUBLE PRECISION,
    nd_ebitda VARCHAR(32),
    yield_pct DOUBLE PRECISION,
    eps_growth_pct DOUBLE PRECISION,
    data_confidence VARCHAR(16) DEFAULT 'High',
    stage_status VARCHAR(32) DEFAULT 'passed',
    near_miss_status VARCHAR(32) DEFAULT 'none',
    score_breakdown JSONB DEFAULT '[]',
    metric_statuses JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_screening_results_run_rank ON screening_results(run_id, rank);
CREATE INDEX IF NOT EXISTS idx_screening_results_stage ON screening_results(run_id, stage_status);
CREATE INDEX IF NOT EXISTS idx_screening_results_near_miss ON screening_results(run_id, near_miss_status);

-- 8. Decisions (Analyst Keep/Drop choices)
CREATE TABLE IF NOT EXISTS decisions (
    decision_id VARCHAR(64) PRIMARY KEY,
    canonical_company_id VARCHAR(64) NOT NULL REFERENCES companies(canonical_id) ON DELETE CASCADE,
    decision VARCHAR(16) NOT NULL,
    decision_reason VARCHAR(255),
    decision_note TEXT,
    run_id VARCHAR(64),
    decided_by VARCHAR(64) DEFAULT 'Analyst',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_decisions_company ON decisions(canonical_company_id);

-- 9. Holdings (Fund positions)
CREATE TABLE IF NOT EXISTS holdings (
    holding_id VARCHAR(64) PRIMARY KEY,
    canonical_company_id VARCHAR(64) NOT NULL REFERENCES companies(canonical_id) ON DELETE CASCADE,
    portfolio_name VARCHAR(128) NOT NULL DEFAULT 'Core Equity Fund',
    shares DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    cost_basis DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    weight_pct DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 10. Schedules (Automated recurring screening)
CREATE TABLE IF NOT EXISTS schedules (
    schedule_id VARCHAR(64) PRIMARY KEY,
    frequency VARCHAR(32) NOT NULL DEFAULT 'Weekly',
    day_of_week VARCHAR(16) DEFAULT 'Monday',
    time_of_day VARCHAR(16) DEFAULT '09:00',
    is_enabled BOOLEAN DEFAULT FALSE,
    auto_run BOOLEAN DEFAULT TRUE,
    notify_on_complete BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 11. Audit Events (System and compliance trail)
CREATE TABLE IF NOT EXISTS audit_events (
    event_id VARCHAR(64) PRIMARY KEY,
    event_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(64),
    user_id VARCHAR(64) DEFAULT 'analyst',
    details JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_audit_events_type ON audit_events(event_type, created_at DESC);

