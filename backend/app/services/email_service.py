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
        subject = f"Zenius ScreenPro: Your Verification Code is {code}"

        plain_body = f"""Hello {display_name},

A new analyst account registration was requested for {to_email} on the Zenius ScreenPro institutional equity platform.

Your 6-digit verification code is: {code}

This code expires in 15 minutes. Please enter it on the verification screen to activate your account.

If you did not initiate this request, no action is needed. Zenius ScreenPro is strictly restricted to authorized @zeniusit.com analysts.

---
Zenius ScreenPro · Institutional Equity Screener & Analytics
"""

        html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f3f6f9; margin: 0; padding: 28px; color: #1e293b;">
    <div style="max-width: 540px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
        <!-- Institutional Header Banner -->
        <div style="background-color: #147b73; padding: 24px; color: #ffffff; text-align: center;">
            <div style="display: inline-block; width: 38px; height: 38px; line-height: 38px; background-color: #e5a420; color: #0d1c31; font-weight: bold; font-size: 18px; border-radius: 8px; margin-bottom: 8px;">
                Z
            </div>
            <h1 style="margin: 0; font-size: 20px; font-weight: 700; letter-spacing: -0.02em;">Zenius ScreenPro</h1>
            <p style="margin: 4px 0 0 0; font-size: 11px; opacity: 0.9; text-transform: uppercase; letter-spacing: 0.08em;">Corporate Email Verification</p>
        </div>

        <!-- Body Content -->
        <div style="padding: 28px 24px;">
            <p style="font-size: 14px; margin-top: 0; color: #334155;">
                Hello <strong>{html.escape(display_name)}</strong>,
            </p>
            <p style="font-size: 13px; line-height: 1.5; color: #475569;">
                A new analyst account registration was requested for <strong>{html.escape(to_email)}</strong> on the Zenius ScreenPro institutional platform.
            </p>
            <p style="font-size: 13px; line-height: 1.5; color: #475569;">
                Please enter the following 6-digit verification code in your browser to confirm your identity and activate your account:
            </p>

            <!-- Code Display Card -->
            <div style="margin: 24px 0; text-align: center;">
                <div style="display: inline-block; background-color: #f0fdfa; border: 2px dashed #147b73; border-radius: 10px; padding: 14px 28px;">
                    <span style="font-family: 'Courier New', Courier, monospace; font-size: 32px; font-weight: 800; letter-spacing: 0.35em; color: #0f675f; margin-left: 0.35em;">
                        {code}
                    </span>
                </div>
                <div style="font-size: 11px; color: #64748b; margin-top: 8px;">
                    This code expires in <strong>15 minutes</strong>.
                </div>
            </div>

            <div style="background-color: #f8fafc; border-left: 3px solid #147b73; padding: 10px 14px; margin: 20px 0; font-size: 12px; color: #475569; line-height: 1.4;">
                <strong>Security Notice:</strong> Zenius ScreenPro is strictly restricted to authorized <code>@zeniusit.com</code> analysts. If you did not initiate this request, no action is needed and the account will remain locked.
            </div>
        </div>

        <!-- Footer -->
        <div style="background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 14px 24px; font-size: 11px; color: #94a3b8; text-align: center;">
            Zenius ScreenPro · Institutional Equity Screener & Analytics
        </div>
    </div>
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
        subject = f"Zenius ScreenPro: Your Password Reset Code is {code}"

        plain_body = f"""Hello {display_name},

We received a request to reset the password for your Zenius ScreenPro account ({to_email}).

Your 6-digit authorization code is: {code}

This code expires in 15 minutes. Enter this code on the password reset screen to set a new password.

If you did not request a password reset, please notify security or your IT administrator immediately.

---
Zenius ScreenPro · Institutional Equity Screener & Analytics
"""

        html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f3f6f9; margin: 0; padding: 28px; color: #1e293b;">
    <div style="max-width: 540px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
        <!-- Institutional Header Banner -->
        <div style="background-color: #147b73; padding: 24px; color: #ffffff; text-align: center;">
            <div style="display: inline-block; width: 38px; height: 38px; line-height: 38px; background-color: #e5a420; color: #0d1c31; font-weight: bold; font-size: 18px; border-radius: 8px; margin-bottom: 8px;">
                Z
            </div>
            <h1 style="margin: 0; font-size: 20px; font-weight: 700; letter-spacing: -0.02em;">Zenius ScreenPro</h1>
            <p style="margin: 4px 0 0 0; font-size: 11px; opacity: 0.9; text-transform: uppercase; letter-spacing: 0.08em;">Password Reset Authorization</p>
        </div>

        <!-- Body Content -->
        <div style="padding: 28px 24px;">
            <p style="font-size: 14px; margin-top: 0; color: #334155;">
                Hello <strong>{html.escape(display_name)}</strong>,
            </p>
            <p style="font-size: 13px; line-height: 1.5; color: #475569;">
                We received a request to reset the password for your Zenius ScreenPro account (<strong>{html.escape(to_email)}</strong>).
            </p>
            <p style="font-size: 13px; line-height: 1.5; color: #475569;">
                Enter the following 6-digit authorization code on the password reset screen to set a new password:
            </p>

            <!-- Code Display Card -->
            <div style="margin: 24px 0; text-align: center;">
                <div style="display: inline-block; background-color: #fefce8; border: 2px dashed #ca8a04; border-radius: 10px; padding: 14px 28px;">
                    <span style="font-family: 'Courier New', Courier, monospace; font-size: 32px; font-weight: 800; letter-spacing: 0.35em; color: #854d0e; margin-left: 0.35em;">
                        {code}
                    </span>
                </div>
                <div style="font-size: 11px; color: #64748b; margin-top: 8px;">
                    This code expires in <strong>15 minutes</strong>.
                </div>
            </div>

            <div style="background-color: #fef2f2; border-left: 3px solid #ef4444; padding: 10px 14px; margin: 20px 0; font-size: 12px; color: #991b1b; line-height: 1.4;">
                <strong>Important:</strong> If you did not request this password reset, please contact security immediately. Your existing password remains secure until this code is verified.
            </div>
        </div>

        <!-- Footer -->
        <div style="background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 14px 24px; font-size: 11px; color: #94a3b8; text-align: center;">
            Zenius ScreenPro · Institutional Equity Screener & Analytics
        </div>
    </div>
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
