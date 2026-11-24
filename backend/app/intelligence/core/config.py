"""
Global configuration management using Pydantic Settings.
Reads from environment variables and .env file.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/interview_intelligence"
    SQLITE_FALLBACK_URL: str = "sqlite:///./interview_intelligence.db"

    # Local AI Models (Ollama / Nemotron)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    PRIMARY_MODEL: str = "nemotron-mini:latest"
    FALLBACK_MODEL: str = "qwen2.5:3b"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384

    # Scraping & Ethical Compliance
    SCRAPING_CONCURRENCY: int = 4
    DEFAULT_REQUEST_DELAY_SEC: float = 1.5
    RESPECT_ROBOTS_TXT: bool = True
    USER_AGENT: str = "InterviewIntelligenceBot/1.0 (+https://github.com/aairo/interview-intelligence; ethical academic data collector)"

    # Source API Credentials (Optional)
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_USER_AGENT: str = "InterviewIntelligence/1.0"

    # Security
    API_SECRET_KEY: str = "local-dev-secret-key-replace-in-prod"
    ADMIN_API_KEY: str = "admin-local-token"

    # Ports
    FASTAPI_PORT: int = 8000
    PROMETHEUS_PORT: int = 8001
    STREAMLIT_PORT: int = 8501


settings = Settings()
