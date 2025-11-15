from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field, PositiveInt, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_ENV_PATH = _PROJECT_ROOT / ".env"

# Load .env early so the process follows the same configuration strategy
# both in local development and inside Docker containers.
if _DEFAULT_ENV_PATH.exists():
    load_dotenv(dotenv_path=_DEFAULT_ENV_PATH, override=False)


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    api_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    api_port: PositiveInt = Field(default=8080, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="APP_LOG_LEVEL")

    chroma_host: str = Field(default="localhost", alias="CHROMA_HOST")
    chroma_port: PositiveInt = Field(default=8000, alias="CHROMA_PORT")
    chroma_ssl: bool = Field(default=False, alias="CHROMA_SSL")
    chroma_api_key: str = Field(default="", alias="CHROMA_API_KEY")
    chroma_collection: str = Field(default="book_pages", alias="CHROMA_COLLECTION")
    chroma_persist_directory: str = Field(default="", alias="CHROMA_PERSIST_DIR")
    chroma_anonymized_telemetry: bool = Field(
        default=False, alias="CHROMA_ANONYMIZED_TELEMETRY"
    )

    embedding_provider: str = Field(default="openai", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")

    redis_url: Optional[str] = Field(default=None, alias="REDIS_URL")
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: PositiveInt = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")

    model_config = SettingsConfigDict(
        env_file=_DEFAULT_ENV_PATH if _DEFAULT_ENV_PATH.exists() else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def redis_dsn(self) -> str:
        if self.redis_url:
            return self.redis_url
        auth_segment = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth_segment}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @field_validator("log_level")
    @classmethod
    def _normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        valid_levels = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        if normalized not in valid_levels:
            logger.warning("Unsupported APP_LOG_LEVEL '%s', falling back to INFO.", value)
            return "INFO"
        return normalized

    @field_validator("embedding_provider")
    @classmethod
    def _validate_provider(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in {"openai"}:
            raise ValueError(
                "Unsupported EMBEDDING_PROVIDER. Only 'openai' is currently supported."
            )
        return normalized


@lru_cache
def get_settings() -> Settings:
    settings = Settings()  # type: ignore[call-arg]
    logger.debug(
        "Settings loaded",
        extra={
            "chroma_host": settings.chroma_host,
            "chroma_port": settings.chroma_port,
            "collection": settings.chroma_collection,
            "redis_host": settings.redis_host if not settings.redis_url else "custom-url",
            "redis_port": settings.redis_port if not settings.redis_url else "n/a",
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.embedding_model,
        },
    )
    return settings


__all__ = ["Settings", "get_settings"]

