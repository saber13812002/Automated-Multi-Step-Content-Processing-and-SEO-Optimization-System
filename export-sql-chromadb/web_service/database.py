"""Database module for storing search history using SQLite."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DB_PATH = _PROJECT_ROOT / "search_history.db"


def get_db_path() -> Path:
    """Get database file path."""
    return _DB_PATH


@contextmanager
def get_db_connection():
    """Get database connection with proper cleanup."""
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database() -> None:
    """Initialize database and create tables if they don't exist."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                result_count INTEGER NOT NULL,
                took_ms REAL NOT NULL,
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                collection TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                results_json TEXT
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON search_history(timestamp DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_query ON search_history(query)
        """)
        conn.commit()
        logger.info("Database initialized at %s", db_path)


def save_search(
    query: str,
    result_count: int,
    took_ms: float,
    collection: str,
    provider: str,
    model: str,
    results: Optional[List[Dict[str, Any]]] = None,
) -> int:
    """Save search query and results to database. Returns search ID."""
    import json

    timestamp = datetime.utcnow().isoformat()
    results_json = json.dumps(results, ensure_ascii=False) if results else None

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO search_history 
            (query, result_count, took_ms, timestamp, collection, provider, model, results_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (query, result_count, took_ms, timestamp, collection, provider, model, results_json))
        search_id = cursor.lastrowid
        logger.debug("Saved search #%d: query='%s', results=%d", search_id, query, result_count)
        return search_id


def get_search_history(
    limit: int = 20,
    offset: int = 0,
    search_id: Optional[int] = None,
) -> tuple[List[Dict[str, Any]], int]:
    """Get search history. Returns (searches, total_count)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if search_id:
            cursor.execute("""
                SELECT id, query, result_count, took_ms, timestamp, collection, provider, model
                FROM search_history
                WHERE id = ?
            """, (search_id,))
            rows = cursor.fetchall()
            total = 1 if rows else 0
        else:
            # Get total count
            cursor.execute("SELECT COUNT(*) FROM search_history")
            total = cursor.fetchone()[0]

            # Get paginated results
            cursor.execute("""
                SELECT id, query, result_count, took_ms, timestamp, collection, provider, model
                FROM search_history
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            rows = cursor.fetchall()

        searches = []
        for row in rows:
            searches.append({
                "id": row["id"],
                "query": row["query"],
                "result_count": row["result_count"],
                "took_ms": row["took_ms"],
                "timestamp": datetime.fromisoformat(row["timestamp"]),
                "collection": row["collection"],
                "provider": row["provider"],
                "model": row["model"],
            })

        return searches, total


def get_search_results(search_id: int) -> Optional[Dict[str, Any]]:
    """Get full results for a specific search ID."""
    import json

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT query, result_count, took_ms, timestamp, collection, provider, model, results_json
            FROM search_history
            WHERE id = ?
        """, (search_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return {
            "id": search_id,
            "query": row["query"],
            "result_count": row["result_count"],
            "took_ms": row["took_ms"],
            "timestamp": datetime.fromisoformat(row["timestamp"]),
            "collection": row["collection"],
            "provider": row["provider"],
            "model": row["model"],
            "results": json.loads(row["results_json"]) if row["results_json"] else None,
        }


__all__ = [
    "init_database",
    "save_search",
    "get_search_history",
    "get_search_results",
    "get_db_path",
]

