from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from .config import get_settings
from .core import AIBenchmark
from .database import get_db, init_db
from .schemas import (
    BenchmarkResultResponse,
    CompareRequest,
    HealthResponse,
    TranscriptionCreate,
    TranscriptionResponse,
)
from .storage import AudioMaster, BenchmarkResult, Transcription

logger = logging.getLogger(__name__)
benchmarker = AIBenchmark()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    logger.info("Database initialized.")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    application = FastAPI(
        title="AI Benchmarker",
        description="Benchmark and evaluate AI transcription outputs",
        version="0.1.0",
        lifespan=lifespan,
    )

    @application.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @application.post(
        "/api/v1/transcription",
        response_model=TranscriptionResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_transcription(
        payload: TranscriptionCreate,
        db: Session = Depends(get_db),
    ) -> TranscriptionResponse:
        audio = db.get(AudioMaster, payload.audio_guid)
        if audio is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"AudioMaster with audio_guid '{payload.audio_guid}' not found.",
            )

        normalized_text = benchmarker._normalize_text(payload.raw_text)
        transcription = Transcription(
            audio_guid=payload.audio_guid,
            model_name=payload.model_name,
            raw_text=payload.raw_text,
            normalized_text=normalized_text,
        )
        db.add(transcription)
        db.commit()
        db.refresh(transcription)

        return TranscriptionResponse(
            id=transcription.id,
            audio_guid=transcription.audio_guid,
            model_name=transcription.model_name,
            normalized_text=transcription.normalized_text,
        )

    @application.post(
        "/api/v1/compare",
        response_model=BenchmarkResultResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def compare_transcriptions(
        payload: CompareRequest,
        db: Session = Depends(get_db),
    ) -> BenchmarkResultResponse:
        reference = db.get(Transcription, payload.ref_id)
        if reference is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transcription with ref_id '{payload.ref_id}' not found.",
            )

        hypothesis = db.get(Transcription, payload.hyp_id)
        if hypothesis is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transcription with hyp_id '{payload.hyp_id}' not found.",
            )

        ref_text = reference.normalized_text
        hyp_text = hypothesis.normalized_text

        result = BenchmarkResult(
            audio_guid=reference.audio_guid,
            ref_id=reference.id,
            hyp_id=hypothesis.id,
            wer=benchmarker.calculate_wer(ref_text, hyp_text),
            ngram_bigram=benchmarker.calculate_ngram_similarity(ref_text, hyp_text, n=2),
            ngram_trigram=benchmarker.calculate_ngram_similarity(ref_text, hyp_text, n=3),
            lcs_score=benchmarker.calculate_lcs_similarity(ref_text, hyp_text),
        )
        db.add(result)
        db.commit()
        db.refresh(result)

        return BenchmarkResultResponse(
            id=result.id,
            audio_guid=result.audio_guid,
            ref_id=result.ref_id,
            hyp_id=result.hyp_id,
            wer=result.wer,
            ngram_bigram=result.ngram_bigram,
            ngram_trigram=result.ngram_trigram,
            lcs_score=result.lcs_score,
        )

    return application


app = create_app()
