"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings
from functools import lru_cache
import os

# Ensure .env is loaded from project root
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")


class Settings(BaseSettings):
    """All application settings loaded from environment variables."""

    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    SECRET_KEY: str = "change-me-to-a-real-secret-key-at-least-32-chars"

    # --- Supabase ---
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    DATABASE_URL: str = "sqlite+aiosqlite:///./digital_fte.db"
    DIRECT_DATABASE_URL: str = ""

    # --- Upstash Redis ---
    UPSTASH_REDIS_URL: str = ""
    UPSTASH_REDIS_REST_URL: str = ""
    UPSTASH_REDIS_REST_TOKEN: str = ""

    # --- LLM Providers ---
    OPENAI_API_KEY: str = ""
    GOOGLE_AI_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    # --- Job Search ---
    SERPAPI_API_KEY: str = ""
    RAPIDAPI_KEY: str = ""
    APIFY_API_KEY: str = ""

    # --- HR Contact ---
    PROSPEO_API_KEY: str = ""
    HUNTER_API_KEY: str = ""       # hunter.io — 25 free domain searches/month
    SNOV_CLIENT_ID: str = ""       # snov.io — 50 free searches/month
    SNOV_CLIENT_SECRET: str = ""   # snov.io

    # --- Google Cloud ---
    GOOGLE_CLOUD_PROJECT_ID: str = ""
    GOOGLE_OAUTH_CLIENT_ID: str = ""
    GOOGLE_OAUTH_CLIENT_SECRET: str = ""
    GOOGLE_REFRESH_TOKEN: str = ""
    GOOGLE_CREDENTIALS_PATH: str = "./credentials.json"

    # --- Observability ---
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "digital-fte"
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # --- Directories ---
    UPLOAD_DIR: str = "./uploads"
    GENERATED_DIR: str = "./generated"

    model_config = {
        "env_file": _env_path,
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
