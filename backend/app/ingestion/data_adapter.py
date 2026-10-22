"""Data normalization adapter.

Transforms heterogeneous vendor payloads (EODHD, LSEG/Refinitiv, FMP, Mock)
into unified, canonical NormalizedSecurityData models.
Applies point-in-time dynamic FX conversion matching the observation date,
rather than static hardcoded rates. Supports client-specified display currencies (defaulting to USD / $).
Logs detailed troubleshooting messages whenever fields are missing, malformed, or ambiguous.
"""

from datetime import date
from typing import Any, Dict, List, Optional, Tuple, Union

from app.core.currency import get_currency_symbol
from app.core.logging import DiagnosticLogger
from app.schemas.company import NormalizedCompany
from app.schemas.estimates import NormalizedEstimates
from app.schemas.financials import NormalizedFinancials
from app.schemas.listing import NormalizedListing
from app.schemas.normalized_data import (
    ConfidenceDetails,
    DataConfidenceLevel,
    NormalizedSecurityData,
)
from app.schemas.price import NormalizedPrice
from app.security_master.identity import (
    generate_canonical_id,
    generate_listing_id,
    normalize_ticker,
)
from app.services.fx_service import fx_service

logger = DiagnosticLogger("ingestion")


def _resolve_nested_path(data: Dict[str, Any], path: str) -> Any:
    """Traverse a dotted path (e.g. 'Financials.Income_Statement.ebitda') in a dict."""
    current = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _extract_first_match(data: Dict[str, Any], possible_paths: List[str]) -> Any:
    """Find the first matching value among multiple vendor-specific field paths."""
    for path in possible_paths:
        val = _resolve_nested_path(data, path)
        if val is not None and val != "" and val != "N/A":
            return val
    return None


def _safe_float(val: Any, field_name: str, ticker: str, default: Optional[float] = None) -> Optional[float]:
    """Safely convert numbers, handling strings, currencies, percentages, and scientific notation."""
    if val is None or val == "" or val == "N/A" or val == "None":
        return default
    if isinstance(val, (int, float)):
        return float(val)

    clean_val = str(val).strip().replace(",", "").replace("$", "").replace("%", "").replace("x", "")
    multiplier = 1.0
    if clean_val.endswith("B") or clean_val.endswith("b"):
        multiplier = 1e9
        clean_val = clean_val[:-1]
    elif clean_val.endswith("M") or clean_val.endswith("m"):
        multiplier = 1e6
        clean_val = clean_val[:-1]
    elif clean_val.endswith("K") or clean_val.endswith("k"):
        multiplier = 1e3
        clean_val = clean_val[:-1]

    try:
        return float(clean_val) * multiplier
    except (ValueError, TypeError):
        logger.normalize_warn(
            ticker,
            f"Field '{field_name}' had unexpected non-numeric value: '{val}'. Defaulted to {default}."
        )
        return default


def normalize_vendor_payload(
    raw_payload: Dict[str, Any],
    default_exchange: str = "nasdaq",
    default_country: str = "us",
    target_display_currency: str = "USD",
    point_in_time_fx_rates: Optional[Dict[str, float]] = None,
) -> NormalizedSecurityData:
    """Normalize a raw vendor dictionary into a validated NormalizedSecurityData object.

    Supports EODHD, LSEG/Refinitiv, and standard JSON formats.
    Converts prices and market values dynamically using the point-in-time FX rates
    for the exact observation date stamp.
    """
    missing_fields: List[str] = []

    # 1. Resolve Ticker & Identifiers
    raw_ticker = _extract_first_match(raw_payload, [
        "ticker", "Code", "Symbol", "symbol", "TR.TickerSymbol", "RIC"
    ]) or "UNKNOWN"
    ticker = normalize_ticker(raw_ticker)

    name = _extract_first_match(raw_payload, [
        "name", "Name", "General.Name", "TR.CompanyName", "companyName"
    ]) or f"{ticker} Corporation"

    country = _extract_first_match(raw_payload, [
        "country", "General.CountryName", "General.CountryISO", "countryISO", "TR.HeadquartersCountry"
    ]) or default_country.upper()

    exchange = _extract_first_match(raw_payload, [
        "exchange", "Exchange", "General.Exchange", "TR.ExchangeName"
    ]) or default_exchange.upper()

    sector = _extract_first_match(raw_payload, [
        "sector", "General.Sector", "TR.TRBCSector", "sectorName"
    ]) or "Unclassified"

    raw_currency = (
        _extract_first_match(raw_payload, ["currency", "General.CurrencyCode", "TR.Currency"])
        or ("INR" if country.upper() in {"IN", "INDIA"} else "USD")
    )

    isin = _extract_first_match(raw_payload, ["isin", "General.ISIN", "TR.ISIN"])
    figi = _extract_first_match(raw_payload, ["figi", "General.OpenFigi", "TR.FIGI"])
    as_of_date = (
        _extract_first_match(raw_payload, ["as_of_date", "freshnessDate", "date"])
        or str(date.today())
    )

    # 2. Market Cap & Categorization (Point-in-Time FX Conversion)
    market_cap_raw = _extract_first_match(raw_payload, [
        "market_cap", "marketCap", "Highlights.MarketCapitalization", "TR.CompanyMarketCap"
    ])
    raw_market_cap = _safe_float(market_cap_raw, "market_cap", ticker, default=0.0)
    if raw_market_cap == 0.0:
        missing_fields.append("market_cap")

    market_cap_usd = fx_service.convert_point_in_time(
        amount=raw_market_cap,
        from_currency=raw_currency,
        to_currency="USD",
        as_of_date=as_of_date,
        provider_rates=point_in_time_fx_rates,
    ) or 0.0

    market_cap_display = fx_service.convert_point_in_time(
        amount=raw_market_cap,
        from_currency=raw_currency,
        to_currency=target_display_currency,
        as_of_date=as_of_date,
        provider_rates=point_in_time_fx_rates,
    ) or 0.0

    if market_cap_usd >= 10e9:
        cap_category = "Large-cap Quality"
    elif market_cap_usd >= 2e9:
        cap_category = "Mid-cap Value"
    else:
        cap_category = "Small-cap Opportunity"

    # 3. Price & Trading Liquidity (Point-in-Time FX Conversion)
    close_price_raw = _extract_first_match(raw_payload, [
        "close_price", "price", "Highlights.LatestClose", "close", "TR.PriceClose"
    ])
    close_price = _safe_float(close_price_raw, "close_price", ticker, default=0.0)
    if close_price == 0.0:
        missing_fields.append("close_price")

    price_usd = fx_service.convert_point_in_time(
        amount=close_price,
        from_currency=raw_currency,
        to_currency="USD",
        as_of_date=as_of_date,
        provider_rates=point_in_time_fx_rates,
    ) or 0.0

    display_price = fx_service.convert_point_in_time(
        amount=close_price,
        from_currency=raw_currency,
        to_currency=target_display_currency,
        as_of_date=as_of_date,
        provider_rates=point_in_time_fx_rates,
    ) or 0.0

    # Calculate exact applied FX multiplier for audit trail
    fx_rate_applied = (display_price / close_price) if close_price else 1.0

    beta_raw = _extract_first_match(raw_payload, ["beta", "Technicals.Beta", "TR.Beta", "Beta"])
    beta = _safe_float(beta_raw, "beta", ticker, default=None)
    if beta is None:
        missing_fields.append("beta")

    avg_volume = _safe_float(
        _extract_first_match(raw_payload, ["avg_daily_volume", "volume", "Technicals.SharesVolume", "TR.VolumeAvg30D"]),
        "avg_daily_volume", ticker
    )

    # 4. Financial Statements & Fundamentals
    ebitda = _safe_float(
        _extract_first_match(raw_payload, [
            "ebitda", "Highlights.EBITDA", "Financials.Income_Statement.ebitda", "TR.EBITDA"
        ]),
        "ebitda", ticker
    )
    if ebitda is None:
        missing_fields.append("ebitda")

    net_debt = _safe_float(
        _extract_first_match(raw_payload, [
            "net_debt", "Highlights.NetDebt", "Financials.Balance_Sheet.netDebt", "TR.NetDebt"
        ]),
        "net_debt", ticker
    )
    if net_debt is None:
        missing_fields.append("net_debt")

    dividend_yield = _safe_float(
        _extract_first_match(raw_payload, [
            "yieldPct", "dividend_yield_pct", "Highlights.DividendYield", "TR.DividendYield"
        ]),
        "dividend_yield", ticker, default=0.0
    )

    revenue = _safe_float(
        _extract_first_match(raw_payload, ["revenue", "Highlights.RevenueTTM", "TR.Revenue"]),
        "revenue", ticker
    )

    # 5. Analyst Estimates & Forward Multiples
    forward_pe = _safe_float(
        _extract_first_match(raw_payload, [
            "fwdPe", "forward_pe", "Valuation.ForwardPE", "Highlights.ForwardPE", "TR.PEForward12M"
        ]),
        "forward_pe", ticker
    )
    if forward_pe is None:
        missing_fields.append("forward_pe")

    peg_ratio = _safe_float(
        _extract_first_match(raw_payload, [
            "peg", "peg_ratio", "Highlights.PEGRatio", "Valuation.PEGRatio", "TR.PEGRatio"
        ]),
        "peg_ratio", ticker
    )
    if peg_ratio is None:
        missing_fields.append("peg_ratio")

    eps_growth_fwd = _safe_float(
        _extract_first_match(raw_payload, [
            "epsGrowthPct", "eps_growth_fwd_pct", "Highlights.EPSSurprisePercent", "TR.EPSGrowth1Yr"
        ]),
        "eps_growth_fwd", ticker
    )

    # 6. Determine Data Confidence Level
    critical_missing = {"market_cap", "close_price", "ebitda", "forward_pe"}
    missing_critical_count = len(critical_missing.intersection(missing_fields))

    if missing_critical_count >= 2 or len(missing_fields) >= 4:
        data_confidence: DataConfidenceLevel = "Low"
    elif missing_critical_count == 1 or len(missing_fields) >= 2:
        data_confidence = "Medium"
    else:
        data_confidence = "High"

    if missing_fields:
        logger.normalize_debug(
            ticker,
            f"Normalized with confidence '{data_confidence}'. Missing fields: {missing_fields}"
        )

    # 7. Assemble Canonical Models
    canonical_id = generate_canonical_id(country, exchange, ticker, isin, figi)
    listing_id = generate_listing_id(exchange, ticker)

    company_model = NormalizedCompany(
        canonical_id=canonical_id,
        name=name,
        ticker=ticker,
        country=country,
        exchange=exchange,
        sector=sector,
        market_cap=market_cap_usd,
        market_cap_display=market_cap_display,
        display_currency=target_display_currency.upper(),
        currency=raw_currency,
        isin=isin,
        figi=figi,
        as_of_date=as_of_date,
    )

    listing_model = NormalizedListing(
        listing_id=listing_id,
        canonical_company_id=canonical_id,
        ticker=ticker,
        exchange_id=exchange.lower(),
        country_id=country.lower(),
        currency=raw_currency,
        is_primary=True,
    )

    price_model = NormalizedPrice(
        ticker=ticker,
        close_price=close_price,
        currency=raw_currency,
        price_usd=price_usd,
        display_currency=target_display_currency.upper(),
        display_price=display_price,
        fx_rate_to_display=fx_rate_applied,
        beta=beta,
        avg_daily_volume=avg_volume,
        as_of_date=as_of_date,
    )

    financials_model = NormalizedFinancials(
        ticker=ticker,
        currency=raw_currency,
        revenue=revenue,
        ebitda=ebitda,
        net_debt=net_debt,
        dividend_yield_pct=dividend_yield,
        is_financial_institution=(sector.lower() in {"financials", "banking"}),
    )

    estimates_model = NormalizedEstimates(
        ticker=ticker,
        currency=raw_currency,
        forward_pe=forward_pe,
        peg_ratio=peg_ratio,
        eps_growth_fwd_pct=eps_growth_fwd,
    )

    confidence_details = ConfidenceDetails(
        estimate_note=_extract_first_match(raw_payload, ["estimateNote", "confidenceDetails.estimateNote"]),
        freshness_note=f"Pricing & FX as of {as_of_date}",
        missing_fields=missing_fields,
    )

    return NormalizedSecurityData(
        canonical_id=canonical_id,
        company=company_model,
        listing=listing_model,
        price=price_model,
        financials=financials_model,
        estimates=estimates_model,
        data_confidence=data_confidence,
        confidence_details=confidence_details,
    )
