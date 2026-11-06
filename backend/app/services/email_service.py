"""Corporate Email Notification Service for Authentication.

Handles secure dispatch of:
1. 6-digit Email Verification Codes for corporate self-registration (@zeniusit.com).
2. 6-digit Authenticated Password Reset Codes.

Implements standard multi-part email (plain text + HTML) for maximum deliverability
and inbox placement across corporate mail filters (including Microsoft 365 Exchange).
"""

from datetime import datetime, timezone
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import html
import logging
from pathlib import Path
import smtplib
import threading
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("app.services.email")

SENT_EMAILS_DIR = Path(__file__).resolve().parent.parent.parent / "logs" / "sent_emails"


class EmailService:
    """Enterprise email dispatcher for account verification and password reset."""

    def __init__(self):
        try:
            SENT_EMAILS_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def _save_to_disk(self, subject: str, recipient: str, html_body: str) -> None:
        """Archive email to disk for developer diagnostics and auditing."""
        try:
            safe_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            safe_user = recipient.replace("@", "_at_").replace(".", "_")
            filepath = SENT_EMAILS_DIR / f"{safe_ts}_{safe_user}.html"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"<!-- Subject: {subject} -->\n<!-- To: {recipient} -->\n{html_body}")
        except Exception as e:
            logger.warning(f"Could not archive email to disk: {e}")

    def _dispatch_smtp(self, recipient: str, subject: str, plain_body: str, html_body: str) -> bool:
        """Synchronously send multi-part email via SMTP with RFC-compliant headers."""
        # Archive to disk for diagnostic audit trail
        self._save_to_disk(subject, recipient, html_body)

        if not (settings.smtp_host and settings.smtp_user and settings.smtp_password):
            logger.warning(
                f"[EmailService] Live SMTP credentials not configured in .env. Email for '{recipient}' archived to disk."
            )
            return False

        try:
            # Construct multi-part alternative message (plain-text + HTML for anti-spam deliverability)
            msg = MIMEMultipart("alternative")
            msg["Subject"] = Header(subject, "utf-8")
            msg["From"] = settings.email_from or f"Zenius ScreenPro <{settings.smtp_user}>"
            msg["To"] = recipient
            msg["Date"] = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

            # 1. Plain text fallback
            part_plain = MIMEText(plain_body, "plain", "utf-8")
            msg.attach(part_plain)

            # 2. Rich HTML version
            part_html = MIMEText(html_body, "html", "utf-8")
            msg.attach(part_html)

            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
            if settings.smtp_use_tls:
                server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
            server.quit()

            logger.info(f"[EmailService] Successfully delivered verification email to {recipient} via SMTP.")
            return True
        except Exception as e:
            logger.error(
                f"[EmailService] SMTP delivery failed for '{recipient}': {e}. Archived to logs/sent_emails/."
            )
            return False

    def send_verification_email(self, to_email: str, code: str, full_name: Optional[str] = None) -> None:
        """Send a 6-digit verification code to activate a new corporate @zeniusit.com account."""
        display_name = full_name.strip() if full_name else to_email.split("@")[0]
        subject = f"Zenius ScreenPro: Corporate Verification Code is {code}"

        plain_body = f"""Hello {display_name},

Your 6-digit corporate verification code for Zenius ScreenPro is: {code}

This code expires in 15 minutes. Enter this code to verify your corporate email and activate your account.

---
Zenius ScreenPro · Institutional Equity Screener & Analytics
"""

        html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; line-height: 1.5; padding: 20px;">
    <h2 style="color: #147b73; margin-top: 0; font-size: 20px;">Zenius ScreenPro</h2>
    <p>Hello <strong>{html.escape(display_name)}</strong>,</p>
    <p>Your 6-digit corporate verification code is:</p>
    <div style="margin: 20px 0;">
        <span style="font-size: 28px; font-weight: bold; font-family: monospace; letter-spacing: 4px; color: #147b73; background: #e6f4f2; padding: 8px 16px; border-radius: 6px; border: 1px solid #147b73;">
            {code}
        </span>
    </div>
    <p style="font-size: 13px; color: #64748b;">This code expires in 15 minutes. Enter this code in your browser to verify your corporate email and activate your account.</p>
    <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;" />
    <p style="font-size: 11px; color: #94a3b8;">Zenius ScreenPro &middot; Institutional Equity Screener & Analytics</p>
</body>
</html>"""

        logger.info(f"[EmailService] Verification OTP code generated for '{to_email}': {code}")
        threading.Thread(
            target=self._dispatch_smtp,
            args=(to_email, subject, plain_body, html_body),
            daemon=True,
        ).start()

    def send_password_reset_email(self, to_email: str, code: str, full_name: Optional[str] = None) -> None:
        """Send a 6-digit password reset code to a verified corporate user."""
        display_name = full_name.strip() if full_name else to_email.split("@")[0]
        subject = f"Zenius ScreenPro: Password Reset Code is {code}"

        plain_body = f"""Hello {display_name},

We received a request to reset your Zenius ScreenPro account password.

Your 6-digit authorization code is: {code}

This code expires in 15 minutes. Enter this code on the password reset screen to set a new password.

---
Zenius ScreenPro · Institutional Equity Screener & Analytics
"""

        html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; line-height: 1.5; padding: 20px;">
    <h2 style="color: #147b73; margin-top: 0; font-size: 20px;">Zenius ScreenPro</h2>
    <p>Hello <strong>{html.escape(display_name)}</strong>,</p>
    <p>We received a request to reset your password. Your 6-digit authorization code is:</p>
    <div style="margin: 20px 0;">
        <span style="font-size: 28px; font-weight: bold; font-family: monospace; letter-spacing: 4px; color: #b45309; background: #fefce8; padding: 8px 16px; border-radius: 6px; border: 1px solid #ca8a04;">
            {code}
        </span>
    </div>
    <p style="font-size: 13px; color: #64748b;">This code expires in 15 minutes. If you did not request this change, please ignore this email.</p>
    <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;" />
    <p style="font-size: 11px; color: #94a3b8;">Zenius ScreenPro &middot; Institutional Equity Screener & Analytics</p>
</body>
</html>"""

        logger.info(f"[EmailService] Password reset OTP generated for '{to_email}': {code}")
        threading.Thread(
            target=self._dispatch_smtp,
            args=(to_email, subject, plain_body, html_body),
            daemon=True,
        ).start()


# Global singleton instance
email_service = EmailService()
