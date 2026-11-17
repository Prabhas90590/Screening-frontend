"""Notification Service for Screening Runs.

Sends automated HTML emails via Outlook / SMTP (or archives to local disk if SMTP
credentials are not yet configured) for 3 distinct run outcomes:
  1. RUN SUCCESS: Professional summary table with top winners + attached .xlsx workbook.
  2. RUN BLOCKED: Diagnostic warning detailing which of the 4 data blockers tripped.
  3. RUN FAILED: Technical crash alert with error diagnosis.

Designed to be completely non-blocking: dispatches in the background without slowing
down the screening API response.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import html
from pathlib import Path
import smtplib
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging import DiagnosticLogger
from app.services.export_service import export_service

logger = DiagnosticLogger("notify")

SENT_EMAILS_DIR = Path(__file__).resolve().parent.parent.parent / "logs" / "sent_emails"
IST_TZ = timezone(timedelta(hours=5, minutes=30))


class NotificationService:
    """Manages email composition, Excel attachment, and background SMTP dispatch."""

    def __init__(self):
        try:
            SENT_EMAILS_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    # =========================================================================
    # PUBLIC NOTIFICATION ENTRYPOINTS
    # =========================================================================

    def notify_run_success(
        self,
        run_id: str,
        profile_name: str,
        duration_ms: float,
        funnel_counts: Any,
        results: List[Any],
        selected_countries: List[str],
        selected_exchanges: List[str],
        decisions_map: Optional[Dict[str, Dict[str, str]]] = None,
        target_email: Optional[str] = None,
    ):
        """Send a success email with HTML executive summary and attached Excel workbook."""
        if not settings.email_notifications_enabled:
            return

        asyncio.create_task(
            self._async_dispatch_success(
                run_id=run_id,
                profile_name=profile_name,
                duration_ms=duration_ms,
                funnel_counts=funnel_counts,
                results=results,
                selected_countries=selected_countries,
                selected_exchanges=selected_exchanges,
                decisions_map=decisions_map,
                target_email=target_email,
            )
        )

    def notify_run_blocked(
        self,
        run_id: str,
        profile_name: str,
        duration_ms: float,
        blocker_type: str,
        blocker_message: str,
        blocker_details: Optional[Dict[str, Any]] = None,
        selected_countries: Optional[List[str]] = None,
        selected_exchanges: Optional[List[str]] = None,
        target_email: Optional[str] = None,
    ):
        """Send a data blocker warning email explaining which pre-flight guardrail halted the run."""
        if not settings.email_notifications_enabled:
            return

        asyncio.create_task(
            self._async_dispatch_blocked(
                run_id=run_id,
                profile_name=profile_name,
                duration_ms=duration_ms,
                blocker_type=blocker_type,
                blocker_message=blocker_message,
                blocker_details=blocker_details or {},
                selected_countries=selected_countries or [],
                selected_exchanges=selected_exchanges or [],
                target_email=target_email,
            )
        )

    def notify_run_failed(
        self,
        run_id: str,
        profile_name: str,
        duration_ms: float,
        error_message: str,
        selected_countries: Optional[List[str]] = None,
        selected_exchanges: Optional[List[str]] = None,
        target_email: Optional[str] = None,
    ):
        """Send an urgent alert email for an unexpected technical pipeline crash."""
        if not settings.email_notifications_enabled:
            return

        asyncio.create_task(
            self._async_dispatch_failed(
                run_id=run_id,
                profile_name=profile_name,
                duration_ms=duration_ms,
                error_message=error_message,
                selected_countries=selected_countries or [],
                selected_exchanges=selected_exchanges or [],
                target_email=target_email,
            )
        )

    def notify_export_decisions(
        self,
        run_id: str,
        profile_name: str,
        results: List[Any],
        decisions_map: Dict[str, Dict[str, str]],
        target_email: str,
        memo_note: Optional[str] = None,
        sender_email: Optional[str] = None,
    ) -> bool:
        """Compose and dispatch screening results with updated analyst decisions attached."""
        try:
            # 1. Generate Excel workbook in memory
            excel_bytes = export_service.generate_screening_workbook(
                run_id=run_id,
                profile_name=profile_name,
                results=results,
                decisions_map=decisions_map,
            )

            # 2. Build HTML Body
            subject = f"📋 [DECISIONS] Screening Results & Decisions: {profile_name} (Run {run_id})"
            html_content = self._build_export_decisions_html(
                run_id=run_id,
                profile_name=profile_name,
                results=results,
                decisions_map=decisions_map,
                memo_note=memo_note,
                sender_email=sender_email,
            )

            # 3. Dispatch
            safe_prof = "".join(c for c in profile_name if c.isalnum() or c in ("-", "_")).strip()
            filename = f"Screening_Results_{safe_prof or 'Export'}_{run_id}.xlsx"
            self._send_email(
                subject=subject,
                html_body=html_content,
                attachment_bytes=excel_bytes,
                attachment_name=filename,
                target_email=target_email,
            )
            return True
        except Exception as e:
            logger.provider_error("NOTIFY", f"Failed to dispatch export decisions email for '{run_id}': {e}")
            raise

    # =========================================================================
    # ASYNCHRONOUS WORKERS
    # =========================================================================

    async def _async_dispatch_success(
        self,
        run_id: str,
        profile_name: str,
        duration_ms: float,
        funnel_counts: Any,
        results: List[Any],
        selected_countries: List[str],
        selected_exchanges: List[str],
        decisions_map: Optional[Dict[str, Dict[str, str]]] = None,
        target_email: Optional[str] = None,
    ):
        """Worker: Generates Excel attachment and sends success email."""
        try:
            # 1. Generate Excel workbook in thread pool
            excel_bytes = await asyncio.to_thread(
                export_service.generate_screening_workbook,
                run_id=run_id,
                profile_name=profile_name,
                results=results,
                decisions_map=decisions_map,
            )

            # 2. Build HTML Body
            subject = f"✅ [SUCCESS] Screening Completed: {profile_name} (Top 20 & Near Misses Attached)"
            html_content = self._build_success_html(
                run_id=run_id,
                profile_name=profile_name,
                duration_ms=duration_ms,
                funnel_counts=funnel_counts,
                results=results,
                selected_countries=selected_countries,
                selected_exchanges=selected_exchanges,
            )

            # 3. Dispatch
            filename = f"Screening_Results_{run_id}.xlsx"
            await asyncio.to_thread(
                self._send_email,
                subject=subject,
                html_body=html_content,
                attachment_bytes=excel_bytes,
                attachment_name=filename,
                target_email=target_email,
            )
        except Exception as e:
            logger.provider_error("NOTIFY", f"Failed to dispatch success email for '{run_id}': {e}")

    async def _async_dispatch_blocked(
        self,
        run_id: str,
        profile_name: str,
        duration_ms: float,
        blocker_type: str,
        blocker_message: str,
        blocker_details: Dict[str, Any],
        selected_countries: List[str],
        selected_exchanges: List[str],
        target_email: Optional[str] = None,
    ):
        """Worker: Builds and sends data blocker warning email."""
        try:
            subject = f"⚠️ [BLOCKED] Screening Halted: {blocker_type} Guardrail Tripped"
            html_content = self._build_blocked_html(
                run_id=run_id,
                profile_name=profile_name,
                duration_ms=duration_ms,
                blocker_type=blocker_type,
                blocker_message=blocker_message,
                blocker_details=blocker_details,
                selected_countries=selected_countries,
                selected_exchanges=selected_exchanges,
            )

            await asyncio.to_thread(
                self._send_email,
                subject=subject,
                html_body=html_content,
                target_email=target_email,
            )
        except Exception as e:
            logger.provider_error("NOTIFY", f"Failed to dispatch blocker email for '{run_id}': {e}")

    async def _async_dispatch_failed(
        self,
        run_id: str,
        profile_name: str,
        duration_ms: float,
        error_message: str,
        selected_countries: List[str],
        selected_exchanges: List[str],
        target_email: Optional[str] = None,
    ):
        """Worker: Builds and sends technical failure alert email."""
        try:
            subject = f"❌ [FAILED] Screening Execution Error: {profile_name}"
            html_content = self._build_failed_html(
                run_id=run_id,
                profile_name=profile_name,
                duration_ms=duration_ms,
                error_message=error_message,
                selected_countries=selected_countries,
                selected_exchanges=selected_exchanges,
            )

            await asyncio.to_thread(
                self._send_email,
                subject=subject,
                html_body=html_content,
                target_email=target_email,
            )
        except Exception as e:
            logger.provider_error("NOTIFY", f"Failed to dispatch failure email for '{run_id}': {e}")

    # =========================================================================
    # CORE DISPATCH ENGINE (SMTP & DISK FALLBACK)
    # =========================================================================

    def _send_email(
        self,
        subject: str,
        html_body: str,
        attachment_bytes: Optional[bytes] = None,
        attachment_name: Optional[str] = None,
        target_email: Optional[str] = None,
    ):
        """Send email via SMTP, strictly only to input recipients."""
        # Strictly accept ONLY what is explicitly given as input (no fallbacks or hidden emails)
        raw_str = (target_email or "").strip()
        recipients = [r.strip() for r in raw_str.replace(";", ",").split(",") if r.strip()]

        if not recipients:
            # If no recipient was provided in input, do NOT send live emails to anyone!
            self._save_to_disk(subject, html_body, attachment_bytes, attachment_name)
            logger.provider_info("NOTIFY", f"Archived email to disk (no recipient input provided; live dispatch skipped).")
            return

        # Construct MIME Message
        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = settings.email_from
        msg["To"] = ", ".join(recipients) if recipients else "Unconfigured <recipient@company.com>"
        msg["Date"] = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

        # HTML Body
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # Optional Attachment
        if attachment_bytes and attachment_name:
            part = MIMEBase("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            part.set_payload(attachment_bytes)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{attachment_name}"')
            msg.attach(part)

        # Check if live SMTP credentials are provided
        has_smtp_creds = bool(settings.smtp_user and settings.smtp_password and recipients)

        if not has_smtp_creds:
            # Save to disk for instant developer inspection
            self._save_to_disk(subject, html_body, attachment_bytes, attachment_name)
            logger.provider_info(
                "NOTIFY",
                f"Archived email to 'backend/logs/sent_emails/' (SMTP credentials or recipient not configured in .env)."
            )
            return

        # Attempt Live SMTP Transmission
        try:
            logger.provider_info("NOTIFY", f"Connecting to SMTP server {settings.smtp_host}:{settings.smtp_port}...")
            import ssl
            context = ssl.create_default_context()
            server = None
            if settings.smtp_port == 465:
                server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=20, context=context)
                server.ehlo()
            else:
                try:
                    server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20)
                    server.ehlo()
                    if settings.smtp_use_tls:
                        server.starttls(context=context)
                        server.ehlo()
                except (smtplib.SMTPServerDisconnected, ConnectionResetError, OSError):
                    # Automatic fallback to port 465 SSL if port 587 was dropped by firewall/ISP
                    server = smtplib.SMTP_SSL(settings.smtp_host, 465, timeout=20, context=context)
                    server.ehlo()

            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
            server.quit()
            logger.provider_info("NOTIFY", f"Email successfully sent to {recipients}: '{subject}'")

            # Also keep a local audit copy
            self._save_to_disk(subject, html_body, attachment_bytes, attachment_name)
        except Exception as smtp_err:
            logger.provider_warn(
                "NOTIFY",
                f"SMTP transmission failed ({smtp_err}). Saved email to 'backend/logs/sent_emails/'."
            )
            self._save_to_disk(subject, html_body, attachment_bytes, attachment_name)

    def _save_to_disk(
        self,
        subject: str,
        html_body: str,
        attachment_bytes: Optional[bytes],
        attachment_name: Optional[str],
    ):
        """Persist email to disk for testing, auditability, and offline review."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            clean_sub = "".join(c for c in subject if c.isalnum() or c in (" ", "-", "_")).strip().replace(" ", "_")
            base_filename = f"{timestamp}_{clean_sub[:40]}"

            html_path = SENT_EMAILS_DIR / f"{base_filename}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_body)

            if attachment_bytes and attachment_name:
                excel_path = SENT_EMAILS_DIR / f"{base_filename}_{attachment_name}"
                with open(excel_path, "wb") as f:
                    f.write(attachment_bytes)
        except Exception as e:
            logger.provider_warn("NOTIFY", f"Could not archive email to disk: {e}")

    # =========================================================================
    # HTML EMAIL TEMPLATES
    # =========================================================================

    @staticmethod
    def _build_success_html(
        run_id: str,
        profile_name: str,
        duration_ms: float,
        funnel_counts: Any,
        results: List[Any],
        selected_countries: List[str],
        selected_exchanges: List[str],
    ) -> str:
        """Compose modern HTML email for successful screening completion."""
        top20 = [r for r in results if getattr(r, "rank", 999) <= 20][:5]
        top_rows_html = ""
        for s in top20:
            rank = getattr(s, "rank", "—")
            ticker = getattr(s, "ticker", "")
            name = getattr(s, "company_name", None) or getattr(s, "name", ticker)
            score = getattr(s, "score", 0)
            sector = getattr(s, "sector", "")
            pe = getattr(s, "fwd_pe", None)
            pe_str = f"{pe:.1f}x" if pe else "—"
            top_rows_html += f"""
            <tr style="border-bottom: 1px solid #E2E8F0; font-size: 13px;">
                <td style="padding: 10px; text-align: center; font-weight: bold; color: #1E3A8A;">#{rank}</td>
                <td style="padding: 10px; font-weight: bold; color: #0F172A;">{html.escape(ticker)}</td>
                <td style="padding: 10px; color: #334155;">{html.escape(name)}</td>
                <td style="padding: 10px; color: #64748B;">{html.escape(sector)}</td>
                <td style="padding: 10px; text-align: center; font-weight: bold; color: #0F172A;">{score}/100</td>
                <td style="padding: 10px; text-align: right; color: #0F172A;">{pe_str}</td>
            </tr>
            """

        # Near Misses Preview (Contenders ranked 21-40 or displaced / near-miss gate dropped)
        near_misses = [
            r for r in results
            if getattr(r, "near_miss_status", "none") in ("rank_near_miss", "rule_near_miss")
            or (getattr(r, "rank", 0) > 20 and getattr(r, "rank", 999) <= 40)
        ][:5]
        nm_rows_html = ""
        for s in near_misses:
            rank = getattr(s, "rank", "—")
            ticker = getattr(s, "ticker", "")
            name = getattr(s, "company_name", None) or getattr(s, "name", ticker)
            score = getattr(s, "score", 0)
            sector = getattr(s, "sector", "")
            near_status = getattr(s, "near_miss_status", "none")
            metric_statuses = getattr(s, "metric_statuses", {}) or {}
            div_reason = metric_statuses.get("diversification") if isinstance(metric_statuses, dict) else None

            if div_reason:
                nm_reason = f"Displaced: {div_reason}"
            elif near_status == "rank_near_miss" or (isinstance(rank, int) and rank > 20):
                nm_reason = f"Rank cut-off (#{rank})"
            elif near_status == "rule_near_miss":
                nm_reason = "Single gate borderline miss"
            else:
                nm_reason = "Near miss contender"

            nm_rows_html += f"""
            <tr style="border-bottom: 1px solid #FEF3C7; font-size: 13px;">
                <td style="padding: 10px; text-align: center; font-weight: bold; color: #B45309;">#{rank}</td>
                <td style="padding: 10px; font-weight: bold; color: #0F172A;">{html.escape(ticker)}</td>
                <td style="padding: 10px; color: #334155;">{html.escape(name)}</td>
                <td style="padding: 10px; color: #64748B;">{html.escape(sector)}</td>
                <td style="padding: 10px; text-align: center; font-weight: bold; color: #0F172A;">{score}/100</td>
                <td style="padding: 10px; text-align: right; color: #B45309; font-weight: 500;">{html.escape(nm_reason)}</td>
            </tr>
            """

        c_str = ", ".join(c.upper() for c in selected_countries) or "Global"
        e_str = ", ".join(e.upper() for e in selected_exchanges) or "All"
        univ = getattr(funnel_counts, "universe_count", getattr(funnel_counts, "universe", len(results)))
        floors = getattr(funnel_counts, "floors_count", getattr(funnel_counts, "floors", "—"))
        gates = getattr(funnel_counts, "gates_count", getattr(funnel_counts, "gates", "—"))
        sel = getattr(funnel_counts, "selected_count", getattr(funnel_counts, "selected", min(len(results), 20)))

        now_ist = datetime.now(IST_TZ)
        now_utc = datetime.now(timezone.utc)
        completion_time_str = f"{now_ist.strftime('%I:%M:%S %p')} IST ({now_utc.strftime('%H:%M:%S')} UTC)"

        return f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F8FAFC; margin: 0; padding: 24px; color: #0F172A;">
            <div style="max-width: 680px; margin: 0 auto; background-color: #FFFFFF; border-radius: 8px; border: 1px solid #E2E8F0; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                
                <!-- Header Banner -->
                <div style="background-color: #065F46; padding: 24px; color: #FFFFFF;">
                    <div style="font-size: 12px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.9;">Screening Run Succeeded</div>
                    <h1 style="margin: 6px 0 0 0; font-size: 22px; font-weight: bold;">{html.escape(profile_name)}</h1>
                </div>

                <!-- Run Overview -->
                <div style="padding: 24px;">
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                        <tr>
                            <td style="padding: 6px 0; color: #64748B; font-size: 13px;">Execution Run ID:</td>
                            <td style="padding: 6px 0; font-weight: 600; font-family: monospace; font-size: 13px;">{html.escape(run_id)}</td>
                            <td style="padding: 6px 0; color: #64748B; font-size: 13px;">Duration:</td>
                            <td style="padding: 6px 0; font-weight: 600; font-size: 13px;">{duration_ms:.0f} ms</td>
                        </tr>
                        <tr>
                            <td style="padding: 6px 0; color: #64748B; font-size: 13px;">Markets Covered:</td>
                            <td style="padding: 6px 0; font-size: 13px;">{html.escape(c_str)} ({html.escape(e_str)})</td>
                            <td style="padding: 6px 0; color: #64748B; font-size: 13px;">Completion Time:</td>
                            <td style="padding: 6px 0; font-weight: 600; font-size: 13px;">{completion_time_str}</td>
                        </tr>
                    </table>

                    <!-- Funnel Statistics Grid -->
                    <div style="display: flex; gap: 12px; margin-bottom: 24px; background-color: #F1F5F9; border-radius: 6px; padding: 12px 16px;">
                        <div style="flex: 1; text-align: center;">
                            <div style="font-size: 11px; color: #64748B; text-transform: uppercase; font-weight: 600;">Total Universe</div>
                            <div style="font-size: 18px; font-weight: bold; color: #0F172A; margin-top: 2px;">{univ}</div>
                        </div>
                        <div style="flex: 1; text-align: center; border-left: 1px solid #CBD5E1;">
                            <div style="font-size: 11px; color: #64748B; text-transform: uppercase; font-weight: 600;">Floors Passed</div>
                            <div style="font-size: 18px; font-weight: bold; color: #0F172A; margin-top: 2px;">{floors}</div>
                        </div>
                        <div style="flex: 1; text-align: center; border-left: 1px solid #CBD5E1;">
                            <div style="font-size: 11px; color: #64748B; text-transform: uppercase; font-weight: 600;">Gates Passed</div>
                            <div style="font-size: 18px; font-weight: bold; color: #0F172A; margin-top: 2px;">{gates}</div>
                        </div>
                        <div style="flex: 1; text-align: center; border-left: 1px solid #CBD5E1;">
                            <div style="font-size: 11px; color: #065F46; text-transform: uppercase; font-weight: bold;">Top 20 Selected</div>
                            <div style="font-size: 18px; font-weight: bold; color: #065F46; margin-top: 2px;">{sel}</div>
                        </div>
                    </div>

                    <!-- Top 5 Preview Table -->
                    <h3 style="font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em; color: #1E3A8A; margin: 0 0 10px 0;">Top Model Contenders Preview</h3>
                    <table style="width: 100%; border-collapse: collapse; border: 1px solid #E2E8F0; border-radius: 6px; overflow: hidden; margin-bottom: 24px;">
                        <thead>
                            <tr style="background-color: #F8FAFC; border-bottom: 2px solid #E2E8F0; font-size: 11px; text-transform: uppercase; color: #64748B;">
                                <th style="padding: 8px 10px; text-align: center;">Rank</th>
                                <th style="padding: 8px 10px; text-align: left;">Ticker</th>
                                <th style="padding: 8px 10px; text-align: left;">Company</th>
                                <th style="padding: 8px 10px; text-align: left;">Sector</th>
                                <th style="padding: 8px 10px; text-align: center;">Score</th>
                                <th style="padding: 8px 10px; text-align: right;">FWD P/E</th>
                            </tr>
                        </thead>
                        <tbody>
                            {top_rows_html}
                        </tbody>
                    </table>

                    <!-- Near Misses Preview Table -->
                    {f'''
                    <div style="margin-bottom: 24px;">
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                            <h3 style="font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em; color: #B45309; margin: 0;">⚡ Near Miss Contenders Preview</h3>
                            <span style="font-size: 11px; color: #92400E; background-color: #FEF3C7; padding: 2px 8px; border-radius: 4px; font-weight: 600;">Included in Sheet 2</span>
                        </div>
                        <table style="width: 100%; border-collapse: collapse; border: 1px solid #FDE68A; border-radius: 6px; overflow: hidden;">
                            <thead>
                                <tr style="background-color: #FFFBEB; border-bottom: 2px solid #FDE68A; font-size: 11px; text-transform: uppercase; color: #92400E;">
                                    <th style="padding: 8px 10px; text-align: center;">Rank</th>
                                    <th style="padding: 8px 10px; text-align: left;">Ticker</th>
                                    <th style="padding: 8px 10px; text-align: left;">Company</th>
                                    <th style="padding: 8px 10px; text-align: left;">Sector</th>
                                    <th style="padding: 8px 10px; text-align: center;">Score</th>
                                    <th style="padding: 8px 10px; text-align: right;">Status / Reason</th>
                                </tr>
                            </thead>
                            <tbody>
                                {nm_rows_html}
                            </tbody>
                        </table>
                    </div>
                    ''' if nm_rows_html else ''}

                    <!-- Attachment Notice -->
                    <div style="background-color: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 6px; padding: 14px 16px;">
                        <div style="font-weight: 600; font-size: 13px; color: #1E40AF; margin-bottom: 4px;">📎 Multi-Sheet Excel Workbook Attached</div>
                        <div style="font-size: 12px; color: #1E3A8A; line-height: 1.5;">
                            The full Excel workbook (<strong>Screening_Results_{html.escape(run_id)}.xlsx</strong>) is attached with 3 comprehensive sheets:
                            <br>• <strong>Sheet 1: Top 20 Winners</strong> — Portfolio picks with audit decisions & rankings.
                            <br>• <strong>Sheet 2: Near Misses</strong> — Contenders falling just outside Top 20 or single-gate misses with reason notes.
                            <br>• <strong>Sheet 3: Master Universe</strong> — All evaluated companies across markets.
                        </div>
                    </div>
                </div>

                <!-- Footer -->
                <div style="background-color: #F8FAFC; border-top: 1px solid #E2E8F0; padding: 16px 24px; font-size: 11px; color: #94A3B8; text-align: center;">
                    Institutional Screening Platform · Automated Notification Service
                </div>
            </div>
        </body>
        </html>
        """

    @staticmethod
    def _build_export_decisions_html(
        run_id: str,
        profile_name: str,
        results: List[Any],
        decisions_map: Dict[str, Dict[str, str]],
        memo_note: Optional[str] = None,
        sender_email: Optional[str] = None,
    ) -> str:
        """Compose institutional HTML email for user-exported screening decisions."""
        keep_count = sum(1 for d in decisions_map.values() if (d.get("decision") or "").upper() == "KEEP")
        drop_count = sum(1 for d in decisions_map.values() if (d.get("decision") or "").upper() == "DROP")

        now_ist = datetime.now(IST_TZ)
        now_utc = datetime.now(timezone.utc)
        export_time_str = f"{now_ist.strftime('%I:%M:%S %p')} IST ({now_utc.strftime('%H:%M:%S')} UTC)"

        # Priority-sort: stocks with explicit decisions first, then top 20 winners
        decided_items = []
        seen_ids = set()
        for s in results:
            c_id = getattr(s, "canonical_company_id", None) or getattr(s, "id", "")
            if c_id in decisions_map and (decisions_map[c_id].get("decision") or "").strip():
                decided_items.append((s, decisions_map[c_id]))
                seen_ids.add(c_id)

        # Include remaining top 20 winners up to 20 preview rows
        for s in results:
            c_id = getattr(s, "canonical_company_id", None) or getattr(s, "id", "")
            if c_id not in seen_ids and getattr(s, "rank", 999) <= 20:
                decided_items.append((s, decisions_map.get(c_id, {})))
                seen_ids.add(c_id)
            if len(decided_items) >= 20:
                break

        table_rows_html = ""
        for s, dec in decided_items:
            rank = getattr(s, "rank", "—")
            ticker = getattr(s, "ticker", "")
            name = getattr(s, "company_name", None) or getattr(s, "name", ticker)
            score = getattr(s, "score", 0)
            sector = getattr(s, "sector", "")
            raw_dec = (dec.get("decision") or getattr(s, "decision", "") or "").strip().upper()
            reason = dec.get("decision_reason") or getattr(s, "decision_reason", "") or "—"

            if raw_dec == "KEEP":
                badge_bg, badge_fg = "#D1FAE5", "#065F46"
            elif raw_dec == "DROP":
                badge_bg, badge_fg = "#FEE2E2", "#991B1B"
            else:
                raw_dec = "—"
                badge_bg, badge_fg = "#F1F5F9", "#475569"

            table_rows_html += f"""
            <tr style="border-bottom: 1px solid #E2E8F0; font-size: 13px;">
                <td style="padding: 10px; text-align: center; font-weight: bold; color: #1E3A8A;">#{rank}</td>
                <td style="padding: 10px; font-weight: bold; color: #0F172A;">{html.escape(ticker)}</td>
                <td style="padding: 10px; color: #334155;">{html.escape(name)}</td>
                <td style="padding: 10px; color: #64748B;">{html.escape(sector)}</td>
                <td style="padding: 10px; text-align: center; font-weight: bold; color: #0F172A;">{score}/100</td>
                <td style="padding: 10px; text-align: center;">
                    <span style="display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; background-color: {badge_bg}; color: {badge_fg};">
                        {html.escape(raw_dec)}
                    </span>
                </td>
                <td style="padding: 10px; color: #334155; font-size: 12px;">{html.escape(reason)}</td>
            </tr>
            """

        if not table_rows_html:
            table_rows_html = """
            <tr>
                <td colspan="7" style="padding: 16px; text-align: center; color: #64748B; font-size: 13px;">
                    No candidates evaluated for this run.
                </td>
            </tr>
            """

        memo_html = ""
        if memo_note and memo_note.strip():
            memo_html = f"""
            <div style="background-color: #F0FDF4; border-left: 4px solid #147B73; padding: 12px 16px; margin: 16px 0; border-radius: 4px;">
                <div style="font-size: 11px; font-weight: bold; text-transform: uppercase; color: #147B73; margin-bottom: 4px;">Analyst Executive Memo</div>
                <div style="font-size: 13px; color: #0F172A; line-height: 1.5;">{html.escape(memo_note.strip())}</div>
            </div>
            """

        sender_html = ""
        if sender_email:
            sender_html = f"""<tr>
                <td style="padding: 6px 0; color: #64748B; font-size: 13px;">Exported By:</td>
                <td colspan="3" style="padding: 6px 0; font-weight: 600; font-size: 13px; color: #0F172A;">{html.escape(sender_email)}</td>
            </tr>"""

        safe_run_id = html.escape(run_id)
        return f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F8FAFC; margin: 0; padding: 24px; color: #0F172A;">
            <div style="max-width: 680px; margin: 0 auto; background-color: #FFFFFF; border-radius: 8px; border: 1px solid #E2E8F0; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                
                <!-- Institutional Header Banner -->
                <div style="background: linear-gradient(135deg, #147B73 0%, #0F766E 100%); padding: 24px; color: #FFFFFF;">
                    <div style="font-size: 12px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.9;">Zenius ScreenPro · Investment Decisions Export</div>
                    <h1 style="margin: 6px 0 0 0; font-size: 22px; font-weight: bold;">{html.escape(profile_name)}</h1>
                </div>

                <!-- Run & Decisions Overview -->
                <div style="padding: 24px;">
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 16px;">
                        <tr>
                            <td style="padding: 6px 0; color: #64748B; font-size: 13px;">Execution Run ID:</td>
                            <td style="padding: 6px 0; font-weight: 600; font-family: monospace; font-size: 13px;">{safe_run_id}</td>
                            <td style="padding: 6px 0; color: #64748B; font-size: 13px;">Export Time:</td>
                            <td style="padding: 6px 0; font-weight: 600; font-size: 13px;">{export_time_str}</td>
                        </tr>
                        {sender_html}
                    </table>

                    <!-- KPI Badges -->
                    <table style="width: 100%; border-collapse: separate; border-spacing: 10px 0; margin-bottom: 20px;">
                        <tr>
                            <td style="background-color: #F1F5F9; border: 1px solid #E2E8F0; border-radius: 6px; padding: 12px; text-align: center; width: 33%;">
                                <div style="font-size: 11px; text-transform: uppercase; color: #64748B; font-weight: 600;">Total Evaluated</div>
                                <div style="font-size: 20px; font-weight: bold; color: #0F172A; margin-top: 2px;">{len(results)}</div>
                            </td>
                            <td style="background-color: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 6px; padding: 12px; text-align: center; width: 33%;">
                                <div style="font-size: 11px; text-transform: uppercase; color: #065F46; font-weight: 600;">Keep Decisions</div>
                                <div style="font-size: 20px; font-weight: bold; color: #047857; margin-top: 2px;">{keep_count}</div>
                            </td>
                            <td style="background-color: #FEF2F2; border: 1px solid #FECACA; border-radius: 6px; padding: 12px; text-align: center; width: 33%;">
                                <div style="font-size: 11px; text-transform: uppercase; color: #991B1B; font-weight: 600;">Drop Decisions</div>
                                <div style="font-size: 20px; font-weight: bold; color: #DC2626; margin-top: 2px;">{drop_count}</div>
                            </td>
                        </tr>
                    </table>

                    {memo_html}

                    <!-- Decisions Table -->
                    <div style="margin-bottom: 24px;">
                        <h3 style="font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em; color: #0F172A; margin: 0 0 10px 0;">Portfolio Selection & Decisions Summary</h3>
                        <table style="width: 100%; border-collapse: collapse; border: 1px solid #E2E8F0; border-radius: 6px; overflow: hidden;">
                            <thead>
                                <tr style="background-color: #F8FAFC; border-bottom: 2px solid #E2E8F0; font-size: 11px; text-transform: uppercase; color: #64748B;">
                                    <th style="padding: 8px 10px; text-align: center;">Rank</th>
                                    <th style="padding: 8px 10px; text-align: left;">Ticker</th>
                                    <th style="padding: 8px 10px; text-align: left;">Company</th>
                                    <th style="padding: 8px 10px; text-align: left;">Sector</th>
                                    <th style="padding: 8px 10px; text-align: center;">Score</th>
                                    <th style="padding: 8px 10px; text-align: center;">Decision</th>
                                    <th style="padding: 8px 10px; text-align: left;">Reason / Note</th>
                                </tr>
                            </thead>
                            <tbody>
                                {table_rows_html}
                            </tbody>
                        </table>
                    </div>

                    <!-- Attachment Notice -->
                    <div style="background-color: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 6px; padding: 14px 16px;">
                        <div style="font-weight: 600; font-size: 13px; color: #1E40AF; margin-bottom: 4px;">📎 Multi-Sheet Excel Workbook Attached</div>
                        <div style="font-size: 12px; color: #1E3A8A; line-height: 1.5;">
                            The full Excel workbook with your updated <strong>Decision</strong> and <strong>Decision Reason</strong> columns is attached with 3 sheets:
                            <br>• <strong>Sheet 1: Top 20 Winners</strong> — Primary portfolio selection with analyst decisions.
                            <br>• <strong>Sheet 2: Near Misses</strong> — Borderline contenders & displaced candidates with attribution notes.
                            <br>• <strong>Sheet 3: Master Universe</strong> — All screened candidates.
                        </div>
                    </div>
                </div>

                <!-- Footer -->
                <div style="background-color: #F8FAFC; border-top: 1px solid #E2E8F0; padding: 16px 24px; font-size: 11px; color: #94A3B8; text-align: center;">
                    Zenius ScreenPro · Institutional Equity Screening Platform
                </div>
            </div>
        </body>
        </html>
        """

    @staticmethod
    def _build_blocked_html(
        run_id: str,
        profile_name: str,
        duration_ms: float,
        blocker_type: str,
        blocker_message: str,
        blocker_details: Dict[str, Any],
        selected_countries: List[str],
        selected_exchanges: List[str],
    ) -> str:
        """Compose warning HTML email for data blocker halts."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F8FAFC; margin: 0; padding: 24px; color: #0F172A;">
            <div style="max-width: 680px; margin: 0 auto; background-color: #FFFFFF; border-radius: 8px; border: 1px solid #E2E8F0; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                
                <!-- Amber Warning Banner -->
                <div style="background-color: #B45309; padding: 24px; color: #FFFFFF;">
                    <div style="font-size: 12px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.9;">Pre-Flight Safety Guardrail Tripped</div>
                    <h1 style="margin: 6px 0 0 0; font-size: 22px; font-weight: bold;">[BLOCKED] {html.escape(blocker_type)}</h1>
                </div>

                <!-- Explanation -->
                <div style="padding: 24px;">
                    <p style="font-size: 14px; line-height: 1.5; color: #334155; margin-top: 0;">
                        The screening run for <strong>{html.escape(profile_name)}</strong> (Run ID: <code>{html.escape(run_id)}</code>)
                        was <strong>intentionally halted</strong> before generating portfolio rankings.
                    </p>

                    <div style="background-color: #FEF3C7; border: 1px solid #FCD34D; border-radius: 6px; padding: 14px 16px; margin: 18px 0;">
                        <div style="font-size: 12px; font-weight: bold; text-transform: uppercase; color: #92400E; margin-bottom: 4px;">Guardrail Diagnosis</div>
                        <div style="font-size: 13px; font-weight: 600; color: #78350F; line-height: 1.4;">
                            {html.escape(blocker_message)}
                        </div>
                    </div>

                    <h4 style="font-size: 13px; text-transform: uppercase; color: #64748B; margin: 18px 0 8px 0;">Why Was This Run Blocked?</h4>
                    <p style="font-size: 12px; color: #475569; line-height: 1.5; margin: 0 0 14px 0;">
                        To protect investment capital, our institutional rules prevent generating a "Top 20" recommendation list
                        whenever vendor prices are stale, currency conversion rates are missing, or universe completeness drops below 75%.
                    </p>

                    <h4 style="font-size: 13px; text-transform: uppercase; color: #64748B; margin: 18px 0 8px 0;">Recommended Action</h4>
                    <ul style="font-size: 12px; color: #475569; line-height: 1.5; margin: 0; padding-left: 20px;">
                        <li>Verify connection and freshness timestamps with the market data vendor.</li>
                        <li>Check if the exchange had an unscheduled market closure or holiday.</li>
                        <li>Once the data vendor pipeline updates, re-trigger the screening execution.</li>
                    </ul>
                </div>

                <!-- Footer -->
                <div style="background-color: #F8FAFC; border-top: 1px solid #E2E8F0; padding: 16px 24px; font-size: 11px; color: #94A3B8; text-align: center;">
                    Institutional Screening Platform · Pre-Flight Data Quality Guardrails
                </div>
            </div>
        </body>
        </html>
        """

    @staticmethod
    def _build_failed_html(
        run_id: str,
        profile_name: str,
        duration_ms: float,
        error_message: str,
        selected_countries: List[str],
        selected_exchanges: List[str],
    ) -> str:
        """Compose alert HTML email for unexpected technical pipeline errors."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F8FAFC; margin: 0; padding: 24px; color: #0F172A;">
            <div style="max-width: 680px; margin: 0 auto; background-color: #FFFFFF; border-radius: 8px; border: 1px solid #E2E8F0; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                
                <!-- Red Alert Banner -->
                <div style="background-color: #991B1B; padding: 24px; color: #FFFFFF;">
                    <div style="font-size: 12px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.9;">Technical Execution Failure</div>
                    <h1 style="margin: 6px 0 0 0; font-size: 22px; font-weight: bold;">[FAILED] Screening Pipeline Crash</h1>
                </div>

                <div style="padding: 24px;">
                    <p style="font-size: 14px; line-height: 1.5; color: #334155; margin-top: 0;">
                        An unexpected technical exception occurred during execution of screening profile <strong>{html.escape(profile_name)}</strong>.
                    </p>

                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                        <tr>
                            <td style="padding: 6px 0; color: #64748B; font-size: 13px;">Execution Run ID:</td>
                            <td style="padding: 6px 0; font-weight: 600; font-family: monospace; font-size: 13px;">{html.escape(run_id)}</td>
                            <td style="padding: 6px 0; color: #64748B; font-size: 13px;">Duration:</td>
                            <td style="padding: 6px 0; font-weight: 600; font-size: 13px;">{duration_ms:.0f} ms</td>
                        </tr>
                    </table>

                    <div style="background-color: #FEE2E2; border: 1px solid #FCA5A5; border-radius: 6px; padding: 14px 16px; margin: 18px 0;">
                        <div style="font-size: 12px; font-weight: bold; text-transform: uppercase; color: #7F1D1D; margin-bottom: 4px;">System Error Diagnosis</div>
                        <div style="font-size: 12px; font-family: monospace; color: #991B1B; line-height: 1.4; word-break: break-all;">
                            {html.escape(error_message)}
                        </div>
                    </div>

                    <h4 style="font-size: 13px; text-transform: uppercase; color: #64748B; margin: 18px 0 8px 0;">Recommended Investigation Steps</h4>
                    <ul style="font-size: 12px; color: #475569; line-height: 1.5; margin: 0; padding-left: 20px;">
                        <li>Check backend terminal and <code>backend/logs/screening.log</code> for full Python stack trace.</li>
                        <li>Verify PostgreSQL service status on port 5432.</li>
                    </ul>
                </div>

                <div style="background-color: #F8FAFC; border-top: 1px solid #E2E8F0; padding: 16px 24px; font-size: 11px; color: #94A3B8; text-align: center;">
                    Institutional Screening Platform · Automated Failure Alerts
                </div>
            </div>
        </body>
        </html>
        """


# Global singleton instance
notification_service = NotificationService()

