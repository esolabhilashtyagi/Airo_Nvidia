from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_async_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest, ForgotPasswordRequest, RefreshTokenRequest, ResetPasswordRequest,
    TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse
)
from app.schemas.common import APIResponse
from app.services.auth_service import AuthService
from app.services.email_delivery import send_registration_emails

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=APIResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegisterRequest,
    http_request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
):
    client_ip = http_request.client.host if http_request.client else "unknown"
    user = await AuthService.register(db, request, client_ip)
    # Registration has committed before these best-effort emails run. SMTP outages
    # must not turn a successful account creation into a misleading API failure.
    background_tasks.add_task(send_registration_emails, user.email, user.full_name, False)
    return APIResponse(data=user, message="User registered successfully")


@router.post("/login", response_model=APIResponse[TokenResponse])
async def login(
    request: UserLoginRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    client_ip = http_request.client.host if http_request.client else "unknown"
    tokens = await AuthService.login(db, request, client_ip)
    return APIResponse(data=tokens, message="Login successful")


@router.post("/refresh", response_model=APIResponse[TokenResponse])
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_async_db)
):
    tokens = await AuthService.refresh_token(db, request.refresh_token)
    return APIResponse(data=tokens, message="Token refreshed successfully")


@router.post("/logout", response_model=APIResponse[dict])
async def logout(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_async_db),
):
    await AuthService.logout(db, request.refresh_token)
    return APIResponse(data={"logged_out": True}, message="Session logged out")


@router.post("/change-password", response_model=APIResponse[dict])
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    await AuthService.change_password(db, current_user, request)
    return APIResponse(data={"changed": True}, message="Password changed; please sign in again")


@router.get("/me", response_model=APIResponse[UserResponse])
async def get_me(
    current_user: User = Depends(get_current_user)
):
    profile_id = current_user.candidate_profile.id if current_user.candidate_profile else None
    user_resp = UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        candidate_profile_id=profile_id,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )
    return APIResponse(data=user_resp, message="Current user profile retrieved")


@router.post("/forgot-password", response_model=APIResponse[dict])
async def forgot_password(request: ForgotPasswordRequest, http_request: Request, db: AsyncSession = Depends(get_async_db)):
    client_ip = http_request.client.host if http_request.client else "unknown"
    await AuthService.request_password_reset(db, str(request.email), client_ip)
    return APIResponse(
        data={"sent": True},
        message="If an active account matches that email, password reset instructions have been sent.",
    )


@router.post("/reset-password", response_model=APIResponse[dict])
async def reset_password(request: ResetPasswordRequest, http_request: Request, db: AsyncSession = Depends(get_async_db)):
    client_ip = http_request.client.host if http_request.client else "unknown"
    await AuthService.reset_password(db, request.token, request.new_password, client_ip)
    return APIResponse(data={"reset": True}, message="Your password has been updated. Sign in with your new password.")
