import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_SERVICE_DIR = PROJECT_ROOT / "web_service"
if str(WEB_SERVICE_DIR) not in sys.path:
    sys.path.append(str(WEB_SERVICE_DIR))

import database  # type: ignore


@pytest.fixture()
def temp_db(tmp_path):
    original_path = database._DB_PATH
    test_db_path = tmp_path / "test_search_history.db"
    database._DB_PATH = test_db_path
    database.init_database()
    yield test_db_path
    database._DB_PATH = original_path


def insert_completed_job(
    job_id: int,
    collection: str,
    embedding_model: str,
    provider: str = "openai",
) -> None:
    completed_at = datetime.utcnow()
    started_at = completed_at - timedelta(minutes=5)
    with database.get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO export_jobs (
                id, status, started_at, completed_at, duration_seconds,
                sql_path, collection, batch_size, max_length, context_length,
                host, port, ssl, embedding_provider, embedding_model, reset,
                total_records, total_books, total_segments, total_documents_in_collection,
                error_message, command_line_args
            ) VALUES (?, 'completed', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                started_at.isoformat(),
                completed_at.isoformat(),
                300.0,
                "test.sql",
                collection,
                32,
                256,
                128,
                "localhost",
                8000,
                0,
                provider,
                embedding_model,
                0,
                100,
                10,
                500,
                500,
                None,
                json.dumps({"test": True}, ensure_ascii=False),
            ),
        )


def test_embedding_model_sync_and_toggle(temp_db):
    insert_completed_job(1, "book_pages", "text-embedding-3-small")
    database.sync_embedding_models_from_jobs(limit=5)

    models = database.get_embedding_models(limit=5, ensure_sync=False)
    assert len(models) == 1
    model_id = models[0]["id"]

    # Toggle model status
    assert database.set_embedding_model_active(model_id, False)
    model = database.get_embedding_model(model_id)
    assert model is not None
    assert model["is_active"] is False

    # Update color
    assert database.update_embedding_model_color(model_id, "#123456")
    updated_model = database.get_embedding_model(model_id)
    assert updated_model["color"] == "#123456"


def test_save_search_vote_and_stats(temp_db):
    guest_id = "guest-123"
    query = "تست رای"

    # Initial like vote
    database.save_search_vote(
        guest_user_id=guest_id,
        query=query,
        vote_type="like",
        model_id=None,
        result_id="doc-1",
    )
    stats = database.get_vote_stats(query=query, model_id=None)
    assert stats["likes"] == 1
    assert stats["dislikes"] == 0

    # Change to dislike (should overwrite)
    database.save_search_vote(
        guest_user_id=guest_id,
        query=query,
        vote_type="dislike",
        model_id=None,
        result_id="doc-1",
    )
    stats = database.get_vote_stats(query=query, model_id=None)
    assert stats["likes"] == 0
    assert stats["dislikes"] == 1

    votes = database.get_search_votes(limit=10, query=query, model_id=None)
    assert len(votes) == 1
    assert votes[0]["vote_type"] == "dislike"

    summary = database.get_vote_summary(limit=10)
    assert summary
    assert summary[0]["dislikes"] == 1

