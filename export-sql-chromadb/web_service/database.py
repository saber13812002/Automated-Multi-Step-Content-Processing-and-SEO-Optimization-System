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
    # Ensure UTF-8 encoding for proper Persian text storage
    conn.execute("PRAGMA encoding='UTF-8'")
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
        
        # Create export_jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS export_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL CHECK(status IN ('pending', 'running', 'completed', 'failed')),
                started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                duration_seconds REAL,
                sql_path TEXT NOT NULL,
                collection TEXT NOT NULL,
                batch_size INTEGER NOT NULL,
                max_length INTEGER NOT NULL,
                context_length INTEGER NOT NULL,
                host TEXT NOT NULL,
                port INTEGER NOT NULL,
                ssl BOOLEAN NOT NULL DEFAULT 0,
                embedding_provider TEXT NOT NULL,
                embedding_model TEXT NOT NULL,
                reset BOOLEAN NOT NULL DEFAULT 0,
                total_records INTEGER,
                total_books INTEGER,
                total_segments INTEGER,
                total_documents_in_collection INTEGER,
                error_message TEXT,
                command_line_args TEXT
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_export_jobs_started_at ON export_jobs(started_at DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_export_jobs_status ON export_jobs(status)
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


def create_export_job(args: Any) -> int:
    """Create a new export job record. Returns job ID."""
    import json
    
    started_at = datetime.utcnow().isoformat()
    
    # Convert args to dict for JSON serialization
    command_args = {
        "sql_path": getattr(args, "sql_path", ""),
        "collection": getattr(args, "collection", ""),
        "batch_size": getattr(args, "batch_size", 0),
        "max_length": getattr(args, "max_length", 0),
        "context": getattr(args, "context", 0),
        "host": getattr(args, "host", ""),
        "port": getattr(args, "port", 0),
        "ssl": getattr(args, "ssl", False),
        "api_key": getattr(args, "api_key", ""),
        "persist_directory": getattr(args, "persist_directory", ""),
        "embedding_provider": getattr(args, "embedding_provider", ""),
        "embedding_model": getattr(args, "embedding_model", ""),
        "openai_api_key": "***" if getattr(args, "openai_api_key", "") else "",  # Hide sensitive data
        "reset": getattr(args, "reset", False),
    }
    command_args_json = json.dumps(command_args, ensure_ascii=False)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO export_jobs 
            (status, started_at, sql_path, collection, batch_size, max_length, context_length,
             host, port, ssl, embedding_provider, embedding_model, reset, command_line_args)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "running",
            started_at,
            getattr(args, "sql_path", ""),
            getattr(args, "collection", ""),
            getattr(args, "batch_size", 0),
            getattr(args, "max_length", 0),
            getattr(args, "context", 0),
            getattr(args, "host", ""),
            getattr(args, "port", 0),
            bool(getattr(args, "ssl", False)),
            getattr(args, "embedding_provider", ""),
            getattr(args, "embedding_model", ""),
            bool(getattr(args, "reset", False)),
            command_args_json,
        ))
        job_id = cursor.lastrowid
        logger.info("Created export job #%d", job_id)
        return job_id


def update_export_job(
    job_id: int,
    status: str,
    **kwargs: Any,
) -> None:
    """Update export job status and fields."""
    if status not in ("pending", "running", "completed", "failed"):
        raise ValueError(f"Invalid status: {status}")
    
    completed_at = None
    duration_seconds = None
    
    if status in ("completed", "failed"):
        completed_at = datetime.utcnow().isoformat()
        # Calculate duration if started_at exists
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT started_at FROM export_jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            if row and row["started_at"]:
                started = datetime.fromisoformat(row["started_at"])
                completed = datetime.fromisoformat(completed_at)
                duration_seconds = (completed - started).total_seconds()
    
    # Build update query dynamically based on kwargs
    update_fields = ["status = ?"]
    values = [status]
    
    if completed_at:
        update_fields.append("completed_at = ?")
        values.append(completed_at)
    
    if duration_seconds is not None:
        update_fields.append("duration_seconds = ?")
        values.append(duration_seconds)
    
    # Add any additional fields from kwargs
    allowed_fields = {
        "total_records", "total_books", "total_segments",
        "total_documents_in_collection", "error_message"
    }
    for key, value in kwargs.items():
        if key in allowed_fields:
            update_fields.append(f"{key} = ?")
            values.append(value)
    
    values.append(job_id)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = f"UPDATE export_jobs SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(query, values)
        logger.debug("Updated export job #%d: status=%s", job_id, status)


def get_export_jobs(limit: int = 50) -> List[Dict[str, Any]]:
    """Get list of export jobs (most recent first, max 50)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, status, started_at, completed_at, duration_seconds,
                   sql_path, collection, batch_size, max_length, context_length,
                   host, port, ssl, embedding_provider, embedding_model, reset,
                   total_records, total_books, total_segments, total_documents_in_collection,
                   error_message, command_line_args
            FROM export_jobs
            ORDER BY started_at DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        
        jobs = []
        for row in rows:
            jobs.append({
                "id": row["id"],
                "status": row["status"],
                "started_at": datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
                "completed_at": datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                "duration_seconds": row["duration_seconds"],
                "sql_path": row["sql_path"],
                "collection": row["collection"],
                "batch_size": row["batch_size"],
                "max_length": row["max_length"],
                "context_length": row["context_length"],
                "host": row["host"],
                "port": row["port"],
                "ssl": bool(row["ssl"]),
                "embedding_provider": row["embedding_provider"],
                "embedding_model": row["embedding_model"],
                "reset": bool(row["reset"]),
                "total_records": row["total_records"],
                "total_books": row["total_books"],
                "total_segments": row["total_segments"],
                "total_documents_in_collection": row["total_documents_in_collection"],
                "error_message": row["error_message"],
                "command_line_args": row["command_line_args"],
            })
        
        return jobs


def get_export_job(job_id: int) -> Optional[Dict[str, Any]]:
    """Get full details of a specific export job."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, status, started_at, completed_at, duration_seconds,
                   sql_path, collection, batch_size, max_length, context_length,
                   host, port, ssl, embedding_provider, embedding_model, reset,
                   total_records, total_books, total_segments, total_documents_in_collection,
                   error_message, command_line_args
            FROM export_jobs
            WHERE id = ?
        """, (job_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return {
            "id": row["id"],
            "status": row["status"],
            "started_at": datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            "completed_at": datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            "duration_seconds": row["duration_seconds"],
            "sql_path": row["sql_path"],
            "collection": row["collection"],
            "batch_size": row["batch_size"],
            "max_length": row["max_length"],
            "context_length": row["context_length"],
            "host": row["host"],
            "port": row["port"],
            "ssl": bool(row["ssl"]),
            "embedding_provider": row["embedding_provider"],
            "embedding_model": row["embedding_model"],
            "reset": bool(row["reset"]),
            "total_records": row["total_records"],
            "total_books": row["total_books"],
            "total_segments": row["total_segments"],
            "total_documents_in_collection": row["total_documents_in_collection"],
            "error_message": row["error_message"],
            "command_line_args": row["command_line_args"],
        }


__all__ = [
    "init_database",
    "save_search",
    "get_search_history",
    "get_search_results",
    "get_db_path",
    "create_export_job",
    "update_export_job",
    "get_export_jobs",
    "get_export_job",
]

