from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, PositiveInt, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_ENV_PATH = _PROJECT_ROOT / ".env"

if _DEFAULT_ENV_PATH.exists():
    load_dotenv(dotenv_path=_DEFAULT_ENV_PATH, override=False)


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    database_url: str = Field(
        default="sqlite:///./ai_benchmarker.db",
        alias="DATABASE_URL",
    )
    api_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    api_port: PositiveInt = Field(default=8090, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="APP_LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=_DEFAULT_ENV_PATH if _DEFAULT_ENV_PATH.exists() else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("log_level")
    @classmethod
    def _normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        valid_levels = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        if normalized not in valid_levels:
            logger.warning("Unsupported APP_LOG_LEVEL '%s', falling back to INFO.", value)
            return "INFO"
        return normalized


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


__all__ = ["Settings", "get_settings"]
