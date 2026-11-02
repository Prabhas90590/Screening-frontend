"""Quick interactive / automated SMTP connectivity tester for Outlook and Gmail.

Reads settings from backend/.env and tests:
  1. DNS resolution of SMTP host.
  2. TLS / SSL handshake (supports Port 587 STARTTLS and Port 465 SSL with auto-fallback).
  3. Authentication with SMTP_USER and SMTP_PASSWORD.
  4. Sends a lightweight test confirmation email to EMAIL_TO.
"""

from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import ssl
import sys

from app.core.config import settings


def _connect_smtp(host: str, port: int, use_tls: bool):
    """Establish a robust connection with proper ehlo handshakes or SSL."""
    context = ssl.create_default_context()
    if port == 465:
        server = smtplib.SMTP_SSL(host, port, timeout=20, context=context)
        server.ehlo()
        return server
    else:
        server = smtplib.SMTP(host, port, timeout=20)
        server.ehlo()
        if use_tls:
            server.starttls(context=context)
            server.ehlo()
        return server


def test_smtp_connection():
    print("=" * 70)
    print("SMTP DIAGNOSTIC & CONNECTIVITY TEST")
    print("=" * 70)

    print(f"SMTP Host:      {settings.smtp_host}")
    print(f"SMTP Port:      {settings.smtp_port}")
    print(f"Use TLS:        {settings.smtp_use_tls}")
    print(f"Sender (From):  {settings.smtp_user or '<NOT CONFIGURED IN .env>'}")
    print(f"Recipient (To): {settings.email_to or '<NOT CONFIGURED IN .env>'}")
    print("-" * 70)

    if not settings.smtp_user or not settings.smtp_password:
        print("[NOTICE] SMTP_USER or SMTP_PASSWORD is not set in backend/.env.")
        print("Please edit backend/.env with your email and password / App Password.\n")
        return

    target_recipients = settings.email_to.strip() if settings.email_to else ""
    if not target_recipients:
        print("[NOTICE] EMAIL_TO is empty in backend/.env (using sender SMTP_USER as test recipient).")
        target_recipients = settings.smtp_user

    server = None
    try:
        print(f"1. Connecting to {settings.smtp_host}:{settings.smtp_port}...")
        try:
            server = _connect_smtp(settings.smtp_host, settings.smtp_port, settings.smtp_use_tls)
        except (smtplib.SMTPServerDisconnected, ConnectionResetError, OSError) as conn_err:
            if settings.smtp_port == 587:
                print(f"   [Notice: Port 587 closed ({conn_err}). Trying secure SSL on Port 465...]")
                server = _connect_smtp(settings.smtp_host, 465, True)
            else:
                raise conn_err

        print(f"2. Authenticating as '{settings.smtp_user}'...")
        server.login(settings.smtp_user, settings.smtp_password)
        print("   [SUCCESS] Authentication accepted by mail server!")

        recipients = [r.strip() for r in target_recipients.replace(";", ",").split(",") if r.strip()]
        print(f"3. Dispatching test email to {recipients}...")
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "✅ [TEST CONFIRMATION] Equity Screening Platform SMTP Connected"
        msg["From"] = settings.email_from
        msg["To"] = ", ".join(recipients)

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; color: #1e293b;">
            <h2 style="color: #065f46;">✅ SMTP Successfully Connected</h2>
            <p>This confirms that the <strong>Institutional Equity Screening Platform</strong> can send automated screening notifications and Excel reports from <code>{settings.smtp_user}</code>.</p>
            <ul>
                <li><strong>Sender:</strong> {settings.smtp_user}</li>
                <li><strong>Recipients:</strong> {', '.join(recipients)}</li>
                <li><strong>Host / Port:</strong> {settings.smtp_host}:{settings.smtp_port}</li>
                <li><strong>Timestamp:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</li>
            </ul>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_body, "html", "utf-8"))
        server.send_message(msg)
        server.quit()

        print(f"   [SUCCESS] Test email delivered to {recipients}!")
        print("\n" + "=" * 70)
        print("SMTP TEST PASSED COMPLETELY! Check your inbox.")
        print("=" * 70)
    except smtplib.SMTPAuthenticationError as auth_err:
        print("\n[AUTHENTICATION FAILED]")
        print(f"Mail server rejected credentials: {auth_err}")
        print("\nTip: For Gmail or Outlook with 2-Factor Authentication, you must use a")
        print("16-character App Password (not your normal web password).")
        print("  - Gmail: https://myaccount.google.com/apppasswords")
        print("  - Outlook: https://account.microsoft.com/security")
    except Exception as e:
        print(f"\n[ERROR] Connection failed: {e}")


if __name__ == "__main__":
    test_smtp_connection()
