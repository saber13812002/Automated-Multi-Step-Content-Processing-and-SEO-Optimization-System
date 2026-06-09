import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from ai_benchmarker.database import get_db
from ai_benchmarker.storage import BenchmarkResult
from conftest import REFERENCE_TEXT, add_transcription, create_reference, run_compare

SRT_REFERENCE = """1
00:00:01,000 --> 00:00:04,000
سلام دنیا

2
00:00:05,000 --> 00:00:08,000
این یک متن مرجع برای تست بنچمارک است
"""


def test_scenario_ideal_perfect_match(client: TestClient):
    ref = create_reference(client)
    hyp = add_transcription(client, ref["audio_guid"], "model-ideal", REFERENCE_TEXT)
    result = run_compare(client, ref["reference_transcription_id"], hyp["id"])

    assert result["wer"] == pytest.approx(0.0)
    assert result["lcs_score"] == pytest.approx(1.0)
    assert result["ngram_bigram"] == pytest.approx(1.0)

    db = next(get_db())
    benchmark = db.get(BenchmarkResult, result["id"])
    assert benchmark is not None

    listed = client.get(f"/api/v1/benchmarks?audio_guid={ref['audio_guid']}")
    assert any(item["id"] == result["id"] for item in listed.json())


def test_scenario_medium_tone_change(client: TestClient):
    ref = create_reference(client)
    hyp_text = "سلام دنیا این یک متن مرجع برای تست بنچمارک هست"
    hyp = add_transcription(client, ref["audio_guid"], "model-medium", hyp_text)
    result = run_compare(client, ref["reference_transcription_id"], hyp["id"])

    assert result["wer"] == pytest.approx(0.1, abs=0.05)
    assert result["lcs_score"] > 0.8
    assert result["ngram_bigram"] > 0.5


def test_scenario_weak_missing_text(client: TestClient):
    ref = create_reference(client)
    hyp_text = "سلام دنیا تست"
    hyp = add_transcription(client, ref["audio_guid"], "model-weak", hyp_text)
    result = run_compare(client, ref["reference_transcription_id"], hyp["id"])

    assert result["wer"] > 0.4
    assert result["lcs_score"] < 0.7


def test_scenario_srt_reference_parsing(client: TestClient):
    ref = create_reference(client, text=SRT_REFERENCE, file_name="ref.srt")
    hyp = add_transcription(
        client,
        ref["audio_guid"],
        "model-srt-test",
        "سلام دنیا این یک متن مرجع برای تست بنچمارک است",
    )
    result = run_compare(client, ref["reference_transcription_id"], hyp["id"])

    assert result["wer"] == pytest.approx(0.0)
    assert result["lcs_score"] == pytest.approx(1.0)


def test_scenario_all_three_ranked_by_wer(client: TestClient):
    ref = create_reference(client)
    ref_id = ref["reference_transcription_id"]

    ideal = add_transcription(client, ref["audio_guid"], "model-ideal", REFERENCE_TEXT)
    medium = add_transcription(
        client, ref["audio_guid"], "model-medium",
        "سلام دنیا این یک متن مرجع برای تست بنچمارک هست",
    )
    weak = add_transcription(client, ref["audio_guid"], "model-weak", "سلام دنیا تست")

    ideal_result = run_compare(client, ref_id, ideal["id"])
    medium_result = run_compare(client, ref_id, medium["id"])
    weak_result = run_compare(client, ref_id, weak["id"])

    assert ideal_result["wer"] < medium_result["wer"] < weak_result["wer"]
