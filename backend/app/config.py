"""
Digital FTE - Application Configuration
Reads all environment variables using Pydantic Settings.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── App ──────────────────────────────────────────────
    APP_ENV: str = "development"
    LOG_LEVEL: str = "DEBUG"
    SECRET_KEY: str = "change-me-to-a-random-string"
    UPLOAD_DIR: str = "./uploads"
    GENERATED_DIR: str = "./generated"

    # ── Database ────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/digital_fte"
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── LLM Providers ──────────────────────────────────
    GOOGLE_AI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None

    # ── Job Search ─────────────────────────────────────
    SERPAPI_API_KEY: Optional[str] = None
    RAPIDAPI_KEY: Optional[str] = None

    # ── HR Contact ─────────────────────────────────────
    HUNTER_API_KEY: Optional[str] = None

    # ── Google Cloud / OAuth ───────────────────────────
    GOOGLE_CLOUD_PROJECT_ID: Optional[str] = None
    GOOGLE_OAUTH_CLIENT_ID: Optional[str] = None
    GOOGLE_OAUTH_CLIENT_SECRET: Optional[str] = None
    GOOGLE_CREDENTIALS_PATH: str = "./credentials.json"

    # ── Observability ──────────────────────────────────
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "digital-fte"
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # ── JWT ─────────────────────────────────────────────
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
