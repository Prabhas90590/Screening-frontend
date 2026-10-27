"""Database connection manager supporting PostgreSQL (with SQLite development fallback).

Automatically initializes database tables on startup without requiring manual SQL commands.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional
import urllib.parse

from app.core.config import settings

logger = logging.getLogger("app.db")

# Table schema DDL for PostgreSQL
POSTGRES_SCHEMA_SQL = """
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

CREATE INDEX IF NOT EXISTS idx_raw_responses_run_id ON raw_responses(run_id);
CREATE INDEX IF NOT EXISTS idx_raw_responses_fingerprint ON raw_responses(fingerprint);

CREATE TABLE IF NOT EXISTS companies (
    canonical_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    primary_ticker VARCHAR(32) NOT NULL,
    country VARCHAR(16) NOT NULL,
    primary_exchange VARCHAR(32) NOT NULL,
    sector VARCHAR(64) NOT NULL DEFAULT 'Unclassified',
    industry VARCHAR(128),
    market_cap DOUBLE PRECISION DEFAULT 0.0,
    market_cap_display DOUBLE PRECISION DEFAULT 0.0,
    display_currency VARCHAR(8) DEFAULT 'USD',
    currency VARCHAR(8) DEFAULT 'USD',
    isin VARCHAR(32),
    figi VARCHAR(32),
    is_bank BOOLEAN DEFAULT FALSE,
    description TEXT,
    as_of_date VARCHAR(32),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_companies_isin ON companies(isin);
CREATE INDEX IF NOT EXISTS idx_companies_figi ON companies(figi);
CREATE INDEX IF NOT EXISTS idx_companies_primary_ticker ON companies(primary_ticker);
CREATE INDEX IF NOT EXISTS idx_companies_country ON companies(country);
CREATE INDEX IF NOT EXISTS idx_companies_sector ON companies(sector);

CREATE TABLE IF NOT EXISTS listings (
    listing_id VARCHAR(64) PRIMARY KEY,
    canonical_company_id VARCHAR(64) NOT NULL REFERENCES companies(canonical_id) ON DELETE CASCADE,
    ticker VARCHAR(32) NOT NULL,
    exchange_id VARCHAR(32) NOT NULL,
    country_id VARCHAR(16) NOT NULL,
    currency VARCHAR(8) DEFAULT 'USD',
    is_primary BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    ric VARCHAR(32),
    sedol VARCHAR(32),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_listings_company_id ON listings(canonical_company_id);
CREATE INDEX IF NOT EXISTS idx_listings_exchange_ticker ON listings(exchange_id, ticker);
CREATE INDEX IF NOT EXISTS idx_listings_ticker ON listings(ticker);

-- Phase 7: Persistence Tables
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

CREATE TABLE IF NOT EXISTS holdings (
    holding_id VARCHAR(64) PRIMARY KEY,
    canonical_company_id VARCHAR(64) NOT NULL REFERENCES companies(canonical_id) ON DELETE CASCADE,
    portfolio_name VARCHAR(128) NOT NULL DEFAULT 'Core Equity Fund',
    shares DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    cost_basis DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    weight_pct DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

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

CREATE TABLE IF NOT EXISTS audit_events (
    event_id VARCHAR(64) PRIMARY KEY,
    event_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(64),
    user_id VARCHAR(64) DEFAULT 'analyst',
    details JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_audit_events_type ON audit_events(event_type, created_at DESC);
"""

# SQLite equivalent DDL (for automatic fallback if Postgres is offline)
SQLITE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS raw_responses (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    provider TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    request_params TEXT DEFAULT '{}',
    response_body TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    status_code INTEGER DEFAULT 200,
    latency_ms REAL DEFAULT 0.0,
    received_at TEXT DEFAULT CURRENT_TIMESTAMP,
    is_success INTEGER DEFAULT 1,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_raw_responses_run_id ON raw_responses(run_id);
CREATE INDEX IF NOT EXISTS idx_raw_responses_fingerprint ON raw_responses(fingerprint);

CREATE TABLE IF NOT EXISTS companies (
    canonical_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    primary_ticker TEXT NOT NULL,
    country TEXT NOT NULL,
    primary_exchange TEXT NOT NULL,
    sector TEXT NOT NULL DEFAULT 'Unclassified',
    industry TEXT,
    market_cap REAL DEFAULT 0.0,
    market_cap_display REAL DEFAULT 0.0,
    display_currency TEXT DEFAULT 'USD',
    currency TEXT DEFAULT 'USD',
    isin TEXT,
    figi TEXT,
    is_bank INTEGER DEFAULT 0,
    description TEXT,
    as_of_date TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_companies_isin ON companies(isin);
CREATE INDEX IF NOT EXISTS idx_companies_figi ON companies(figi);
CREATE INDEX IF NOT EXISTS idx_companies_primary_ticker ON companies(primary_ticker);
CREATE INDEX IF NOT EXISTS idx_companies_country ON companies(country);
CREATE INDEX IF NOT EXISTS idx_companies_sector ON companies(sector);

CREATE TABLE IF NOT EXISTS listings (
    listing_id TEXT PRIMARY KEY,
    canonical_company_id TEXT NOT NULL REFERENCES companies(canonical_id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    exchange_id TEXT NOT NULL,
    country_id TEXT NOT NULL,
    currency TEXT DEFAULT 'USD',
    is_primary INTEGER DEFAULT 1,
    is_active INTEGER DEFAULT 1,
    ric TEXT,
    sedol TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_listings_company_id ON listings(canonical_company_id);
CREATE INDEX IF NOT EXISTS idx_listings_exchange_ticker ON listings(exchange_id, ticker);
CREATE INDEX IF NOT EXISTS idx_listings_ticker ON listings(ticker);

-- Phase 7: Persistence Tables
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

CREATE TABLE IF NOT EXISTS holdings (
    holding_id VARCHAR(64) PRIMARY KEY,
    canonical_company_id VARCHAR(64) NOT NULL REFERENCES companies(canonical_id) ON DELETE CASCADE,
    portfolio_name VARCHAR(128) NOT NULL DEFAULT 'Core Equity Fund',
    shares DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    cost_basis DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    weight_pct DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

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

CREATE TABLE IF NOT EXISTS audit_events (
    event_id VARCHAR(64) PRIMARY KEY,
    event_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(64),
    user_id VARCHAR(64) DEFAULT 'analyst',
    details JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_audit_events_type ON audit_events(event_type, created_at DESC);
"""


class DatabaseManager:
    """Manages database connection lifecycle and schema auto-creation."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.is_postgres = database_url.startswith("postgresql://") or database_url.startswith("postgres://")
        self._initialized = False

    def get_connection(self):
        """Obtain a live database connection."""
        if self.is_postgres:
            try:
                import psycopg2
                from psycopg2.extras import RealDictCursor
                conn = psycopg2.connect(self.database_url)
                return conn
            except ImportError:
                logger.warning("psycopg2 is not installed. Run 'pip install psycopg2-binary'. Falling back to SQLite.")
            except Exception as e:
                logger.warning(
                    f"Could not connect to PostgreSQL at '{self.database_url}' ({e}). "
                    "Make sure PostgreSQL is running. Falling back to local SQLite temporarily."
                )

        # SQLite fallback connection
        import sqlite3
        db_path = Path("./screening.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_tables(self):
        """Automatically create tables in the database if they don't already exist."""
        if self._initialized:
            return

        conn = self.get_connection()
        is_postgres_active = hasattr(conn, "info") or "psycopg2" in str(type(conn))

        try:
            cursor = conn.cursor()
            if is_postgres_active:
                logger.info("Initializing PostgreSQL database schema (raw_responses, companies, listings, screening_runs, results, rules, snapshots)...")
                cursor.execute(POSTGRES_SCHEMA_SQL)
                cursor.execute("ALTER TABLE rule_versions ADD COLUMN IF NOT EXISTS changes JSONB DEFAULT '[]';")
                cursor.execute("ALTER TABLE rule_versions ADD COLUMN IF NOT EXISTS selected_countries JSONB DEFAULT '[]';")
                conn.commit()
                logger.info("PostgreSQL persistence tables verified/created successfully.")
            else:
                logger.info("Initializing SQLite database schema (all persistence tables)...")
                cursor.executescript(SQLITE_SCHEMA_SQL)
                conn.commit()
                logger.info("SQLite persistence tables verified/created successfully.")
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize database tables: {e}")
        finally:
            conn.close()


# Global database manager instance
db_manager = DatabaseManager(settings.database_url)
