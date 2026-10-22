"""Currency and FX conversion utilities.

Enables clients to select their desired reporting currency (defaulting to USD / $),
and provides standardized currency formatting and exchange rate conversions across global markets.
"""

from typing import Dict, Optional


# Standard currency symbols for clean UI formatting
CURRENCY_SYMBOLS: Dict[str, str] = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "INR": "₹",
    "JPY": "¥",
    "CAD": "C$",
    "AUD": "A$",
    "SGD": "S$",
    "CHF": "CHF",
    "HKD": "HK$",
    "KRW": "₩",
    "SEK": "kr",
    "NOK": "kr",
    "TWD": "NT$",
    "BRL": "R$",
    "CNY": "¥",
    "SAR": "SR",
    "AED": "AED",
    "ZAR": "R",
    "IDR": "Rp",
    "MXN": "Mex$",
    "NZD": "NZ$",
}

# Baseline FX rates relative to 1 USD
# E.g., 1 USD = 84.10 INR, 1 USD = 0.92 EUR
DEFAULT_FX_RATES_TO_USD: Dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "INR": 84.10,
    "JPY": 152.50,
    "CAD": 1.38,
    "AUD": 1.51,
    "SGD": 1.32,
    "CHF": 0.87,
    "HKD": 7.77,
    "KRW": 1380.0,
    "SEK": 10.55,
    "NOK": 10.95,
    "TWD": 32.10,
    "BRL": 5.70,
    "CNY": 7.12,
    "SAR": 3.75,
    "AED": 3.67,
    "ZAR": 17.80,
    "IDR": 15600.0,
    "MXN": 19.85,
    "NZD": 1.67,
}


def get_currency_symbol(currency_code: str) -> str:
    """Return the display symbol for a currency code (e.g. 'USD' -> '$', 'INR' -> '₹')."""
    return CURRENCY_SYMBOLS.get(currency_code.upper(), currency_code.upper())


def convert_currency(
    amount: Optional[float],
    from_currency: str,
    to_currency: str = "USD",
    fx_rates_to_usd: Optional[Dict[str, float]] = None,
) -> Optional[float]:
    """Convert an amount from one currency to another using USD as the base pivot.

    Example:
        convert_currency(1850, from_currency="INR", to_currency="USD") -> 22.0
    """
    if amount is None:
        return None

    rates = fx_rates_to_usd or DEFAULT_FX_RATES_TO_USD
    from_code = from_currency.upper()
    to_code = to_currency.upper()

    if from_code == to_code:
        return amount

    # Step 1: Convert to USD
    from_rate = rates.get(from_code, 1.0)
    amount_in_usd = amount / from_rate if from_rate else amount

    # Step 2: Convert from USD to target currency
    to_rate = rates.get(to_code, 1.0)
    converted = amount_in_usd * to_rate

    return round(converted, 2)


def format_currency_value(
    amount: Optional[float],
    currency_code: str = "USD",
    abbreviate: bool = False,
) -> str:
    """Format a monetary amount with its symbol and optional abbreviations (B, M, K).

    Examples:
        format_currency_value(14200000000, "USD", abbreviate=True) -> "$14.2B"
        format_currency_value(22.0, "USD") -> "$22.00"
        format_currency_value(1850.0, "INR") -> "₹1,850.00"
    """
    if amount is None:
        return "—"

    symbol = get_currency_symbol(currency_code)

    if abbreviate:
        abs_amount = abs(amount)
        if abs_amount >= 1e12:
            return f"{symbol}{amount / 1e12:.2f}T"
        if abs_amount >= 1e9:
            return f"{symbol}{amount / 1e9:.2f}B"
        if abs_amount >= 1e6:
            return f"{symbol}{amount / 1e6:.2f}M"
        if abs_amount >= 1e3:
            return f"{symbol}{amount / 1e3:.2f}K"

    return f"{symbol}{amount:,.2f}"
