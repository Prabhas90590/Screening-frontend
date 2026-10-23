-- Migration 002: Create Security Master tables (companies and listings) for PostgreSQL
-- Establishes single legal entity tracking with dual-listing de-duplication.

-- 1. Companies Master Table
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

-- 2. Listings Table (links multiple exchange listings/ADRs to one canonical company)
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

