   # Equity Screening Backend - Phase-wise Implementation Plan

   ## Purpose

   The backend will receive selected countries, exchanges, and screening rules from
   the frontend. It will fetch market data, preserve the original responses,
   normalize the data, calculate metrics, apply rules, store explainable results,
   and return those results to the frontend.

   Development can begin without a vendor API key by using a mock data provider.
   When a real vendor is selected, only the vendor adapter and environment
   configuration need to change.

   ## Target backend structure

   ```text
   backend/
   ├── app/
   │   ├── main.py
   │   ├── api/routes/
   │   │   ├── health.py
   │   │   ├── screening.py
   │   │   ├── rules.py
   │   │   ├── runs.py
   │   │   ├── results.py
   │   │   ├── schedules.py
   │   │   ├── holdings.py
   │   │   ├── decisions.py
   │   │   └── exports.py
   │   ├── adapters/
   │   │   ├── base.py
   │   │   ├── mock_adapter.py
   │   │   ├── vendor_adapter.py
   │   │   └── registry.py
   │   ├── ingestion/
   │   │   ├── data_adapter.py
   │   │   ├── ingestion_service.py
   │   │   └── raw_response_store.py
   │   ├── security_master/
   │   │   ├── company_service.py
   │   │   └── listing_service.py
   │   ├── metrics/
   │   │   ├── metrics_engine.py
   │   │   ├── valuation_metrics.py
   │   │   ├── growth_metrics.py
   │   │   ├── leverage_metrics.py
   │   │   └── income_metrics.py
   │   ├── rules/
   │   │   ├── rule_engine.py
   │   │   ├── rule_catalog.py
   │   │   └── rule_version_service.py
   │   ├── services/
   │   │   ├── screening_service.py
   │   │   ├── run_manager.py
   │   │   ├── scheduler_service.py
   │   │   ├── holdings_service.py
   │   │   ├── decision_service.py
   │   │   ├── export_service.py
   │   │   └── audit_service.py
   │   ├── models/
   │   │   ├── company.py
   │   │   ├── listing.py
   │   │   ├── raw_response.py
   │   │   ├── financial_snapshot.py
   │   │   ├── estimate_snapshot.py
   │   │   ├── rule.py
   │   │   ├── screening_run.py
   │   │   ├── screening_result.py
   │   │   ├── funnel_count.py
   │   │   ├── score_breakdown.py
   │   │   ├── holding.py
   │   │   ├── decision.py
   │   │   ├── schedule.py
   │   │   └── audit_event.py
   │   ├── schemas/
   │   │   ├── market.py
   │   │   ├── company.py
   │   │   ├── financials.py
   │   │   ├── screening.py
   │   │   ├── rule.py
   │   │   ├── result.py
   │   │   ├── schedule.py
   │   │   ├── holding.py
   │   │   ├── decision.py
   │   │   └── export.py
   │   ├── repositories/
   │   │   ├── company_repository.py
   │   │   ├── raw_response_repository.py
   │   │   ├── screening_repository.py
   │   │   ├── results_repository.py
   │   │   ├── holdings_repository.py
   │   │   ├── decision_repository.py
   │   │   └── audit_repository.py
   │   ├── db/
   │   │   ├── connection.py
   │   │   └── migrations/
   │   └── core/
   │       ├── config.py
   │       ├── logging.py
   │       ├── errors.py
   │       └── security.py
   ├── tests/
   ├── requirements.txt
   ├── .env.example
   ├── .gitignore
   └── README.md
   ```

   ## Phase 1: Backend foundation

   ### Purpose

   Create a reliable FastAPI application that can run locally and communicate
   with the frontend.

   ### Main files

   ```text
   app/main.py
   app/core/config.py
   app/core/logging.py
   app/core/errors.py
   app/api/routes/health.py
   app/db/connection.py
   ```

   ### Features

   - Start the FastAPI server.
   - Add a health endpoint.
   - Configure CORS for the frontend.
   - Read settings from `.env`.
   - Add application logs.
   - Add common error responses.
   - Prepare database connection handling.

   ## Phase 2: Common data contracts

   ### Purpose

   Define one standard format for all data, independent of the vendor.

   ### Main files

   ```text
   app/schemas/market.py
   app/schemas/company.py
   app/schemas/financials.py
   app/adapters/base.py
   app/ingestion/data_adapter.py
   ```

   Different vendors may use different field names. The adapter converts their
   responses into the application's common format.

   Example:

   ```json
   {
   "canonical_id": "company-001",
   "name": "Example Company",
   "ticker": "EXM",
   "country": "US",
   "exchange": "NASDAQ"
   }
   ```

   ## Phase 3: Mock data provider

   ### Purpose

   Allow the complete backend flow to work without an API key.

   ### Main files

   ```text
   app/adapters/mock_adapter.py
   app/adapters/registry.py
   ```

   The mock adapter provides sample companies, exchanges, prices, financial data,
   estimates, and historical values.

   ```env
   DATA_PROVIDER=mock
   VENDOR_API_KEY=
   VENDOR_BASE_URL=
   ```

   Mock data must be clearly identified as development data.

   ## Phase 4: Replaceable vendor adapter

   ### Purpose

   Prepare the system for a real vendor later.

   ### Common adapter operations

   ```text
   get_companies()
   get_prices()
   get_financials()
   get_estimates()
   ```

   The screening system calls these common methods instead of calling a vendor
   directly. When a vendor is selected, the adapter and configuration can change
   without changing the metrics or rule engine.

   ```env
   DATA_PROVIDER=vendor_name
   VENDOR_API_KEY=provided-api-key
   VENDOR_BASE_URL=vendor-url
   ```

   API keys must never be committed to Git or written to frontend code.

   ## Phase 5: Raw response storage

   ### Purpose

   Save every external API response exactly as received. This protects historical
   data such as analyst estimates and allows past runs to be reproduced honestly.

   ### Main files

   ```text
   app/ingestion/raw_response_store.py
   app/models/raw_response.py
   app/repositories/raw_response_repository.py
   ```

   Store the provider, endpoint, request parameters, original response,
   received time, fingerprint/hash, run ID, and success or failure status.

   ## Phase 6: Security master

   ### Purpose

   Create one stable record for every company and connect all of its listings.

   ### Main files

   ```text
   app/security_master/company_service.py
   app/security_master/listing_service.py
   app/models/company.py
   app/models/listing.py
   app/repositories/company_repository.py
   ```

   This prevents duplicate or incorrect matching when vendors use different
   identifiers or ticker symbols.

   ## Phase 7: Database and persistence

   ### Purpose

   Store data permanently instead of keeping it only in memory.

   ### Main records

   ```text
   companies
   listings
   raw_responses
   financial_snapshots
   estimate_snapshots
   rules
   rule_versions
   screening_runs
   screening_results
   funnel_counts
   score_breakdowns
   holdings
   decisions
   schedules
   audit_events
   exports
   ```

   PostgreSQL is recommended for production. SQLite can be used temporarily for
   local development if the production database has not yet been selected.

   ## Phase 8: Screening request API

   ### Purpose

   Receive selected countries, exchanges, and rules from the frontend.

   ```text
   POST /api/screenings
   ```

   Example request:

   ```json
   {
   "countries": ["US", "IN"],
   "exchanges": ["NASDAQ", "NSE"],
   "rule_version_id": "profile-v1"
   }
   ```

   The backend validates countries, exchanges, their relationship, the rule
   version, and required values.

   Example response:

   ```json
   {
   "run_id": "run-001",
   "status": "queued"
   }
   ```

   ## Phase 9: Data ingestion

   ### Purpose

   Fetch data for the selected countries and exchanges.

   ```text
   Selected countries and exchanges
         ↓
   Vendor or mock adapter
         ↓
   Save raw response
         ↓
   Normalize data
         ↓
   Update security master
   ```

   The ingestion service works the same whether the provider is mock or real.

   ## Phase 10: Metrics engine

   ### Purpose

   Calculate financial metrics using the application's own formulas.

   ### Metrics

   - Forward P/E
   - PEG
   - EV/EBITDA
   - Beta
   - Net debt/EBITDA
   - Dividend yield
   - EPS growth
   - Revenue growth
   - Profit margin

   For every metric, store the input values, formula version, calculated value,
   calculation time, and any missing-data reason.

   ## Phase 11: Versioned rule engine

   ### Purpose

   Apply the rules configured in the frontend while preserving rule history.

   ### Main files

   ```text
   app/rules/rule_engine.py
   app/rules/rule_catalog.py
   app/rules/rule_version_service.py
   app/models/rule.py
   app/schemas/rule.py
   ```

   For every rule result, store the rule name, version, actual value, condition,
   required value, pass/fail result, failure reason, and score contribution.

   ## Phase 12: Funnel and score breakdown

   ### Purpose

   Explain how companies move through the screening process.

   ```text
   Universe
   → Markets
   → Floors
   → Gates
   → Score
   → Shortlist
   → Selected
   ```

   Store the count at every stage and a score breakdown for every company.

   ## Phase 13: Run manager

   ### Purpose

   Create traceable and immutable screening runs.

   ### Main files

   ```text
   app/services/run_manager.py
   app/models/screening_run.py
   app/repositories/screening_repository.py
   app/api/routes/runs.py
   ```

   Store the run ID, timestamps, selected markets, rule version, data provider,
   raw response references, status, funnel counts, result count, and errors.

   APIs:

   ```text
   GET  /api/runs
   GET  /api/runs/{run_id}
   POST /api/runs/{run_id}/retry
   ```

   Completed runs should not be silently overwritten.

   ## Phase 14: Results APIs

   ### Purpose

   Return screening results to the frontend.

   ```text
   GET /api/runs/{run_id}/results?view=top20
   GET /api/runs/{run_id}/results?view=rank_near_misses
   GET /api/runs/{run_id}/results?view=rule_near_misses
   GET /api/runs/{run_id}/results?view=all_screened
   GET /api/runs/{run_id}/results/{company_id}
   ```

   Views:

   - `top20`: ranks 1-20.
   - `rank_near_misses`: ranks 21-40.
   - `rule_near_misses`: companies closest to passing the rules.
   - `all_screened`: every company included in the run.

   ## Phase 15: Holdings import and storage

   ### Purpose

   Allow users to upload or manually enter their holdings.

   ### Main files

   ```text
   app/api/routes/holdings.py
   app/services/holdings_service.py
   app/models/holding.py
   app/schemas/holding.py
   app/repositories/holdings_repository.py
   ```

   APIs:

   ```text
   POST   /api/holdings/import
   POST   /api/holdings
   GET    /api/holdings
   DELETE /api/holdings/{holding_id}
   ```

   The backend will read CSV/XLS/XLSX rows, validate identifiers, match them
   against the security master, store matched holdings, and return matched and
   unmatched rows.

   ## Phase 16: Analyst decisions

   ### Purpose

   Store Keep/Drop decisions permanently.

   ### Main files

   ```text
   app/api/routes/decisions.py
   app/services/decision_service.py
   app/models/decision.py
   app/schemas/decision.py
   app/repositories/decision_repository.py
   ```

   Store the company ID, run ID, decision, reason, note, user, and timestamps.
   These decisions can later support learning and backtesting.

   ## Phase 17: Scheduler

   ### Purpose

   Run screenings automatically or on demand.

   ### Main files

   ```text
   app/api/routes/schedules.py
   app/services/scheduler_service.py
   app/models/schedule.py
   app/schemas/schedule.py
   ```

   APIs:

   ```text
   POST   /api/schedules
   GET    /api/schedules
   PUT    /api/schedules/{schedule_id}
   DELETE /api/schedules/{schedule_id}
   POST   /api/runs/now
   ```

   Scheduled runs must use the same screening service as manual runs.

   ## Phase 18: Excel export

   ### Purpose

   Export screening results, holdings, and decisions.

   ### Main files

   ```text
   app/api/routes/exports.py
   app/services/export_service.py
   app/schemas/export.py
   ```

   Exports should include company information, market, metrics, score, rule
   breakdown, decision, reason, run ID, rule version, and data date.

   ## Phase 19: Audit and troubleshooting logs

   ### Purpose

   Track business changes and technical failures.

   ### Main files

   ```text
   app/core/logging.py
   app/services/audit_service.py
   app/models/audit_event.py
   app/repositories/audit_repository.py
   ```

   Audit events include rule changes, profile changes, run creation, decision
   changes, holdings uploads, and exports.

   Technical logs include request ID, endpoint, run ID, provider, response status,
   duration, error type, and a safe error message.

   Never log API keys, passwords, full uploaded files, or sensitive user data.

   ## Configuration without an API key

   ```env
   APP_ENV=development
   DATA_PROVIDER=mock
   VENDOR_API_KEY=
   VENDOR_BASE_URL=
   DATABASE_URL=sqlite:///./screening.db
   ```

   Later:

   ```env
   APP_ENV=development
   DATA_PROVIDER=vendor_name
   VENDOR_API_KEY=provided-api-key
   VENDOR_BASE_URL=https://vendor-api-url
   DATABASE_URL=postgresql://...
   ```

   ## Recommended implementation order

   ```text
   1.  FastAPI foundation
   2.  Common data contracts
   3.  Mock provider
   4.  Replaceable vendor adapter
   5.  Raw response storage
   6.  Security master
   7.  Database and migrations
   8.  Screening request API
   9.  Data ingestion
   10. Metrics engine
   11. Rule engine
   12. Funnel and score breakdown
   13. Run manager
   14. Results APIs
   15. Holdings import and storage
   16. Analyst decisions
   17. Scheduler
   18. Excel export
   19. Audit and troubleshooting logs
   20. Connect frontend to backend
   ```

   ## Expected final flow

   ```text
   Frontend
      ↓
   Selected countries, exchanges, and rules
      ↓
   Backend validates the request
      ↓
   Mock or real vendor adapter fetches data
      ↓
   Raw response is stored
      ↓
   Data is normalized
      ↓
   Security master is updated
      ↓
   Metrics are calculated
      ↓
   Rules are applied
      ↓
   Funnel and score breakdowns are stored
      ↓
   Immutable run is saved
      ↓
   Results are returned to the frontend
      ↓
   User reviews results, holdings, and decisions
   ```

   ## Manager summary

   We will build the backend in phases, starting with a mock data provider so
   development does not depend on an API key. The backend will use a
   vendor-independent adapter and common data format. When the real vendor and
   API key are provided, we will replace the mock adapter without changing the
   metrics engine, rule engine, database structure, or frontend API flow.

   This approach supports raw data history, reproducible screening runs,
   explainable results, holdings, decisions, scheduling, exports, and audit logs.
