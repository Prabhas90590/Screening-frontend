"""Canonical financial statements and fundamentals schema.

Represents standardized balance sheet, income statement, and cash flow items.
"""

from typing import Optional
from pydantic import BaseModel, Field


class NormalizedFinancials(BaseModel):
    """Normalized financial statement fundamentals."""
    ticker: str = Field(..., description="Ticker symbol")
    currency: str = Field(default="USD", description="Currency of reported figures")
    reporting_period: Optional[str] = Field(None, description="e.g. '2025-Q4' or 'FY2025'")
    revenue: Optional[float] = Field(None, description="Total revenue (trailing 12 months)")
    ebitda: Optional[float] = Field(None, description="Earnings Before Interest, Taxes, Depreciation, Amortization")
    operating_income: Optional[float] = Field(None, description="Operating income (EBIT)")
    net_income: Optional[float] = Field(None, description="Net income attributable to common shareholders")
    eps: Optional[float] = Field(None, description="Diluted earnings per share (trailing 12M)")
    total_debt: Optional[float] = Field(None, description="Total short-term and long-term debt")
    cash_and_equivalents: Optional[float] = Field(None, description="Cash, cash equivalents, and short-term investments")
    net_debt: Optional[float] = Field(None, description="Total debt minus cash and equivalents")
    free_cash_flow: Optional[float] = Field(None, description="Operating cash flow minus CapEx")
    enterprise_value: Optional[float] = Field(None, description="Market cap + Net Debt + Minority Interest - Preferred")
    dividend_per_share: Optional[float] = Field(None, description="Annualized dividend per share")
    dividend_yield_pct: Optional[float] = Field(None, description="Dividend yield as a percentage, e.g. 8.9")
    shares_outstanding: Optional[float] = Field(None, description="Weighted average shares diluted")
    profit_margin_pct: Optional[float] = Field(None, description="Net profit margin percentage")
    is_financial_institution: bool = Field(default=False, description="True for Banks/Insurance where debt/EBITDA is N/A")

