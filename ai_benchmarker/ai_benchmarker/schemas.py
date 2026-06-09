from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class TranscriptionCreate(BaseModel):
    audio_guid: str = Field(..., min_length=1)
    model_name: str = Field(..., min_length=1)
    raw_text: str = Field(..., min_length=1)


class TranscriptionResponse(BaseModel):
    id: int
    audio_guid: str
    model_name: str
    raw_text: str
    normalized_text: str


class CompareRequest(BaseModel):
    ref_id: int = Field(..., ge=1)
    hyp_id: int = Field(..., ge=1)


class BenchmarkResultResponse(BaseModel):
    id: int
    audio_guid: str
    ref_id: int
    hyp_id: int
    ref_model_name: Optional[str] = None
    hyp_model_name: Optional[str] = None
    wer: float
    ngram_bigram: float
    ngram_trigram: float
    lcs_score: float


class HealthResponse(BaseModel):
    status: str = "ok"


class AudioMasterResponse(BaseModel):
    audio_guid: str
    file_name: str
    approved_text: str
    transcription_count: int = 0


class AudioMasterCreateJson(BaseModel):
    file_name: str = Field(default="reference.txt", min_length=1)
    approved_text: str = Field(..., min_length=1)


class AudioMasterCreateResponse(BaseModel):
    audio_guid: str
    file_name: str
    approved_text: str
    reference_transcription_id: int


class AudioMasterListResponse(BaseModel):
    items: List[AudioMasterResponse]
