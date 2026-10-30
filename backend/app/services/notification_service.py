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
from datetime import datetime, timezone
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
            )
        )

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
            subject = f"✅ [SUCCESS] Screening Completed: {profile_name} (Top 20 Attached)"
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
    ):
        """Send email via Outlook/Office 365 SMTP, or save to disk if unconfigured."""
        recipients_str = settings.email_to.strip()
        recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]

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
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20)
            if settings.smtp_use_tls:
                server.starttls()
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

        c_str = ", ".join(c.upper() for c in selected_countries) or "Global"
        e_str = ", ".join(e.upper() for e in selected_exchanges) or "All"
        univ = getattr(funnel_counts, "universe", len(results))
        sel = getattr(funnel_counts, "selected", min(len(results), 20))

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
                            <td style="padding: 6px 0; font-size: 13px;">{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}</td>
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
                            <div style="font-size: 18px; font-weight: bold; color: #0F172A; margin-top: 2px;">{getattr(funnel_counts, 'floors', '—')}</div>
                        </div>
                        <div style="flex: 1; text-align: center; border-left: 1px solid #CBD5E1;">
                            <div style="font-size: 11px; color: #64748B; text-transform: uppercase; font-weight: 600;">Gates Passed</div>
                            <div style="font-size: 18px; font-weight: bold; color: #0F172A; margin-top: 2px;">{getattr(funnel_counts, 'gates', '—')}</div>
                        </div>
                        <div style="flex: 1; text-align: center; border-left: 1px solid #CBD5E1;">
                            <div style="font-size: 11px; color: #065F46; text-transform: uppercase; font-weight: bold;">Top 20 Selected</div>
                            <div style="font-size: 18px; font-weight: bold; color: #065F46; margin-top: 2px;">{sel}</div>
                        </div>
                    </div>

                    <!-- Top 5 Preview Table -->
                    <h3 style="font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em; color: #475569; margin: 0 0 12px 0;">Top Model Contenders Preview</h3>
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

                    <!-- Attachment Notice -->
                    <div style="background-color: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 6px; padding: 14px 16px;">
                        <div style="font-weight: 600; font-size: 13px; color: #1E40AF; margin-bottom: 4px;">📎 Complete Excel Workbook Attached</div>
                        <div style="font-size: 12px; color: #3B82F6; line-height: 1.4;">
                            The full Excel workbook (<strong>Screening_Results_{html.escape(run_id)}.xlsx</strong>) is attached to this email. It contains 3 tabs:
                            <strong>Top 20 Winners</strong>, <strong>Near Misses</strong>, and <strong>Master Universe</strong>, with side-by-side Decision and Reason audit columns.
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
