import os
import secrets
import smtplib
from email.message import EmailMessage


class EmailServiceError(Exception):
    pass


def _first_env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return default


SMTP_HOST = _first_env("SMTP_HOST", "EMAIL_HOST", default="smtp.gmail.com")
SMTP_PORT = int(_first_env("SMTP_PORT", "EMAIL_PORT", default="587"))
SMTP_USERNAME = _first_env(
    "SMTP_USERNAME",
    "SMTP_USER",
    "GMAIL_EMAIL",
    "EMAIL_ADDRESS",
    "EMAIL_HOST_USER",
    "MAIL_USERNAME",
)
SMTP_PASSWORD = _first_env(
    "SMTP_PASSWORD",
    "GMAIL_APP_PASSWORD",
    "EMAIL_PASSWORD",
    "EMAIL_HOST_PASSWORD",
    "MAIL_PASSWORD",
)
SMTP_FROM_EMAIL = _first_env("SMTP_FROM_EMAIL", default=SMTP_USERNAME).strip()
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Step").strip()
APP_NAME = os.getenv("APP_NAME", "Step").strip()


def generate_verification_otp() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def send_verification_email(recipient_email: str, otp_code: str) -> None:
    if not SMTP_USERNAME or not SMTP_PASSWORD or not SMTP_FROM_EMAIL:
        raise EmailServiceError(
            "SMTP credentials are missing. Set SMTP_USERNAME, SMTP_PASSWORD, and SMTP_FROM_EMAIL."
        )
    if SMTP_PORT != 587:
        raise EmailServiceError("Gmail SMTP must use port 587 with TLS.")

    message = EmailMessage()
    message["Subject"] = f"{APP_NAME} verification code"
    message["From"] = (
        f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        if SMTP_FROM_NAME
        else SMTP_FROM_EMAIL
    )
    message["To"] = recipient_email
    message.set_content(f"Your verification code is: {otp_code}")

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
            smtp.send_message(message)
    except Exception as exc:
        raise EmailServiceError(f"Failed to send verification email: {exc}") from exc
