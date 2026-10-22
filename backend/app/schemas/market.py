"""Market and exchange schemas for equity screening.

Defines canonical representations of countries and stock exchanges,
and request/response validation schemas for user market selections.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ExchangeBase(BaseModel):
    id: str = Field(..., description="Unique exchange identifier, e.g. 'nasdaq', 'nyse'")
    name: str = Field(..., description="Full display name, e.g. 'Nasdaq', 'NYSE'")
    country_id: str = Field(..., description="Parent country identifier, e.g. 'us'")
    mic_code: Optional[str] = Field(None, description="ISO 10383 Market Identifier Code, e.g. 'XNAS'")
    currency: Optional[str] = Field(None, description="Trading currency ISO code, e.g. 'USD'")


class ExchangeItem(ExchangeBase):
    selected: bool = Field(default=False, description="Whether selected by the user")


class CountryBase(BaseModel):
    id: str = Field(..., description="Unique country identifier, e.g. 'us', 'jp'")
    name: str = Field(..., description="Full display country name, e.g. 'United States'")
    iso_code: str = Field(..., description="ISO 3166-1 alpha-2 code, e.g. 'US', 'JP'")
    default_currency: str = Field(..., description="Default currency code, e.g. 'USD', 'JPY'")


class CountryItem(CountryBase):
    selected: bool = Field(default=False, description="Whether selected by the user")


class MarketSelectionRequest(BaseModel):
    """Payload sent by the frontend when screening a market universe."""
    countries: List[str] = Field(..., description="List of selected country IDs, e.g. ['us', 'ca']")
    exchanges: List[str] = Field(..., description="List of selected exchange IDs, e.g. ['nasdaq', 'nyse']")


class MarketUniverseResponse(BaseModel):
    """Returns available and selected countries and exchanges."""
    countries: List[CountryItem]
    exchanges: List[ExchangeItem]


# Canonical reference catalog matching frontend defaults
SUPPORTED_COUNTRIES: List[CountryBase] = [
    CountryBase(id="us", name="United States", iso_code="US", default_currency="USD"),
    CountryBase(id="in", name="India", iso_code="IN", default_currency="INR"),
    CountryBase(id="uk", name="United Kingdom", iso_code="GB", default_currency="GBP"),
    CountryBase(id="jp", name="Japan", iso_code="JP", default_currency="JPY"),
    CountryBase(id="ca", name="Canada", iso_code="CA", default_currency="CAD"),
    CountryBase(id="de", name="Germany", iso_code="DE", default_currency="EUR"),
    CountryBase(id="fr", name="France", iso_code="FR", default_currency="EUR"),
    CountryBase(id="ch", name="Switzerland", iso_code="CH", default_currency="CHF"),
    CountryBase(id="hk", name="Hong Kong", iso_code="HK", default_currency="HKD"),
    CountryBase(id="sg", name="Singapore", iso_code="SG", default_currency="SGD"),
    CountryBase(id="au", name="Australia", iso_code="AU", default_currency="AUD"),
    CountryBase(id="kr", name="South Korea", iso_code="KR", default_currency="KRW"),
    CountryBase(id="nl", name="Netherlands", iso_code="NL", default_currency="EUR"),
    CountryBase(id="no", name="Norway", iso_code="NO", default_currency="NOK"),
    CountryBase(id="se", name="Sweden", iso_code="SE", default_currency="SEK"),
    CountryBase(id="cn", name="China", iso_code="CN", default_currency="CNY"),
    CountryBase(id="tw", name="Taiwan", iso_code="TW", default_currency="TWD"),
    CountryBase(id="br", name="Brazil", iso_code="BR", default_currency="BRL"),
    CountryBase(id="it", name="Italy", iso_code="IT", default_currency="EUR"),
    CountryBase(id="es", name="Spain", iso_code="ES", default_currency="EUR"),
    CountryBase(id="sa", name="Saudi Arabia", iso_code="SA", default_currency="SAR"),
    CountryBase(id="ae", name="United Arab Emirates", iso_code="AE", default_currency="AED"),
    CountryBase(id="za", name="South Africa", iso_code="ZA", default_currency="ZAR"),
    CountryBase(id="id", name="Indonesia", iso_code="ID", default_currency="IDR"),
    CountryBase(id="mx", name="Mexico", iso_code="MX", default_currency="MXN"),
    CountryBase(id="nz", name="New Zealand", iso_code="NZ", default_currency="NZD"),
]

SUPPORTED_EXCHANGES: List[ExchangeBase] = [
    # United States
    ExchangeBase(id="nyse", name="NYSE", country_id="us", mic_code="XNYS", currency="USD"),
    ExchangeBase(id="nasdaq", name="Nasdaq", country_id="us", mic_code="XNAS", currency="USD"),
    ExchangeBase(id="cboe", name="Cboe BZX", country_id="us", mic_code="BATS", currency="USD"),

    # India
    ExchangeBase(id="nse", name="NSE (National Stock Exchange)", country_id="in", mic_code="XNSE", currency="INR"),
    ExchangeBase(id="bse", name="BSE (Bombay Stock Exchange)", country_id="in", mic_code="XBOM", currency="INR"),

    # United Kingdom
    ExchangeBase(id="lse", name="London Stock Exchange", country_id="uk", mic_code="XLON", currency="GBP"),

    # Japan
    ExchangeBase(id="tse", name="Tokyo Stock Exchange", country_id="jp", mic_code="XTKS", currency="JPY"),

    # Canada
    ExchangeBase(id="tsx", name="Toronto Stock Exchange", country_id="ca", mic_code="XTSE", currency="CAD"),
    ExchangeBase(id="tsxv", name="TSX Venture Exchange", country_id="ca", mic_code="XTSX", currency="CAD"),

    # Germany
    ExchangeBase(id="xetra", name="Xetra", country_id="de", mic_code="XETR", currency="EUR"),
    ExchangeBase(id="fra", name="Frankfurt Stock Exchange", country_id="de", mic_code="XFRA", currency="EUR"),

    # France
    ExchangeBase(id="euronext-paris", name="Euronext Paris", country_id="fr", mic_code="XPAR", currency="EUR"),

    # Switzerland
    ExchangeBase(id="six", name="SIX Swiss Exchange", country_id="ch", mic_code="XSWX", currency="CHF"),

    # Hong Kong
    ExchangeBase(id="hkex", name="Hong Kong Stock Exchange", country_id="hk", mic_code="XHKG", currency="HKD"),

    # Singapore
    ExchangeBase(id="sgx", name="Singapore Exchange", country_id="sg", mic_code="XSES", currency="SGD"),

    # Australia
    ExchangeBase(id="asx", name="ASX", country_id="au", mic_code="XASX", currency="AUD"),

    # South Korea
    ExchangeBase(id="krx", name="Korea Exchange (KRX)", country_id="kr", mic_code="XKRX", currency="KRW"),

    # Netherlands
    ExchangeBase(id="euronext-amsterdam", name="Euronext Amsterdam", country_id="nl", mic_code="XAMS", currency="EUR"),

    # Norway
    ExchangeBase(id="ose", name="Oslo Børs", country_id="no", mic_code="XOSL", currency="NOK"),

    # Sweden
    ExchangeBase(id="omx-stockholm", name="Nasdaq Stockholm", country_id="se", mic_code="XSTO", currency="SEK"),

    # China
    ExchangeBase(id="sse", name="Shanghai Stock Exchange", country_id="cn", mic_code="XSHG", currency="CNY"),
    ExchangeBase(id="szse", name="Shenzhen Stock Exchange", country_id="cn", mic_code="XSHE", currency="CNY"),

    # Taiwan
    ExchangeBase(id="twse", name="Taiwan Stock Exchange", country_id="tw", mic_code="XTAI", currency="TWD"),

    # Brazil
    ExchangeBase(id="b3", name="B3", country_id="br", mic_code="BVMF", currency="BRL"),

    # Italy
    ExchangeBase(id="milan", name="Borsa Italiana", country_id="it", mic_code="XMIL", currency="EUR"),

    # Spain
    ExchangeBase(id="bme-madrid", name="BME Spanish Exchanges", country_id="es", mic_code="BMEX", currency="EUR"),

    # Saudi Arabia
    ExchangeBase(id="tadawul", name="Tadawul (Saudi Exchange)", country_id="sa", mic_code="XSAU", currency="SAR"),

    # UAE
    ExchangeBase(id="dfm", name="Dubai Financial Market", country_id="ae", mic_code="XDFM", currency="AED"),
    ExchangeBase(id="adx", name="Abu Dhabi Securities Exchange", country_id="ae", mic_code="XADS", currency="AED"),

    # South Africa
    ExchangeBase(id="jse", name="Johannesburg Stock Exchange", country_id="za", mic_code="XJSE", currency="ZAR"),

    # Indonesia
    ExchangeBase(id="idx", name="Indonesia Stock Exchange", country_id="id", mic_code="XIDX", currency="IDR"),

    # Mexico
    ExchangeBase(id="bmv", name="Bolsa Mexicana de Valores", country_id="mx", mic_code="XMEX", currency="MXN"),

    # New Zealand
    ExchangeBase(id="nzx", name="New Zealand Exchange", country_id="nz", mic_code="XNZE", currency="NZD"),
]
