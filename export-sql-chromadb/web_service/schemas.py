from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Free text query.")
    top_k: int = Field(10, ge=1, le=50, description="Maximum number of results to return.")


class SearchResult(BaseModel):
    id: str
    distance: Optional[float] = None
    score: Optional[float] = None
    document: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


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


