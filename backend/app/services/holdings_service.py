"""Phase 15: Holdings Ingestion & Portfolio Management Service.

Handles multi-format file parsing (CSV, XLSX, XLS), Security Master reconciliation,
and persistent bulk storage of fund holdings in PostgreSQL.
"""

import csv
import io
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import openpyxl

from app.models.holding import HoldingRecord, HoldingWithDetails
from app.repositories.company_repository import company_repository
from app.repositories.holdings_repository import holdings_repository
from app.schemas.holding import (
    CreateHoldingRequest,
    HoldingItemSchema,
    HoldingsImportResponse,
    HoldingsSummary,
    UnmatchedHoldingRow,
)
from app.security_master.company_service import company_service
from app.security_master.identity import normalize_ticker

logger = logging.getLogger("app.services.holdings")


class HoldingsService:
    """Service orchestrating portfolio import, identifier matching, and storage."""

    def __init__(self, repository=holdings_repository):
        self.repo = repository

    def parse_file_rows(self, file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
        """Parse raw file bytes (CSV or XLSX) into standardized dictionaries."""
        lower_name = filename.lower()

        if lower_name.endswith(".xlsx") or lower_name.endswith(".xls"):
            return self._parse_excel_bytes(file_bytes)
        else:
            return self._parse_csv_bytes(file_bytes)

    def _parse_csv_bytes(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        """Parse CSV bytes trying UTF-8 first, then Latin-1."""
        text = None
        for enc in ["utf-8-sig", "utf-8", "latin-1"]:
            try:
                text = file_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if not text:
            raise ValueError("Unable to decode CSV file with supported encodings (UTF-8, Latin-1).")

        reader = csv.DictReader(io.StringIO(text))
        rows: List[Dict[str, Any]] = []
        for r in reader:
            cleaned = {str(k).strip(): str(v).strip() for k, v in r.items() if k is not None}
            if any(cleaned.values()):
                rows.append(cleaned)
        return rows

    def _parse_excel_bytes(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        """Parse Excel spreadsheet bytes using openpyxl."""
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        sheet = wb.active
        if not sheet:
            return []

        rows_iter = sheet.iter_rows(values_only=True)
        try:
            header_row = next(rows_iter)
        except StopIteration:
            return []

        headers = [str(h).strip() if h is not None else f"col_{i}" for i, h in enumerate(header_row)]

        result: List[Dict[str, Any]] = []
        for row_values in rows_iter:
            if not row_values or not any(row_values):
                continue
            row_dict = {}
            for i, val in enumerate(row_values):
                if i < len(headers):
                    row_dict[headers[i]] = str(val).strip() if val is not None else ""
            if any(row_dict.values()):
                result.append(row_dict)
        return result

    def _detect_column(self, headers: List[str], candidates: List[str]) -> Optional[str]:
        """Find best matching column name case-insensitively."""
        norm_map = {re.sub(r"[^a-zA-Z0-9]", "", h).lower(): h for h in headers}
        for cand in candidates:
            norm_cand = re.sub(r"[^a-zA-Z0-9]", "", cand).lower()
            if norm_cand in norm_map:
                return norm_map[norm_cand]
        return None

    def _safe_float(self, val: Any, default: float = 0.0) -> float:
        if val is None:
            return default
        clean_str = str(val).replace("$", "").replace("₹", "").replace("%", "").replace(",", "").strip()
        try:
            return float(clean_str)
        except (ValueError, TypeError):
            return default

    def import_holdings_file(
        self,
        file_bytes: bytes,
        filename: str,
        portfolio_name: str = "Core Equity Fund",
    ) -> HoldingsImportResponse:
        """Parse, reconcile, and persist portfolio holdings from uploaded file."""
        raw_rows = self.parse_file_rows(file_bytes, filename)
        if not raw_rows:
            return HoldingsImportResponse(
                portfolio_name=portfolio_name,
                total_rows=0,
                matched_count=0,
                unmatched_count=0,
                message="File contained no data rows.",
            )

        headers = list(raw_rows[0].keys())
        ticker_col = self._detect_column(headers, ["ticker", "symbol", "security", "securityid", "code", "isin"])
        shares_col = self._detect_column(headers, ["shares", "quantity", "qty", "units", "position"])
        cost_col = self._detect_column(headers, ["costbasis", "cost", "price", "avgcost", "purchaseprice"])
        weight_col = self._detect_column(headers, ["weight", "weightpct", "weightpercentage", "allocation", "pct"])

        if not ticker_col:
            return HoldingsImportResponse(
                portfolio_name=portfolio_name,
                total_rows=len(raw_rows),
                matched_count=0,
                unmatched_count=len(raw_rows),
                unmatched=[
                    UnmatchedHoldingRow(
                        row_index=i + 1,
                        raw_identifier="",
                        reason="Missing 'Ticker' or 'Symbol' column in file header.",
                        raw_data=r,
                    )
                    for i, r in enumerate(raw_rows)
                ],
                message="Could not locate a Ticker or Symbol column in spreadsheet headers.",
            )

        matched_records: List[HoldingRecord] = []
        unmatched_rows: List[UnmatchedHoldingRow] = []

        port_slug = re.sub(r"[^a-zA-Z0-9]", "-", portfolio_name.lower()).strip("-")

        for idx, row in enumerate(raw_rows):
            raw_id = row.get(ticker_col, "").strip()
            if not raw_id:
                unmatched_rows.append(
                    UnmatchedHoldingRow(
                        row_index=idx + 1,
                        raw_identifier="",
                        reason="Empty ticker value in row",
                        raw_data=row,
                    )
                )
                continue

            # Resolve against Security Master
            company = self._reconcile_identifier(raw_id)
            if not company:
                unmatched_rows.append(
                    UnmatchedHoldingRow(
                        row_index=idx + 1,
                        raw_identifier=raw_id,
                        reason=f"Security '{raw_id}' could not be matched against Security Master",
                        raw_data=row,
                    )
                )
                continue

            shares = self._safe_float(row.get(shares_col)) if shares_col else 0.0
            cost_basis = self._safe_float(row.get(cost_col)) if cost_col else 0.0
            weight = self._safe_float(row.get(weight_col)) if weight_col else 0.0

            holding_id = f"hld-{company.canonical_id}-{port_slug}"
            matched_records.append(
                HoldingRecord(
                    holding_id=holding_id,
                    canonical_company_id=company.canonical_id,
                    portfolio_name=portfolio_name,
                    shares=shares,
                    cost_basis=cost_basis,
                    weight_pct=weight,
                )
            )

        # Bulk save matched holdings into PostgreSQL
        if matched_records:
            self.repo.save_holdings_batch(matched_records)

        # Retrieve saved holdings with enriched company details
        detailed = self.repo.get_holdings_with_details(portfolio_name)
        schema_items = [self._to_schema_item(d) for d in detailed]

        msg = (
            f"Successfully imported {len(matched_records)} of {len(raw_rows)} holdings "
            f"into '{portfolio_name}'."
        )
        if unmatched_rows:
            msg += f" {len(unmatched_rows)} rows could not be matched."

        return HoldingsImportResponse(
            portfolio_name=portfolio_name,
            total_rows=len(raw_rows),
            matched_count=len(matched_records),
            unmatched_count=len(unmatched_rows),
            holdings=schema_items,
            unmatched=unmatched_rows,
            message=msg,
        )

    def _reconcile_identifier(self, identifier: str):
        """Match incoming ticker/ISIN against database companies or known mock universe."""
        clean = normalize_ticker(identifier)

        # 1. Search company repository by ticker
        comp = company_repository.get_company_by_ticker(clean)
        if comp:
            return comp

        # 2. Check if identifier is an ISIN
        if len(clean) == 12 and clean[:2].isalpha():
            comp = company_repository.get_company_by_isin(clean)
            if comp:
                return comp

        # 3. Check listings table
        listings = company_repository.list_listings(limit=10000)
        for l in listings:
            if l.ticker.upper() == clean:
                return company_repository.get_company_by_id(l.canonical_company_id)

        # 4. If database companies table was wiped, check mock data fixtures and auto-register company!
        from app.adapters.mock_adapter import MockAdapter
        adapter = MockAdapter()
        for raw in adapter._securities:
            raw_t = (raw.get("ticker") or raw.get("Code", "")).upper()
            raw_isin = (raw.get("isin") or "").upper()
            if clean in {raw_t, raw_isin}:
                from app.ingestion.data_adapter import normalize_vendor_payload
                normalized_sec = normalize_vendor_payload(raw)
                registered = company_service.upsert_company_from_normalized(normalized_sec.company)
                return registered

        return None

    def add_manual_holding(self, request: CreateHoldingRequest) -> HoldingItemSchema:
        """Manually add or update a single holding in the portfolio."""
        company = self._reconcile_identifier(request.ticker)
        if not company:
            raise ValueError(f"Ticker '{request.ticker}' could not be resolved in the Security Master.")

        port_slug = re.sub(r"[^a-zA-Z0-9]", "-", request.portfolio_name.lower()).strip("-")
        holding_id = f"hld-{company.canonical_id}-{port_slug}"

        record = HoldingRecord(
            holding_id=holding_id,
            canonical_company_id=company.canonical_id,
            portfolio_name=request.portfolio_name,
            shares=request.shares or 0.0,
            cost_basis=request.cost_basis or 0.0,
            weight_pct=request.weight_pct or 0.0,
        )
        self.repo.save_holding(record)

        detailed = self.repo.get_holdings_with_details(request.portfolio_name)
        match = next((d for d in detailed if d.holding_id == holding_id), None)
        if match:
            return self._to_schema_item(match)

        return HoldingItemSchema(
            holding_id=holding_id,
            canonical_company_id=company.canonical_id,
            ticker=company.primary_ticker,
            name=company.name,
            country=company.country,
            exchange=company.primary_exchange,
            sector=company.sector,
            shares=record.shares,
            cost_basis=record.cost_basis,
            weight_pct=record.weight_pct,
            portfolio_name=record.portfolio_name,
            created_at=record.created_at,
        )

    def list_holdings(self, portfolio_name: Optional[str] = None) -> List[HoldingItemSchema]:
        """List active holdings enriched with Security Master details."""
        detailed = self.repo.get_holdings_with_details(portfolio_name)
        return [self._to_schema_item(d) for d in detailed]

    def get_summary(self, portfolio_name: str = "Core Equity Fund") -> HoldingsSummary:
        """Calculate high-level diversification and allocation summary of holdings."""
        detailed = self.repo.get_holdings_with_details(portfolio_name)
        schema_items = [self._to_schema_item(d) for d in detailed]
        total_weight = sum(item.weight_pct for item in schema_items)
        sectors = sorted(list({item.sector for item in schema_items if item.sector}))
        countries = sorted(list({item.country for item in schema_items if item.country}))

        return HoldingsSummary(
            portfolio_name=portfolio_name,
            total_positions=len(schema_items),
            total_weight_pct=round(total_weight, 2),
            sectors_represented=sectors,
            countries_represented=countries,
            holdings=schema_items,
        )

    def delete_holding(self, holding_id: str) -> bool:
        """Delete single holding."""
        return self.repo.delete_holding(holding_id)

    def clear_holdings(self, portfolio_name: Optional[str] = None) -> int:
        """Clear all holdings for a portfolio."""
        return self.repo.clear_holdings(portfolio_name)

    def _to_schema_item(self, d: HoldingWithDetails) -> HoldingItemSchema:
        return HoldingItemSchema(
            holding_id=d.holding_id,
            canonical_company_id=d.canonical_company_id,
            ticker=d.ticker,
            name=d.company_name,
            country=d.country,
            exchange=d.exchange,
            sector=d.sector,
            shares=d.shares,
            cost_basis=d.cost_basis,
            weight_pct=d.weight_pct,
            portfolio_name=d.portfolio_name,
            created_at=d.created_at,
        )


holdings_service = HoldingsService()
