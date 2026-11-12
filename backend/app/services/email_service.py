"""Corporate Email Notification Service for Authentication.

Handles secure dispatch of:
1. 6-digit Email Verification Codes for corporate self-registration (@zeniusit.com).
2. 6-digit Authenticated Password Reset Codes.

Delivery strategy (tried in order):
  1. SMTP_SSL on port 465  — preferred; better Microsoft 365 / Exchange Online compatibility.
  2. STARTTLS on port 587  — standard Gmail / fallback.
Both methods are attempted; first to succeed wins. Codes are always written to
backend/logs/otp_admin.log as a secure operator fallback (never exposed in HTTP/UI).
"""

from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import html
import logging
import smtplib
import ssl
import threading
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("app.services.email")

SENT_EMAILS_DIR = Path(__file__).resolve().parent.parent.parent / "logs" / "sent_emails"
OTP_ADMIN_LOG   = Path(__file__).resolve().parent.parent.parent / "logs" / "otp_admin.log"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_dirs() -> None:
    SENT_EMAILS_DIR.mkdir(parents=True, exist_ok=True)
    OTP_ADMIN_LOG.parent.mkdir(parents=True, exist_ok=True)


def _write_otp_admin_log(action: str, recipient: str, code: str) -> None:
    """Write active OTP to a local operator log — NEVER returned in any HTTP response."""
    try:
        _ensure_dirs()
        ts   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        line = f"[{ts}] {action:<28} | email={recipient:<45} | code={code}\n"
        with open(OTP_ADMIN_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        logger.warning(f"[EmailService] Could not write OTP admin log: {e}")


def _save_html_archive(subject: str, recipient: str, html_body: str) -> None:
    """Archive rendered HTML email to disk for diagnostics."""
    try:
        _ensure_dirs()
        safe_ts   = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_user = recipient.replace("@", "_at_").replace(".", "_")
        filepath  = SENT_EMAILS_DIR / f"{safe_ts}_{safe_user}.html"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"<!-- Subject: {subject} -->\n<!-- To: {recipient} -->\n{html_body}")
    except Exception as e:
        logger.warning(f"[EmailService] Could not archive email HTML: {e}")


def _build_msg(recipient: str, subject: str, plain_body: str, html_body: str) -> MIMEMultipart:
    """Build an RFC-compliant multi-part MIME message."""
    msg = MIMEMultipart("alternative")
    msg["Subject"]        = subject
    # Plain sender address (no fancy display-name) is more trustworthy to M365 filters
    msg["From"]           = settings.smtp_user
    msg["To"]             = recipient
    msg["Date"]           = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    msg["X-Mailer"]       = "Zenius-ScreenPro/1.0"
    msg["Precedence"]     = "transactional"
    msg["Auto-Submitted"] = "auto-generated"
    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body,  "html",  "utf-8"))
    return msg


def _try_ssl_465(recipient: str, subject: str, plain_body: str, html_body: str) -> bool:
    """SMTP_SSL on port 465 — preferred for Microsoft 365 / Exchange Online."""
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(settings.smtp_host, 465, context=ctx, timeout=15) as server:
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(_build_msg(recipient, subject, plain_body, html_body))
        logger.info(f"[EmailService] Delivered via SMTP_SSL(465) to {recipient}.")
        return True
    except Exception as e:
        logger.debug(f"[EmailService] SMTP_SSL(465) failed for {recipient}: {e}")
        return False


def _try_starttls_587(recipient: str, subject: str, plain_body: str, html_body: str) -> bool:
    """STARTTLS on port 587 — standard Gmail / fallback."""
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port or 587, timeout=15) as server:
            server.ehlo()
            if settings.smtp_use_tls:
                server.starttls(context=ctx)
                server.ehlo()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(_build_msg(recipient, subject, plain_body, html_body))
        logger.info(f"[EmailService] Delivered via STARTTLS(587) to {recipient}.")
        return True
    except Exception as e:
        logger.debug(f"[EmailService] STARTTLS(587) failed for {recipient}: {e}")
        return False


def _dispatch_smtp(recipient: str, subject: str, plain_body: str, html_body: str) -> bool:
    """Try SSL-465 first, then STARTTLS-587. Archive HTML regardless."""
    _save_html_archive(subject, recipient, html_body)

    if not (settings.smtp_host and settings.smtp_user and settings.smtp_password):
        logger.warning(
            f"[EmailService] SMTP credentials not configured. Email for '{recipient}' archived to disk only."
        )
        return False

    if _try_ssl_465(recipient, subject, plain_body, html_body):
        return True

    if _try_starttls_587(recipient, subject, plain_body, html_body):
        return True

    logger.error(
        f"[EmailService] Both SMTP methods failed for '{recipient}'. "
        "Check backend/logs/otp_admin.log for the active OTP."
    )
    return False


# ---------------------------------------------------------------------------
# Public service class
# ---------------------------------------------------------------------------

class EmailService:
    """Enterprise email dispatcher for account verification and password reset."""

    def send_verification_email(
        self, to_email: str, code: str, full_name: Optional[str] = None
    ) -> None:
        """Dispatch 6-digit verification OTP to activate a new @zeniusit.com account."""
        display_name = full_name.strip() if full_name else to_email.split("@")[0]
        subject      = "Zenius ScreenPro - Email Verification Code"

        plain_body = (
            f"Hello {display_name},\n\n"
            f"Your 6-digit corporate verification code for Zenius ScreenPro is:\n\n"
            f"  {code}\n\n"
            f"This code expires in 15 minutes.\n"
            f"Enter this code in the browser to verify your corporate email and activate your account.\n\n"
            f"If you did not create an account, please ignore this email.\n\n"
            f"-- Zenius ScreenPro"
        )

        html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f6f9;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f6f9;padding:32px 0;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;">
        <tr><td style="background:#147b73;padding:20px 32px;">
          <p style="margin:0;font-size:18px;font-weight:bold;color:#ffffff;">Zenius ScreenPro</p>
          <p style="margin:4px 0 0;font-size:12px;color:#a7d7d4;">Institutional Equity Screener</p>
        </td></tr>
        <tr><td style="padding:32px;">
          <p style="margin:0 0 8px;font-size:15px;color:#1e293b;">Hello <strong>{html.escape(display_name)}</strong>,</p>
          <p style="margin:0 0 24px;font-size:14px;color:#475569;line-height:1.6;">
            Your corporate email verification code for <strong>Zenius ScreenPro</strong> is:
          </p>
          <div style="text-align:center;margin:0 0 24px;">
            <span style="display:inline-block;font-size:32px;font-weight:bold;
                         font-family:'Courier New',Courier,monospace;letter-spacing:8px;
                         color:#147b73;background:#e6f4f2;
                         padding:12px 24px;border-radius:6px;border:2px solid #147b73;">
              {code}
            </span>
          </div>
          <p style="margin:0 0 8px;font-size:13px;color:#64748b;line-height:1.6;">
            This code expires in <strong>15 minutes</strong>.
            Enter it in the browser to verify your corporate email and activate your account.
          </p>
          <p style="margin:0;font-size:12px;color:#94a3b8;">If you did not create an account, you can safely ignore this email.</p>
        </td></tr>
        <tr><td style="background:#f8fafc;padding:16px 32px;border-top:1px solid #e2e8f0;">
          <p style="margin:0;font-size:11px;color:#94a3b8;">Zenius ScreenPro &middot; Institutional Equity Screener &amp; Analytics</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

        logger.info(f"[EmailService] Verification OTP code generated for '{to_email}': {code}")
        _write_otp_admin_log("SIGNUP_VERIFICATION", to_email, code)
        threading.Thread(
            target=_dispatch_smtp,
            args=(to_email, subject, plain_body, html_body),
            daemon=True,
        ).start()

    def send_password_reset_email(
        self, to_email: str, code: str, full_name: Optional[str] = None
    ) -> None:
        """Dispatch 6-digit password reset OTP to a verified corporate user."""
        display_name = full_name.strip() if full_name else to_email.split("@")[0]
        subject      = "Zenius ScreenPro - Password Reset Code"

        plain_body = (
            f"Hello {display_name},\n\n"
            f"We received a request to reset your Zenius ScreenPro account password.\n\n"
            f"Your 6-digit authorization code is:\n\n"
            f"  {code}\n\n"
            f"This code expires in 15 minutes.\n"
            f"If you did not request this, please ignore this email.\n\n"
            f"-- Zenius ScreenPro"
        )

        html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f6f9;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f6f9;padding:32px 0;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;">
        <tr><td style="background:#147b73;padding:20px 32px;">
          <p style="margin:0;font-size:18px;font-weight:bold;color:#ffffff;">Zenius ScreenPro</p>
          <p style="margin:4px 0 0;font-size:12px;color:#a7d7d4;">Password Reset Request</p>
        </td></tr>
        <tr><td style="padding:32px;">
          <p style="margin:0 0 8px;font-size:15px;color:#1e293b;">Hello <strong>{html.escape(display_name)}</strong>,</p>
          <p style="margin:0 0 24px;font-size:14px;color:#475569;line-height:1.6;">
            We received a request to reset your <strong>Zenius ScreenPro</strong> password. Your authorization code is:
          </p>
          <div style="text-align:center;margin:0 0 24px;">
            <span style="display:inline-block;font-size:32px;font-weight:bold;
                         font-family:'Courier New',Courier,monospace;letter-spacing:8px;
                         color:#b45309;background:#fefce8;
                         padding:12px 24px;border-radius:6px;border:2px solid #ca8a04;">
              {code}
            </span>
          </div>
          <p style="margin:0 0 8px;font-size:13px;color:#64748b;line-height:1.6;">
            This code expires in <strong>15 minutes</strong>.
            Enter it on the password reset screen to set a new password.
          </p>
          <p style="margin:0;font-size:12px;color:#94a3b8;">If you did not request this change, you can safely ignore this email.</p>
        </td></tr>
        <tr><td style="background:#f8fafc;padding:16px 32px;border-top:1px solid #e2e8f0;">
          <p style="margin:0;font-size:11px;color:#94a3b8;">Zenius ScreenPro &middot; Institutional Equity Screener &amp; Analytics</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

        logger.info(f"[EmailService] Password reset OTP generated for '{to_email}': {code}")
        _write_otp_admin_log("PASSWORD_RESET", to_email, code)
        threading.Thread(
            target=_dispatch_smtp,
            args=(to_email, subject, plain_body, html_body),
            daemon=True,
        ).start()


# Global singleton instance
email_service = EmailService()
