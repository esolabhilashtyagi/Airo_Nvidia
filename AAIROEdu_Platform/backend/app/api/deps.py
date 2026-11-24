import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Callable, List, Optional
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_async_db
from app.core.security import decode_token
from app.models.candidate import CandidateProfile
from app.models.system import RefreshTokenSession
from app.models.user import User, UserRole

security_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type: expected access token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload missing subject identifier",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = uuid.UUID(user_id_str)
        token_version = payload["ver"]
        if type(token_version) is not int or token_version < 0:
            raise ValueError("Invalid token version")
        family_claim = payload["fam"]
        if not isinstance(family_claim, str):
            raise ValueError("Invalid session family")
        family_id = uuid.UUID(family_claim)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials or token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    query = select(User).where(User.id == user_id).options(selectinload(User.candidate_profile))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with token no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )

    if token_version != user.auth_token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    active_family = await db.scalar(select(exists().where(
        RefreshTokenSession.user_id == user.id,
        RefreshTokenSession.family_id == family_id,
        RefreshTokenSession.revoked_at.is_(None),
        RefreshTokenSession.expires_at > datetime.now(timezone.utc),
    )))
    if not active_family:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    return current_user


def require_role(allowed_roles: List[UserRole]) -> Callable:
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles and current_user.role != UserRole.ADMINISTRATOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of the following roles: {[r.value for r in allowed_roles]}"
            )
        return current_user
    return role_checker


async def get_current_candidate_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
) -> CandidateProfile:
    query = (
        select(CandidateProfile)
        .where(CandidateProfile.user_id == current_user.id)
        .options(
            selectinload(CandidateProfile.education_history),
            selectinload(CandidateProfile.experience_history),
            selectinload(CandidateProfile.target_companies),
            selectinload(CandidateProfile.industry)
        )
    )
    result = await db.execute(query)
    profile = result.scalar_one_or_none()

    if not profile:
        # Automatically initialize candidate profile if not present
        profile = CandidateProfile(
            user_id=current_user.id,
            onboarding_completed=False,
            onboarding_step=1
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    return profile
