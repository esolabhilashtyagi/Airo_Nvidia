from app.core.config import settings
from app.services import email_delivery
from app.services.email_delivery import email_delivery_is_configured, send_password_reset_email


def test_password_reset_email_uses_configured_smtp_and_secure_transport(monkeypatch):
    calls = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            calls.append(("connect", host, port, timeout))

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def ehlo(self):
            calls.append(("ehlo",))

        def starttls(self, context):
            calls.append(("starttls", context))

        def login(self, username, password):
            calls.append(("login", username, password))

        def send_message(self, message):
            calls.append(("message", message))

    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(settings, "SMTP_USERNAME", "mailer@example.test")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "test-only-secret")
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "AAIRO <no-reply@example.test>")
    monkeypatch.setattr(settings, "SMTP_USE_SSL", False)
    monkeypatch.setattr(settings, "SMTP_STARTTLS", True)
    monkeypatch.setattr(settings, "SMTP_TIMEOUT_SECONDS", 15)
    monkeypatch.setattr(email_delivery.smtplib, "SMTP", FakeSMTP)

    assert email_delivery_is_configured()
    send_password_reset_email("candidate@example.test", "https://aairo.example/reset-password?token=test-token")

    sent_message = next(call[1] for call in calls if call[0] == "message")
    assert sent_message["To"] == "candidate@example.test"
    assert "Reset your AAIRO password" in sent_message["Subject"]
    assert "https://aairo.example/reset-password?token=test-token" in sent_message.get_content()
    assert any(call[0] == "starttls" for call in calls)
    assert any(call[0] == "login" and call[2] == "test-only-secret" for call in calls)


def test_password_reset_email_provider_is_unavailable_without_required_settings(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "")
    assert not email_delivery_is_configured()
