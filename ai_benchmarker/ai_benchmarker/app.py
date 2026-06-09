from __future__ import annotations

import csv
import io
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse, HTMLResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .core import AIBenchmark
from .database import get_db, init_db
from .schemas import (
    AudioMasterCreateJson,
    AudioMasterCreateResponse,
    AudioMasterListResponse,
    AudioMasterResponse,
    BenchmarkResultResponse,
    CompareRequest,
    HealthResponse,
    TranscriptionCreate,
    TranscriptionResponse,
)
from .storage import AudioMaster, BenchmarkResult, Transcription
from .utils import generate_audio_guid, parse_subtitle_text

logger = logging.getLogger(__name__)
benchmarker = AIBenchmark()
_STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    logger.info("Database initialized.")
    yield


def _create_transcription_record(
    db: Session,
    audio_guid: str,
    model_name: str,
    raw_text: str,
) -> Transcription:
    normalized_text = benchmarker._normalize_text(raw_text)
    transcription = Transcription(
        audio_guid=audio_guid,
        model_name=model_name,
        raw_text=raw_text,
        normalized_text=normalized_text,
    )
    db.add(transcription)
    db.commit()
    db.refresh(transcription)
    return transcription


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    application = FastAPI(
        title="AI Benchmarker",
        description="Benchmark and evaluate AI transcription outputs",
        version="0.2.0",
        lifespan=lifespan,
    )

    @application.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @application.get("/admin", response_class=HTMLResponse)
    def admin_panel() -> FileResponse:
        admin_file = _STATIC_DIR / "admin.html"
        if not admin_file.exists():
            raise HTTPException(status_code=404, detail="Admin panel not found.")
        return FileResponse(admin_file)

    @application.get("/reports", response_class=HTMLResponse)
    def reports_panel() -> FileResponse:
        reports_file = _STATIC_DIR / "reports.html"
        if not reports_file.exists():
            raise HTTPException(status_code=404, detail="Reports page not found.")
        return FileResponse(reports_file)

    def _register_audio_master(
        db: Session,
        file_name: str,
        text: str,
    ) -> AudioMasterCreateResponse:
        audio_guid = generate_audio_guid()
        audio = AudioMaster(
            audio_guid=audio_guid,
            file_name=file_name,
            approved_text=text,
        )
        db.add(audio)
        db.commit()
        db.refresh(audio)
        reference = _create_transcription_record(
            db,
            audio_guid=audio_guid,
            model_name="reference",
            raw_text=text,
        )
        return AudioMasterCreateResponse(
            audio_guid=audio.audio_guid,
            file_name=audio.file_name,
            approved_text=audio.approved_text,
            reference_transcription_id=reference.id,
        )

    @application.post(
        "/api/v1/audio/json",
        response_model=AudioMasterCreateResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_audio_master_json(
        payload: AudioMasterCreateJson,
        db: Session = Depends(get_db),
    ) -> AudioMasterCreateResponse:
        text = parse_subtitle_text(payload.approved_text, payload.file_name)
        if not text.strip():
            raise HTTPException(status_code=400, detail="Reference text is empty.")
        return _register_audio_master(db, payload.file_name, text)

    @application.get("/api/v1/audio", response_model=AudioMasterListResponse)
    def list_audio_masters(db: Session = Depends(get_db)) -> AudioMasterListResponse:
        rows = db.scalars(select(AudioMaster).order_by(AudioMaster.file_name)).all()
        items: List[AudioMasterResponse] = []
        for audio in rows:
            count = db.scalar(
                select(func.count())
                .select_from(Transcription)
                .where(Transcription.audio_guid == audio.audio_guid)
            )
            items.append(
                AudioMasterResponse(
                    audio_guid=audio.audio_guid,
                    file_name=audio.file_name,
                    approved_text=audio.approved_text,
                    transcription_count=count or 0,
                )
            )
        return AudioMasterListResponse(items=items)

    @application.get(
        "/api/v1/audio/{audio_guid}",
        response_model=AudioMasterResponse,
    )
    def get_audio_master(audio_guid: str, db: Session = Depends(get_db)) -> AudioMasterResponse:
        audio = db.get(AudioMaster, audio_guid)
        if audio is None:
            raise HTTPException(status_code=404, detail="Audio not found.")
        count = db.scalar(
            select(func.count())
            .select_from(Transcription)
            .where(Transcription.audio_guid == audio_guid)
        )
        return AudioMasterResponse(
            audio_guid=audio.audio_guid,
            file_name=audio.file_name,
            approved_text=audio.approved_text,
            transcription_count=count or 0,
        )

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

        text = parse_subtitle_text(payload.raw_text)
        transcription = _create_transcription_record(
            db,
            audio_guid=payload.audio_guid,
            model_name=payload.model_name,
            raw_text=text,
        )

        return TranscriptionResponse(
            id=transcription.id,
            audio_guid=transcription.audio_guid,
            model_name=transcription.model_name,
            raw_text=transcription.raw_text,
            normalized_text=transcription.normalized_text,
        )

    @application.get("/api/v1/transcriptions", response_model=List[TranscriptionResponse])
    def list_transcriptions(
        audio_guid: Optional[str] = None,
        db: Session = Depends(get_db),
    ) -> List[TranscriptionResponse]:
        query = select(Transcription).order_by(Transcription.id.desc())
        if audio_guid:
            query = query.where(Transcription.audio_guid == audio_guid)
        rows = db.scalars(query).all()
        return [
            TranscriptionResponse(
                id=row.id,
                audio_guid=row.audio_guid,
                model_name=row.model_name,
                raw_text=row.raw_text,
                normalized_text=row.normalized_text,
            )
            for row in rows
        ]

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
            ref_model_name=reference.model_name,
            hyp_model_name=hypothesis.model_name,
            wer=result.wer,
            ngram_bigram=result.ngram_bigram,
            ngram_trigram=result.ngram_trigram,
            lcs_score=result.lcs_score,
        )

    def _benchmark_rows(db: Session, audio_guid: Optional[str] = None) -> list:
        query = select(BenchmarkResult).order_by(BenchmarkResult.id.desc())
        if audio_guid:
            query = query.where(BenchmarkResult.audio_guid == audio_guid)
        return db.scalars(query).all()

    @application.get("/api/v1/benchmarks/export.csv")
    def export_benchmarks_csv(
        audio_guid: Optional[str] = Query(None),
        db: Session = Depends(get_db),
    ) -> Response:
        rows = _benchmark_rows(db, audio_guid)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow([
            "id", "audio_guid", "ref_model", "hyp_model",
            "wer", "ngram_bigram", "ngram_trigram", "lcs_score",
        ])
        for row in rows:
            ref = db.get(Transcription, row.ref_id)
            hyp = db.get(Transcription, row.hyp_id)
            writer.writerow([
                row.id,
                row.audio_guid,
                ref.model_name if ref else "",
                hyp.model_name if hyp else "",
                row.wer,
                row.ngram_bigram,
                row.ngram_trigram,
                row.lcs_score,
            ])
        return Response(
            content=buffer.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=benchmark_results.csv",
            },
        )

    @application.get("/api/v1/benchmarks", response_model=List[BenchmarkResultResponse])
    def list_benchmarks(
        audio_guid: Optional[str] = None,
        db: Session = Depends(get_db),
    ) -> List[BenchmarkResultResponse]:
        rows = _benchmark_rows(db, audio_guid)
        results: List[BenchmarkResultResponse] = []
        for row in rows:
            ref = db.get(Transcription, row.ref_id)
            hyp = db.get(Transcription, row.hyp_id)
            results.append(
                BenchmarkResultResponse(
                    id=row.id,
                    audio_guid=row.audio_guid,
                    ref_id=row.ref_id,
                    hyp_id=row.hyp_id,
                    ref_model_name=ref.model_name if ref else None,
                    hyp_model_name=hyp.model_name if hyp else None,
                    wer=row.wer,
                    ngram_bigram=row.ngram_bigram,
                    ngram_trigram=row.ngram_trigram,
                    lcs_score=row.lcs_score,
                )
            )
        return results

    return application


app = create_app()
