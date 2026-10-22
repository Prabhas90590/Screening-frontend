"""Provider registry and adapter factory.

Instantiates and returns the active data provider adapter based on
the DATA_PROVIDER environment configuration (defaults to 'mock').
"""

from typing import Dict, Optional

from app.adapters.base import BaseDataProvider
from app.adapters.mock_adapter import MockAdapter
from app.core.config import settings
from app.core.logging import DiagnosticLogger

logger = DiagnosticLogger("adapter_registry")

_ACTIVE_PROVIDER: Optional[BaseDataProvider] = None


def get_data_provider() -> BaseDataProvider:
    """Retrieve the singleton data provider adapter configured in .env.

    If DATA_PROVIDER=mock: Returns MockAdapter.
    If DATA_PROVIDER=eodhd: Returns EODHDAdapter (Phase 4).
    If DATA_PROVIDER=lseg:  Returns LSEGAdapter (Phase 4).
    """
    global _ACTIVE_PROVIDER
    if _ACTIVE_PROVIDER is not None:
        return _ACTIVE_PROVIDER

    provider_name = settings.data_provider.strip().lower()
    logger.provider_info("REGISTRY", f"Initializing market data provider: '{provider_name}'")

    if provider_name == "mock":
        _ACTIVE_PROVIDER = MockAdapter()
        return _ACTIVE_PROVIDER

    # Future phase hooks
    if provider_name == "eodhd":
        try:
            from app.adapters.vendor_adapter import EODHDAdapter
            _ACTIVE_PROVIDER = EODHDAdapter(
                api_key=settings.vendor_api_key,
                base_url=settings.vendor_base_url or "https://eodhistoricaldata.com/api",
            )
            return _ACTIVE_PROVIDER
        except ImportError:
            logger.provider_warn(
                "REGISTRY",
                "EODHDAdapter not yet implemented. Falling back to MockAdapter for development."
            )
            _ACTIVE_PROVIDER = MockAdapter()
            return _ACTIVE_PROVIDER

    if provider_name == "lseg":
        try:
            from app.adapters.vendor_adapter import LSEGAdapter
            _ACTIVE_PROVIDER = LSEGAdapter(
                api_key=settings.vendor_api_key,
                base_url=settings.vendor_base_url or "https://api.refinitiv.com",
            )
            return _ACTIVE_PROVIDER
        except ImportError:
            logger.provider_warn(
                "REGISTRY",
                "LSEGAdapter not yet implemented. Falling back to MockAdapter for development."
            )
            _ACTIVE_PROVIDER = MockAdapter()
            return _ACTIVE_PROVIDER

    raise ValueError(
        f"Unsupported DATA_PROVIDER '{provider_name}'. Supported values: 'mock', 'eodhd', 'lseg'."
    )

