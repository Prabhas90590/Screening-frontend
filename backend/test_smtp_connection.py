"""Quick interactive / automated SMTP connectivity tester for Outlook.

Reads settings from backend/.env and tests:
  1. DNS resolution of SMTP host (smtp.office365.com).
  2. TCP socket connection on port 587.
  3. TLS handshake negotiation (STARTTLS).
  4. Authentication with SMTP_USER and SMTP_PASSWORD.
  5. Sends a lightweight test confirmation email to EMAIL_TO.
"""

from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import sys

from app.core.config import settings


def test_smtp_connection():
    print("=" * 70)
    print("OUTLOOK / MICROSOFT 365 SMTP DIAGNOSTIC TEST")
    print("=" * 70)

    print(f"SMTP Host:      {settings.smtp_host}")
    print(f"SMTP Port:      {settings.smtp_port}")
    print(f"Use TLS:        {settings.smtp_use_tls}")
    print(f"Sender (From):  {settings.smtp_user or '<NOT CONFIGURED IN .env>'}")
    print(f"Recipient (To): {settings.email_to or '<NOT CONFIGURED IN .env>'}")
    print("-" * 70)

    if not settings.smtp_user or not settings.smtp_password:
        print("[NOTICE] SMTP_USER or SMTP_PASSWORD is not set in backend/.env.")
        print("Please edit backend/.env with your Outlook email and password / App Password.")
        print("Until configured, the system safely archives all emails & Excel files to:")
        print("  backend/logs/sent_emails/\n")
        return

    if not settings.email_to:
        print("[NOTICE] EMAIL_TO is not set in backend/.env.")
        print("Please set EMAIL_TO in backend/.env to your manager's email (or your own for testing).\n")
        return

    try:
        print(f"1. Connecting to {settings.smtp_host}:{settings.smtp_port}...")
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)

        if settings.smtp_use_tls:
            print("2. Initiating STARTTLS handshake...")
            server.starttls()

        print(f"3. Authenticating as '{settings.smtp_user}'...")
        server.login(settings.smtp_user, settings.smtp_password)
        print("   [SUCCESS] Authentication accepted by Microsoft 365!")

        print(f"4. Dispatching test email to '{settings.email_to}'...")
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "✅ [TEST CONFIRMATION] Screening Platform Outlook SMTP Connected"
        msg["From"] = settings.email_from
        msg["To"] = settings.email_to

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; color: #1e293b;">
            <h2 style="color: #065f46;">✅ Outlook SMTP Successfully Connected</h2>
            <p>This confirms that the <strong>Institutional Equity Screening Platform</strong> can send automated screening notifications and Excel reports from your Outlook account.</p>
            <ul>
                <li><strong>Sender:</strong> {settings.smtp_user}</li>
                <li><strong>Recipient:</strong> {settings.email_to}</li>
                <li><strong>Timestamp:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</li>
            </ul>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_body, "html", "utf-8"))
        server.send_message(msg)
        server.quit()

        print(f"   [SUCCESS] Test email delivered to '{settings.email_to}'!")
        print("\n" + "=" * 70)
        print("OUTLOOK SMTP TEST PASSED COMPLETELY")
        print("=" * 70)
    except smtplib.SMTPAuthenticationError as auth_err:
        print("\n[AUTHENTICATION FAILED]")
        print(f"Microsoft rejected credentials: {auth_err}")
        print("\nTip: If you have 2-Factor Authentication enabled on your Outlook account,")
        print("you must use a 16-character Microsoft App Password instead of your normal password.")
        print("Generate one at: https://account.microsoft.com/security")
    except Exception as e:
        print(f"\n[ERROR] Connection failed: {e}")


if __name__ == "__main__":
    test_smtp_connection()
