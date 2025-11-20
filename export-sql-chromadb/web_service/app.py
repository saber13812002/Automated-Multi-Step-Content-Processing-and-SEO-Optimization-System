from __future__ import annotations

import hashlib
import json
import logging
import math
import secrets
import time
from contextlib import asynccontextmanager
from functools import partial
from typing import Any, Dict, List, Optional

import anyio
from chromadb.errors import NotFoundError as ChromaNotFoundError
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.responses import JSONResponse as StarletteJSONResponse

from .clients import (
    create_embedder_for_model,
    get_chroma_client,
    get_collection,
    get_query_embedder,
    get_redis_client,
    validate_chroma_connection,
    validate_embedder_config,
    validate_redis_connection,
)
from .config import Settings, get_settings
from .database import (
    approve_query,
    create_api_token,
    create_api_user,
    delete_export_job,
    delete_query,
    get_active_embedding_models,
    get_all_tokens,
    get_all_users,
    get_api_token,
    get_embedding_model,
    get_embedding_models,
    get_embedding_models_by_ids,
    get_export_job,
    get_export_jobs,
    get_query_approvals,
    get_query_stats,
    get_search_history,
    get_search_results,
    get_search_votes,
    get_token_usage_today,
    get_top_search_queries,
    get_vote_stats,
    get_vote_summary,
    increment_token_usage,
    init_database,
    reject_query,
    revoke_token,
    save_search,
    save_search_vote,
    set_embedding_model_active,
    sync_embedding_models_from_jobs,
    update_embedding_model_color,
    update_query_search_count,
)
from .logging_setup import configure_logging
from .schemas import (
    ChromaCollectionInfo,
    ChromaCollectionsResponse,
    ChromaDeleteResponse,
    ChromaTestResponse,
    CreateTokenRequest,
    CreateUserRequest,
    DeleteJobResponse,
    EmbeddingModelItem,
    EmbeddingModelsResponse,
    ExportCommandRequest,
    ExportCommandResponse,
    ExportJobDetail,
    ExportJobItem,
    ExportJobsResponse,
    HealthComponent,
    HealthResponse,
    MultiModelResult,
    MultiModelSearchRequest,
    MultiModelSearchResponse,
    PaginationInfo,
    QueryApprovalItem,
    QueryApprovalsResponse,
    QueryStatsResponse,
    SearchHistoryResponse,
    TopQueryItem,
    TopQueriesResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    TokenItem,
    TokenResponse,
    TokenUsageResponse,
    TokensResponse,
    ToggleModelRequest,
    UpdateModelColorRequest,
    UserItem,
    UsersResponse,
    UvicornCommandRequest,
    UvicornCommandResponse,
    VoteItem,
    VoteRequest,
    VoteResponse,
    VoteSummaryItem,
    VoteSummaryResponse,
    VotesResponse,
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


app = FastAPI(
    title="Chroma Search Service",
    version="1.0.0",
    description="""
    سرویس وب FastAPI برای جستجوی معنایی در ChromaDB.
    
    ## ویژگی‌ها
    
    - جستجوی معنایی با استفاده از embeddings
    - مدیریت سوابق جستجو
    - پنل مدیریت برای Export Jobs و Query Approvals
    - Health checks برای ChromaDB و Redis
    - تولید دستورات Export و Uvicorn
    
    ## مستندات
    
    - `/docs` - Swagger UI
    - `/redoc` - ReDoc
    """,
    lifespan=lifespan,
    tags_metadata=[
        {
            "name": "search",
            "description": "جستجوی معنایی در ChromaDB",
        },
        {
            "name": "admin",
            "description": "پنل مدیریت و تنظیمات",
        },
        {
            "name": "health",
            "description": "بررسی وضعیت سرویس‌ها",
        },
    ],
)

# Override default JSONResponse to ensure UTF-8 encoding
class UTF8JSONResponse(StarletteJSONResponse):
    media_type = "application/json; charset=utf-8"

app.default_response_class = UTF8JSONResponse

# Add CORS middleware for HTML UI (before auth middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth middleware must be added after CORS but before other middleware
# It's already defined as a function, we'll register it properly

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


def _build_embedding_model_item(model: Dict[str, Any]) -> EmbeddingModelItem:
    """Convert DB row dict to schema object."""
    return EmbeddingModelItem(**model)


def _is_valid_hex_color(value: str) -> bool:
    """Validate HEX color codes like #fff or #ffffff."""
    if not value or not value.startswith("#"):
        return False
    hex_part = value[1:]
    if len(hex_part) not in (3, 6):
        return False
    allowed = set("0123456789abcdefABCDEF")
    return all(ch in allowed for ch in hex_part)


def _build_multi_search_cache_key(query: str, model_ids: List[int], top_k: int) -> str:
    """Create deterministic cache key for multi-model search."""
    normalized_query = " ".join(query.strip().lower().split())
    digest = hashlib.sha256(normalized_query.encode("utf-8")).hexdigest()
    ids_part = ",".join(str(mid) for mid in sorted(set(model_ids)))
    return f"multi-search:{digest}:{ids_part}:k{top_k}"


def _build_single_search_cache_key(
    query: str,
    provider: str,
    model: str,
    collection: str,
    top_k: int,
    page: int = 1,
    page_size: int = 20,
    include_full_context: bool = False,
) -> str:
    """Create deterministic cache key for single-model search with model info."""
    normalized_query = " ".join(query.strip().lower().split())
    digest = hashlib.sha256(normalized_query.encode("utf-8")).hexdigest()
    # Include model info to ensure cache is model-specific
    model_part = f"{provider}:{model}:{collection}"
    context_flag = "ctx" if include_full_context else "seg"
    return f"search:{digest}:{model_part}:k{top_k}:p{page}:ps{page_size}:{context_flag}"


@app.post(
    "/search",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="جستجوی معنایی",
    description="""
    انجام جستجوی معنایی در ChromaDB با استفاده از embeddings.
    
    کوئری متنی کاربر امبدینگ می‌شود و سپس در ChromaDB جستجو می‌شود.
    نتایج شامل متن سند، متادیتا، امتیاز شباهت و فاصله است.
    """,
    tags=["search"],
)
async def search_documents(
    payload: SearchRequest,
    request: Request,
    app_state: Dict[str, Any] = Depends(get_app_state),
) -> SearchResponse:
    logger.info(
        "Received search request",
        extra={
            "query": payload.query,
            "top_k": payload.top_k,
            "page": payload.page,
            "page_size": payload.page_size,
            "model_id": payload.model_id,
        },
    )

    settings: Settings = app_state["settings"]
    chroma_client = app_state["chroma_client"]
    redis_client = app_state.get("redis_client")
    
    # If model_id is provided, use that model's collection and embedder
    if payload.model_id:
        from web_service.database import get_embedding_model
        from web_service.clients import create_embedder_for_model
        
        model_info = get_embedding_model(payload.model_id)
        if not model_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"مدل با شناسه {payload.model_id} یافت نشد.",
            )
        
        if not model_info.get("is_active", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"مدل با شناسه {payload.model_id} غیرفعال است.",
            )
        
        # Get collection for this specific model
        collection_name = model_info["collection"]
        try:
            collection = chroma_client.get_collection(collection_name)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"عدم دسترسی به کالکشن {collection_name}: {exc}",
            ) from exc
        
        # Create embedder for this specific model
        embedder = create_embedder_for_model(
            provider=model_info["embedding_provider"],
            model=model_info["embedding_model"],
            api_key=settings.openai_api_key,
            device="",
        )
        
        # Use model-specific provider and model for cache key
        actual_provider = model_info["embedding_provider"]
        actual_model = model_info["embedding_model"]
        actual_collection = collection_name
        
        logger.info(
            "Using model-specific collection and embedder",
            extra={
                "model_id": payload.model_id,
                "collection": collection_name,
                "provider": actual_provider,
                "model": actual_model,
            },
        )
    else:
        # Use default collection and embedder
        collection = app_state["collection"]
        embedder = app_state["embedder"]
        actual_provider = settings.embedding_provider
        actual_model = settings.embedding_model
        actual_collection = settings.chroma_collection
        
        logger.debug("Using default collection and embedder")
    
    # Check Redis cache if enabled
    use_cache = payload.use_cache if hasattr(payload, 'use_cache') else settings.default_use_cache
    include_full_context = getattr(payload, 'include_full_context', False)
    if use_cache and redis_client:
        cache_key = _build_single_search_cache_key(
            query=payload.query,
            provider=actual_provider,
            model=actual_model,
            collection=actual_collection,
            top_k=payload.top_k,
            page=payload.page,
            page_size=payload.page_size,
            include_full_context=include_full_context,
        )
        try:
            cached_raw = redis_client.get(cache_key)
            if cached_raw:
                cached_data = json.loads(cached_raw)
                logger.info("Cache hit for query: %s", payload.query[:50])
                return SearchResponse(
                    **cached_data,
                    cache_source="cache",
                )
        except Exception as cache_exc:
            logger.debug("Cache read failed: %s", cache_exc)

    # Validate that query embedding model matches collection's export model
    try:
        collection_metadata = await anyio.to_thread.run_sync(lambda: collection.metadata)
        if collection_metadata and isinstance(collection_metadata, dict):
            export_provider = collection_metadata.get("embedding_provider")
            export_model = collection_metadata.get("embedding_model")
            if export_provider and export_model:
                if export_provider != actual_provider or export_model != actual_model:
                    warning_msg = (
                        f"⚠️  Warning: Query model mismatch! "
                        f"Collection was exported with {export_provider}/{export_model}, "
                        f"but query is using {actual_provider}/{actual_model}. "
                        f"Results may be inaccurate."
                    )
                    logger.warning(warning_msg)
                    # Don't fail the request, but log the warning
                else:
                    logger.debug(
                        "✅ Query model matches collection export model: %s/%s",
                        export_provider,
                        export_model,
                    )
    except Exception as meta_exc:
        logger.warning("Could not validate embedding model match: %s", meta_exc)

    start = time.perf_counter()
    
    # Calculate n_results based on pagination
    # For pagination, we need to fetch enough results for the current page
    # If pagination is enabled, fetch enough for current page + some buffer for estimation
    if settings.enable_pagination:
        # Fetch enough results for current page, but cap at max_estimated_results
        n_results = min((payload.page * payload.page_size), settings.max_estimated_results)
        # Ensure we fetch at least page_size results
        n_results = max(n_results, payload.page_size)
    else:
        n_results = payload.top_k
    
    # If model_id is provided, we MUST use query_embeddings to ensure we use the correct model
    # Otherwise, collection.query with query_texts might use a different embedding function
    if payload.model_id:
        # Generate embeddings with the model-specific embedder
        logger.debug("Model ID provided, generating embeddings with model-specific embedder")
        try:
            embeddings = await anyio.to_thread.run_sync(embedder.embed, [payload.query])
            if not embeddings or len(embeddings) == 0:
                raise ValueError("Failed to generate embeddings for query")
            
            query_func_embeddings = partial(
                collection.query,
                query_embeddings=embeddings,
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            )
            results = await anyio.to_thread.run_sync(query_func_embeddings)
            logger.debug("Used query_embeddings with model-specific embedder")
        except Exception as embed_exc:
            error_msg = f"Failed to query ChromaDB with model-specific embedder: {str(embed_exc)}"
            logger.exception("ChromaDB query failed with model-specific embedder.", extra={"error": str(embed_exc), "query": payload.query, "model_id": payload.model_id})
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=error_msg,
            ) from embed_exc
    else:
        # No model_id: Try query_texts first (if collection has embedding function)
        # This is the same approach as verify_chroma_export.py
        # Use functools.partial to pass keyword arguments to run_sync
        try:
            query_func = partial(
                collection.query,
                query_texts=[payload.query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            )
            results = await anyio.to_thread.run_sync(query_func)
            logger.debug("Used query_texts (collection has embedding function)")
        except (ValueError, TypeError, AttributeError) as text_query_exc:
            # If query_texts fails, generate embeddings and use query_embeddings
            logger.debug("query_texts failed, generating embeddings and using query_embeddings: %s", str(text_query_exc))
            try:
                embeddings = await anyio.to_thread.run_sync(embedder.embed, [payload.query])
                if not embeddings or len(embeddings) == 0:
                    raise ValueError("Failed to generate embeddings for query")
                
                query_func_embeddings = partial(
                    collection.query,
                    query_embeddings=embeddings,
                    n_results=n_results,
                    include=["documents", "metadatas", "distances"],
                )
                results = await anyio.to_thread.run_sync(query_func_embeddings)
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

    # Apply pagination to results if enabled
    if settings.enable_pagination:
        start_idx = (payload.page - 1) * payload.page_size
        end_idx = start_idx + payload.page_size
        ids = ids[start_idx:end_idx]
        distances = distances[start_idx:end_idx]
        documents = documents[start_idx:end_idx]
        metadatas = metadatas[start_idx:end_idx]

    # Helper function to get paragraph context
    async def get_paragraph_context(
        coll, book_id: int, page_id: int, paragraph_index: int
    ) -> Optional[str]:
        """Fetch and combine all segments from the same paragraph."""
        try:
            # Try to get paragraph_full_text from metadata first (faster)
            # If not available, fetch all segments and combine
            para_results = await anyio.to_thread.run_sync(
                lambda: coll.get(
                    where={
                        "book_id": book_id,
                        "page_id": page_id,
                        "paragraph_index": paragraph_index,
                    },
                    include=["documents", "metadatas"],
                )
            )
            
            if not para_results.get("ids") or len(para_results["ids"]) == 0:
                return None
            
            # Check if paragraph_full_text is in metadata
            metadatas_list = para_results.get("metadatas", [])
            if metadatas_list and len(metadatas_list) > 0:
                first_meta = metadatas_list[0]
                if first_meta and "paragraph_full_text" in first_meta:
                    return first_meta["paragraph_full_text"]
            
            # Otherwise, combine segments
            segment_docs = para_results.get("documents", [])
            segment_metas = para_results.get("metadatas", [])
            
            # Create list of (segment_index, document) tuples
            segments_list = []
            for seg_idx, seg_meta in enumerate(segment_metas):
                if seg_idx < len(segment_docs):
                    seg_index = seg_meta.get("segment_index", 0) if seg_meta else 0
                    segments_list.append((seg_index, segment_docs[seg_idx]))
            
            # Sort by segment_index and combine
            segments_list.sort(key=lambda x: x[0])
            combined_text = " ".join([doc for _, doc in segments_list])
            return combined_text
        except Exception as exc:
            logger.debug("Failed to fetch paragraph context: %s", exc)
            return None

    response_items: List[SearchResult] = []
    for index, doc_id in enumerate(ids):
        distance = distances[index] if index < len(distances) else None
        score = None
        if distance is not None:
            score = 1.0 - distance
        
        metadata = metadatas[index] if index < len(metadatas) else {}
        document_text = documents[index] if index < len(documents) else None
        
        # If include_full_context is requested and this is a segment (not page-level)
        if include_full_context and metadata and not metadata.get("page_level"):
            # Try to get paragraph_full_text from metadata first
            if "paragraph_full_text" in metadata:
                document_text = metadata["paragraph_full_text"]
            else:
                # Fetch all segments from same paragraph and combine
                book_id = metadata.get("book_id")
                page_id = metadata.get("page_id")
                para_index = metadata.get("paragraph_index")
                if book_id is not None and page_id is not None and para_index is not None:
                    para_context = await get_paragraph_context(collection, book_id, page_id, para_index)
                    if para_context:
                        document_text = para_context
        
        # Log document length for debugging (first result only)
        if index == 0 and document_text:
            logger.debug(
                "First result document length: %d chars (metadata segment_length: %s)",
                len(document_text),
                metadata.get("segment_length", "N/A"),
            )
        
        response_items.append(
            SearchResult(
                id=str(doc_id),
                distance=distance if distance is not None else None,
                score=score,
                document=document_text,
                metadata=metadata,
            )
        )

    # Get total documents in collection if enabled
    total_documents = None
    if settings.enable_total_documents:
        try:
            total_documents = await anyio.to_thread.run_sync(collection.count)
        except Exception as exc:
            logger.warning("Failed to get total documents count: %s", exc)

    # Calculate pagination info if enabled
    pagination = None
    if settings.enable_pagination:
        # Check if we got max results (might be more)
        all_results_count = len(results.get("ids", [[]])[0])
        estimated_total = None
        has_next_page = False
        total_pages = None

        if settings.enable_estimated_results:
            if all_results_count >= settings.max_estimated_results:
                estimated_total = "1000+"
                has_next_page = True
            else:
                estimated_total = str(all_results_count)
                # Check if there are more results on next page
                has_next_page = (payload.page * payload.page_size) < all_results_count
                if estimated_total and not estimated_total.startswith("1000+"):
                    try:
                        total_pages = (int(estimated_total) + payload.page_size - 1) // payload.page_size
                    except (ValueError, TypeError):
                        pass
        else:
            # Without estimation, just check if we have a full page
            has_next_page = len(response_items) == payload.page_size

        pagination = PaginationInfo(
            page=payload.page,
            page_size=payload.page_size,
            total_pages=total_pages,
            has_next_page=has_next_page,
            has_previous_page=payload.page > 1,
            estimated_total_results=estimated_total,
        )

    logger.info(
        "Search completed",
        extra={
            "query": payload.query,
            "top_k": payload.top_k,
            "returned": len(response_items),
            "took_ms": took_ms,
            "page": payload.page if settings.enable_pagination else None,
            "page_size": payload.page_size if settings.enable_pagination else None,
        },
    )

    response = SearchResponse(
        query=payload.query,
        top_k=payload.top_k,
        returned=len(response_items),
        provider=actual_provider,
        model=actual_model,
        collection=actual_collection,
        results=response_items,
        took_ms=took_ms,
        total_documents=total_documents,
        pagination=pagination,
        cache_source="realtime",  # Mark as realtime (not from cache)
    )
    
    # Store in Redis cache if enabled
    if use_cache and redis_client and response_items:
        try:
            cache_key = _build_single_search_cache_key(
                query=payload.query,
                provider=actual_provider,
                model=actual_model,
                collection=actual_collection,
                top_k=payload.top_k,
                page=payload.page,
                page_size=payload.page_size,
                include_full_context=include_full_context,
            )
            # Convert response to dict for caching
            response_dict = {
                "query": response.query,
                "collection": response.collection,
                "provider": response.provider,
                "model": response.model,
                "returned": response.returned,
                "top_k": response.top_k,
                "results": [
                    {
                        "id": r.id,
                        "distance": r.distance,
                        "score": r.score,
                        "document": r.document,
                        "metadata": r.metadata,
                    }
                    for r in response.results
                ],
                "took_ms": response.took_ms,
                "total_documents": response.total_documents,
                "pagination": response.pagination.dict() if response.pagination else None,
            }
            redis_client.setex(
                cache_key,
                settings.search_cache_ttl,
                json.dumps(response_dict, ensure_ascii=False),
            )
            logger.debug("Cached search result for key: %s", cache_key)
        except Exception as cache_exc:
            logger.warning("Failed to cache search result: %s", cache_exc)

    # Save to database if requested
    if payload.save:
        try:
            # Convert results to dict for JSON serialization
            results_dict = [item.model_dump() for item in response_items]
            save_search(
                query=payload.query,
                result_count=len(response_items),
                took_ms=took_ms,
                collection=actual_collection,
                provider=actual_provider,
                model=actual_model,
                results=results_dict,
            )
            logger.debug("Search results saved to database")
        except Exception as exc:
            logger.warning("Failed to save search to database: %s", exc)
            # Don't fail the request if saving fails

    return response


@app.post(
    "/search/multi",
    response_model=MultiModelSearchResponse,
    tags=["search"],
    summary="جستجو با چند مدل انتخابی",
)
async def multi_model_search(
    payload: MultiModelSearchRequest,
    app_state: Dict[str, Any] = Depends(get_app_state),
) -> MultiModelSearchResponse:
    """Perform semantic search across up to 3 embedding models."""
    if not payload.model_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="حداقل یک مدل باید انتخاب شود.",
        )

    # Preserve selection order but ensure uniqueness
    ordered_ids: List[int] = []
    for model_id in payload.model_ids:
        if model_id not in ordered_ids:
            ordered_ids.append(model_id)

    models = get_embedding_models_by_ids(ordered_ids)
    model_map = {model["id"]: model for model in models}

    missing_ids = [mid for mid in ordered_ids if mid not in model_map]
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"مدل‌های {missing_ids} یافت نشدند.",
        )

    inactive_models = [model for model in models if not model["is_active"]]
    if inactive_models:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="برخی از مدل‌های انتخاب شده غیرفعال هستند.",
        )

    redis_client = app_state.get("redis_client")
    cache_key = _build_multi_search_cache_key(payload.query, ordered_ids, payload.top_k)
    if redis_client:
        try:
            cached_raw = redis_client.get(cache_key)
            if cached_raw:
                cached_payload = json.loads(cached_raw)
                return MultiModelSearchResponse(
                    **cached_payload, cache_source="cache"
                )
        except Exception as exc:  # pragma: no cover - cache errors
            logger.warning("Failed to read multi-search cache: %s", exc)

    settings: Settings = app_state["settings"]
    chroma_client = app_state["chroma_client"]

    model_count = len(ordered_ids)
    per_model_limit = (
        payload.top_k
        if model_count == 1
        else min(payload.top_k, math.ceil(20 / model_count))
    )
    overall_limit = (
        per_model_limit
        if model_count == 1
        else min(per_model_limit * model_count, 20)
    )
    fetch_n = min(max(per_model_limit, payload.top_k), settings.max_estimated_results)

    include_fields = ["documents", "metadatas", "distances"]
    per_model_results: Dict[int, List[Dict[str, Any]]] = {}
    model_errors: List[Dict[str, str]] = []

    start = time.perf_counter()

    for model_id in ordered_ids:
        model_info = model_map[model_id]
        collection_name = model_info["collection"]
        model_display_name = model_info["embedding_model"]
        
        try:
            collection = chroma_client.get_collection(collection_name)
            
            # Validate that query embedding model matches collection's export model
            try:
                collection_metadata = await anyio.to_thread.run_sync(lambda: collection.metadata)
                if collection_metadata and isinstance(collection_metadata, dict):
                    export_provider = collection_metadata.get("embedding_provider")
                    export_model = collection_metadata.get("embedding_model")
                    query_provider = model_info["embedding_provider"]
                    query_model = model_info["embedding_model"]
                    if export_provider and export_model:
                        if export_provider != query_provider or export_model != query_model:
                            warning_msg = (
                                f"⚠️  Model mismatch for collection '{collection_name}': "
                                f"exported with {export_provider}/{export_model}, "
                                f"but query uses {query_provider}/{query_model}. "
                                f"Results may be inaccurate."
                            )
                            logger.warning(warning_msg)
                        else:
                            logger.debug(
                                "✅ Model match for collection '%s': %s/%s",
                                collection_name,
                                export_provider,
                                export_model,
                            )
            except Exception as meta_exc:
                logger.debug("Could not validate model match for '%s': %s", collection_name, meta_exc)
                
        except Exception as exc:  # pragma: no cover - network errors
            error_msg = f"عدم دسترسی به کالکشن {collection_name}"
            logger.warning(
                "Failed to access collection '%s': %s", collection_name, exc
            )
            model_errors.append({
                "collection": collection_name,
                "model": model_display_name,
                "error": error_msg
            })
            continue  # Skip this model and continue with others

        try:
            # Create embedder for this specific model
            try:
                embedder = create_embedder_for_model(
                    provider=model_info["embedding_provider"],
                    model=model_info["embedding_model"],
                    api_key=settings.openai_api_key,
                    device="",  # Auto-detect device for HuggingFace
                )
                # Generate embeddings with model-specific embedder
                query_embeddings = await anyio.to_thread.run_sync(
                    embedder.embed, [payload.query]
                )
                if not query_embeddings or len(query_embeddings) == 0:
                    raise ValueError("Failed to generate embeddings for query")
                
                # Query using the generated embeddings
                query_func = partial(
                    collection.query,
                    query_embeddings=query_embeddings,
                    n_results=fetch_n,
                    include=include_fields,
                )
                results = await anyio.to_thread.run_sync(query_func)
                logger.debug(
                    "✅ Query embedded and searched for model %s/%s in collection '%s'",
                    model_info["embedding_provider"],
                    model_info["embedding_model"],
                    collection_name,
                )
            except Exception as embed_exc:
                # Fallback: try query_texts if collection has embedding function
                logger.debug(
                    "Model-specific embedding failed for '%s', trying collection's embedding function: %s",
                    collection_name,
                    embed_exc,
                )
                try:
                    query_func = partial(
                        collection.query,
                        query_texts=[payload.query],
                        n_results=fetch_n,
                        include=include_fields,
                    )
                    results = await anyio.to_thread.run_sync(query_func)
                    logger.warning(
                        "⚠️  Used collection's embedding function instead of model-specific embedder for '%s'",
                        collection_name,
                    )
                except Exception as text_query_exc:
                    raise embed_exc from text_query_exc
        except Exception as exc:  # pragma: no cover - network errors
            error_msg = f"جستجو در کالکشن {collection_name} ناموفق بود"
            logger.warning(
                "ChromaDB multi search failed for collection '%s': %s",
                collection_name,
                exc,
            )
            model_errors.append({
                "collection": collection_name,
                "model": model_display_name,
                "error": error_msg
            })
            continue  # Skip this model and continue with others

        ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        model_items: List[Dict[str, Any]] = []
        for index, doc_id in enumerate(ids):
            distance = distances[index] if index < len(distances) else None
            score = 1.0 - distance if distance is not None else None
            model_items.append(
                {
                    "id": str(doc_id),
                    "distance": distance,
                    "score": score,
                    "document": documents[index] if index < len(documents) else None,
                    "metadata": metadatas[index] if index < len(metadatas) else {},
                    "model_id": model_id,
                    "model_color": model_info["color"],
                    "embedding_model": model_info["embedding_model"],
                    "embedding_provider": model_info["embedding_provider"],
                }
            )
        per_model_results[model_id] = model_items

    # If all models failed, return an error
    if not per_model_results and model_errors:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"جستجو در تمام مدل‌ها ناموفق بود. {model_errors[0]['error']}",
        )

    # Only use successful models for combining results
    successful_model_ids = [mid for mid in ordered_ids if mid in per_model_results]
    successful_count = len(successful_model_ids)
    
    combined_results: List[Dict[str, Any]] = []
    if successful_count == 0:
        # This should not happen due to check above, but just in case
        combined_results = []
    elif successful_count == 1:
        combined_results = per_model_results[successful_model_ids[0]][:per_model_limit]
    else:
        # Round-robin merge with deduplication by document ID
        seen_doc_ids: set[str] = set()
        max_depth = max((len(per_model_results.get(mid, [])) for mid in successful_model_ids), default=0)
        for depth in range(max_depth):
            for model_id in successful_model_ids:
                if len(combined_results) >= overall_limit:
                    break
                model_items = per_model_results.get(model_id, [])
                if depth < len(model_items):
                    item = model_items[depth]
                    doc_id = item.get("id")
                    # Deduplicate: if we've seen this document, skip it
                    # (keep the first occurrence which has better score from earlier model)
                    if doc_id and doc_id not in seen_doc_ids:
                        combined_results.append(item)
                        seen_doc_ids.add(doc_id)
            if len(combined_results) >= overall_limit:
                break

    took_ms = (time.perf_counter() - start) * 1000.0
    response_payload = {
        "query": payload.query,
        "model_ids": ordered_ids,
        "returned": len(combined_results),
        "results": combined_results,
        "took_ms": took_ms,
        "errors": model_errors if model_errors else None,
    }

    if redis_client and combined_results:
        try:
            redis_client.setex(
                cache_key,
                24 * 60 * 60,
                json.dumps(response_payload, ensure_ascii=False),
            )
        except Exception as exc:  # pragma: no cover - cache errors
            logger.warning("Failed to store multi-search cache: %s", exc)

    if payload.save:
        # Only save successful models
        for model_id in successful_model_ids:
            model_info = model_map[model_id]
            model_results = per_model_results.get(model_id, [])[:per_model_limit]
            if not model_results:
                continue
            # Convert to SearchResult for persistence
            search_items = [
                SearchResult(
                    id=item["id"],
                    distance=item["distance"],
                    score=item["score"],
                    document=item["document"],
                    metadata=item["metadata"],
                )
                for item in model_results
            ]
            try:
                save_search(
                    query=payload.query,
                    result_count=len(search_items),
                    took_ms=took_ms,
                    collection=model_info["collection"],
                    provider=model_info["embedding_provider"],
                    model=model_info["embedding_model"],
                    results=[item.model_dump() for item in search_items],
                )
            except Exception as exc:  # pragma: no cover - db errors
                logger.warning("Failed to save multi-search history: %s", exc)

    return MultiModelSearchResponse(**response_payload, cache_source="live")


@app.post("/search/vote", response_model=VoteResponse, tags=["search"])
async def submit_vote(payload: VoteRequest) -> VoteResponse:
    """Register like/dislike for a search result."""
    if payload.model_id:
        model = get_embedding_model(payload.model_id)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="مدل انتخابی یافت نشد"
            )

    try:
        save_search_vote(
            guest_user_id=payload.guest_user_id,
            query=payload.query,
            vote_type=payload.vote_type,
            model_id=payload.model_id,
            result_id=payload.result_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    stats = get_vote_stats(query=payload.query, model_id=payload.model_id)
    return VoteResponse(success=True, likes=stats["likes"], dislikes=stats["dislikes"])


@app.get("/admin/search/votes", response_model=VotesResponse, tags=["admin"])
async def list_votes(
    limit: int = Query(100, ge=1, le=500),
    query: Optional[str] = Query(None, description="فیلتر براساس عبارت جستجو"),
    model_id: Optional[int] = Query(None, description="فیلتر براساس مدل"),
) -> VotesResponse:
    try:
        votes = get_search_votes(limit=limit, query=query, model_id=model_id)
        vote_items = [
            VoteItem(
                id=vote["id"],
                guest_user_id=vote["guest_user_id"],
                query=vote["query"],
                vote_type=vote["vote_type"],
                created_at=vote["created_at"],
                model_id=vote["model_id"],
                result_id=vote["result_id"],
                embedding_provider=vote["embedding_provider"],
                embedding_model=vote["embedding_model"],
                collection=vote["collection"],
                color=vote["color"],
            )
            for vote in votes
        ]
        return VotesResponse(votes=vote_items)
    except Exception as exc:
        logger.exception("Failed to load votes", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در دریافت رای‌ها",
        ) from exc


@app.get(
    "/admin/search/votes/summary",
    response_model=VoteSummaryResponse,
    tags=["admin"],
)
async def votes_summary(
    limit: int = Query(100, ge=1, le=500, description="تعداد ردیف‌های خلاصه"),
) -> VoteSummaryResponse:
    try:
        summary_rows = get_vote_summary(limit=limit)
        items = [
            VoteSummaryItem(
                query=row["query"],
                model_id=row["model_id"],
                embedding_provider=row["embedding_provider"],
                embedding_model=row["embedding_model"],
                collection=row["collection"],
                likes=row["likes"],
                dislikes=row["dislikes"],
                last_vote_at=row["last_vote_at"],
            )
            for row in summary_rows
        ]
        return VoteSummaryResponse(items=items)
    except Exception as exc:
        logger.exception("Failed to load vote summary", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در دریافت خلاصه رای‌ها",
        ) from exc


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


@app.get("/history/top", response_model=TopQueriesResponse)
async def get_top_queries(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of top queries to return"),
    min_count: int = Query(1, ge=1, description="Minimum search count to include"),
):
    """Get top search queries by count."""
    try:
        top_queries = get_top_search_queries(limit=limit, min_count=min_count)
        query_items = [
            TopQueryItem(
                query=q["query"],
                search_count=q["search_count"],
                last_searched_at=q["last_searched_at"],
            )
            for q in top_queries
        ]
        return TopQueriesResponse(queries=query_items, total=len(query_items))
    except Exception as exc:
        logger.exception("Failed to get top queries")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve top queries: {exc}",
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


@app.get("/admin/debug/segment-info/{doc_id:path}", tags=["admin", "debug"])
async def get_segment_info(
    doc_id: str,
    app_state: Dict[str, Any] = Depends(get_app_state),
):
    """Get diagnostic information about a segment/document."""
    try:
        settings: Settings = app_state["settings"]
        collection = app_state["collection"]
        
        # Get document from ChromaDB
        result = await anyio.to_thread.run_sync(
            lambda: collection.get(ids=[doc_id], include=["documents", "metadatas"])
        )
        
        if not result.get("ids") or len(result["ids"][0]) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {doc_id} not found",
            )
        
        document = result["documents"][0][0] if result["documents"] else None
        metadata = result["metadatas"][0][0] if result["metadatas"] else {}
        
        stored_text_length = len(document) if document else 0
        metadata_segment_length = metadata.get("segment_length", 0)
        actual_retrieved_length = len(document) if document else 0
        
        return {
            "doc_id": doc_id,
            "stored_text_length": stored_text_length,
            "metadata_segment_length": metadata_segment_length,
            "actual_retrieved_length": actual_retrieved_length,
            "length_match": stored_text_length == metadata_segment_length,
            "metadata": metadata,
            "text_preview": document[:200] + "..." if document and len(document) > 200 else document,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get segment info")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve segment info: {exc}",
        ) from exc


@app.get("/admin", response_class=FileResponse)
async def admin_panel():
    """Serve admin panel HTML page."""
    admin_path = static_dir / "admin.html"
    if admin_path.exists():
        return FileResponse(admin_path)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Admin panel not found",
    )


@app.get("/admin/jobs", response_model=ExportJobsResponse)
async def get_admin_jobs():
    """Get list of export jobs (last 50, most recent first)."""
    try:
        jobs = get_export_jobs(limit=50)
        # Convert to ExportJobItem models
        job_items = [
            ExportJobItem(
                id=job["id"],
                status=job["status"],
                started_at=job["started_at"],
                completed_at=job["completed_at"],
                duration_seconds=job["duration_seconds"],
                collection=job["collection"],
                total_records=job["total_records"],
                total_books=job["total_books"],
                total_segments=job["total_segments"],
                total_documents_in_collection=job["total_documents_in_collection"],
                error_message=job["error_message"],
            )
            for job in jobs
        ]
        return ExportJobsResponse(jobs=job_items)
    except Exception as exc:
        logger.exception("Failed to get export jobs")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve export jobs: {exc}",
        ) from exc


@app.get("/admin/jobs/{job_id}", response_model=ExportJobDetail)
async def get_admin_job(job_id: int):
    """Get full details of a specific export job."""
    try:
        job = get_export_job(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Export job with ID {job_id} not found",
            )
        return ExportJobDetail(**job)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get export job")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve export job: {exc}",
        ) from exc


@app.delete("/admin/jobs/{job_id}", response_model=DeleteJobResponse)
async def delete_admin_job(job_id: int):
    """Delete a failed/stale export job."""
    try:
        removed = delete_export_job(job_id)
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Export job {job_id} not found",
            )
        return DeleteJobResponse(success=True, message=f"Job {job_id} deleted.")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to delete export job")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete export job: {exc}",
        ) from exc


@app.get("/admin/chroma/collections", response_model=ChromaCollectionsResponse)
async def get_chroma_collections(
    app_state: Dict[str, Any] = Depends(get_app_state),
):
    """Get list of all collections in ChromaDB."""
    try:
        chroma_client = app_state["chroma_client"]
        collections = await anyio.to_thread.run_sync(chroma_client.list_collections)
        
        collection_infos = []
        for col in collections:
            try:
                count = await anyio.to_thread.run_sync(col.count)
                metadata = await anyio.to_thread.run_sync(lambda: col.metadata) if hasattr(col, 'metadata') else {}
            except Exception:
                count = None
                metadata = {}
            
            collection_infos.append(
                ChromaCollectionInfo(
                    name=col.name,
                    count=count,
                    metadata=metadata if isinstance(metadata, dict) else {},
                )
            )
        
        return ChromaCollectionsResponse(collections=collection_infos)
    except Exception as exc:
        logger.exception("Failed to list ChromaDB collections")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list collections: {exc}",
        ) from exc


@app.post("/admin/chroma/test-connection", response_model=ChromaTestResponse)
async def test_chroma_connection(
    app_state: Dict[str, Any] = Depends(get_app_state),
):
    """Test connection to ChromaDB and list available collections."""
    try:
        chroma_client = app_state["chroma_client"]
        
        # Test heartbeat
        heartbeat = await anyio.to_thread.run_sync(chroma_client.heartbeat)
        
        # List collections
        collections = await anyio.to_thread.run_sync(chroma_client.list_collections)
        collection_names = [col.name for col in collections] if collections else []
        
        return ChromaTestResponse(
            success=True,
            message=f"Successfully connected to ChromaDB. Found {len(collection_names)} collection(s).",
            heartbeat=heartbeat,
            collections=collection_names,
        )
    except Exception as exc:
        logger.exception("ChromaDB connection test failed")
        return ChromaTestResponse(
            success=False,
            message=f"Failed to connect to ChromaDB: {exc}",
            heartbeat=None,
            collections=None,
        )


@app.delete("/admin/chroma/collections/{collection_name}", response_model=ChromaDeleteResponse)
async def delete_chroma_collection(
    collection_name: str,
    app_state: Dict[str, Any] = Depends(get_app_state),
):
    """Delete a Chroma collection (use with caution)."""
    try:
        chroma_client = app_state["chroma_client"]
        await anyio.to_thread.run_sync(lambda: chroma_client.delete_collection(collection_name))
        return ChromaDeleteResponse(
            success=True,
            message=f"Collection '{collection_name}' deleted.",
        )
    except ChromaNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{collection_name}' not found",
        )
    except Exception as exc:
        logger.exception("Failed to delete Chroma collection %s", collection_name)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete collection: {exc}",
        ) from exc


@app.post("/admin/chroma/generate-export-command", response_model=ExportCommandResponse)
async def generate_export_command(
    request: ExportCommandRequest,
    app_state: Dict[str, Any] = Depends(get_app_state),
):
    """Generate export command with provided parameters."""
    try:
        settings: Settings = app_state["settings"]
        
        # Build command parts
        cmd_parts = ["python3", "export-sql-backup-to-chromadb.py"]
        cmd_parts.append(f"--sql-path {request.sql_path}")
        cmd_parts.append(f"--collection {request.collection}")
        cmd_parts.append(f"--embedding-provider {request.embedding_provider}")
        cmd_parts.append(f"--embedding-model {request.embedding_model}")
        
        if request.reset:
            cmd_parts.append("--reset")
        
        # Use provided host/port or fallback to settings
        host = request.host or settings.chroma_host
        port = request.port or settings.chroma_port
        
        if host != "localhost" or port != 8000:
            cmd_parts.append(f"--host {host}")
            cmd_parts.append(f"--port {port}")
        
        if request.ssl:
            cmd_parts.append("--ssl")
        
        if request.batch_size != 48:
            cmd_parts.append(f"--batch-size {request.batch_size}")
        
        if request.max_length != 200:
            cmd_parts.append(f"--max-length {request.max_length}")
        
        if request.context_length != 100:
            cmd_parts.append(f"--context {request.context_length}")
        
        command = "   ".join(cmd_parts)
        
        description = (
            f"Export command for collection '{request.collection}' "
            f"using {request.embedding_provider}/{request.embedding_model}"
        )
        
        return ExportCommandResponse(command=command, description=description)
    except Exception as exc:
        logger.exception("Failed to generate export command")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate command: {exc}",
        ) from exc


@app.post("/admin/chroma/generate-uvicorn-command", response_model=UvicornCommandResponse)
async def generate_uvicorn_command(
    request: UvicornCommandRequest,
    app_state: Dict[str, Any] = Depends(get_app_state),
):
    """Generate uvicorn command with optional collection override."""
    try:
        # Build command
        cmd_parts = ["uvicorn", "web_service.app:app"]
        cmd_parts.append(f"--host {request.host}")
        cmd_parts.append(f"--port {request.port}")
        
        if request.reload:
            cmd_parts.append("--reload")
        
        command = " ".join(cmd_parts)
        
        description = f"Start web service on {request.host}:{request.port}"
        
        env_vars = None
        if request.collection:
            env_vars = {"CHROMA_COLLECTION": request.collection}
            description += f" with collection override: {request.collection}"
        
        return UvicornCommandResponse(
            command=command,
            description=description,
            env_vars=env_vars,
        )
    except Exception as exc:
        logger.exception("Failed to generate uvicorn command")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate command: {exc}",
        ) from exc


@app.get("/admin/queries", response_model=QueryApprovalsResponse)
async def get_admin_queries(
    min_count: int = Query(0, ge=0, description="Minimum search count"),
    status: Optional[str] = Query(None, description="Filter by status (approved/rejected/pending)"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
):
    """Get list of query approvals with filters."""
    try:
        queries = get_query_approvals(limit=limit, min_count=min_count, status=status)
        stats = get_query_stats()
        
        query_items = [
            QueryApprovalItem(
                id=q["id"],
                query=q["query"],
                status=q["status"],
                approved_at=q["approved_at"],
                rejected_at=q["rejected_at"],
                notes=q["notes"],
                search_count=q["search_count"],
                last_searched_at=q["last_searched_at"],
            )
            for q in queries
        ]
        
        return QueryApprovalsResponse(queries=query_items, stats=stats)
    except Exception as exc:
        logger.exception("Failed to get query approvals")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve query approvals: {exc}",
        ) from exc


@app.post("/admin/queries/{query:path}/approve")
async def approve_admin_query(query: str):
    """Approve a query."""
    try:
        from urllib.parse import unquote
        decoded_query = unquote(query)
        approve_query(decoded_query)
        return {"success": True, "message": f"Query '{decoded_query}' approved"}
    except Exception as exc:
        logger.exception("Failed to approve query")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve query: {exc}",
        ) from exc


@app.post("/admin/queries/{query:path}/reject")
async def reject_admin_query(query: str):
    """Reject a query."""
    try:
        from urllib.parse import unquote
        decoded_query = unquote(query)
        reject_query(decoded_query)
        return {"success": True, "message": f"Query '{decoded_query}' rejected"}
    except Exception as exc:
        logger.exception("Failed to reject query")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject query: {exc}",
        ) from exc


@app.delete("/admin/queries/{query:path}")
async def delete_admin_query(query: str):
    """Delete a query from approvals."""
    try:
        from urllib.parse import unquote
        decoded_query = unquote(query)
        delete_query(decoded_query)
        return {"success": True, "message": f"Query '{decoded_query}' deleted"}
    except Exception as exc:
        logger.exception("Failed to delete query")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete query: {exc}",
        ) from exc


@app.get("/admin/queries/stats", response_model=QueryStatsResponse)
async def get_admin_query_stats():
    """Get query statistics."""
    try:
        stats = get_query_stats()
        return QueryStatsResponse(**stats)
    except Exception as exc:
        logger.exception("Failed to get query stats")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve query stats: {exc}",
        ) from exc


@app.get("/admin/models", response_model=EmbeddingModelsResponse, tags=["admin"])
async def get_admin_models(
    limit: int = Query(10, ge=1, le=10, description="حداکثر 10 مدل")
) -> EmbeddingModelsResponse:
    """List latest embedding models for admin view."""
    try:
        models = get_embedding_models(limit=limit)
        return EmbeddingModelsResponse(
            models=[_build_embedding_model_item(model) for model in models]
        )
    except Exception as exc:
        logger.exception("Failed to list embedding models", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در دریافت مدل‌ها",
        ) from exc


@app.get(
    "/models/active",
    response_model=EmbeddingModelsResponse,
    tags=["search"],
    summary="مدل‌های فعال برای جستجو",
)
async def get_active_models(
    limit: int = Query(10, ge=1, le=10, description="حداکثر 10 مدل فعال")
) -> EmbeddingModelsResponse:
    try:
        models = get_active_embedding_models(limit=limit)
        return EmbeddingModelsResponse(
            models=[_build_embedding_model_item(model) for model in models]
        )
    except Exception as exc:
        logger.exception("Failed to list active models", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در دریافت مدل‌های فعال",
        ) from exc


@app.post(
    "/admin/models/{model_id}/toggle",
    response_model=EmbeddingModelItem,
    tags=["admin"],
)
async def toggle_admin_model(
    model_id: int, payload: ToggleModelRequest
) -> EmbeddingModelItem:
    updated = set_embedding_model_active(model_id, payload.is_active)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="مدل یافت نشد"
        )
    model = get_embedding_model(model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="مدل یافت نشد"
        )
    return _build_embedding_model_item(model)


@app.put(
    "/admin/models/{model_id}/color",
    response_model=EmbeddingModelItem,
    tags=["admin"],
)
async def update_admin_model_color(
    model_id: int, payload: UpdateModelColorRequest
) -> EmbeddingModelItem:
    if not _is_valid_hex_color(payload.color):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="کد رنگ نامعتبر است. مثال: #3B82F6",
        )
    updated = update_embedding_model_color(model_id, payload.color)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="مدل یافت نشد"
        )
    model = get_embedding_model(model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="مدل یافت نشد"
        )
    return _build_embedding_model_item(model)


@app.post("/admin/auth/users", status_code=status.HTTP_201_CREATED)
async def create_admin_user(request: CreateUserRequest):
    """Create a new API user."""
    try:
        user_id = create_api_user(request.username, request.email)
        return {"success": True, "user_id": user_id, "message": f"User '{request.username}' created"}
    except Exception as exc:
        logger.exception("Failed to create user")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {exc}",
        ) from exc


@app.get("/admin/auth/users", response_model=UsersResponse)
async def get_admin_users():
    """Get list of all API users."""
    try:
        users = get_all_users()
        user_items = []
        for user in users:
            # Get token count for each user
            tokens = get_all_tokens(user_id=user["id"])
            user_items.append(
                UserItem(
                    id=user["id"],
                    username=user["username"],
                    email=user["email"],
                    created_at=user["created_at"],
                    is_active=user["is_active"],
                    token_count=len(tokens),
                )
            )
        return UsersResponse(users=user_items)
    except Exception as exc:
        logger.exception("Failed to get users")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve users: {exc}",
        ) from exc


@app.post("/admin/auth/tokens", status_code=status.HTTP_201_CREATED, response_model=TokenResponse)
async def create_admin_token(request: CreateTokenRequest):
    """Create a new API token."""
    try:
        from datetime import datetime
        
        # Generate secure token
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        expires_at_str = None
        if request.expires_at:
            expires_at_str = request.expires_at.isoformat()
        
        token_id = create_api_token(
            user_id=request.user_id,
            token=token_hash,
            name=request.name,
            rate_limit_per_day=request.rate_limit_per_day,
            expires_at=expires_at_str,
        )
        
        # Get user info
        users = get_all_users()
        user = next((u for u in users if u["id"] == request.user_id), None)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {request.user_id} not found",
            )
        
        return TokenResponse(
            id=token_id,
            user_id=request.user_id,
            token=token,  # Return plain token only once
            name=request.name,
            rate_limit_per_day=request.rate_limit_per_day,
            created_at=datetime.utcnow(),
            expires_at=request.expires_at,
            username=user["username"],
            email=user["email"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to create token")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create token: {exc}",
        ) from exc


@app.get("/admin/auth/tokens", response_model=TokensResponse)
async def get_admin_tokens(user_id: Optional[int] = Query(None, description="Filter by user ID")):
    """Get list of all API tokens."""
    try:
        tokens = get_all_tokens(user_id=user_id)
        token_items = []
        for token in tokens:
            usage_today = get_token_usage_today(token["id"])
            token_items.append(
                TokenItem(
                    id=token["id"],
                    user_id=token["user_id"],
                    name=token["name"],
                    rate_limit_per_day=token["rate_limit_per_day"],
                    created_at=token["created_at"],
                    expires_at=token["expires_at"],
                    is_active=token["is_active"],
                    last_used_at=token["last_used_at"],
                    username=token["username"],
                    email=token["email"],
                    usage_today=usage_today,
                )
            )
        return TokensResponse(tokens=token_items)
    except Exception as exc:
        logger.exception("Failed to get tokens")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve tokens: {exc}",
        ) from exc


@app.delete("/admin/auth/tokens/{token_id}")
async def delete_admin_token(token_id: int):
    """Revoke (deactivate) an API token."""
    try:
        revoke_token(token_id)
        return {"success": True, "message": f"Token #{token_id} revoked"}
    except Exception as exc:
        logger.exception("Failed to revoke token")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke token: {exc}",
        ) from exc


@app.get("/admin/auth/tokens/{token_id}/usage", response_model=TokenUsageResponse)
async def get_admin_token_usage(token_id: int):
    """Get usage statistics for a specific token."""
    try:
        from datetime import datetime, timedelta
        
        tokens = get_all_tokens()
        token = next((t for t in tokens if t["id"] == token_id), None)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Token with ID {token_id} not found",
            )
        
        usage_today = get_token_usage_today(token_id)
        rate_limit = token["rate_limit_per_day"]
        remaining = max(0, rate_limit - usage_today)
        
        # Calculate reset time (midnight UTC)
        now = datetime.utcnow()
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        return TokenUsageResponse(
            token_id=token_id,
            usage_today=usage_today,
            rate_limit=rate_limit,
            remaining=remaining,
            reset_at=tomorrow,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get token usage")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve token usage: {exc}",
        ) from exc


@app.get("/approved-queries", response_model=QueryApprovalsResponse)
async def get_approved_queries(
    app_state: Dict[str, Any] = Depends(get_app_state),
):
    """Get approved queries for display on main page."""
    try:
        settings: Settings = app_state["settings"]
        
        if not settings.show_approved_queries:
            return QueryApprovalsResponse(queries=[], stats={})
        
        queries = get_query_approvals(
            limit=settings.approved_queries_limit,
            min_count=settings.approved_queries_min_count,
            status="approved",
        )
        stats = get_query_stats()
        
        query_items = [
            QueryApprovalItem(
                id=q["id"],
                query=q["query"],
                status=q["status"],
                approved_at=q["approved_at"],
                rejected_at=q["rejected_at"],
                notes=q["notes"],
                search_count=q["search_count"],
                last_searched_at=q["last_searched_at"],
            )
            for q in queries
        ]
        
        return QueryApprovalsResponse(queries=query_items, stats=stats)
    except Exception as exc:
        logger.exception("Failed to get approved queries")
        # Don't fail the request, just return empty
        return QueryApprovalsResponse(queries=[], stats={})


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="بررسی وضعیت سرویس",
    description="""
    بررسی وضعیت ChromaDB، Redis و کالکشن.
    
    این endpoint وضعیت اتصال به ChromaDB (heartbeat)، تعداد مستندات در کالکشن،
    و وضعیت اتصال به Redis را بررسی می‌کند.
    """,
    tags=["health"],
)
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


async def verify_api_token(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    app_state: Dict[str, Any] = Depends(get_app_state),
) -> Optional[Dict[str, Any]]:
    """Verify API token from Authorization header. Returns token info or None."""
    settings: Settings = app_state["settings"]
    
    if not settings.enable_api_auth:
        return None
    
    # Skip auth for public endpoints
    public_paths = ["/", "/health", "/docs", "/redoc", "/openapi.json", "/static", "/approved-queries", "/admin"]
    if any(request.url.path.startswith(path) for path in public_paths):
        return None
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract token from "Bearer <token>" format
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format. Use 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Hash token for lookup (in production, store hashed tokens)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    token_info = get_api_token(token_hash)
    
    if not token_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check expiration
    if token_info["expires_at"]:
        from datetime import datetime
        if datetime.utcnow() > token_info["expires_at"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    return token_info


async def check_rate_limit(
    token_info: Optional[Dict[str, Any]] = Depends(verify_api_token),
) -> None:
    """Check rate limit for API token."""
    if not token_info:
        return
    
    token_id = token_info["id"]
    rate_limit = token_info["rate_limit_per_day"]
    
    usage_today = get_token_usage_today(token_id)
    
    if usage_today >= rate_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Limit: {rate_limit} requests per day",
            headers={
                "X-RateLimit-Limit": str(rate_limit),
                "X-RateLimit-Remaining": "0",
                "Retry-After": "86400",  # 24 hours in seconds
            },
        )
    
    # Increment usage
    increment_token_usage(token_id)
    
    # Add rate limit headers to response
    remaining = rate_limit - usage_today - 1
    # This will be set in middleware


@app.middleware("http")
async def auth_and_rate_limit_middleware(request: Request, call_next):
    """Middleware for authentication and rate limiting."""
    settings = get_settings()
    
    # Skip for public endpoints
    public_paths = ["/", "/health", "/docs", "/redoc", "/openapi.json", "/static", "/approved-queries", "/admin"]
    if any(request.url.path.startswith(path) for path in public_paths):
        response = await call_next(request)
        return response
    
    if settings.enable_api_auth:
        try:
            # Verify token
            authorization = request.headers.get("Authorization")
            if not authorization:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Authorization header required"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            if not authorization.startswith("Bearer "):
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid authorization format. Use 'Bearer <token>'"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            token = authorization[7:].strip()
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            token_info = get_api_token(token_hash)
            
            if not token_info:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid or expired token"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Check expiration
            if token_info["expires_at"]:
                from datetime import datetime
                if datetime.utcnow() > token_info["expires_at"]:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "Token has expired"},
                        headers={"WWW-Authenticate": "Bearer"},
                    )
            
            # Check rate limit
            token_id = token_info["id"]
            rate_limit = token_info["rate_limit_per_day"]
            usage_today = get_token_usage_today(token_id)
            
            if usage_today >= rate_limit:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": f"Rate limit exceeded. Limit: {rate_limit} requests per day"},
                    headers={
                        "X-RateLimit-Limit": str(rate_limit),
                        "X-RateLimit-Remaining": "0",
                        "Retry-After": "86400",
                    },
                )
            
            # Increment usage
            increment_token_usage(token_id)
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            remaining = rate_limit - usage_today - 1
            response.headers["X-RateLimit-Limit"] = str(rate_limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
            
            # Calculate reset time (midnight UTC)
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            reset_timestamp = int(tomorrow.timestamp())
            response.headers["X-RateLimit-Reset"] = str(reset_timestamp)
            
            return response
            
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Auth middleware error")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error"},
            )
    else:
        # Auth disabled, just process request
        response = await call_next(request)
        return response


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
    return UTF8JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


__all__ = ["app"]

