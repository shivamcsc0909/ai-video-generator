"""
Application configuration loaded from environment variables / .env file.
Uses pydantic-settings for validation and type coercion.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings.

    All fields are loaded from environment variables or the `.env` file
    in the project root.  Sensitive fields (API keys, passwords) are
    typed as ``Optional[str]`` so they can be omitted in development.
    """

    # ------------------------------------------------------------------ #
    # Application
    # ------------------------------------------------------------------ #
    APP_NAME: str = "Local AI Video Production Studio"
    APP_ENV: str = "development"
    APP_PORT: int = 8000
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    DEBUG: bool = False

    # Fernet symmetric encryption key for ProviderAccount.encrypted_api_key
    # Generate with: from cryptography.fernet import Fernet; Fernet.generate_key()
    ENCRYPTION_KEY: str = "change-me-generate-with-fernet-generate_key"

    # ------------------------------------------------------------------ #
    # Database
    # ------------------------------------------------------------------ #
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/aivideo"
    DATABASE_SYNC_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/aivideo"

    # ------------------------------------------------------------------ #
    # Redis / Celery
    # ------------------------------------------------------------------ #
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ------------------------------------------------------------------ #
    # Storage paths
    # ------------------------------------------------------------------ #
    STORAGE_BASE_PATH: str = "./storage"

    @property
    def PROJECTS_PATH(self) -> Path:  # noqa: N802
        return Path(self.STORAGE_BASE_PATH) / "projects"

    @property
    def ASSETS_PATH(self) -> Path:  # noqa: N802
        return Path(self.STORAGE_BASE_PATH) / "assets"

    @property
    def RENDERS_PATH(self) -> Path:  # noqa: N802
        return Path(self.STORAGE_BASE_PATH) / "renders"

    @property
    def TEMP_PATH(self) -> Path:  # noqa: N802
        return Path(self.STORAGE_BASE_PATH) / "temp"

    @property
    def MODELS_PATH(self) -> Path:  # noqa: N802
        return Path(self.STORAGE_BASE_PATH) / "models"

    # ------------------------------------------------------------------ #
    # ComfyUI (local image / video generation)
    # ------------------------------------------------------------------ #
    COMFYUI_URL: str = "http://127.0.0.1:8188"
    COMFYUI_ENABLED: bool = False

    # ------------------------------------------------------------------ #
    # Local AI services
    # ------------------------------------------------------------------ #
    LOCAL_LLM_URL: str = "http://127.0.0.1:11434"
    LOCAL_LLM_MODEL: str = "llama3"
    WHISPER_MODEL: str = "base"
    LOCAL_TTS_ENGINE: str = "coqui"

    # ------------------------------------------------------------------ #
    # External API credentials  (never logged / stored in plaintext in DB)
    # ------------------------------------------------------------------ #
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    HF_TOKEN: Optional[str] = None
    FAL_KEY: Optional[str] = None
    REPLICATE_API_TOKEN: Optional[str] = None
    ELEVENLABS_API_KEY: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Hardware
    # ------------------------------------------------------------------ #
    FORCE_CPU: bool = False
    MAX_CONCURRENT_JOBS: int = 2

    # ------------------------------------------------------------------ #
    # Observability
    # ------------------------------------------------------------------ #
    LOG_LEVEL: str = "INFO"

    # ------------------------------------------------------------------ #
    # Auth / Admin
    # ------------------------------------------------------------------ #
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: Optional[str] = None
    JWT_EXPIRE_MINUTES: int = 10080  # 7 days

    # ------------------------------------------------------------------ #
    # Pydantic-settings configuration
    # ------------------------------------------------------------------ #
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    def ensure_storage_dirs(self) -> None:
        """Create all storage directories if they do not already exist."""
        for path in (
            self.PROJECTS_PATH,
            self.ASSETS_PATH,
            self.RENDERS_PATH,
            self.TEMP_PATH,
            self.MODELS_PATH,
        ):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton ``Settings`` instance.

    Using ``@lru_cache`` guarantees the ``.env`` file is parsed only once
    per process lifetime, which is important for Celery workers that share
    the same process.
    """
    return Settings()
