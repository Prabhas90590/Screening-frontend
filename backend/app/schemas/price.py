"""Canonical price and trading volume schema.

Represents standardized price points, trading liquidity, beta, and historical returns,
supporting client-specified display currencies (defaulting to USD / $).
"""

from typing import Optional
from pydantic import BaseModel, Field


class NormalizedPrice(BaseModel):
    """Normalized market pricing, liquidity, and risk metrics."""
    ticker: str = Field(..., description="Ticker symbol")
    close_price: float = Field(..., description="Latest closing price in original local exchange currency")
    currency: str = Field(default="USD", description="Local quotation currency, e.g. 'INR', 'JPY', 'USD'")
    price_usd: float = Field(..., description="Price converted to global benchmark USD ($)")
    display_currency: str = Field(
        default="USD", description="Currency specified by the client for display (default 'USD' / '$')"
    )
    display_price: float = Field(
        default=0.0, description="Price converted to the client's chosen display_currency"
    )
    fx_rate_to_display: float = Field(
        default=1.0, description="Exchange rate applied: close_price * fx_rate_to_display = display_price"
    )
    avg_daily_volume: Optional[float] = Field(None, description="Average daily trading volume (shares)")
    avg_daily_traded_value_usd: Optional[float] = Field(None, description="Average daily traded value in USD")
    beta: Optional[float] = Field(None, description="Beta vs market benchmark (e.g. S&P 500 / MSCI World)")
    high_52w: Optional[float] = Field(None, description="52-week high price in local currency")
    low_52w: Optional[float] = Field(None, description="52-week low price in local currency")
    return_3y: Optional[float] = Field(None, description="3-year total return percentage")
    return_5y: Optional[float] = Field(None, description="5-year total return percentage")
    as_of_date: Optional[str] = Field(None, description="Date stamp of the price observation")
