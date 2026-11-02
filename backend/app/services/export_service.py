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

            is_top20_slot = (rank is not None and 1 <= rank <= 20)
            is_nm = (
                near_miss in ("rank_near_miss", "rule_near_miss")
                or (rank is not None and rank > 20 and stage_status == "passed")
            )

            # Tab 1: The Top 20 Candidates only (ranks 1..20)
            if is_top20_slot:
                top20_results.append(r)
            # Tab 2: ALL Near Misses (displaced candidates + rank cutoffs + borderline misses)
            if is_nm:
                near_miss_results.append(r)
            master_results.append(r)

        # -----------------------------------------------------------------
        # Sheet 1: Top 20 (Dedicated Tab 1 - Capped at 20 rows)
        # -----------------------------------------------------------------
        core_picks_count = len([r for r in top20_results if getattr(r, "near_miss_status", "none") == "none"])
        displaced_count = len([r for r in top20_results if getattr(r, "near_miss_status", "none") != "none"])
        ws_top20 = wb.create_sheet(title="Top 20")
        cls._populate_sheet(
            ws=ws_top20,
            title=f"Top 20 Portfolio Selection — {profile_name}",
            subtitle=f"Run ID: {run_id} | Core Portfolio: {core_picks_count} Selected Winners | {displaced_count} Displaced Near Misses",
            results=top20_results,
            category_label="Top 20 Winner",
            dec_map=dec_map,
            theme_color="1E3A8A",  # Navy
        )

        # -----------------------------------------------------------------
        # Sheet 2: Near Misses (Dedicated Tab 2 - All Near Misses)
        # -----------------------------------------------------------------
        ws_nm = wb.create_sheet(title="Near Misses")
        cls._populate_sheet(
            ws=ws_nm,
            title=f"Near Miss Contenders — {profile_name}",
            subtitle=f"Run ID: {run_id} | Total Near Misses: {len(near_miss_results)} (Displaced & Single-Gate Misses)",
            results=near_miss_results,
            category_label="Near Miss",
            dec_map=dec_map,
            theme_color="B45309",  # Amber / Dark Bronze
        )

        # -----------------------------------------------------------------
        # Sheet 3: Master Universe (Dedicated Tab 3 - All Screened Securities)
        # -----------------------------------------------------------------
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
        """Format and write a single-section sheet with auto-fit columns."""
        cls._populate_section(
            ws=ws,
            start_row=1,
            title=title,
            subtitle=subtitle,
            results=results,
            category_label=category_label,
            dec_map=dec_map,
            theme_color=theme_color,
        )
        cls._autofit_columns(ws)

    @classmethod
    def _populate_section(
        cls,
        ws,
        start_row: int,
        title: str,
        subtitle: str,
        results: List[Any],
        category_label: str,
        dec_map: Dict[str, Dict[str, str]],
        theme_color: str = "1E3A8A",
    ) -> int:
        """Format and write a complete section (banner, subtitle, table headers, and rows). Returns next free row index."""
        if not results:
            return start_row

        r_title = start_row
        r_subtitle = start_row + 1
        r_spacer = start_row + 2
        r_header = start_row + 3
        r_data_start = start_row + 4

        # 1. Section Title Banner
        ws.merge_cells(f"A{r_title}:U{r_title}")
        cell_t = ws[f"A{r_title}"]
        cell_t.value = title
        cell_t.font = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
        cell_t.fill = PatternFill(start_color=theme_color, end_color=theme_color, fill_type="solid")
        cell_t.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ws.row_dimensions[r_title].height = 26

        # Subtitle
        ws.merge_cells(f"A{r_subtitle}:U{r_subtitle}")
        cell_s = ws[f"A{r_subtitle}"]
        cell_s.value = subtitle
        cell_s.font = Font(name="Calibri", size=10, italic=True, color="475569")
        cell_s.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ws.row_dimensions[r_subtitle].height = 18

        # Empty row
        ws.row_dimensions[r_spacer].height = 6

        # 2. Table Headers
        header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
        thin_border = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1"),
        )

        ws.row_dimensions[r_header].height = 24
        for col_idx, h_text in enumerate(cls.HEADERS, 1):
            c = ws.cell(row=r_header, column=col_idx, value=h_text)
            c.font = header_font
            c.fill = header_fill
            c.alignment = Alignment(horizontal="center" if col_idx in (1, 2, 8) else "left", vertical="center")
            c.border = thin_border

        # 3. Data Rows
        row_font = Font(name="Calibri", size=10, color="0F172A")
        zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        amber_row_fill = PatternFill(start_color="FFFBEB", end_color="FFFBEB", fill_type="solid")

        current_row = r_data_start
        for idx, sec in enumerate(results):
            row_idx = current_row
            is_even = (idx % 2 == 0)
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

            # Resolve decision and status details
            sec_dec = dec_map.get(c_id, {})
            user_decision = getattr(sec, "decision", None) or sec_dec.get("decision", "")
            user_reason = getattr(sec, "decision_reason", None) or sec_dec.get("decision_reason", "")
            user_note = getattr(sec, "decision_note", None) or sec_dec.get("decision_note", "")

            sec_nm = getattr(sec, "near_miss_status", "none")
            sec_stage = getattr(sec, "stage_status", "passed")
            metric_statuses = getattr(sec, "metric_statuses", {}) or {}
            div_reason = metric_statuses.get("diversification") if isinstance(metric_statuses, dict) else None

            is_displaced = (sec_nm == "rank_near_miss")
            is_rule_nm = (sec_nm == "rule_near_miss")

            if is_displaced:
                row_category = "Near Miss (Displaced)"
                row_decision = user_decision or "NEAR MISS"
                row_reason = user_reason or (f"Displaced: {div_reason}" if div_reason else f"Rank cut-off outside selection (#{rank})")
                row_note = user_note or (f"Diversification: {div_reason}" if div_reason else f"Rank #{rank} cut-off")
            elif is_rule_nm:
                row_category = "Near Miss (Borderline)"
                row_decision = user_decision or "NEAR MISS"
                row_reason = user_reason or "Single-gate borderline miss (within 5% threshold)"
                row_note = user_note or "Borderline Rule Miss"
            elif category_label == "Top 20 Winner" or (rank and isinstance(rank, int) and rank <= 20 and sec_nm == "none"):
                row_category = "Top 20 Winner"
                row_decision = user_decision or "KEEP"
                row_reason = user_reason or "Selected Core Portfolio Pick"
                row_note = user_note or f"Top Pick #{rank}"
            else:
                row_category = category_label
                row_decision = user_decision or ""
                row_reason = user_reason or ""
                row_note = user_note or ""

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
                row_category,
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
                row_decision.upper() if row_decision else "",
                row_reason if row_reason else "",
                row_note if row_note else "",
            ]

            for col_idx, val in enumerate(row_values, 1):
                c = ws.cell(row=row_idx, column=col_idx, value=val)
                c.font = row_font
                c.border = thin_border
                
                # Apply row background: amber tint for near misses, else zebra
                if is_displaced or is_rule_nm or theme_color == "B45309":
                    c.fill = amber_row_fill
                elif is_even:
                    c.fill = zebra_fill

                # Alignments & conditional formatting
                if col_idx == 1:  # Category
                    c.alignment = Alignment(horizontal="left", vertical="center")
                    if "Near Miss" in str(val):
                        c.font = Font(name="Calibri", size=10, bold=True, color="B45309")
                    elif "Top 20 Winner" in str(val):
                        c.font = Font(name="Calibri", size=10, bold=True, color="1E3A8A")
                elif col_idx in (2, 8):  # Rank, Score
                    c.alignment = Alignment(horizontal="center", vertical="center")
                    if col_idx == 8:
                        c.font = Font(name="Calibri", size=10, bold=True, color="0F172A")
                elif col_idx in (9, 10, 11, 12, 13, 14, 15, 16, 17):
                    c.alignment = Alignment(horizontal="right", vertical="center")
                elif col_idx in (19,):  # Decision
                    c.alignment = Alignment(horizontal="center", vertical="center")
                    if "NEAR MISS" in str(val):
                        c.font = Font(name="Calibri", size=10, bold=True, color="92400E")
                        c.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
                    elif val == "KEEP":
                        c.font = Font(name="Calibri", size=10, bold=True, color="065F46")
                        c.fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")
                    elif val == "DROP":
                        c.font = Font(name="Calibri", size=10, bold=True, color="991B1B")
                        c.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
                else:
                    c.alignment = Alignment(horizontal="left", vertical="center")

            current_row += 1

        return current_row

    @classmethod
    def _autofit_columns(cls, ws):
        """Auto-fit column widths based on cell content (excluding wide title banners)."""
        for col_idx in range(1, len(cls.HEADERS) + 1):
            col_letter = get_column_letter(col_idx)
            max_len = 0
            for r in range(1, ws.max_row + 1):
                val = ws.cell(row=r, column=col_idx).value
                if val is not None:
                    s_val = str(val)
                    if not (s_val.startswith("🏆") or s_val.startswith("⚡") or s_val.startswith("Top") or s_val.startswith("Near Miss") or s_val.startswith("Complete") or s_val.startswith("Run ID:")):
                        max_len = max(max_len, len(s_val))
            ws.column_dimensions[col_letter].width = max(max_len + 3, 11)


# Global singleton instance
export_service = ExportService()
