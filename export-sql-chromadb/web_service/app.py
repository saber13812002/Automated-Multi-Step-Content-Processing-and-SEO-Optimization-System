from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List

import anyio
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from .clients import (
    get_chroma_client,
    get_collection,
    get_query_embedder,
    get_redis_client,
    validate_chroma_connection,
    validate_embedder_config,
    validate_redis_connection,
)
from .config import Settings, get_settings
from .logging_setup import configure_logging
from .schemas import HealthComponent, HealthResponse, SearchRequest, SearchResponse, SearchResult

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)

    logger.info(
        "🚀 Starting Chroma Search Service",
        extra={
            "chroma_host": settings.chroma_host,
            "chroma_port": settings.chroma_port,
            "collection": settings.chroma_collection,
            "redis": settings.redis_dsn,
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.embedding_model,
        },
    )

    # Validate all connections before starting service
    logger.info("📋 Running pre-startup validations...")
    
    errors = []
    
    # Validate ChromaDB
    chroma_valid, chroma_error = validate_chroma_connection(settings)
    if not chroma_valid:
        errors.append(f"ChromaDB: {chroma_error}")
    
    # Validate Redis (optional, but warn if not available)
    redis_valid, redis_error = validate_redis_connection(settings)
    if not redis_valid:
        logger.warning(
            "⚠️  Redis validation failed (service will continue, but health check may fail): %s",
            redis_error
        )
    
    # Validate Embedder config
    embedder_valid, embedder_error = validate_embedder_config(settings)
    if not embedder_valid:
        errors.append(f"Embedder: {embedder_error}")
    
    # Fail fast if critical errors
    if errors:
        error_summary = "\n".join(f"  • {err}" for err in errors)
        fatal_msg = (
            "❌ Service startup failed due to configuration errors:\n"
            f"{error_summary}\n"
            "Please fix the errors above and restart the service."
        )
        logger.error(fatal_msg)
        raise RuntimeError(fatal_msg)
    
    logger.info("✅ All validations passed. Initializing clients...")
    
    # Initialize clients - these should not fail now that we validated
    try:
        chroma_client = get_chroma_client(settings)
        collection = get_collection(settings)
        embedder = get_query_embedder(settings)
        redis_client = get_redis_client(settings)
    except Exception as exc:
        logger.exception("Failed to initialize clients after validation")
        raise RuntimeError(f"Failed to initialize clients: {exc}") from exc

    app.state.settings = settings
    app.state.chroma_client = chroma_client
    app.state.collection = collection
    app.state.embedder = embedder
    app.state.redis_client = redis_client

    try:
        yield
    finally:
        try:
            redis_client.close()
        except Exception:  # pragma: no cover - defensive shutdown
            logger.exception("Failed to close Redis connection.")


app = FastAPI(title="Chroma Search Service", version="1.0.0", lifespan=lifespan)


def get_app_state(request: Request) -> Dict[str, Any]:
    return {
        "settings": request.app.state.settings,
        "chroma_client": request.app.state.chroma_client,
        "collection": request.app.state.collection,
        "embedder": request.app.state.embedder,
        "redis_client": request.app.state.redis_client,
    }


@app.post(
    "/search",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
)
async def search_documents(
    payload: SearchRequest,
    request: Request,
    app_state: Dict[str, Any] = Depends(get_app_state),
) -> SearchResponse:
    logger.info("Received search request", extra={"query": payload.query, "top_k": payload.top_k})

    settings: Settings = app_state["settings"]
    collection = app_state["collection"]
    embedder = app_state["embedder"]

    start = time.perf_counter()
    try:
        embeddings = await anyio.to_thread.run_sync(embedder.embed, [payload.query])
    except Exception as exc:  # pragma: no cover - network errors
        logger.exception("Embedding generation failed.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate embeddings for the query.",
        ) from exc

    try:
        results = await anyio.to_thread.run_sync(
            collection.query,
            query_embeddings=embeddings,
            n_results=payload.top_k,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:  # pragma: no cover - network errors
        logger.exception("ChromaDB query failed.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="ChromaDB query failed.",
        ) from exc

    took_ms = (time.perf_counter() - start) * 1000.0
    ids = results.get("ids", [[]])[0]
    distances = results.get("distances", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    response_items: List[SearchResult] = []
    for index, doc_id in enumerate(ids):
        distance = distances[index] if index < len(distances) else None
        score = None
        if distance is not None:
            score = 1.0 - distance
        response_items.append(
            SearchResult(
                id=str(doc_id),
                distance=distance if distance is not None else None,
                score=score,
                document=documents[index] if index < len(documents) else None,
                metadata=metadatas[index] if index < len(metadatas) else {},
            )
        )

    logger.info(
        "Search completed",
        extra={
            "query": payload.query,
            "top_k": payload.top_k,
            "returned": len(response_items),
            "took_ms": took_ms,
        },
    )

    return SearchResponse(
        query=payload.query,
        top_k=payload.top_k,
        returned=len(response_items),
        provider=settings.embedding_provider,
        model=settings.embedding_model,
        collection=settings.chroma_collection,
        results=response_items,
        took_ms=took_ms,
    )


@app.get("/health", response_model=HealthResponse)
async def healthcheck(request: Request, app_state: Dict[str, Any] = Depends(get_app_state)):
    settings: Settings = app_state["settings"]
    collection = app_state["collection"]
    redis_client = app_state["redis_client"]

    chroma_component = HealthComponent(status="ok")
    collection_component = HealthComponent(status="ok")
    redis_component = HealthComponent(status="ok")
    overall_status = "ok"

    # Chroma heartbeat
    try:
        start = time.perf_counter()
        chroma_client = app_state["chroma_client"]
        heartbeat = await anyio.to_thread.run_sync(chroma_client.heartbeat)
        chroma_component.latency_ms = (time.perf_counter() - start) * 1000.0
        chroma_component.extras = {"heartbeat": heartbeat}
    except Exception as exc:
        logger.exception("Chroma heartbeat failed.")
        chroma_component.status = "error"
        chroma_component.detail = str(exc)
        overall_status = "degraded"

    # Collection stats
    try:
        start = time.perf_counter()
        count = await anyio.to_thread.run_sync(collection.count)
        collection_component.latency_ms = (time.perf_counter() - start) * 1000.0
        collection_component.extras = {
            "collection": settings.chroma_collection,
            "documents": count,
        }
    except Exception as exc:
        logger.exception("Failed to fetch collection stats.")
        collection_component.status = "error"
        collection_component.detail = str(exc)
        overall_status = "degraded"

    # Redis connectivity
    try:
        start = time.perf_counter()
        pong = await anyio.to_thread.run_sync(redis_client.ping)
        redis_component.latency_ms = (time.perf_counter() - start) * 1000.0
        redis_component.extras = {"ping": pong, "url": settings.redis_dsn}
    except Exception as exc:
        logger.exception("Redis ping failed.")
        redis_component.status = "error"
        redis_component.detail = str(exc)
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        chroma=chroma_component,
        collection=collection_component,
        redis=redis_component,
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug("Handling request", extra={"path": request.url.path, "method": request.method})
    try:
        response = await call_next(request)
        return response
    except Exception:
        logger.exception("Unhandled exception during request processing.")
        raise


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception", extra={"path": request.url.path})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


__all__ = ["app"]

