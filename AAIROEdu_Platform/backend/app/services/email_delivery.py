"""Small SMTP adapter for transactional account email."""

import smtplib
import ssl
import logging
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger("aairo.email")


def email_delivery_is_configured() -> bool:
    return bool(settings.SMTP_HOST.strip() and settings.SMTP_FROM_EMAIL.strip())


def _send_email(message: EmailMessage) -> None:
    if not email_delivery_is_configured():
        raise RuntimeError("SMTP email delivery is not configured")

    message["From"] = settings.SMTP_FROM_EMAIL.strip()

    context = ssl.create_default_context()
    client_type = smtplib.SMTP_SSL if settings.SMTP_USE_SSL else smtplib.SMTP
    client_context = (
        client_type(settings.SMTP_HOST.strip(), settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS, context=context)
        if settings.SMTP_USE_SSL
        else client_type(settings.SMTP_HOST.strip(), settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS)
    )
    with client_context as client:
        client.ehlo()
        if settings.SMTP_STARTTLS and not settings.SMTP_USE_SSL:
            client.starttls(context=context)
            client.ehlo()
        if settings.SMTP_USERNAME.strip():
            client.login(settings.SMTP_USERNAME.strip(), settings.SMTP_PASSWORD)
        client.send_message(message)


def _message(recipient: str, subject: str, body: str) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = subject
    message["To"] = recipient
    message.set_content(body)
    return message


def send_password_reset_email(recipient: str, reset_url: str) -> None:
    """Send a reset link; exceptions are surfaced to the caller without secrets."""
    message = _message(
        recipient,
        "Reset your AAIRO password",
        "We received a request to reset your AAIRO password.\n\n"
        f"Use this one-time link within 30 minutes:\n{reset_url}\n\n"
        "If you did not request this, you can ignore this email. Your password will not change.",
    )
    _send_email(message)


def send_welcome_email(recipient: str, full_name: str) -> None:
    name = full_name.strip() or "there"
    onboarding_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/onboarding"
    message = _message(
        recipient,
        "Welcome to AAIRO",
        f"Hi {name},\n\n"
        "Welcome to AAIRO, your career learning and interview preparation platform. "
        "Your account is ready. You can sign in and explore your candidate dashboard.\n\n"
        f"Get started: {onboarding_url}\n\n"
        "We’re glad you’re here.\nThe AAIRO team",
    )
    _send_email(message)


def send_profile_incomplete_email(recipient: str, full_name: str) -> None:
    name = full_name.strip() or "there"
    onboarding_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/onboarding"
    message = _message(
        recipient,
        "Complete your AAIRO career profile",
        f"Hi {name},\n\n"
        "Your AAIRO profile is not complete yet. Finish the onboarding steps to personalize "
        "your career roadmap, learning recommendations, and practice experience.\n\n"
        f"Continue your profile: {onboarding_url}\n\n"
        "You can return to this link whenever you’re ready.\nThe AAIRO team",
    )
    _send_email(message)


def send_registration_emails(recipient: str, full_name: str, profile_complete: bool = False) -> None:
    """Deliver post-registration emails without making account creation depend on SMTP."""
    if not email_delivery_is_configured():
        logger.warning("Registration emails were not sent because SMTP is not configured")
        return

    emails = [("welcome", send_welcome_email)]
    if not profile_complete:
        emails.append(("profile completion", send_profile_incomplete_email))

    for label, send in emails:
        try:
            send(recipient, full_name)
        except Exception as exc:
            # The account is already committed; log only the failure class, never credentials or PII.
            logger.warning("Registration %s email delivery failed (%s)", label, type(exc).__name__)
