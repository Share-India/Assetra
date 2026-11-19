import os
import smtplib
import logging
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from dotenv import load_dotenv

logger = logging.getLogger("email_service")

# Test mailbox for development and automated testing
_test_mailbox: Dict[str, Dict[str, Any]] = {}
_IS_TEST_MODE: bool = False

def set_test_mode(enabled: bool = True):
    """Enable or disable test mode for automated test suites."""
    global _IS_TEST_MODE
    _IS_TEST_MODE = enabled

def is_test_mode() -> bool:
    global _IS_TEST_MODE
    return _IS_TEST_MODE or os.getenv("TESTING", "").strip().lower() == "true"

def get_smtp_config():
    # Always load fresh configuration from backend/.env so runtime changes are picked up immediately
    backend_dir = Path(__file__).resolve().parent
    env_file = backend_dir / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file, override=True)

    return {
        "host": os.getenv("SMTP_HOST", "").strip(),
        "port": int(os.getenv("SMTP_PORT", "587").strip()),
        "security": os.getenv("SMTP_SECURITY", "starttls").strip().lower(),
        "timeout": int(os.getenv("SMTP_TIMEOUT", "10").strip()),
        "user": os.getenv("SMTP_USER", "").strip(),
        "password": os.getenv("SMTP_PASSWORD", "").strip(),
        "mail_from": os.getenv("MAIL_FROM", "noreply@farcalculator.com").strip(),
        "mail_reply_to": os.getenv("MAIL_REPLY_TO", os.getenv("MAIL_FROM", "noreply@farcalculator.com")).strip(),
        "sender_name": os.getenv("MAIL_SENDER_NAME", "ASSETRA").strip(),
        "frontend_url": os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/"),
        "env": os.getenv("ENV", "development").strip().lower()
    }

def send_email(to_email: str, subject: str, text_content: str, html_content: Optional[str] = None) -> bool:
    """
    Sends an email using configured SMTP settings.
    Supports STARTTLS (port 587), SSL (port 465), and timeouts.
    Never logs secret tokens or passwords.
    """
    to_email_clean = to_email.strip().lower()
    config = get_smtp_config()

    # Always record into the test mailbox for test assertion
    _test_mailbox[to_email_clean] = {
        "to": to_email_clean,
        "subject": subject,
        "text": text_content,
        "html": html_content
    }

    # If automated unit test mode is enabled, record and return success
    if is_test_mode():
        logger.info("Test mode active: Email recorded to test mailbox for: %s", to_email_clean)
        return True

    # If SMTP is not configured, do not pretend email was sent!
    if not config["host"]:
        logger.error(
            "Failed to send email to %s: SMTP_HOST is not configured in backend/.env",
            to_email_clean
        )
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    sender_header = f'"{config["sender_name"]}" <{config["mail_from"]}>' if config["sender_name"] else config["mail_from"]
    msg["From"] = sender_header
    msg["Reply-To"] = config["mail_reply_to"] if config["mail_reply_to"] else config["mail_from"]
    msg["To"] = to_email_clean

    part1 = MIMEText(text_content, "plain")
    msg.attach(part1)
    if html_content:
        part2 = MIMEText(html_content, "html")
        msg.attach(part2)

    envelope_from = config["user"] if config["user"] else config["mail_from"]

    try:
        if config["security"] == "ssl" or config["port"] == 465:
            with smtplib.SMTP_SSL(config["host"], config["port"], timeout=config["timeout"]) as server:
                server.ehlo()
                if config["user"] and config["password"]:
                    server.login(config["user"], config["password"])
                server.sendmail(envelope_from, [to_email_clean], msg.as_string())
        else:
            with smtplib.SMTP(config["host"], config["port"], timeout=config["timeout"]) as server:
                server.ehlo()
                if config["security"] == "starttls" or config["port"] == 587:
                    server.starttls()
                    server.ehlo()
                if config["user"] and config["password"]:
                    server.login(config["user"], config["password"])
                server.sendmail(envelope_from, [to_email_clean], msg.as_string())

        logger.info("Email successfully sent via SMTP to: %s", to_email_clean)
        return True
    except Exception as e:
        err_str = str(e)
        if config["password"] and config["password"] in err_str:
            err_str = err_str.replace(config["password"], "[MASKED_PASSWORD]")
        logger.error("Failed to send email via SMTP to %s: %s", to_email_clean, err_str)
        return False

def send_verification_code_email(to_email: str, code: str) -> bool:
    """Send a 6-digit email verification code expiring in 15 minutes with both plain-text and HTML."""
    to_email_clean = to_email.strip().lower()
    config = get_smtp_config()
    subject = "ASSETRA - Your Verification Code"

    text = (
        f"Hello,\n\n"
        f"Thank you for signing up for ASSETRA.\n"
        f"Your 6-digit email verification code is:\n\n"
        f"    {code}\n\n"
        f"This code will expire in 15 minutes (maximum 5 attempts).\n"
        f"If you did not request this verification, you can safely ignore this email.\n\n"
        f"— ASSETRA Team"
    )

    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="border-bottom: 2px solid #2563eb; padding-bottom: 12px; margin-bottom: 20px;">
          <h2 style="color: #1e3a8a; margin: 0;">ASSETRA</h2>
        </div>
        <p>Hello,</p>
        <p>Thank you for creating your account. Please use the 6-digit verification code below to verify your email address:</p>
        <div style="background-color: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 8px; padding: 18px; text-align: center; margin: 24px 0;">
          <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #1e3e62; font-family: monospace;">{code}</span>
        </div>
        <p style="font-size: 13px; color: #64748b; margin-bottom: 6px;">
          • This code is valid for <strong>15 minutes</strong>.<br/>
          • For security, you have a maximum of 5 attempts.
        </p>
        <p style="font-size: 13px; color: #94a3b8; margin-top: 24px; border-top: 1px solid #e2e8f0; padding-top: 12px;">
          If you did not sign up for ASSETRA, please ignore this email.
        </p>
      </body>
    </html>
    """

    # Development-only fallback logging (never log secret codes or tokens)
    if not config["host"] and config["env"] == "development":
        logger.info("Development mode (no SMTP host): verification code generated for %s", to_email_clean)

    result = send_email(to_email_clean, subject, text, html)
    if to_email_clean in _test_mailbox:
        _test_mailbox[to_email_clean]["code"] = code
    return result

def send_password_reset_otp_email(to_email: str, otp: str) -> bool:
    """Send a 6-digit One-Time Password (OTP) for password reset expiring in 10 minutes (NO links or URLs)."""
    to_email_clean = to_email.strip().lower()
    config = get_smtp_config()
    subject = "Share India ASSETRA - Password Reset OTP"

    text = (
        f"Hello,\n\n"
        f"We received a request to reset your password for your Share India ASSETRA account.\n\n"
        f"Your 6-digit One-Time Password (OTP) is:\n\n"
        f"    {otp}\n\n"
        f"This OTP will expire in 10 minutes.\n"
        f"Please enter this code on the password reset screen to set your new password.\n\n"
        f"For your security, never share this code with anyone.\n"
        f"If you did not request a password reset, you can safely ignore this email.\n\n"
        f"— Share India Insurance Team"
    )

    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #1e293b; max-width: 580px; margin: 0 auto; padding: 24px; background-color: #f8fafc;">
        <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
          <div style="border-bottom: 2px solid #0284c7; padding-bottom: 16px; margin-bottom: 24px; text-align: center;">
            <h2 style="color: #0f172a; margin: 0; font-size: 20px; font-weight: 700;">Share India Insurance</h2>
            <p style="color: #64748b; margin: 4px 0 0; font-size: 13px;">ASSETRA Replacement Value Calculator</p>
          </div>
          
          <h3 style="color: #0f172a; font-size: 17px; margin-top: 0;">Password Reset Verification Code</h3>
          <p style="color: #475569; font-size: 14px;">We received a request to reset the password for your account. Use the 6-digit One-Time Password (OTP) below to complete your password reset:</p>
          
          <div style="margin: 28px 0; text-align: center;">
            <div style="display: inline-block; background-color: #f0fdf4; border: 2px dashed #22c55e; border-radius: 10px; padding: 14px 28px;">
              <span style="font-family: monospace, Consolas, sans-serif; font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #15803d;">
                {otp}
              </span>
            </div>
            <div style="font-size: 12px; color: #dc2626; font-weight: 600; margin-top: 10px;">
              Expires in 10 minutes
            </div>
          </div>
          
          <p style="font-size: 13px; color: #64748b; line-height: 1.5;">
            Enter this 6-digit OTP on the password reset screen along with your new password. For security, never share this code with anyone.
          </p>
          <p style="font-size: 12px; color: #94a3b8; margin-top: 24px; border-top: 1px solid #e2e8f0; padding-top: 16px;">
            If you did not request this password reset, your account is safe and you can ignore this email.
          </p>
        </div>
      </body>
    </html>
    """

    if not config["host"] and config["env"] == "development":
        logger.info("Development mode (no SMTP host): password reset OTP %s generated for %s", otp, to_email_clean)

    result = send_email(to_email_clean, subject, text, html)
    if to_email_clean in _test_mailbox:
        _test_mailbox[to_email_clean]["otp"] = otp
        _test_mailbox[to_email_clean]["token"] = otp
    return result

def send_password_reset_email(to_email: str, token_or_otp: str) -> bool:
    """Backward compatible wrapper that sends the 6-digit OTP without links."""
    return send_password_reset_otp_email(to_email, token_or_otp)

def send_account_deletion_email(to_email: str, name: str) -> bool:
    """Send confirmation email that an account has been permanently deleted."""
    to_email_clean = to_email.strip().lower()
    subject = "ASSETRA - Account Deleted"
    text = (
        f"Hello {name},\n\n"
        f"Your ASSETRA account and all associated analyses and data have been permanently deleted as requested.\n"
        f"In accordance with our retention policy, existing system backups are kept for the retention period and will expire automatically.\n\n"
        f"Thank you for using ASSETRA."
    )
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #dc2626;">Account Permanently Deleted</h2>
        <p>Hello {name},</p>
        <p>Your ASSETRA account and all associated analyses and calculation rows have been permanently deleted from our systems as requested.</p>
        <p style="font-size: 13px; color: #64748b;">In accordance with our retention policy, system backups are maintained for the configured retention period and expire automatically.</p>
        <p>Thank you for using ASSETRA.</p>
      </body>
    </html>
    """
    return send_email(to_email_clean, subject, text, html)

def get_last_test_email(to_email: str) -> Optional[Dict[str, Any]]:
    """Helper for automated tests to retrieve the latest message for an email."""
    return _test_mailbox.get(to_email.strip().lower())

def clear_test_mailbox():
    """Helper for testing to reset mailbox."""
    _test_mailbox.clear()
