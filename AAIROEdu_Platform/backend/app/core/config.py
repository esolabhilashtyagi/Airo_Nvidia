import json
import os
from ipaddress import ip_address
from pathlib import Path
from typing import List
from urllib.parse import urlsplit, urlunsplit
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / ".env"


def normalize_nvidia_base_url(value: str) -> str:
    """Canonicalize the inference endpoint without retaining URL credentials."""
    value = value.strip()
    error = "NVIDIA_BASE_URL must be an HTTP(S) URL without credentials, query, or fragment"
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
        if (
            parsed.scheme not in {"http", "https"}
            or not hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or any(character.isspace() for character in value)
            or "\\" in value
        ):
            raise ValueError(error)
    except ValueError:
        raise ValueError(error) from None

    hostname = hostname.lower().rstrip(".")
    if not hostname:
        raise ValueError(error)
    authority = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None and port != {"http": 80, "https": 443}[parsed.scheme]:
        authority += f":{port}"
    return urlunsplit((parsed.scheme, authority, parsed.path.rstrip("/"), "", ""))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "Candidate Dashboard AAIRO"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    
    SECRET_KEY: str = "replace-this-with-a-secure-random-secret-key-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    AUTH_LOGIN_MAX_FAILURES: int = 5
    AUTH_REGISTER_MAX_ATTEMPTS: int = 100
    AUTH_PASSWORD_RESET_MAX_ATTEMPTS: int = 5
    AUTH_RATE_WINDOW_SECONDS: int = 900
    AUTH_LOCKOUT_SECONDS: int = 900

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "aairo_user"
    POSTGRES_PASSWORD: str = "aairo_secure_password"
    POSTGRES_DB: str = "aairo_db"
    DATABASE_URL: str = "postgresql+asyncpg://aairo_user:aairo_secure_password@localhost:5432/aairo_db"
    DATABASE_URL_SYNC: str = "postgresql://aairo_user:aairo_secure_password@localhost:5432/aairo_db"

    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_BYTES: int = 15 * 1024 * 1024  # 15MB

    # AI Configuration. NVIDIA's hosted API and self-hosted OpenAI-compatible
    # servers use the same provider implementation. Gemini remains opt-in.
    AI_PROVIDER: str = "nvidia"
    NVIDIA_API_KEY: str = ""
    NVIDIA_MODEL: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_STRUCTURED_OUTPUT_MODE: str = "json_object"
    YOUTUBE_API_KEY: str = ""
    OPENALEX_BASE_URL: str = "https://api.openalex.org"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"
    AI_REQUEST_TIMEOUT_SECONDS: int = 45
    AI_MAX_RETRIES: int = 2

    # Optional SMTP delivery used for transactional account messages.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_USE_SSL: bool = False
    SMTP_STARTTLS: bool = True
    SMTP_TIMEOUT_SECONDS: int = 15
    FRONTEND_BASE_URL: str = "http://localhost:5173"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        url = str(value).strip()
        if url.startswith("sqlite"):
            return url
        if url.startswith("postgres://"):
            url = "postgresql+asyncpg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = "postgresql+asyncpg://" + url[len("postgresql://"):]
        return url

    @field_validator("DATABASE_URL_SYNC", mode="before")
    @classmethod
    def normalize_database_url_sync(cls, value: str) -> str:
        url = str(value).strip()
        if url.startswith("sqlite"):
            return url
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        elif url.startswith("postgresql+asyncpg://"):
            url = "postgresql://" + url[len("postgresql+asyncpg://"):]
        return url

    @field_validator("AI_PROVIDER", mode="before")
    @classmethod
    def validate_ai_provider(cls, value):
        normalized = str(value).strip().lower()
        if normalized not in {"nvidia", "gemini"}:
            raise ValueError("AI_PROVIDER must be either 'nvidia' or 'gemini'")
        return normalized

    @field_validator("NVIDIA_MODEL", mode="before")
    @classmethod
    def validate_nvidia_model(cls, value):
        normalized = str(value).strip()
        if not normalized:
            raise ValueError("NVIDIA_MODEL must not be blank")
        return normalized

    @field_validator("NVIDIA_BASE_URL")
    @classmethod
    def validate_nvidia_base_url(cls, value):
        return normalize_nvidia_base_url(value)

    @field_validator("NVIDIA_STRUCTURED_OUTPUT_MODE", mode="before")
    @classmethod
    def validate_nvidia_structured_output_mode(cls, value):
        normalized = str(value).strip().lower()
        if normalized not in {"json_object", "prompt"}:
            raise ValueError("NVIDIA_STRUCTURED_OUTPUT_MODE must be 'json_object' or 'prompt'")
        return normalized

    @field_validator("AI_REQUEST_TIMEOUT_SECONDS")
    @classmethod
    def validate_ai_timeout(cls, value):
        if value < 1 or value > 300:
            raise ValueError("AI_REQUEST_TIMEOUT_SECONDS must be between 1 and 300")
        return value

    @field_validator("AI_MAX_RETRIES")
    @classmethod
    def validate_ai_retries(cls, value):
        if value < 0 or value > 5:
            raise ValueError("AI_MAX_RETRIES must be between 0 and 5")
        return value

    # Candidate-scoped resume API limits (fixed windows, persisted in PostgreSQL).
    RESUME_UPLOAD_RATE_LIMIT: int = 20
    RESUME_UPLOAD_RATE_WINDOW_SECONDS: int = 3600
    RESUME_EXTRACTION_RATE_LIMIT: int = 20
    RESUME_EXTRACTION_RATE_WINDOW_SECONDS: int = 3600
    RESUME_AI_RATE_LIMIT: int = 5
    RESUME_AI_RATE_WINDOW_SECONDS: int = 3600

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173"
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                try:
                    return json.loads(value)
                except Exception:
                    pass
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    # Initial Admin Seed
    INITIAL_ADMIN_EMAIL: str = "admin@aairo.ai"
    INITIAL_ADMIN_PASSWORD: str = "AdminPassword123!"

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def normalize_environment(cls, value):
        return str(value).strip().lower()

    def validate_production_safety(self):
        if self.ENVIRONMENT != "production":
            return self

        errors = []
        if self.DEBUG:
            errors.append("DEBUG must be false")
        placeholder_markers = ("replace", "change-me", "changeme", "placeholder", "example", "your-")
        secret_is_placeholder = any(marker in self.SECRET_KEY.strip().lower() for marker in placeholder_markers)
        if (
            len(self.SECRET_KEY.strip()) < 32
            or secret_is_placeholder
        ):
            errors.append("SECRET_KEY must be an owner-provided random value with at least 32 characters")
        admin_password_is_placeholder = any(
            marker in self.INITIAL_ADMIN_PASSWORD.strip().lower() for marker in placeholder_markers
        )
        if self.INITIAL_ADMIN_PASSWORD == "AdminPassword123!" or admin_password_is_placeholder:
            errors.append("INITIAL_ADMIN_PASSWORD must not use the development default")
        invalid_origins = []
        for origin in self.CORS_ORIGINS:
            parsed = urlsplit(origin.strip())
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.hostname.lower() in {"localhost", "127.0.0.1", "::1"}
                or parsed.path not in {"", "/"}
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
            ):
                invalid_origins.append(origin)
        if not self.CORS_ORIGINS or invalid_origins:
            errors.append("CORS_ORIGINS must contain only explicit HTTPS origins without paths or credentials")
        if self.AI_PROVIDER == "nvidia":
            endpoint = urlsplit(self.NVIDIA_BASE_URL)
            if endpoint.scheme == "http":
                hostname = endpoint.hostname.lower().rstrip(".")
                private_endpoint = hostname == "localhost"
                if not private_endpoint:
                    try:
                        address = ip_address(hostname)
                        private_endpoint = (
                            address.is_private
                            and not address.is_unspecified
                            and not address.is_multicast
                        )
                    except ValueError:
                        # Do not infer that arbitrary DNS names resolve privately.
                        private_endpoint = False
                if self.NVIDIA_API_KEY.strip() or not private_endpoint:
                    errors.append(
                        "NVIDIA_BASE_URL must use HTTPS except for explicit localhost/private-IP "
                        "endpoints without NVIDIA_API_KEY"
                    )
        if errors:
            # List setting names only. Validation exceptions can be logged by
            # a process supervisor; never include secret/config values here.
            raise RuntimeError("Unsafe production configuration: " + "; ".join(errors))
        return self


settings = Settings()
settings.validate_production_safety()

# Ensure uploads directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
