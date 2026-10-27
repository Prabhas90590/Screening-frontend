"""Mock data provider adapter.

Simulates a real financial market data vendor (like EODHD or LSEG) completely offline.
Provides realistic equity universes across multiple countries and sectors,
point-in-time dynamic FX exchange rates, and edge-case testing fixtures.
"""

from datetime import date
import hashlib
from typing import Any, Dict, List, Optional

from app.adapters.base import BaseDataProvider
from app.core.currency import DEFAULT_FX_RATES_TO_USD
from app.core.logging import DiagnosticLogger
from app.ingestion.data_adapter import normalize_vendor_payload
from app.schemas.listing import NormalizedListing
from app.schemas.normalized_data import NormalizedSecurityData

logger = DiagnosticLogger("mock_adapter")


# Curated realistic mock raw payloads simulating vendor JSON formats
RAW_MOCK_SECURITIES: List[Dict[str, Any]] = [
    {
        "ticker": "HMP",
        "name": "Harbor Midstream Partners",
        "country": "US",
        "exchange": "NASDAQ",
        "sector": "Energy",
        "currency": "USD",
        "market_cap": 8.4e9,
        "close_price": 42.50,
        "fwdPe": 10.4,
        "peg": 0.8,
        "ebitda": 1.1e9,
        "net_debt": 3.74e9,  # ~3.4x Net Debt / EBITDA
        "beta": 0.62,
        "yieldPct": 8.9,
        "epsGrowthPct": 11.2,
        "revenue": 4.2e9,
        "avg_daily_volume": 1250000,
        "estimateNote": "EPS FY2 estimate consensus strong across 8 analysts",
        "freshnessNote": "Fundamentals as of latest quarterly filing",
    },
    {
        "Code": "KSTL",  # EODHD-style key
        "General": {"Name": "Kestrel Components", "CountryISO": "US", "Sector": "Info Tech", "Exchange": "NASDAQ"},
        "currency": "USD",
        "Highlights": {"MarketCapitalization": 14.8e9, "LatestClose": 118.20, "EBITDA": 1.76e9, "NetDebt": 1.58e9},
        "Valuation": {"ForwardPE": 12.1, "PEGRatio": 0.7},
        "beta": 0.95,
        "yieldPct": 1.2,
        "epsGrowthPct": 14.0,
    },
    {
        "ticker": "6501-TO",
        "name": "Sakura Precision",
        "country": "JP",
        "exchange": "TSE",
        "sector": "Industrials",
        "currency": "JPY",
        "market_cap": 850e9,  # JPY
        "close_price": 2850.0,
        "fwdPe": 14.2,
        "peg": 1.3,
        "ebitda": 108e9,
        "net_debt": -15e9,  # Net cash
        "beta": 0.84,
        "yieldPct": 2.1,
        "epsGrowthPct": 7.8,
        "estimateNote": "TSE reporting cycle +3 days translation lag",
    },
    {
        "ticker": "INFY",
        "name": "Infosys Limited",
        "country": "IN",
        "exchange": "NSE",
        "sector": "Info Tech",
        "currency": "INR",
        "market_cap": 7750e9,  # INR ~92B USD
        "close_price": 1850.0,
        "fwdPe": 24.2,
        "peg": 1.8,
        "ebitda": 380e9,
        "net_debt": -85e9,  # Net cash
        "beta": 0.82,
        "yieldPct": 2.4,
        "epsGrowthPct": 10.5,
        "isin": "INE009A01021",
    },
    {
        "ticker": "FJDM",
        "name": "Fjord Maritime",
        "country": "NO",
        "exchange": "OSE",
        "sector": "Industrials",
        "currency": "NOK",
        "market_cap": 18.2e9,  # NOK
        "close_price": 145.0,
        "fwdPe": 6.8,
        "peg": 0.8,
        "ebitda": 3.37e9,
        "net_debt": 7.08e9,  # 2.1x
        "beta": 0.92,
        "yieldPct": 6.5,
        "epsGrowthPct": 8.5,
    },
    {
        "ticker": "BNYF",
        "name": "Banyan Foods",
        "country": "SG",
        "exchange": "SGX",
        "sector": "Cons. Staples",
        "currency": "SGD",
        "market_cap": 6.5e9,
        "close_price": 4.80,
        "fwdPe": 16.4,
        "peg": 1.5,
        "ebitda": 680e6,
        "net_debt": 816e6,  # 1.2x
        "beta": 0.54,
        "yieldPct": 3.5,
        "epsGrowthPct": 6.2,
    },
    {
        "ticker": "CBT",
        "name": "Cobalt Telecom",
        "country": "US",
        "exchange": "NYSE",
        "sector": "Comm.",
        "currency": "USD",
        "market_cap": 22.4e9,
        "close_price": 34.20,
        "fwdPe": 12.9,
        "peg": 1.4,
        "ebitda": 3.6e9,
        "net_debt": 10.1e9,  # 2.8x
        "beta": 0.65,
        "yieldPct": 5.8,
        "epsGrowthPct": 4.1,
    },
    {
        "ticker": "BRE",
        "name": "Bharat Renewable Energy",
        "country": "IN",
        "exchange": "NSE",
        "sector": "Utilities",
        "currency": "INR",
        "market_cap": 920e9,
        "close_price": 420.0,
        "fwdPe": 18.5,
        "peg": 1.6,
        "ebitda": 52e9,
        "net_debt": 286e9,  # 5.5x Net debt / EBITDA (Tests sector limit)
        "beta": 0.75,
        "yieldPct": 3.8,
        "epsGrowthPct": 8.0,
    },
    {
        "ticker": "TFT",
        "name": "Toronto Financial Trust",
        "country": "CA",
        "exchange": "TSX",
        "sector": "Financials",
        "currency": "CAD",
        "market_cap": 31.0e9,
        "close_price": 76.50,
        "fwdPe": 11.2,
        "peg": 1.1,
        "ebitda": None,  # Financials: EBITDA is N/A
        "net_debt": None,
        "beta": 0.88,
        "yieldPct": 4.6,
        "epsGrowthPct": 7.2,
    },
    {
        "ticker": "TCS",
        "name": "Tata Consultancy Services",
        "country": "IN",
        "exchange": "BSE",
        "sector": "Info Tech",
        "currency": "INR",
        "market_cap": 14200e9,  # ~168B USD
        "close_price": 3950.0,
        "fwdPe": 26.5,
        "peg": 2.1,
        "ebitda": 640e9,
        "net_debt": -120e9,  # Net cash
        "beta": 0.78,
        "yieldPct": 1.9,
        "epsGrowthPct": 12.0,
        "isin": "INE467B01029",
    },
    {
        "ticker": "NOVN",
        "name": "Novartis International",
        "country": "CH",
        "exchange": "SIX",
        "sector": "Health Care",
        "currency": "CHF",
        "market_cap": 210.0e9,  # CHF
        "close_price": 98.40,
        "fwdPe": 14.8,
        "peg": 1.2,
        "ebitda": 21.5e9,
        "net_debt": 15.2e9,
        "beta": 0.58,
        "yieldPct": 3.6,
        "epsGrowthPct": 8.4,
    },
    {
        "ticker": "AZN",
        "name": "AstraZeneca PLC",
        "country": "UK",
        "exchange": "LSE",
        "sector": "Health Care",
        "currency": "GBP",
        "market_cap": 185.0e9,  # GBP
        "close_price": 118.50,
        "fwdPe": 16.5,
        "peg": 1.4,
        "ebitda": 19.8e9,
        "net_debt": 24.5e9,
        "beta": 0.62,
        "yieldPct": 2.2,
        "epsGrowthPct": 11.5,
    },
    {
        "ticker": "005930",
        "name": "Samsung Electronics",
        "country": "KR",
        "exchange": "KRX",
        "sector": "Info Tech",
        "currency": "KRW",
        "market_cap": 420000e9,  # KRW
        "close_price": 68000.0,
        "fwdPe": 10.8,
        "peg": 0.9,
        "ebitda": 58000e9,
        "net_debt": -85000e9,  # Massive Net Cash
        "beta": 0.94,
        "yieldPct": 2.1,
        "epsGrowthPct": 14.5,
    },
    {
        "ticker": "0700",
        "name": "Tencent Holdings",
        "country": "HK",
        "exchange": "HKEX",
        "sector": "Comm.",
        "currency": "HKD",
        "market_cap": 3800.0e9,  # HKD
        "close_price": 420.0,
        "fwdPe": 15.2,
        "peg": 1.1,
        "ebitda": 260.0e9,
        "net_debt": -45.0e9,
        "beta": 0.88,
        "yieldPct": 1.1,
        "epsGrowthPct": 15.0,
    },
    # Edge-case fixture 1: Loss-making company (Tests negative EBITDA/EPS guards)
    {
        "ticker": "NOVX",
        "name": "Nova BioTech Research",
        "country": "US",
        "exchange": "NASDAQ",
        "sector": "Health Care",
        "currency": "USD",
        "market_cap": 1.8e9,
        "close_price": 18.20,
        "fwdPe": None,  # Loss-making
        "peg": None,
        "ebitda": -45e6,  # Negative EBITDA!
        "net_debt": -120e6,
        "beta": 1.45,
        "yieldPct": 0.0,
        "epsGrowthPct": -12.0,
    },
    # Edge-case fixture 2: Missing data company (Tests confidence downgrade & logs)
    {
        "ticker": "AMPL",
        "name": "Amplify Global Materials",
        "country": "US",
        "exchange": "NYSE",
        "sector": "Materials",
        "currency": "USD",
        "market_cap": 3.2e9,
        "close_price": 28.00,
        "fwdPe": None,  # Missing
        "peg": None,    # Missing
        "ebitda": None, # Missing
        "net_debt": 800e6,
        "beta": 1.10,
        "yieldPct": 2.0,
        "epsGrowthPct": None,
    },
]


class MockAdapter(BaseDataProvider):
    """Mock implementation of BaseDataProvider for local offline development."""

    def __init__(self):
        from app.adapters.indian_stocks_fixtures import INDIAN_MOCK_SECURITIES
        from app.adapters.global_stocks_fixtures import GLOBAL_MOCK_SECURITIES
        self._securities = RAW_MOCK_SECURITIES + INDIAN_MOCK_SECURITIES + GLOBAL_MOCK_SECURITIES

    @property
    def provider_name(self) -> str:
        return "mock"

    async def fetch_listings(
        self, country_id: str, exchange_id: str
    ) -> List[NormalizedListing]:
        """Return mock listings for the given country and exchange."""
        logger.provider_info("MOCK", f"Fetching listings for {country_id.upper()}/{exchange_id.upper()}")
        listings: List[NormalizedListing] = []

        norm_country = country_id.lower()
        norm_exchange = exchange_id.lower()

        for raw in self._securities:
            raw_country = (raw.get("country") or raw.get("General", {}).get("CountryISO", "US")).lower()
            raw_exchange = (raw.get("exchange") or raw.get("General", {}).get("Exchange", "NASDAQ")).lower()

            if (raw_country == norm_country or norm_country in {"all", "*"}) and (
                not raw_exchange or raw_exchange == norm_exchange or norm_exchange in {"all", "*"}
            ):
                ticker = raw.get("ticker") or raw.get("Code", "UNKN")
                listings.append(
                    NormalizedListing(
                        listing_id=f"list-{norm_exchange}-{ticker.lower()}",
                        canonical_company_id=f"comp-{norm_country}-{norm_exchange}-{ticker.lower()}",
                        ticker=ticker,
                        exchange_id=norm_exchange,
                        country_id=norm_country,
                        currency=raw.get("currency", "USD"),
                        is_primary=True,
                    )
                )

        logger.provider_info("MOCK", f"Found {len(listings)} listings for {norm_country}/{norm_exchange}")
        return listings

    async def fetch_security_data(
        self, ticker: str, exchange_id: str
    ) -> Optional[NormalizedSecurityData]:
        """Find a single mock security by ticker and return normalized data."""
        clean_ticker = ticker.strip().upper()
        logger.provider_info("MOCK", f"Fetching fundamentals for ticker '{clean_ticker}' on {exchange_id}")

        for raw in self._securities:
            cand_ticker = (raw.get("ticker") or raw.get("Code", "")).upper()
            if cand_ticker == clean_ticker:
                return normalize_vendor_payload(raw, default_exchange=exchange_id)

        logger.provider_warn("MOCK", f"Ticker '{clean_ticker}' not found in mock fixtures.")
        return None

    async def fetch_batch_securities(
        self, exchange_id: str, tickers: Optional[List[str]] = None
    ) -> List[NormalizedSecurityData]:
        """Fetch all mock securities belonging to the exchange."""
        logger.provider_info(
            "MOCK",
            f"Batch fetching securities for exchange '{exchange_id}' (filtered to {len(tickers)} tickers)"
            if tickers else f"Batch fetching all securities for exchange '{exchange_id}'"
        )

        filter_set = {t.strip().upper() for t in tickers} if tickers else None
        results: List[NormalizedSecurityData] = []
        norm_exchange = exchange_id.lower()

        for raw in self._securities:
            raw_exchange = (raw.get("exchange") or raw.get("General", {}).get("Exchange", "")).lower()
            if raw_exchange and raw_exchange != norm_exchange and raw_exchange != "*":
                continue

            cand_ticker = (raw.get("ticker") or raw.get("Code", "")).upper()
            if filter_set is None or cand_ticker in filter_set:
                norm_data = normalize_vendor_payload(raw, default_exchange=exchange_id)
                results.append(norm_data)

        logger.provider_info("MOCK", f"Normalized and returned {len(results)} securities for '{exchange_id}'")
        return results

    async def fetch_fx_rates(
        self, base_currency: str = "USD", as_of_date: Optional[str] = None
    ) -> Dict[str, float]:
        """Generate realistic point-in-time daily FX rates with slight deterministic drift."""
        date_str = as_of_date or str(date.today())
        logger.provider_info("MOCK", f"Fetching point-in-time FX rates for date '{date_str}'")

        # Create a deterministic small drift based on date hash (e.g. +/- 0.5%)
        # so historical dates realistically differ from today without being random
        seed = int(hashlib.md5(date_str.encode()).hexdigest()[:6], 16)
        drift_factor = 1.0 + ((seed % 100) - 50) / 10000.0  # Range: 0.995 to 1.005

        dynamic_rates: Dict[str, float] = {}
        for curr, base_rate in DEFAULT_FX_RATES_TO_USD.items():
            if curr == "USD":
                dynamic_rates[curr] = 1.0
            else:
                dynamic_rates[curr] = round(base_rate * drift_factor, 4)

        logger.provider_info(
            "MOCK",
            f"Generated FX rates for '{date_str}': USD/INR={dynamic_rates.get('INR')}, USD/EUR={dynamic_rates.get('EUR')}"
        )
        return dynamic_rates

    async def check_health(self) -> bool:
        """Mock provider is always available offline."""
        return True

