import json
import logging
import os
import secrets
import urllib.error
import urllib.request


class EmailServiceError(Exception):
    pass


logger = logging.getLogger("step.email")


def _first_env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return default


RESEND_API_URL = "https://api.resend.com/emails"
RESEND_API_KEY = _first_env(
    "RESEND_API_KEY",
    "RESEND_KEY",
    "RESEND_TOKEN",
    "EMAIL_API_KEY",
)
RESEND_FROM_EMAIL = _first_env(
    "RESEND_FROM_EMAIL",
    "FROM_EMAIL",
    "RESEND_FROM",
    "EMAIL_FROM",
    default="onboarding@resend.dev",
).strip()
RESEND_FROM_NAME = _first_env("RESEND_FROM_NAME", default="Step").strip()
APP_NAME = os.getenv("APP_NAME", "Step").strip()


def generate_verification_otp() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def _build_from_value() -> str:
    if RESEND_FROM_NAME:
        return f"{RESEND_FROM_NAME} <{RESEND_FROM_EMAIL}>"
    return RESEND_FROM_EMAIL


def send_verification_email(recipient_email: str, otp_code: str) -> None:
    if not RESEND_API_KEY:
        logger.error("Resend API key is missing")
        raise EmailServiceError(
            "Resend API key is missing. Set RESEND_API_KEY in Railway variables."
        )

    payload = {
        "from": _build_from_value(),
        "to": [recipient_email],
        "subject": f"{APP_NAME} verification code",
        "html": (
            "<div style=\"font-family:Arial,sans-serif;line-height:1.6\">"
            f"<h2>{APP_NAME}</h2>"
            f"<p>Your verification code is:</p><p style=\"font-size:28px;font-weight:bold\">{otp_code}</p>"
            "<p>This code expires soon.</p>"
            "</div>"
        ),
        "text": f"Your verification code is: {otp_code}",
    }

    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        RESEND_API_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "step-backend/1.0",
        },
    )

    try:
        logger.info(
            "Sending verification email via Resend to %s using from=%s",
            recipient_email,
            RESEND_FROM_EMAIL,
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8", errors="replace")
            logger.info("Resend email sent to %s: %s", recipient_email, raw)
    except urllib.error.HTTPError as exc:
        raw_error = exc.read().decode("utf-8", errors="replace")
        logger.exception(
            "Resend HTTP error while sending verification email to %s: %s",
            recipient_email,
            raw_error,
        )
        try:
            parsed = json.loads(raw_error)
            detail = parsed.get("message") or parsed.get("error") or raw_error
        except Exception:
            detail = raw_error or str(exc)
        raise EmailServiceError(f"Failed to send verification email: {detail}") from exc
    except Exception as exc:
        logger.exception("Unexpected Resend error for %s", recipient_email)
        raise EmailServiceError(f"Failed to send verification email: {exc}") from exc
