"""Abstract base interface for all market data provider adapters.

Any vendor (Mock, EODHD, LSEG/Refinitiv, FactSet, AlphaVantage, etc.) must implement
this contract. The core screening engine, metrics engine, and rules engine interact
exclusively through this interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from app.schemas.listing import NormalizedListing
from app.schemas.normalized_data import NormalizedSecurityData


class BaseDataProvider(ABC):
    """Abstract interface defining required vendor operations."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Machine-readable name of the provider, e.g. 'mock', 'eodhd', 'lseg'."""
        pass

    @abstractmethod
    async def fetch_listings(
        self, country_id: str, exchange_id: str
    ) -> List[NormalizedListing]:
        """Retrieve all active listings for a given exchange.

        Args:
            country_id: Canonical country identifier, e.g. 'us', 'jp'
            exchange_id: Canonical exchange identifier, e.g. 'nasdaq', 'tse'

        Returns:
            List of NormalizedListing objects.
        """
        pass

    @abstractmethod
    async def fetch_security_data(
        self, ticker: str, exchange_id: str
    ) -> Optional[NormalizedSecurityData]:
        """Fetch full normalized fundamentals, prices, and estimates for a single security.

        Args:
            ticker: Security trading symbol, e.g. 'HMP' or '6501-TO'
            exchange_id: Exchange identifier, e.g. 'nasdaq', 'tse'

        Returns:
            NormalizedSecurityData object, or None if not found.
        """
        pass

    @abstractmethod
    async def fetch_batch_securities(
        self, exchange_id: str, tickers: Optional[List[str]] = None
    ) -> List[NormalizedSecurityData]:
        """Fetch normalized fundamentals for multiple securities (efficient bulk ingestion).

        Args:
            exchange_id: Canonical exchange identifier
            tickers: Optional list of tickers to restrict the batch to

        Returns:
            List of NormalizedSecurityData objects.
        """
        pass

    @abstractmethod
    async def fetch_fx_rates(
        self, base_currency: str = "USD", as_of_date: Optional[str] = None
    ) -> Dict[str, float]:
        """Fetch point-in-time daily foreign exchange rates for a specific date.

        Args:
            base_currency: Anchor currency (typically 'USD')
            as_of_date: Trading date stamp (e.g. '2026-09-25'), or None for latest market close

        Returns:
            Dict mapping currency codes to exchange rates relative to 1 base unit
            (e.g. {'INR': 83.92, 'EUR': 0.91, 'JPY': 151.20})
        """
        pass

    @abstractmethod
    async def check_health(self) -> bool:
        """Verify connectivity to the provider endpoint or local mock availability."""
        pass
