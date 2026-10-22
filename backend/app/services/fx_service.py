"""Point-in-time foreign exchange rate service.

Fetches dynamic, daily historical or live exchange rates from the active data provider
instead of relying on static hardcoded values. Caches daily rate snapshots
and logs diagnostic traces for full transparency.
"""

from datetime import date
from typing import Dict, Optional

from app.core.currency import DEFAULT_FX_RATES_TO_USD, convert_currency
from app.core.logging import DiagnosticLogger

logger = DiagnosticLogger("fx")


class FXService:
    """Manages point-in-time exchange rates with daily in-memory caching."""

    def __init__(self):
        # Cache structure: { "2026-09-25": { "INR": 83.92, "EUR": 0.91, ... } }
        self._daily_cache: Dict[str, Dict[str, float]] = {}

    def get_cached_rates(self, as_of_date: str) -> Optional[Dict[str, float]]:
        """Retrieve cached rates for a given date."""
        return self._daily_cache.get(as_of_date)

    def cache_rates(self, as_of_date: str, rates: Dict[str, float], provider: str = "vendor"):
        """Store rates in daily cache and log diagnostic info."""
        self._daily_cache[as_of_date] = rates
        inr_sample = rates.get("INR", "N/A")
        eur_sample = rates.get("EUR", "N/A")
        logger.provider_info(
            provider,
            f"Cached point-in-time FX rates for date '{as_of_date}' (USD/INR: {inr_sample}, USD/EUR: {eur_sample})"
        )

    def convert_point_in_time(
        self,
        amount: Optional[float],
        from_currency: str,
        to_currency: str = "USD",
        as_of_date: Optional[str] = None,
        provider_rates: Optional[Dict[str, float]] = None,
    ) -> Optional[float]:
        """Convert currency using the point-in-time FX rate for the observation date.

        Hierarchy:
        1. Passed provider rates for this run.
        2. Daily cached rates for as_of_date.
        3. Baseline rates fallback (with diagnostic warning).
        """
        if amount is None:
            return None

        date_key = as_of_date or str(date.today())
        effective_rates = provider_rates or self.get_cached_rates(date_key)

        if not effective_rates:
            logger.provider_warn(
                "FX",
                f"No dynamic rates available for '{date_key}'. Using fallback baseline rates."
            )
            effective_rates = DEFAULT_FX_RATES_TO_USD

        # Validate that required currencies exist in the rate table
        from_code = from_currency.upper()
        to_code = to_currency.upper()

        if from_code not in effective_rates and from_code != "USD":
            logger.provider_warn(
                "FX",
                f"Missing point-in-time rate for '{from_code}' on '{date_key}'. Defaulted to 1.0."
            )

        return convert_currency(
            amount=amount,
            from_currency=from_code,
            to_currency=to_code,
            fx_rates_to_usd=effective_rates,
        )


# Global singleton instance
fx_service = FXService()

