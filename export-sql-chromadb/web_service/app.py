from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import anyio
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

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
from .database import init_database, get_search_history, get_search_results, save_search
from .logging_setup import configure_logging
from .schemas import (
    HealthComponent,
    HealthResponse,
    SearchHistoryResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)

    # Print configuration for comparison (without sensitive data)
    config_summary = f"""
{'=' * 80}
🚀 Starting Chroma Search Service
{'=' * 80}
📋 Configuration Settings:
   App Host:               {settings.api_host}
   App Port:               {settings.api_port}
   Log Level:              {settings.log_level}
   
   ChromaDB Host:          {settings.chroma_host}
   ChromaDB Port:          {settings.chroma_port}
   ChromaDB SSL:           {settings.chroma_ssl}
   ChromaDB API Key:       {'***SET***' if settings.chroma_api_key else '(not set)'}
   ChromaDB Collection:    {settings.chroma_collection}
   ChromaDB Persist Dir:   {settings.chroma_persist_directory or '(not set)'}
   ChromaDB Telemetry:     {settings.chroma_anonymized_telemetry}
   
   Embedding Provider:     {settings.embedding_provider}
   Embedding Model:        {settings.embedding_model}
   OpenAI API Key:         {'***SET***' if settings.openai_api_key else '(not set)'}
   
   Redis URL:              {settings.redis_url or '(not set)'}
   Redis Host:             {settings.redis_host}
   Redis Port:             {settings.redis_port}
   Redis DB:               {settings.redis_db}
   Redis Password:         {'***SET***' if settings.redis_password else '(not set)'}
   Redis DSN:              {settings.redis_dsn}
{'=' * 80}
"""
    print(config_summary)
    logger.info(
        "Service configuration loaded",
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
    
    # Initialize database
    try:
        init_database()
        logger.info("Database initialized")
    except Exception as exc:
        logger.warning("Failed to initialize database (search history will not be saved): %s", exc)
    
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

# Add CORS middleware for HTML UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for HTML UI
from pathlib import Path

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # Serve index.html at root
    @app.get("/")
    async def root():
        index_path = static_dir / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return {"message": "Chroma Search API", "docs": "/docs", "health": "/health"}


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
    
    # Try query_texts first (if collection has embedding function)
    # This is the same approach as verify_chroma_export.py
    try:
        results = await anyio.to_thread.run_sync(
            collection.query,
            query_texts=[payload.query],
            n_results=payload.top_k,
            include=["documents", "metadatas", "distances"],
        )
        logger.debug("Used query_texts (collection has embedding function)")
    except (ValueError, TypeError, AttributeError) as text_query_exc:
        # If query_texts fails, generate embeddings and use query_embeddings
        logger.debug("query_texts failed, generating embeddings and using query_embeddings: %s", str(text_query_exc))
        try:
            embeddings = await anyio.to_thread.run_sync(embedder.embed, [payload.query])
            if not embeddings or len(embeddings) == 0:
                raise ValueError("Failed to generate embeddings for query")
            
            results = await anyio.to_thread.run_sync(
                collection.query,
                query_embeddings=embeddings,
                n_results=payload.top_k,
                include=["documents", "metadatas", "distances"],
            )
            logger.debug("Used query_embeddings")
        except Exception as embed_exc:  # pragma: no cover - network errors
            error_msg = f"Failed to query ChromaDB: {str(embed_exc)}"
            logger.exception("ChromaDB query failed after trying both methods.", extra={"error": str(embed_exc), "query": payload.query})
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=error_msg,
            ) from embed_exc
    except Exception as exc:  # pragma: no cover - network errors
        error_msg = f"ChromaDB query failed: {str(exc)}"
        logger.exception("ChromaDB query failed.", extra={"error": str(exc), "query": payload.query})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=error_msg,
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

    response = SearchResponse(
        query=payload.query,
        top_k=payload.top_k,
        returned=len(response_items),
        provider=settings.embedding_provider,
        model=settings.embedding_model,
        collection=settings.chroma_collection,
        results=response_items,
        took_ms=took_ms,
    )

    # Save to database if requested
    if payload.save:
        try:
            # Convert results to dict for JSON serialization
            results_dict = [item.model_dump() for item in response_items]
            save_search(
                query=payload.query,
                result_count=len(response_items),
                took_ms=took_ms,
                collection=settings.chroma_collection,
                provider=settings.embedding_provider,
                model=settings.embedding_model,
                results=results_dict,
            )
            logger.debug("Search results saved to database")
        except Exception as exc:
            logger.warning("Failed to save search to database: %s", exc)
            # Don't fail the request if saving fails

    return response


@app.get("/history", response_model=SearchHistoryResponse)
async def get_history(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of searches to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    search_id: Optional[int] = Query(None, description="Get specific search by ID"),
):
    """Get search history."""
    try:
        searches, total = get_search_history(limit=limit, offset=offset, search_id=search_id)
        return SearchHistoryResponse(
            searches=searches,
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        logger.exception("Failed to get search history")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve search history: {exc}",
        ) from exc


@app.get("/history/{search_id}", response_model=Dict[str, Any])
async def get_history_item(search_id: int):
    """Get full details of a specific search including results."""
    try:
        search_data = get_search_results(search_id)
        if not search_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Search with ID {search_id} not found",
            )
        return search_data
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get search history item")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve search history item: {exc}",
        ) from exc


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

