from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Request model for semantic search."""
    query: str = Field(
        ...,
        min_length=1,
        description="متن جستجو",
        example="آموزش عقاید چیست؟",
    )
    top_k: int = Field(
        10,
        ge=1,
        le=50,
        description="حداکثر تعداد نتایج",
        example=10,
    )
    save: bool = Field(
        False,
        description="ذخیره نتایج در دیتابیس",
        example=False,
    )
    page: int = Field(
        1,
        ge=1,
        description="شماره صفحه (شروع از 1)",
        example=1,
    )
    page_size: int = Field(
        20,
        ge=1,
        le=100,
        description="تعداد نتایج در هر صفحه",
        example=20,
    )
    use_cache: bool = Field(
        True,
        description="استفاده از کش Redis برای نتایج (اگر در کمتر از 1 ساعت جستجو شده باشد)",
        example=True,
    )
    include_full_context: bool = Field(
        False,
        description="شامل کردن متن کامل پاراگراف به جای فقط سگمنت",
        example=False,
    )
    model_id: Optional[int] = Field(
        None,
        description="شناسه مدل امبدینگ انتخابی (اگر ارائه شود، از کالکشن و embedder این مدل استفاده می‌شود)",
        example=None,
    )


class SearchResult(BaseModel):
    id: str
    distance: Optional[float] = None
    score: Optional[float] = None
    document: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PaginationInfo(BaseModel):
    page: int = Field(..., description="Current page number.")
    page_size: int = Field(..., description="Number of results per page.")
    total_pages: Optional[int] = Field(None, description="Total number of pages (null if > 1000 results).")
    has_next_page: bool = Field(..., description="Whether there is a next page.")
    has_previous_page: bool = Field(..., description="Whether there is a previous page.")
    estimated_total_results: Optional[str] = Field(None, description="Estimated total results ('1000+' or exact number as string).")


class SearchResponse(BaseModel):
    query: str
    top_k: int
    returned: int
    provider: str
    model: str
    collection: str
    results: List[SearchResult]
    took_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    total_documents: Optional[int] = Field(None, description="Total documents in collection.")
    pagination: Optional[PaginationInfo] = Field(None, description="Pagination information.")
    cache_source: Optional[str] = Field(None, description="منبع نتایج (cache یا realtime)")


class MultiModelSearchRequest(BaseModel):
    """Request payload for multi-model search."""

    query: str = Field(..., min_length=1, description="متن جستجو")
    model_ids: List[int] = Field(
        ...,
        min_length=1,
        max_length=3,
        description="شناسه مدل‌های انتخاب‌شده (حداکثر 3)",
    )
    top_k: int = Field(20, ge=1, le=50, description="حداکثر تعداد نتایج per model")
    save: bool = Field(False, description="ذخیره نتایج در دیتابیس")


class MultiModelResult(SearchResult):
    """Single result item tagged with model info."""

    model_id: int
    model_color: str
    embedding_model: str
    embedding_provider: str


class MultiModelSearchResponse(BaseModel):
    """Response payload for multi-model search."""

    query: str
    model_ids: List[int]
    returned: int
    results: List[MultiModelResult]
    took_ms: float
    cache_source: str = Field(description="منبع نتایج (cache یا realtime)")
    errors: Optional[List[Dict[str, str]]] = Field(
        None, description="خطاهای مدل‌های ناموفق (collection, error_message)"
    )


class HealthComponent(BaseModel):
    status: str
    detail: Optional[str] = None
    latency_ms: Optional[float] = None
    extras: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    chroma: HealthComponent
    collection: HealthComponent
    redis: HealthComponent
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SearchHistoryItem(BaseModel):
    id: int
    query: str
    result_count: int
    took_ms: float
    timestamp: datetime
    collection: str
    provider: str
    model: str


class SearchHistoryResponse(BaseModel):
    searches: List[SearchHistoryItem]
    total: int
    limit: int
    offset: int


class ExportJobItem(BaseModel):
    """Export job item for list view."""
    id: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    collection: str
    total_records: Optional[int] = None
    total_books: Optional[int] = None
    total_segments: Optional[int] = None
    total_documents_in_collection: Optional[int] = None
    error_message: Optional[str] = None


class ExportJobDetail(BaseModel):
    """Full export job details."""
    id: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    sql_path: str
    collection: str
    batch_size: int
    max_length: int
    context_length: int
    host: str
    port: int
    ssl: bool
    embedding_provider: str
    embedding_model: str
    reset: bool
    total_records: Optional[int] = None
    total_books: Optional[int] = None
    total_segments: Optional[int] = None
    total_documents_in_collection: Optional[int] = None
    error_message: Optional[str] = None
    command_line_args: Optional[str] = None


class ExportJobsResponse(BaseModel):
    """Response for export jobs list."""
    jobs: List[ExportJobItem]


class DeleteJobResponse(BaseModel):
    success: bool
    message: str


class ChromaDeleteResponse(BaseModel):
    success: bool
    message: str


class EmbeddingModelItem(BaseModel):
    """Embedding model info for admin and user selection."""

    id: int
    embedding_provider: str
    embedding_model: str
    collection: str
    is_active: bool
    color: str
    job_id: Optional[int] = None
    completed_at: Optional[datetime] = None
    total_documents_in_collection: Optional[int] = None
    total_records: Optional[int] = None
    total_books: Optional[int] = None
    total_segments: Optional[int] = None


class EmbeddingModelsResponse(BaseModel):
    """List of embedding models."""

    models: List[EmbeddingModelItem]


class ToggleModelRequest(BaseModel):
    """Toggle embedding model status."""

    is_active: bool


class UpdateModelColorRequest(BaseModel):
    """Update embedding model color."""

    color: str = Field(..., min_length=4, max_length=7, description="کد رنگ HEX")


class ChromaCollectionInfo(BaseModel):
    """Information about a ChromaDB collection."""
    name: str
    count: Optional[int] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChromaCollectionsResponse(BaseModel):
    """Response for list of collections."""
    collections: List[ChromaCollectionInfo]


class ChromaTestResponse(BaseModel):
    """Response for ChromaDB connection test."""
    success: bool
    message: str
    heartbeat: Optional[Any] = None
    collections: Optional[List[str]] = None


class ExportCommandRequest(BaseModel):
    """Request to generate export command."""
    sql_path: str = Field(..., description="Path to SQL file")
    collection: str = Field(..., description="Collection name")
    embedding_provider: str = Field("openai", description="Embedding provider (openai/none)")
    embedding_model: str = Field("text-embedding-3-small", description="Embedding model")
    reset: bool = Field(False, description="Reset collection before export")
    host: Optional[str] = Field(None, description="ChromaDB host (uses env if not provided)")
    port: Optional[int] = Field(None, description="ChromaDB port (uses env if not provided)")
    ssl: bool = Field(False, description="Use SSL")
    batch_size: int = Field(48, description="Batch size")
    max_length: int = Field(200, description="Max segment length")
    context_length: int = Field(100, description="Context length")


class ExportCommandResponse(BaseModel):
    """Generated export command."""
    command: str
    description: str


class UvicornCommandRequest(BaseModel):
    """Request to generate uvicorn command."""
    host: str = Field("0.0.0.0", description="Host to bind")
    port: int = Field(8080, description="Port to bind")
    reload: bool = Field(True, description="Enable auto-reload")
    collection: Optional[str] = Field(None, description="Override collection name (via env)")


class UvicornCommandResponse(BaseModel):
    """Generated uvicorn command."""
    command: str
    description: str
    env_vars: Optional[dict[str, str]] = None


class QueryApprovalItem(BaseModel):
    """Query approval item."""
    id: Optional[int] = None
    query: str
    status: str
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    notes: Optional[str] = None
    search_count: int
    last_searched_at: Optional[datetime] = None


class QueryApprovalsResponse(BaseModel):
    """Response for query approvals list."""
    queries: List[QueryApprovalItem]
    stats: dict[str, Any]


class QueryStatsResponse(BaseModel):
    """Response for query statistics."""
    total: int
    approved: int
    rejected: int
    pending: int
    total_searches: int


class TopQueryItem(BaseModel):
    """Top search query item."""
    query: str
    search_count: int
    last_searched_at: Optional[datetime] = None


class TopQueriesResponse(BaseModel):
    """Response for top search queries."""
    queries: List[TopQueryItem]
    total: int


class CreateUserRequest(BaseModel):
    """Request to create a new API user."""
    username: str = Field(..., min_length=1, description="Username")
    email: Optional[str] = Field(None, description="Email address")


class CreateTokenRequest(BaseModel):
    """Request to create a new API token."""
    user_id: int = Field(..., description="User ID")
    name: str = Field(..., min_length=1, description="Token name")
    rate_limit_per_day: int = Field(1000, ge=1, description="Rate limit per day")
    expires_at: Optional[datetime] = Field(None, description="Expiration date (optional)")


class TokenResponse(BaseModel):
    """Response for token creation."""
    id: int
    user_id: int
    token: str
    name: str
    rate_limit_per_day: int
    created_at: datetime
    expires_at: Optional[datetime] = None
    username: str
    email: Optional[str] = None


class TokenItem(BaseModel):
    """Token item for list view."""
    id: int
    user_id: int
    name: str
    rate_limit_per_day: int
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool
    last_used_at: Optional[datetime] = None
    username: str
    email: Optional[str] = None
    usage_today: Optional[int] = None


class UserItem(BaseModel):
    """User item for list view."""
    id: int
    username: str
    email: Optional[str] = None
    created_at: datetime
    is_active: bool
    token_count: Optional[int] = None


class UsersResponse(BaseModel):
    """Response for users list."""
    users: List[UserItem]


class TokensResponse(BaseModel):
    """Response for tokens list."""
    tokens: List[TokenItem]


class TokenUsageResponse(BaseModel):
    """Response for token usage stats."""
    token_id: int
    usage_today: int
    rate_limit: int
    remaining: int
    reset_at: datetime


class VoteRequest(BaseModel):
    """Request payload for voting on search results."""

    guest_user_id: str = Field(..., min_length=8)
    query: str = Field(..., min_length=1)
    vote_type: str = Field(..., pattern="^(like|dislike)$")
    model_id: Optional[int] = Field(None, description="شناسه مدل (اختیاری)")
    result_id: Optional[str] = Field(None, description="شناسه نتیجه (اختیاری)")


class VoteResponse(BaseModel):
    """Response after registering a vote."""

    success: bool
    likes: int
    dislikes: int


class VoteItem(BaseModel):
    """Single vote entry for admin."""

    id: int
    guest_user_id: str
    query: str
    vote_type: str
    created_at: datetime
    model_id: Optional[int] = None
    result_id: Optional[str] = None
    embedding_provider: Optional[str] = None
    embedding_model: Optional[str] = None
    collection: Optional[str] = None
    color: Optional[str] = None


class VotesResponse(BaseModel):
    """List of votes for admin view."""

    votes: List[VoteItem]


class VoteSummaryItem(BaseModel):
    """Aggregated votes per query/model."""

    query: str
    model_id: Optional[int] = None
    embedding_provider: Optional[str] = None
    embedding_model: Optional[str] = None
    collection: Optional[str] = None
    likes: int
    dislikes: int
    last_vote_at: Optional[datetime] = None


class VoteSummaryResponse(BaseModel):
    """Vote summaries."""

    items: List[VoteSummaryItem]


