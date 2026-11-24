import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from jose import jwt
from pydantic import ValidationError
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.models.system import AuthAttemptLimit
from app.schemas.auth import ChangePasswordRequest, ResetPasswordRequest, UserLoginRequest, UserRegisterRequest
from app.services.auth_rate_limiter import AuthRateLimiter


_PASSWORD_REQUESTS = [
    (UserRegisterRequest, "password", {"email": "zz_test_boundary@example.com", "full_name": "zz_test Boundary"}),
    (UserLoginRequest, "password", {"email": "zz_test_boundary@example.com"}),
    (ResetPasswordRequest, "new_password", {"token": "synthetic-reset-token"}),
    (ChangePasswordRequest, "current_password", {"new_password": "ZzTestNewPassword456!"}),
    (ChangePasswordRequest, "new_password", {"current_password": "ZzTestOldPassword123!"}),
]
_PASSWORDS_AT_LIMIT = ["Zz9!Kx2@" + suffix for suffix in ("Q" * 64, "é" * 32, "𐐀" * 16)]
_OVERSIZED_PASSWORDS = ["Zz9!Kx2@" + "Q" * 65, "Zz9!Kx2@" + "é" * 33]


@pytest.mark.parametrize("schema,field,other_fields", _PASSWORD_REQUESTS)
@pytest.mark.parametrize("password", _OVERSIZED_PASSWORDS, ids=["ascii-73-bytes", "utf8-74-bytes"])
def test_password_request_rejects_more_than_72_utf8_bytes(schema, field, other_fields, password):
    assert len(password) <= 128
    assert len(password.encode("utf-8")) > 72
    with pytest.raises(ValidationError, match="72 bytes"):
        schema.model_validate({**other_fields, field: password})


@pytest.mark.parametrize("schema,field,other_fields", _PASSWORD_REQUESTS)
@pytest.mark.parametrize("password", _PASSWORDS_AT_LIMIT, ids=["ascii", "two-byte-utf8", "four-byte-utf8"])
def test_password_request_accepts_exactly_72_utf8_bytes(schema, field, other_fields, password):
    assert len(password.encode("utf-8")) == 72
    assert getattr(schema.model_validate({**other_fields, field: password}), field) == password


@pytest.mark.parametrize("password", _OVERSIZED_PASSWORDS, ids=["ascii", "utf8"])
def test_hash_password_rejects_oversized_password(password):
    with pytest.raises(ValueError, match="72 bytes"):
        hash_password(password)


@pytest.mark.parametrize("password", _PASSWORDS_AT_LIMIT, ids=["ascii", "two-byte-utf8", "four-byte-utf8"])
def test_verify_password_rejects_truncated_prefix_collision(password):
    stored_hash = hash_password(password)
    assert verify_password(password, stored_hash)
    assert not verify_password(password + "X", stored_hash)
    assert not verify_password(password + "é", stored_hash)


@pytest.mark.parametrize("claim", ["exp", "iat", "sub"])
def test_decode_token_requires_standard_claims(claim):
    payload = decode_token(create_access_token(uuid.uuid4()))
    del payload[claim]
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    with pytest.raises(ValueError, match="Invalid or expired token"):
        decode_token(token)


@pytest.mark.parametrize("claim", ["exp", "iat", "sub"])
def test_decode_token_rejects_null_standard_claims(claim):
    payload = decode_token(create_access_token(uuid.uuid4()))
    payload[claim] = None
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    with pytest.raises(ValueError, match="Invalid or expired token"):
        decode_token(token)


def test_standard_token_helpers_supply_required_claims():
    subject = str(uuid.uuid4())
    for token in (create_access_token(subject), create_refresh_token(subject)):
        payload = decode_token(token)
        assert payload["sub"] == subject
        assert payload["exp"] > payload["iat"]


@pytest.mark.asyncio
async def test_register_and_login(async_client: AsyncClient):
    unique_email = f"test_{uuid.uuid4().hex[:8]}@aairo.ai"
    password = "ZzTestSecureAuth456!"

    # 1. Register
    reg_res = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": unique_email,
            "password": password,
            "full_name": "Test Candidate User",
            "role": "administrator"
        }
    )
    assert reg_res.status_code == 201
    reg_data = reg_res.json()["data"]
    assert reg_data["email"] == unique_email
    assert reg_data["role"] == "candidate"

    # 2. Duplicate registration fails
    dup_res = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": unique_email,
            "password": password,
            "full_name": "Duplicate"
        }
    )
    assert dup_res.status_code == 400

    # 3. Login
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": password}
    )
    assert login_res.status_code == 200
    login_data = login_res.json()["data"]
    assert "access_token" in login_data
    assert "refresh_token" in login_data

    # 4. Get Current User profile with Token
    headers = {"Authorization": f"Bearer {login_data['access_token']}"}
    me_res = await async_client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["data"]["email"] == unique_email

    # 5. Invalid credentials fail
    bad_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": "WrongPassword!"}
    )
    assert bad_login.status_code == 401


def _auth_client(client_ip: str) -> AsyncClient:
    from httpx import ASGITransport
    from app.main import app

    return AsyncClient(
        transport=ASGITransport(app=app, client=(client_ip, 54321)),
        base_url="http://test",
    )


def _synthetic_ip() -> str:
    value = uuid.uuid4().int
    return f"198.18.{(value >> 8) & 255}.{value & 255}"


async def _register_account(client: AsyncClient, email: str, password: str = "ZzTestAuthUser123!") -> None:
    response = await client.post("/api/v1/auth/register", json={
        "email": email, "password": password, "full_name": "zz_test Auth User",
    })
    assert response.status_code == 201, response.text


@pytest.mark.asyncio
async def test_login_lockout_is_persistent_per_email_and_expires(async_client: AsyncClient, monkeypatch):
    import asyncio
    from app.core.config import settings

    monkeypatch.setattr(settings, "AUTH_LOGIN_MAX_FAILURES", 2)
    monkeypatch.setattr(settings, "AUTH_LOCKOUT_SECONDS", 1)
    email = f"zz_test_login_lock_{uuid.uuid4().hex}@example.com"
    password = "ZzTestLoginLock123!"
    await _register_account(async_client, email, password)

    for index, ip in enumerate((_synthetic_ip(), _synthetic_ip())):
        async with _auth_client(ip) as client:
            failed = await client.post("/api/v1/auth/login", json={"email": email, "password": "Incorrect123!"})
            assert failed.status_code == 401, failed.text

    async with _auth_client(_synthetic_ip()) as client:
        locked = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert locked.status_code == 429, locked.text
        assert int(locked.headers["Retry-After"]) >= 1

    await asyncio.sleep(1.1)
    async with _auth_client(_synthetic_ip()) as client:
        after_expiry = await client.post("/api/v1/auth/login", json={"email": email, "password": "Incorrect123!"})
        assert after_expiry.status_code == 401, after_expiry.text


@pytest.mark.asyncio
async def test_login_lockout_is_per_ip_across_email_addresses(async_client: AsyncClient, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "AUTH_LOGIN_MAX_FAILURES", 2)
    monkeypatch.setattr(settings, "AUTH_LOCKOUT_SECONDS", 30)
    password = "ZzTestIpLockUser123!"
    emails = [f"zz_test_ip_lock_{uuid.uuid4().hex}@example.com" for _ in range(3)]
    for email in emails:
        await _register_account(async_client, email, password)

    ip = _synthetic_ip()
    async with _auth_client(ip) as client:
        for email in emails[:2]:
            response = await client.post("/api/v1/auth/login", json={"email": email, "password": "Incorrect123!"})
            assert response.status_code == 401, response.text
        locked = await client.post("/api/v1/auth/login", json={"email": emails[2], "password": password})
        assert locked.status_code == 429, locked.text
        assert int(locked.headers["Retry-After"]) >= 1


@pytest.mark.asyncio
async def test_registration_is_rate_limited_per_email_and_per_ip(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "AUTH_REGISTER_MAX_ATTEMPTS", 2)
    monkeypatch.setattr(settings, "AUTH_LOCKOUT_SECONDS", 30)
    email = f"zz_test_register_limit_{uuid.uuid4().hex}@example.com"
    for index, ip in enumerate((_synthetic_ip(), _synthetic_ip())):
        async with _auth_client(ip) as client:
            response = await client.post("/api/v1/auth/register", json={
                "email": email, "password": "ZzTestRegisterUser123!", "full_name": "zz_test Register User",
            })
            assert response.status_code == (201 if index == 0 else 400), response.text
    async with _auth_client(_synthetic_ip()) as client:
        blocked_email = await client.post("/api/v1/auth/register", json={
            "email": email, "password": "ZzTestRegisterUser123!", "full_name": "zz_test Register User",
        })
        assert blocked_email.status_code == 429, blocked_email.text
        assert "Retry-After" in blocked_email.headers

    shared_ip = _synthetic_ip()
    for _ in range(2):
        async with _auth_client(shared_ip) as client:
            response = await client.post("/api/v1/auth/register", json={
                "email": f"zz_test_register_ip_{uuid.uuid4().hex}@example.com",
                "password": "ZzTestRegisterUser123!", "full_name": "zz_test Register User",
            })
            assert response.status_code == 201, response.text
    async with _auth_client(shared_ip) as client:
        blocked_ip = await client.post("/api/v1/auth/register", json={
            "email": f"zz_test_register_ip_{uuid.uuid4().hex}@example.com",
            "password": "ZzTestRegisterUser123!", "full_name": "zz_test Register User",
        })
        assert blocked_ip.status_code == 429, blocked_ip.text
        assert "Retry-After" in blocked_ip.headers


@pytest.mark.asyncio
async def test_refresh_rotation_reuse_revokes_token_family(async_client: AsyncClient):
    email = f"zz_test_refresh_reuse_{uuid.uuid4().hex}@example.com"
    password = "ZzTestRefreshReuse123!"
    await _register_account(async_client, email, password)
    logged_in = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    old_refresh = logged_in.json()["data"]["refresh_token"]

    rotated = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert rotated.status_code == 200, rotated.text
    new_refresh = rotated.json()["data"]["refresh_token"]
    old_access = logged_in.json()["data"]["access_token"]
    new_access = rotated.json()["data"]["access_token"]
    for access in (old_access, new_access):
        assert (await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})).status_code == 200

    reuse = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse.status_code == 401, reuse.text
    family_revoked = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert family_revoked.status_code == 401, family_revoked.text
    for access in (old_access, new_access):
        assert (await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})).status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh_and_access_tokens(async_client: AsyncClient):
    email = f"zz_test_logout_{uuid.uuid4().hex}@example.com"
    password = "ZzTestLogoutUser123!"
    await _register_account(async_client, email, password)
    login = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    tokens = login.json()["data"]

    logout = await async_client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert logout.status_code == 200, logout.text
    refresh = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 401
    me = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 401


@pytest.mark.asyncio
async def test_password_change_revokes_previous_access_and_refresh_tokens(async_client: AsyncClient):
    email = f"zz_test_password_change_{uuid.uuid4().hex}@example.com"
    old_password = "ZzTestOldPassword123!"
    new_password = "ZzTestNewPassword456!"
    await _register_account(async_client, email, old_password)
    login = await async_client.post("/api/v1/auth/login", json={"email": email, "password": old_password})
    tokens = login.json()["data"]
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    changed = await async_client.post("/api/v1/auth/change-password", headers=headers, json={
        "current_password": old_password, "new_password": new_password,
    })
    assert changed.status_code == 200, changed.text
    assert (await async_client.get("/api/v1/auth/me", headers=headers)).status_code == 401
    assert (await async_client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})).status_code == 401
    assert (await async_client.post("/api/v1/auth/login", json={"email": email, "password": new_password})).status_code == 200


@pytest.mark.asyncio
async def test_weak_common_password_is_rejected(async_client: AsyncClient):
    response = await async_client.post("/api/v1/auth/register", json={
        "email": f"zz_test_weak_password_{uuid.uuid4().hex}@example.com",
        "password": "Password123!", "full_name": "zz_test Weak Password",
    })
    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_deactivated_user_cannot_refresh_or_use_access_token(
    async_client: AsyncClient, admin_headers: dict,
):
    email = f"zz_test_deactivated_auth_{uuid.uuid4().hex}@example.com"
    password = "ZzTestDeactivatedUser123!"
    await _register_account(async_client, email, password)
    login = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    tokens = login.json()["data"]
    # Locate the test account through the administrator's persisted user list.
    users = (await async_client.get("/api/v1/admin/users", headers=admin_headers)).json()["data"]
    target_id = next(user["id"] for user in users if user["email"] == email)
    deactivated = await async_client.patch(f"/api/v1/admin/users/{target_id}/active", headers=admin_headers,
        json={"is_active": False})
    assert deactivated.status_code == 200, deactivated.text
    assert (await async_client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})).status_code == 401
    assert (await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})).status_code == 403


@pytest.mark.asyncio
async def test_successful_own_login_does_not_clear_same_ip_victim_failures(async_client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_LOGIN_MAX_FAILURES", 3)
    monkeypatch.setattr(settings, "AUTH_LOCKOUT_SECONDS", 30)
    password = "ZzTestAggregateUser123!"
    own_email = f"zz_test_own_login_{uuid.uuid4().hex}@example.com"
    victims = [f"zz_test_victim_{uuid.uuid4().hex}@example.com" for _ in range(3)]
    for email in [own_email, *victims]:
        await _register_account(async_client, email, password)

    async with _auth_client(_synthetic_ip()) as client:
        for index, victim in enumerate(victims):
            failed = await client.post("/api/v1/auth/login", json={"email": victim, "password": "Incorrect123!"})
            assert failed.status_code == 401, failed.text
            own_login = await client.post("/api/v1/auth/login", json={"email": own_email, "password": password})
            assert own_login.status_code == (200 if index < 2 else 429), own_login.text
        assert int(own_login.headers["Retry-After"]) >= 1


@pytest.mark.asyncio
async def test_clear_login_failures_clears_email_but_preserves_ip_aggregate():
    email = f"zz_test_clear_failures_{uuid.uuid4().hex}@example.com"
    ip = _synthetic_ip()
    async with AsyncSessionLocal() as db:
        await AuthRateLimiter.record_attempt(db, "login", email, ip)
        await AuthRateLimiter.clear_login_failures(db, email, ip)
        await db.commit()
        for scope, key_hash in AuthRateLimiter._keys(email, ip):
            row = await db.scalar(select(AuthAttemptLimit).where(
                AuthAttemptLimit.endpoint == "login",
                AuthAttemptLimit.scope == scope,
                AuthAttemptLimit.key_hash == key_hash,
            ))
            if scope == "email":
                assert row is None
            else:
                assert row is not None
                assert row.failed_attempts == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ["login", "register"])
@pytest.mark.parametrize("scope", ["email", "ip"])
@pytest.mark.parametrize("operation", ["ensure_allowed", "record_attempt"])
async def test_active_auth_lock_survives_expired_counter_window(endpoint, scope, operation, monkeypatch):
    from fastapi import HTTPException

    monkeypatch.setattr(settings, "AUTH_RATE_WINDOW_SECONDS", 60)
    monkeypatch.setattr(settings, "AUTH_LOCKOUT_SECONDS", 300)
    email = f"zz_test_stale_lock_{uuid.uuid4().hex}@example.com"
    ip = _synthetic_ip()
    now = datetime.now(timezone.utc)
    window_started_at = now - timedelta(seconds=120)
    locked_until = now + timedelta(seconds=180)
    row_id = uuid.uuid4()
    async with AsyncSessionLocal() as db:
        db.add(AuthAttemptLimit(
            id=row_id, endpoint=endpoint, scope=scope,
            key_hash=dict(AuthRateLimiter._keys(email, ip))[scope],
            failed_attempts=7, window_started_at=window_started_at, locked_until=locked_until,
        ))
        await db.commit()
        if operation == "ensure_allowed":
            with pytest.raises(HTTPException) as raised:
                await AuthRateLimiter.ensure_allowed(db, endpoint, email, ip)
            assert raised.value.status_code == 429
            assert int(raised.value.headers["Retry-After"]) >= 1
        else:
            await AuthRateLimiter.record_attempt(db, endpoint, email, ip)

    async with AsyncSessionLocal() as db:
        row = await db.get(AuthAttemptLimit, row_id)
        assert row.failed_attempts == 7
        assert row.window_started_at == window_started_at
        assert row.locked_until == locked_until


@pytest.mark.asyncio
@pytest.mark.parametrize("claim", ["exp", "iat", "sub", "ver", "fam", "type"])
async def test_access_boundary_rejects_missing_claims(async_client: AsyncClient, claim):
    email = f"zz_test_missing_claim_{uuid.uuid4().hex}@example.com"
    password = "ZzTestMissingClaim123!"
    await _register_account(async_client, email, password)
    login = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    access_token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    assert (await async_client.get("/api/v1/auth/me", headers=headers)).status_code == 200
    payload = decode_token(access_token)
    del payload[claim]
    invalid_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    response = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {invalid_token}"})
    assert response.status_code == 401, response.text
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.asyncio
@pytest.mark.parametrize("claim,value", [
    ("ver", None), ("ver", False), ("ver", "0"), ("ver", -1), ("ver", 0.0),
    ("fam", None), ("fam", ""), ("fam", "not-a-uuid"), ("fam", 123),
    ("fam", str(uuid.uuid4())), ("type", "refresh"),
])
async def test_access_boundary_rejects_invalid_session_claims(async_client: AsyncClient, claim, value):
    email = f"zz_test_invalid_claim_{uuid.uuid4().hex}@example.com"
    password = "ZzTestInvalidClaim123!"
    await _register_account(async_client, email, password)
    login = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    payload = decode_token(login.json()["data"]["access_token"])
    payload[claim] = value
    invalid_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    response = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {invalid_token}"})
    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_utf8_password_boundary_is_enforced_by_auth_routes(async_client: AsyncClient):
    email = f"zz_test_utf8_password_{uuid.uuid4().hex}@example.com"
    password = "Zz9!Kx2@" + "é" * 32
    oversized = password + "é"
    rejected = await async_client.post("/api/v1/auth/register", json={
        "email": email, "password": oversized, "full_name": "zz_test UTF8 Password",
    })
    assert rejected.status_code == 422, rejected.text
    await _register_account(async_client, email, password)
    login = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    rejected_login = await async_client.post("/api/v1/auth/login", json={"email": email, "password": oversized})
    assert rejected_login.status_code == 422, rejected_login.text
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    for current_password, new_password in [(oversized, "ZzTestNewPassword456!"), (password, oversized)]:
        changed = await async_client.post("/api/v1/auth/change-password", headers=headers, json={
            "current_password": current_password, "new_password": new_password,
        })
        assert changed.status_code == 422, changed.text
    reset = await async_client.post("/api/v1/auth/reset-password", json={
        "token": "synthetic-reset-token", "new_password": oversized,
    })
    assert reset.status_code == 422, reset.text
    assert (await async_client.get("/api/v1/auth/me", headers=headers)).status_code == 200
