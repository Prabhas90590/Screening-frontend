"""Institutional Excel Export Service.

Generates multi-sheet Excel workbooks matching the frontend specifications:
  - Sheet 1: Top 20 Winners (Rank 1..20)
  - Sheet 2: Near Misses (Contenders within 5% or 1 gate)
  - Sheet 3: Master Universe (All evaluated candidates)

Includes side-by-side Decision and Decision Reason columns, header styling,
and automated column width fitting.
"""

from io import BytesIO
from typing import Any, Dict, List, Optional
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.core.logging import DiagnosticLogger
from app.models.screening_run import ScreeningResultRecord

logger = DiagnosticLogger("export")


class ExportService:
    """Generates formatted Excel workbooks from screening results."""

    HEADERS = [
        "Category",
        "Rank",
        "Security Name",
        "Ticker",
        "Exchange",
        "Sector",
        "Country",
        "Score",
        "Price",
        "Market Cap",
        "FWD P/E",
        "PEG",
        "EV/EBITDA",
        "Beta",
        "ND/EBITDA",
        "Yield %",
        "EPS Growth %",
        "Data Confidence",
        "Decision",
        "Decision Reason",
        "Status / Note",
    ]

    @classmethod
    def generate_screening_workbook(
        cls,
        run_id: str,
        profile_name: str,
        results: List[Any],
        decisions_map: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> bytes:
        """Create a complete multi-sheet Excel workbook in memory."""
        dec_map = decisions_map or {}
        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # Remove default blank sheet

        # Partition results
        top20_results = []
        near_miss_results = []
        master_results = []

        for r in results:
            rank = getattr(r, "rank", None)
            stage_status = getattr(r, "stage_status", "passed")
            near_miss = getattr(r, "near_miss_status", "none")

            is_top = (rank is not None and 1 <= rank <= 20)
            is_nm = (
                near_miss in ("rank_near_miss", "rule_near_miss")
                or (rank is not None and 21 <= rank <= 40)
            )

            if is_top:
                top20_results.append(r)
            elif is_nm:
                near_miss_results.append(r)
            master_results.append(r)

        # Build Sheet 1: Top 20 Winners
        ws_top20 = wb.create_sheet(title="Top 20 Winners")
        cls._populate_sheet(
            ws=ws_top20,
            title=f"Top 20 Portfolio Selection — {profile_name}",
            subtitle=f"Run ID: {run_id} | Total Top Picks: {len(top20_results)}",
            results=top20_results,
            category_label="Top 20 Winner",
            dec_map=dec_map,
            theme_color="1E3A8A",  # Navy
        )

        # Build Sheet 2: Near Misses
        ws_nm = wb.create_sheet(title="Near Misses")
        cls._populate_sheet(
            ws=ws_nm,
            title=f"Near Miss Contenders — {profile_name}",
            subtitle=f"Run ID: {run_id} | Displaced & Single-Gate Misses: {len(near_miss_results)}",
            results=near_miss_results,
            category_label="Near Miss",
            dec_map=dec_map,
            theme_color="B45309",  # Amber / Dark Bronze
        )

        # Build Sheet 3: Master Universe
        ws_master = wb.create_sheet(title="Master Universe")
        cls._populate_sheet(
            ws=ws_master,
            title=f"Complete Screened Universe — {profile_name}",
            subtitle=f"Run ID: {run_id} | Total Candidates: {len(master_results)}",
            results=master_results,
            category_label="Universe",
            dec_map=dec_map,
            theme_color="334155",  # Slate
        )

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()

    @classmethod
    def _populate_sheet(
        cls,
        ws,
        title: str,
        subtitle: str,
        results: List[Any],
        category_label: str,
        dec_map: Dict[str, Dict[str, str]],
        theme_color: str = "1E3A8A",
    ):
        """Format and write header, banner, and security data rows to a sheet."""
        # 1. Sheet Title Banner
        ws.merge_cells("A1:U1")
        cell_t = ws["A1"]
        cell_t.value = title
        cell_t.font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
        cell_t.fill = PatternFill(start_color=theme_color, end_color=theme_color, fill_type="solid")
        cell_t.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ws.row_dimensions[1].height = 28

        # Subtitle
        ws.merge_cells("A2:U2")
        cell_s = ws["A2"]
        cell_s.value = subtitle
        cell_s.font = Font(name="Calibri", size=10, italic=True, color="475569")
        cell_s.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ws.row_dimensions[2].height = 18

        # Empty row 3
        ws.row_dimensions[3].height = 8

        # 2. Table Headers (Row 4)
        header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
        thin_border = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1"),
        )

        ws.row_dimensions[4].height = 24
        for col_idx, h_text in enumerate(cls.HEADERS, 1):
            c = ws.cell(row=4, column=col_idx, value=h_text)
            c.font = header_font
            c.fill = header_fill
            c.alignment = Alignment(horizontal="center" if col_idx in (1, 2, 8) else "left", vertical="center")
            c.border = thin_border

        # 3. Data Rows (Row 5..N)
        row_font = Font(name="Calibri", size=10, color="0F172A")
        zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

        for row_idx, sec in enumerate(results, start=5):
            is_even = (row_idx % 2 == 0)
            ws.row_dimensions[row_idx].height = 20

            # Resolve ticker & company
            c_id = getattr(sec, "canonical_company_id", None) or getattr(sec, "id", "")
            ticker = getattr(sec, "ticker", "")
            name = getattr(sec, "company_name", None) or getattr(sec, "name", ticker)
            country = getattr(sec, "country", "")
            exchange = getattr(sec, "exchange", "")
            sector = getattr(sec, "sector", "")
            rank = getattr(sec, "rank", "")
            score = getattr(sec, "score", 0)

            price = getattr(sec, "display_price", None)
            mkt_cap = getattr(sec, "market_cap_display", None)
            fwd_pe = getattr(sec, "fwd_pe", None)
            peg = getattr(sec, "peg", None)
            ev_ebitda = getattr(sec, "ev_ebitda", None)
            beta = getattr(sec, "beta", None)
            nd_ebitda = getattr(sec, "nd_ebitda", "N/A")
            yield_pct = getattr(sec, "yield_pct", None)
            eps_growth = getattr(sec, "eps_growth_pct", None)
            data_conf = getattr(sec, "data_confidence", "High")

            # Resolve decision
            sec_dec = dec_map.get(c_id, {})
            decision = getattr(sec, "decision", None) or sec_dec.get("decision", "")
            decision_reason = getattr(sec, "decision_reason", None) or sec_dec.get("decision_reason", "")
            note = getattr(sec, "decision_note", None) or sec_dec.get("decision_note", "")

            # Format cell values
            price_str = f"${price:.2f}" if price is not None else "—"
            cap_str = f"${mkt_cap / 1e9:.2f}B" if (mkt_cap and mkt_cap > 0) else "—"
            pe_str = f"{fwd_pe:.1f}x" if fwd_pe is not None else "—"
            peg_str = f"{peg:.2f}x" if peg is not None else "—"
            ev_str = f"{ev_ebitda:.1f}x" if ev_ebitda is not None else "—"
            beta_str = f"{beta:.2f}" if beta is not None else "—"
            yield_str = f"{yield_pct:.2f}%" if yield_pct is not None else "—"
            growth_str = f"{eps_growth:.1f}%" if eps_growth is not None else "—"

            row_values = [
                category_label,
                rank if rank else "—",
                name,
                ticker,
                exchange,
                sector,
                country,
                score,
                price_str,
                cap_str,
                pe_str,
                peg_str,
                ev_str,
                beta_str,
                str(nd_ebitda),
                yield_str,
                growth_str,
                data_conf,
                decision.upper() if decision else "",
                decision_reason if decision_reason else "",
                note if note else "",
            ]

            for col_idx, val in enumerate(row_values, 1):
                c = ws.cell(row=row_idx, column=col_idx, value=val)
                c.font = row_font
                c.border = thin_border
                if is_even:
                    c.fill = zebra_fill

                # Alignments
                if col_idx in (2, 8):  # Rank, Score
                    c.alignment = Alignment(horizontal="center", vertical="center")
                    if col_idx == 8:
                        c.font = Font(name="Calibri", size=10, bold=True, color="0F172A")
                elif col_idx in (9, 10, 11, 12, 13, 14, 15, 16, 17):
                    c.alignment = Alignment(horizontal="right", vertical="center")
                elif col_idx in (19,):  # Decision
                    c.alignment = Alignment(horizontal="center", vertical="center")
                    if val == "KEEP":
                        c.font = Font(name="Calibri", size=10, bold=True, color="065F46")
                        c.fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")
                    elif val == "DROP":
                        c.font = Font(name="Calibri", size=10, bold=True, color="991B1B")
                        c.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
                else:
                    c.alignment = Alignment(horizontal="left", vertical="center")

        # 4. Auto-fit column widths
        for col_idx in range(1, len(cls.HEADERS) + 1):
            col_letter = get_column_letter(col_idx)
            max_len = max(
                len(str(ws.cell(row=r, column=col_idx).value or ""))
                for r in range(4, ws.max_row + 1)
            )
            ws.column_dimensions[col_letter].width = max(max_len + 3, 11)


# Global singleton instance
export_service = ExportService()
