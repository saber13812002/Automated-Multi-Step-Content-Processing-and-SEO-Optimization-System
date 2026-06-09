from __future__ import annotations

from pydantic import BaseModel, Field


class TranscriptionCreate(BaseModel):
    audio_guid: str = Field(..., min_length=1)
    model_name: str = Field(..., min_length=1)
    raw_text: str = Field(..., min_length=1)


class TranscriptionResponse(BaseModel):
    id: int
    audio_guid: str
    model_name: str
    normalized_text: str


class CompareRequest(BaseModel):
    ref_id: int = Field(..., ge=1)
    hyp_id: int = Field(..., ge=1)


class BenchmarkResultResponse(BaseModel):
    id: int
    audio_guid: str
    ref_id: int
    hyp_id: int
    wer: float
    ngram_bigram: float
    ngram_trigram: float
    lcs_score: float


class HealthResponse(BaseModel):
    status: str = "ok"
