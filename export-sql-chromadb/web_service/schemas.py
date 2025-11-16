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
    id: int
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


