import hashlib
import hmac
import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import case, delete, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.system import AuthAttemptLimit


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class AuthRateLimiter:
    @staticmethod
    def _fingerprint(scope: str, value: str) -> str:
        message = f"{scope}:{value.strip().lower()}".encode("utf-8")
        return hmac.new(settings.SECRET_KEY.encode("utf-8"), message, hashlib.sha256).hexdigest()

    @classmethod
    def _keys(cls, email: str, client_ip: str) -> list[tuple[str, str]]:
        return [
            ("email", cls._fingerprint("email", email)),
            ("ip", cls._fingerprint("ip", client_ip or "unknown")),
        ]

    @staticmethod
    def _limit(endpoint: str) -> int:
        if endpoint == "login":
            return settings.AUTH_LOGIN_MAX_FAILURES
        if endpoint == "register":
            return settings.AUTH_REGISTER_MAX_ATTEMPTS
        if endpoint == "password_reset":
            return settings.AUTH_PASSWORD_RESET_MAX_ATTEMPTS
        raise ValueError(f"Unsupported authentication endpoint: {endpoint}")

    @classmethod
    async def ensure_allowed(
        cls, db: AsyncSession, endpoint: str, email: str, client_ip: str,
    ) -> None:
        now = datetime.now(timezone.utc)
        reset_before = now - timedelta(seconds=settings.AUTH_RATE_WINDOW_SECONDS)
        retry_after = 0
        changed = False
        for scope, key_hash in cls._keys(email, client_ip):
            row = await db.scalar(select(AuthAttemptLimit).where(
                AuthAttemptLimit.endpoint == endpoint,
                AuthAttemptLimit.scope == scope,
                AuthAttemptLimit.key_hash == key_hash,
            ).with_for_update())
            if not row:
                continue
            locked_until = _as_utc(row.locked_until)
            window_started_at = _as_utc(row.window_started_at)
            if locked_until and locked_until > now:
                retry_after = max(retry_after, math.ceil((locked_until - now).total_seconds()))
                continue
            if (window_started_at and window_started_at <= reset_before) or (locked_until and locked_until <= now):
                row.failed_attempts = 0
                row.window_started_at = now
                row.locked_until = None
                changed = True

        if changed:
            await db.commit()
        if retry_after:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many authentication attempts. Please try again later.",
                headers={"Retry-After": str(max(retry_after, 1))},
            )

    @classmethod
    async def record_attempt(
        cls, db: AsyncSession, endpoint: str, email: str, client_ip: str,
    ) -> None:
        now = datetime.now(timezone.utc)
        reset_before = now - timedelta(seconds=settings.AUTH_RATE_WINDOW_SECONDS)
        limit = cls._limit(endpoint)
        lock_until = now + timedelta(seconds=settings.AUTH_LOCKOUT_SECONDS)

        bind = db.get_bind() if hasattr(db, "get_bind") else db.bind
        is_sqlite = getattr(getattr(bind, "dialect", None), "name", "") == "sqlite"
        insert_fn = sqlite_insert if is_sqlite else pg_insert

        for scope, key_hash in cls._keys(email, client_ip):
            expired = or_(
                AuthAttemptLimit.window_started_at <= reset_before,
                AuthAttemptLimit.locked_until <= now,
            )
            next_count = case(
                (expired, 1),
                else_=AuthAttemptLimit.failed_attempts + 1,
            )
            statement = insert_fn(AuthAttemptLimit).values(
                id=uuid.uuid4(),
                endpoint=endpoint,
                scope=scope,
                key_hash=key_hash,
                failed_attempts=1,
                window_started_at=now,
                locked_until=lock_until if limit <= 1 else None,
            ).on_conflict_do_update(
                index_elements=["endpoint", "scope", "key_hash"],
                set_={
                    "failed_attempts": next_count,
                    "window_started_at": case((expired, now), else_=AuthAttemptLimit.window_started_at),
                    "locked_until": case((next_count >= limit, lock_until), else_=None),
                },
                # A concurrent request must never reset or extend an active lock.
                where=or_(
                    AuthAttemptLimit.locked_until.is_(None),
                    AuthAttemptLimit.locked_until <= now,
                ),
            )
            await db.execute(statement)
        await db.commit()

    @classmethod
    async def clear_login_failures(cls, db: AsyncSession, email: str, client_ip: str) -> None:
        # Successful authentication clears only this account's failures; source-IP
        # failures aggregate across accounts and must survive successful logins.
        await db.execute(delete(AuthAttemptLimit).where(
            AuthAttemptLimit.endpoint == "login",
            AuthAttemptLimit.scope == "email",
            AuthAttemptLimit.key_hash == cls._fingerprint("email", email),
        ))
