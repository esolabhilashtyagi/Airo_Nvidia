import uuid
import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from app.core.security import validate_password_length
from app.models.user import UserRole


_COMMON_PASSWORDS = {
    "password", "password1", "password12", "password123", "password1234",
    "qwerty", "qwerty123", "welcome", "welcome123", "letmein", "letmein123",
    "admin123", "adminpassword123", "candidatepass123", "managerpass123",
    "securepassword123", "iloveyou", "iloveyou123", "changeme", "changeme123",
    "12345678", "123456789", "11111111", "00000000",
}


def validate_password_strength(password: str) -> str:
    normalized = re.sub(r"[^a-z0-9]", "", password.casefold())
    sequences = ("0123456789", "12345678", "abcdefgh", "qwerty", "asdfgh", "zxcvbn")
    if normalized in _COMMON_PASSWORDS or len(set(normalized)) <= 2 or any(
        sequence in normalized for sequence in sequences
    ):
        raise ValueError("Choose a less common password; avoid common words, keyboard patterns, and simple sequences.")
    return password


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=255)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(validate_password_length(value))


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("password")
    @classmethod
    def password_length(cls, value: str) -> str:
        return validate_password_length(value)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(validate_password_length(value))


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("current_password")
    @classmethod
    def current_password_length(cls, value: str) -> str:
        return validate_password_length(value)

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(validate_password_length(value))


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    candidate_profile_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
