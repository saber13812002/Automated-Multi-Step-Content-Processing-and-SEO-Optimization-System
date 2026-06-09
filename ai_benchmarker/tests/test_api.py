import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from ai_benchmarker.app import create_app
from ai_benchmarker.core import AIBenchmark
from ai_benchmarker.database import get_db, init_db, reset_engine, seed_audio_master
from ai_benchmarker.storage import BenchmarkResult, Transcription


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    reset_engine()
    init_db()

    app = create_app()

    with TestClient(app) as test_client:
        yield test_client

    reset_engine()


def _seed_audio(db: Session) -> str:
    audio_guid = "test-audio-001"
    seed_audio_master(
        db,
        audio_guid=audio_guid,
        file_name="sample.wav",
        approved_text="hello world",
    )
    return audio_guid


def test_health_endpoint(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_transcription_requires_existing_audio_master(client: TestClient):
    response = client.post(
        "/api/v1/transcription",
        json={
            "audio_guid": "missing-guid",
            "model_name": "whisper-large",
            "raw_text": "hello world",
        },
    )
    assert response.status_code == 404


def test_transcription_and_compare_flow(client: TestClient):
    db = next(get_db())
    audio_guid = _seed_audio(db)

    ref_response = client.post(
        "/api/v1/transcription",
        json={
            "audio_guid": audio_guid,
            "model_name": "approved",
            "raw_text": "hello world",
        },
    )
    assert ref_response.status_code == 201
    ref_id = ref_response.json()["id"]

    hyp_response = client.post(
        "/api/v1/transcription",
        json={
            "audio_guid": audio_guid,
            "model_name": "whisper-large",
            "raw_text": "hello word",
        },
    )
    assert hyp_response.status_code == 201
    hyp_id = hyp_response.json()["id"]

    compare_response = client.post(
        "/api/v1/compare",
        json={"ref_id": ref_id, "hyp_id": hyp_id},
    )
    assert compare_response.status_code == 201

    payload = compare_response.json()
    assert payload["audio_guid"] == audio_guid
    assert payload["ref_id"] == ref_id
    assert payload["hyp_id"] == hyp_id
    assert payload["wer"] == pytest.approx(0.5)

    benchmark = db.get(BenchmarkResult, payload["id"])
    assert benchmark is not None
    assert benchmark.ngram_bigram >= 0.0
    assert benchmark.lcs_score >= 0.0


def test_compare_returns_404_for_missing_transcription(client: TestClient):
    db = next(get_db())
    _seed_audio(db)

    ref = Transcription(
        audio_guid="test-audio-001",
        model_name="approved",
        raw_text="hello",
        normalized_text=AIBenchmark._normalize_text("hello"),
    )
    db.add(ref)
    db.commit()
    db.refresh(ref)

    response = client.post(
        "/api/v1/compare",
        json={"ref_id": ref.id, "hyp_id": 9999},
    )
    assert response.status_code == 404
