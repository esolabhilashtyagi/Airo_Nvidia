import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.core.config import settings
from app.models.candidate import CandidateProfile
from app.models.system import PasswordResetToken, RefreshTokenSession
from app.models.user import User, UserRole
from app.schemas.auth import (
    ChangePasswordRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth_rate_limiter import AuthRateLimiter
from app.services.email_delivery import email_delivery_is_configured, send_password_reset_email
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger("aairo.auth")


class AuthService:
    PASSWORD_RESET_TTL = timedelta(minutes=30)

    @staticmethod
    def _reset_token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @classmethod
    async def request_password_reset(cls, db: AsyncSession, email: str, client_ip: str = "unknown") -> bool:
        normalized_email = email.strip().lower()
        await AuthRateLimiter.ensure_allowed(db, "password_reset", normalized_email, client_ip)
        await AuthRateLimiter.record_attempt(db, "password_reset", normalized_email, client_ip)
        if not email_delivery_is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Password recovery email is not configured. Set SMTP_HOST and SMTP_FROM_EMAIL, then restart the backend.",
            )

        user = await db.scalar(select(User).where(User.email == normalized_email))
        # Do not reveal whether an account exists or is active.
        if not user or not user.is_active:
            logger.info("Password reset request skipped: no active account matched")
            return True

        now = datetime.now(timezone.utc)
        await db.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user.id, PasswordResetToken.redeemed_at.is_(None))
            .values(redeemed_at=now)
        )
        token = secrets.token_urlsafe(32)
        db.add(PasswordResetToken(
            token_hash=cls._reset_token_hash(token),
            user_id=user.id,
            expires_at=now + cls.PASSWORD_RESET_TTL,
        ))
        await db.commit()

        reset_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/reset-password#{urlencode({'token': token})}"
        try:
            await run_in_threadpool(send_password_reset_email, user.email, reset_url)
            logger.info("Password reset email accepted by configured SMTP server")
        except Exception as exc:
            await db.execute(
                update(PasswordResetToken)
                .where(PasswordResetToken.token_hash == cls._reset_token_hash(token))
                .values(redeemed_at=datetime.now(timezone.utc))
            )
            await db.commit()
            logger.warning("Password reset email delivery failed (%s)", type(exc).__name__)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Password reset email could not be delivered. Check SMTP settings and try again.",
            ) from exc
        return True

    @classmethod
    async def reset_password(cls, db: AsyncSession, token: str, new_password: str, client_ip: str = "unknown") -> None:
        token_hash = cls._reset_token_hash(token)
        await AuthRateLimiter.ensure_allowed(db, "password_reset", token_hash, client_ip)
        await AuthRateLimiter.record_attempt(db, "password_reset", token_hash, client_ip)
        now = datetime.now(timezone.utc)
        token_row = await db.scalar(
            select(PasswordResetToken)
            .where(PasswordResetToken.token_hash == token_hash)
            .with_for_update()
        )
        if not token_row or token_row.redeemed_at is not None or token_row.expires_at <= now:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This password reset link is invalid or expired. Request a new one.")

        user = await db.scalar(select(User).where(User.id == token_row.user_id).with_for_update())
        if not user or not user.is_active:
            token_row.redeemed_at = now
            await db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This password reset link is invalid or expired. Request a new one.")

        user.hashed_password = hash_password(new_password)
        user.auth_token_version += 1
        token_row.redeemed_at = now
        await db.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user.id, PasswordResetToken.redeemed_at.is_(None))
            .values(redeemed_at=now)
        )
        await db.execute(
            update(RefreshTokenSession)
            .where(RefreshTokenSession.user_id == user.id, RefreshTokenSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await db.commit()

    @staticmethod
    async def register(db: AsyncSession, request: UserRegisterRequest, client_ip: str = "unknown") -> UserResponse:
        email = request.email.lower().strip()
        await AuthRateLimiter.ensure_allowed(db, "register", email, client_ip)
        # Count accepted attempts, including duplicate-email responses, by both email and source IP.
        await AuthRateLimiter.record_attempt(db, "register", email, client_ip)

        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists",
            )

        new_user = User(
            email=email,
            hashed_password=hash_password(request.password),
            full_name=request.full_name.strip(),
            role=UserRole.CANDIDATE,
            is_active=True,
            is_verified=True,
        )
        db.add(new_user)
        await db.flush()
        profile = CandidateProfile(
            user_id=new_user.id,
            onboarding_completed=False,
            onboarding_step=1,
        )
        db.add(profile)
        await db.flush()
        await db.commit()
        await db.refresh(new_user)

        return UserResponse(
            id=new_user.id,
            email=new_user.email,
            full_name=new_user.full_name,
            role=new_user.role,
            is_active=new_user.is_active,
            is_verified=new_user.is_verified,
            candidate_profile_id=profile.id,
            created_at=new_user.created_at,
            updated_at=new_user.updated_at,
        )

    @staticmethod
    def _user_claims(user: User, family_id: uuid.UUID) -> dict[str, object]:
        return {
            "email": user.email,
            "role": user.role.value,
            "full_name": user.full_name,
            "ver": user.auth_token_version,
            "fam": str(family_id),
        }

    @classmethod
    async def _issue_tokens(
        cls,
        db: AsyncSession,
        user: User,
        family_id: uuid.UUID | None = None,
    ) -> TokenResponse:
        now = datetime.now(timezone.utc)
        family_id = family_id or uuid.uuid4()
        jti = uuid.uuid4()
        expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        expires_at = now + expires_delta
        db.add(RefreshTokenSession(
            jti=jti,
            user_id=user.id,
            family_id=family_id,
            issued_at=now,
            expires_at=expires_at,
        ))
        access_token = create_access_token(
            user.id,
            extra_claims=cls._user_claims(user, family_id),
        )
        refresh_token = create_refresh_token(
            user.id,
            expires_delta=expires_delta,
            jti=str(jti),
            family_id=str(family_id),
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @classmethod
    async def login(
        cls,
        db: AsyncSession,
        request: UserLoginRequest,
        client_ip: str = "unknown",
    ) -> TokenResponse:
        email = request.email.lower().strip()
        await AuthRateLimiter.ensure_allowed(db, "login", email, client_ip)
        query = select(User).where(User.email == email).options(selectinload(User.candidate_profile))
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user or not verify_password(request.password, user.hashed_password):
            await AuthRateLimiter.record_attempt(db, "login", email, client_ip)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has been deactivated. Please contact support.",
            )

        tokens = await cls._issue_tokens(db, user)
        await AuthRateLimiter.clear_login_failures(db, email, client_ip)
        await db.commit()
        return tokens

    @staticmethod
    async def _decode_refresh_claims(refresh_token_str: str) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
        try:
            payload = decode_token(refresh_token_str)
            if payload.get("type") != "refresh":
                raise ValueError("Not a refresh token")
            return (
                uuid.UUID(payload["sub"]),
                uuid.UUID(payload["jti"]),
                uuid.UUID(payload["fam"]),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            ) from exc

    @staticmethod
    async def _revoke_family(db: AsyncSession, family_id: uuid.UUID, now: datetime) -> None:
        await db.execute(
            update(RefreshTokenSession)
            .where(RefreshTokenSession.family_id == family_id, RefreshTokenSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    @classmethod
    async def refresh_token(cls, db: AsyncSession, refresh_token_str: str) -> TokenResponse:
        user_id, jti, family_id = await cls._decode_refresh_claims(refresh_token_str)
        now = datetime.now(timezone.utc)
        session = await db.scalar(
            select(RefreshTokenSession)
            .where(RefreshTokenSession.jti == jti)
            .with_for_update()
        )
        if not session or session.user_id != user_id or session.family_id != family_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

        if session.revoked_at is not None or session.replaced_by_jti is not None:
            await cls._revoke_family(db, family_id, now)
            await db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token reuse detected")
        if session.expires_at <= now:
            session.revoked_at = now
            await db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

        user = await db.scalar(select(User).where(User.id == user_id))
        if not user or not user.is_active:
            await cls._revoke_family(db, family_id, now)
            await db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer active")

        session.revoked_at = now
        tokens = await cls._issue_tokens(db, user, family_id)
        # _issue_tokens creates a new unique jti; keep the link consistent with that row.
        # Resolve its JTI from the just-issued token payload.
        next_payload = decode_token(tokens.refresh_token)
        session.replaced_by_jti = uuid.UUID(next_payload["jti"])
        await db.commit()
        return tokens

    @classmethod
    async def logout(cls, db: AsyncSession, refresh_token_str: str) -> None:
        user_id, _jti, family_id = await cls._decode_refresh_claims(refresh_token_str)
        await db.execute(
            update(RefreshTokenSession)
            .where(
                RefreshTokenSession.user_id == user_id,
                RefreshTokenSession.family_id == family_id,
                RefreshTokenSession.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await db.commit()

    @staticmethod
    async def change_password(
        db: AsyncSession,
        user: User,
        request: ChangePasswordRequest,
    ) -> None:
        if not verify_password(request.current_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
        user.hashed_password = hash_password(request.new_password)
        user.auth_token_version += 1
        now = datetime.now(timezone.utc)
        await db.execute(
            update(RefreshTokenSession)
            .where(RefreshTokenSession.user_id == user.id, RefreshTokenSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await db.commit()
