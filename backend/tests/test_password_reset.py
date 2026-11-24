from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import HTTPException

from app.models.system import PasswordResetToken
from app.services import auth_service
from app.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_password_reset_request_stores_only_hash_and_sends_one_time_link(monkeypatch, caplog):
    user = SimpleNamespace(id="user-1", email="person@example.com", is_active=True)
    db = SimpleNamespace(
        scalar=AsyncMock(return_value=user), execute=AsyncMock(), commit=AsyncMock(), add=MagicMock(),
    )
    delivered = []
    monkeypatch.setattr(auth_service, "email_delivery_is_configured", lambda: True)
    monkeypatch.setattr(auth_service, "send_password_reset_email", lambda recipient, url: delivered.append((recipient, url)))
    monkeypatch.setattr(auth_service.AuthRateLimiter, "ensure_allowed", AsyncMock())
    monkeypatch.setattr(auth_service.AuthRateLimiter, "record_attempt", AsyncMock())
    monkeypatch.setattr(auth_service.settings, "FRONTEND_BASE_URL", "https://aairo.example")
    caplog.set_level("INFO", logger="aairo.auth")

    assert await AuthService.request_password_reset(db, " Person@example.com ") is True

    assert db.execute.await_count == 1
    assert db.commit.await_count == 1
    auth_service.AuthRateLimiter.ensure_allowed.assert_awaited_once()
    stored = db.add.call_args.args[0]
    assert isinstance(stored, PasswordResetToken)
    assert stored.user_id == "user-1"
    assert len(stored.token_hash) == 64
    assert delivered[0][0] == user.email
    url = urlsplit(delivered[0][1])
    raw_token = parse_qs(url.fragment)["token"][0]
    assert url.path == "/reset-password"
    assert AuthService._reset_token_hash(raw_token) == stored.token_hash
    assert raw_token != stored.token_hash
    assert "accepted by configured SMTP server" in caplog.text


@pytest.mark.asyncio
async def test_password_reset_request_logs_generic_skip_for_unknown_account(monkeypatch, caplog):
    db = SimpleNamespace(scalar=AsyncMock(return_value=None), execute=AsyncMock(), commit=AsyncMock(), add=MagicMock())
    send_email = MagicMock()
    monkeypatch.setattr(auth_service, "email_delivery_is_configured", lambda: True)
    monkeypatch.setattr(auth_service, "send_password_reset_email", send_email)
    monkeypatch.setattr(auth_service.AuthRateLimiter, "ensure_allowed", AsyncMock())
    monkeypatch.setattr(auth_service.AuthRateLimiter, "record_attempt", AsyncMock())
    caplog.set_level("INFO", logger="aairo.auth")

    assert await AuthService.request_password_reset(db, "person@example.com") is True

    send_email.assert_not_called()
    db.commit.assert_not_awaited()
    assert "no active account matched" in caplog.text
    assert "person@example.com" not in caplog.text


@pytest.mark.asyncio
async def test_password_reset_is_single_use_and_revokes_sessions(monkeypatch):
    now = datetime.now(timezone.utc)
    token_row = SimpleNamespace(
        token_hash=AuthService._reset_token_hash("valid-token"), user_id="user-1",
        expires_at=now + timedelta(minutes=10), redeemed_at=None,
    )
    user = SimpleNamespace(id="user-1", hashed_password="old-hash", auth_token_version=2, is_active=True)
    db = SimpleNamespace(scalar=AsyncMock(side_effect=[token_row, user]), execute=AsyncMock(), commit=AsyncMock())
    monkeypatch.setattr(auth_service, "hash_password", lambda _password: "new-secure-hash")
    monkeypatch.setattr(auth_service.AuthRateLimiter, "ensure_allowed", AsyncMock())
    monkeypatch.setattr(auth_service.AuthRateLimiter, "record_attempt", AsyncMock())

    await AuthService.reset_password(db, "valid-token", "StrongNewPassword!42")

    assert user.hashed_password == "new-secure-hash"
    assert user.auth_token_version == 3
    assert token_row.redeemed_at is not None
    assert db.execute.await_count == 2
    assert db.commit.await_count == 1


@pytest.mark.asyncio
async def test_password_reset_rejects_expired_or_redeemed_token(monkeypatch):
    token_row = SimpleNamespace(
        token_hash=AuthService._reset_token_hash("old-token"), user_id="user-1",
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1), redeemed_at=None,
    )
    db = SimpleNamespace(scalar=AsyncMock(return_value=token_row), execute=AsyncMock(), commit=AsyncMock())
    monkeypatch.setattr(auth_service.AuthRateLimiter, "ensure_allowed", AsyncMock())
    monkeypatch.setattr(auth_service.AuthRateLimiter, "record_attempt", AsyncMock())

    with pytest.raises(HTTPException, match="invalid or expired") as error:
        await AuthService.reset_password(db, "old-token", "StrongNewPassword!42")

    assert error.value.status_code == 400
    db.execute.assert_not_awaited()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_password_reset_request_reports_missing_smtp_configuration(monkeypatch):
    db = SimpleNamespace(scalar=AsyncMock(), execute=AsyncMock(), commit=AsyncMock(), add=MagicMock())
    monkeypatch.setattr(auth_service, "email_delivery_is_configured", lambda: False)
    monkeypatch.setattr(auth_service.AuthRateLimiter, "ensure_allowed", AsyncMock())
    monkeypatch.setattr(auth_service.AuthRateLimiter, "record_attempt", AsyncMock())

    with pytest.raises(HTTPException, match="SMTP_HOST") as error:
        await AuthService.request_password_reset(db, "person@example.com")

    assert error.value.status_code == 503
    db.scalar.assert_not_awaited()
