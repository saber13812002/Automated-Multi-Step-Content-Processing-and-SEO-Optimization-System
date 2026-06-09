import csv
import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from ai_benchmarker.core import AIBenchmark
from ai_benchmarker.database import get_db, seed_audio_master
from ai_benchmarker.storage import BenchmarkResult, Transcription
from conftest import add_transcription, create_reference, run_compare


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


def test_create_audio_json_and_admin(client: TestClient):
    response = client.post(
        "/api/v1/audio/json",
        json={
            "file_name": "ref.txt",
            "approved_text": "hello world reference",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["audio_guid"]
    assert data["reference_transcription_id"] >= 1

    admin = client.get("/admin")
    assert admin.status_code == 200

    listings = client.get("/api/v1/audio")
    assert listings.status_code == 200
    assert len(listings.json()["items"]) >= 1


def test_reports_page(client: TestClient):
    response = client.get("/reports")
    assert response.status_code == 200
    assert "گزارش" in response.text or "Benchmark" in response.text


def test_list_transcriptions_and_benchmarks(client: TestClient):
    ref = create_reference(client, text="one two three four five")
    hyp = add_transcription(client, ref["audio_guid"], "test-model", "one two three")
    run_compare(client, ref["reference_transcription_id"], hyp["id"])

    tx = client.get(f"/api/v1/transcriptions?audio_guid={ref['audio_guid']}")
    assert tx.status_code == 200
    assert len(tx.json()) >= 2

    benchmarks = client.get(f"/api/v1/benchmarks?audio_guid={ref['audio_guid']}")
    assert benchmarks.status_code == 200
    assert len(benchmarks.json()) >= 1


def test_export_csv_returns_valid_rows(client: TestClient):
    ref = create_reference(client, text="alpha beta gamma delta")
    hyp = add_transcription(client, ref["audio_guid"], "csv-model", "alpha beta gamma")
    run_compare(client, ref["reference_transcription_id"], hyp["id"])

    response = client.get(f"/api/v1/benchmarks/export.csv?audio_guid={ref['audio_guid']}")
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
    assert "attachment" in response.headers.get("content-disposition", "")

    reader = csv.DictReader(io.StringIO(response.text))
    rows = list(reader)
    assert len(rows) >= 1
    assert "wer" in rows[0]
    assert "ref_model" in rows[0]
    assert rows[0]["hyp_model"] == "csv-model"


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
