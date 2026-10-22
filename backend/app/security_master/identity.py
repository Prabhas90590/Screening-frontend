"""Security master identity service.

Generates and matches stable, canonical security identities across different
vendor naming schemes, dual listings, and ticker renames.
"""

import re
from typing import Optional


def normalize_ticker(raw_ticker: str) -> str:
    """Standardize ticker format by removing vendor prefixes/suffixes, dots, and spaces.

    Examples:
        'AAPL.US' -> 'AAPL'
        ' 6501-TO ' -> '6501-TO'
        'EXM:NASDAQ' -> 'EXM'
    """
    cleaned = raw_ticker.strip().upper()
    # Strip common exchange suffixes like '.US', '.TO', '.L' if dot-separated
    parts = cleaned.split(".")
    if len(parts) == 2 and len(parts[1]) <= 3 and not parts[0].isdigit():
        return parts[0]
    return cleaned


def generate_canonical_id(
    country_code: str,
    exchange_code: str,
    ticker: str,
    isin: Optional[str] = None,
    figi: Optional[str] = None,
) -> str:
    """Generate a deterministic, canonical company ID.

    Priority hierarchy:
    1. Global FIGI (if present): 'comp-figi-{figi}'
    2. Global ISIN (if present): 'comp-isin-{isin}'
    3. Country + Exchange + Normalized Ticker: 'comp-{country}-{exchange}-{ticker}'
    """
    if figi and figi.strip():
        sanitized_figi = re.sub(r"[^A-Za-z0-9]", "", figi.strip()).lower()
        return f"comp-figi-{sanitized_figi}"

    if isin and isin.strip():
        sanitized_isin = re.sub(r"[^A-Za-z0-9]", "", isin.strip()).lower()
        return f"comp-isin-{sanitized_isin}"

    clean_country = re.sub(r"[^A-Za-z0-9]", "", country_code.strip()).lower()
    clean_exchange = re.sub(r"[^A-Za-z0-9]", "", exchange_code.strip()).lower()
    clean_ticker = re.sub(r"[^A-Za-z0-9]", "", normalize_ticker(ticker)).lower()

    return f"comp-{clean_country}-{clean_exchange}-{clean_ticker}"


def generate_listing_id(exchange_code: str, ticker: str) -> str:
    """Generate a deterministic listing identifier."""
    clean_exchange = re.sub(r"[^A-Za-z0-9]", "", exchange_code.strip()).lower()
    clean_ticker = re.sub(r"[^A-Za-z0-9]", "", normalize_ticker(ticker)).lower()
    return f"list-{clean_exchange}-{clean_ticker}"

