from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ai_benchmarker.app import create_app
from ai_benchmarker.database import init_db, reset_engine

REFERENCE_TEXT = "سلام دنیا این یک متن مرجع برای تست بنچمارک است"


@pytest.fixture()
def client(monkeypatch, tmp_path):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    reset_engine()
    init_db()

    app = create_app()

    with TestClient(app) as test_client:
        yield test_client

    reset_engine()


def create_reference(client: TestClient, text: str = REFERENCE_TEXT, file_name: str = "ref.txt"):
    response = client.post(
        "/api/v1/audio/json",
        json={"file_name": file_name, "approved_text": text},
    )
    assert response.status_code == 201
    return response.json()


def add_transcription(client: TestClient, audio_guid: str, model_name: str, raw_text: str):
    response = client.post(
        "/api/v1/transcription",
        json={
            "audio_guid": audio_guid,
            "model_name": model_name,
            "raw_text": raw_text,
        },
    )
    assert response.status_code == 201
    return response.json()


def run_compare(client: TestClient, ref_id: int, hyp_id: int):
    response = client.post(
        "/api/v1/compare",
        json={"ref_id": ref_id, "hyp_id": hyp_id},
    )
    assert response.status_code == 201
    return response.json()
