from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Free text query.")
    top_k: int = Field(10, ge=1, le=50, description="Maximum number of results to return.")
    save: bool = Field(False, description="Save search results to database.")
    page: int = Field(1, ge=1, description="Page number (1-indexed).")
    page_size: int = Field(20, ge=1, le=100, description="Number of results per page.")


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


