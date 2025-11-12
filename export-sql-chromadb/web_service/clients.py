from __future__ import annotations

import logging
from functools import lru_cache
from typing import List, Sequence

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.errors import NotFoundError

try:
    from chromadb.utils import embedding_functions
except ImportError:  # pragma: no cover - compatibility with newer Chroma releases
    embedding_functions = None  # type: ignore

from redis import Redis

from .config import Settings, get_settings

logger = logging.getLogger(__name__)


class QueryEmbedder:
    """Thin wrapper around Chroma's OpenAI embedding helper."""

    def __init__(self, settings: Settings):
        self._provider = settings.embedding_provider
        self._model = settings.embedding_model
        self._api_key = settings.openai_api_key

        if self._provider != "openai":
            raise RuntimeError(f"Unsupported embedding provider: {self._provider}")

        if not self._api_key:
            raise RuntimeError("OPENAI_API_KEY is required for query embeddings.")

        if embedding_functions is None:
            raise RuntimeError(
                "chromadb.utils.embedding_functions is unavailable. "
                "Upgrade/downgrade chromadb to a compatible version."
            )

        self._embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=self._api_key,
            model_name=self._model,
        )

    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        if not texts:
            return []
        embeddings = self._embedding_function(texts)
        logger.debug("Generated embeddings for %d text(s).", len(texts))
        return embeddings


@lru_cache
def get_chroma_client(settings: Settings | None = None):
    cfg = settings or get_settings()
    sdk_settings = ChromaSettings(
        anonymized_telemetry=cfg.chroma_anonymized_telemetry,
    )

    if cfg.chroma_persist_directory:
        logger.info(
            "Connecting to Chroma persistent client at %s", cfg.chroma_persist_directory
        )
        client = chromadb.PersistentClient(path=cfg.chroma_persist_directory, settings=sdk_settings)
    else:
        logger.info(
            "Connecting to Chroma HTTP client at %s:%s (ssl=%s)",
            cfg.chroma_host,
            cfg.chroma_port,
            cfg.chroma_ssl,
        )
        headers = {"Authorization": cfg.chroma_api_key} if cfg.chroma_api_key else None
        client = chromadb.HttpClient(
            host=cfg.chroma_host,
            port=cfg.chroma_port,
            ssl=cfg.chroma_ssl,
            headers=headers,
            settings=sdk_settings,
        )

    return client


@lru_cache
def get_query_embedder(settings: Settings | None = None) -> QueryEmbedder:
    cfg = settings or get_settings()
    return QueryEmbedder(cfg)


@lru_cache
def get_collection(settings: Settings | None = None):
    cfg = settings or get_settings()
    client = get_chroma_client(cfg)
    try:
        collection = client.get_collection(cfg.chroma_collection)
        logger.info("Connected to Chroma collection '%s'.", cfg.chroma_collection)
    except NotFoundError as exc:
        logger.error("Chroma collection '%s' not found.", cfg.chroma_collection)
        raise RuntimeError(
            f"Chroma collection '{cfg.chroma_collection}' not found. Ensure the exporter has populated it."
        ) from exc
    return collection


@lru_cache
def get_redis_client(settings: Settings | None = None) -> Redis:
    cfg = settings or get_settings()
    logger.info("Connecting to Redis at %s", cfg.redis_dsn)
    return Redis.from_url(cfg.redis_dsn, decode_responses=True)


__all__ = [
    "get_chroma_client",
    "get_collection",
    "get_query_embedder",
    "get_redis_client",
    "QueryEmbedder",
]

