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
        
        # Create query_approvals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'approved' CHECK(status IN ('approved', 'rejected', 'pending')),
                approved_at DATETIME,
                rejected_at DATETIME,
                notes TEXT,
                search_count INTEGER NOT NULL DEFAULT 0,
                last_searched_at DATETIME
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_approvals_status ON query_approvals(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_approvals_search_count ON query_approvals(search_count DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_approvals_last_searched ON query_approvals(last_searched_at DESC)
        """)
        
        # Create API authentication tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN NOT NULL DEFAULT 1
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_users_username ON api_users(username)
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                rate_limit_per_day INTEGER NOT NULL DEFAULT 1000,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                last_used_at DATETIME,
                FOREIGN KEY (user_id) REFERENCES api_users(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_tokens_token ON api_tokens(token)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_tokens_user_id ON api_tokens(user_id)
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_id INTEGER NOT NULL,
                date DATE NOT NULL,
                request_count INTEGER NOT NULL DEFAULT 0,
                last_request_at DATETIME,
                FOREIGN KEY (token_id) REFERENCES api_tokens(id) ON DELETE CASCADE,
                UNIQUE(token_id, date)
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_token_usage_token_date ON api_token_usage(token_id, date DESC)
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
        
        # Update query search count
        try:
            update_query_search_count(query)
        except Exception as exc:
            logger.warning("Failed to update query search count: %s", exc)
        
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


def get_query_approvals(
    limit: int = 50,
    min_count: int = 0,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get query approvals with filters."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = """
            SELECT id, query, status, approved_at, rejected_at, notes, 
                   search_count, last_searched_at
            FROM query_approvals
            WHERE search_count >= ?
        """
        params = [min_count]
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY search_count DESC, last_searched_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        approvals = []
        for row in rows:
            approvals.append({
                "id": row["id"],
                "query": row["query"],
                "status": row["status"],
                "approved_at": datetime.fromisoformat(row["approved_at"]) if row["approved_at"] else None,
                "rejected_at": datetime.fromisoformat(row["rejected_at"]) if row["rejected_at"] else None,
                "notes": row["notes"],
                "search_count": row["search_count"],
                "last_searched_at": datetime.fromisoformat(row["last_searched_at"]) if row["last_searched_at"] else None,
            })
        
        return approvals


def approve_query(query: str, notes: Optional[str] = None) -> None:
    """Approve a query."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        
        # Try to update existing, or insert new
        cursor.execute("""
            INSERT INTO query_approvals (query, status, approved_at, notes)
            VALUES (?, 'approved', ?, ?)
            ON CONFLICT(query) DO UPDATE SET
                status = 'approved',
                approved_at = ?,
                rejected_at = NULL,
                notes = COALESCE(?, notes)
        """, (query, now, notes, now, notes))
        logger.debug("Approved query: %s", query)


def reject_query(query: str, notes: Optional[str] = None) -> None:
    """Reject a query."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        
        cursor.execute("""
            INSERT INTO query_approvals (query, status, rejected_at, notes)
            VALUES (?, 'rejected', ?, ?)
            ON CONFLICT(query) DO UPDATE SET
                status = 'rejected',
                rejected_at = ?,
                approved_at = NULL,
                notes = COALESCE(?, notes)
        """, (query, now, notes, now, notes))
        logger.debug("Rejected query: %s", query)


def delete_query(query: str) -> None:
    """Delete a query from approvals."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM query_approvals WHERE query = ?", (query,))
        logger.debug("Deleted query: %s", query)


def get_query_stats() -> Dict[str, Any]:
    """Get statistics about queries."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(search_count) as total_searches
            FROM query_approvals
        """)
        row = cursor.fetchone()
        
        return {
            "total": row["total"] if row else 0,
            "approved": row["approved"] if row else 0,
            "rejected": row["rejected"] if row else 0,
            "pending": row["pending"] if row else 0,
            "total_searches": row["total_searches"] if row else 0,
        }


def update_query_search_count(query: str) -> None:
    """Update search count and last searched time for a query."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        
        # Insert or update
        cursor.execute("""
            INSERT INTO query_approvals (query, status, search_count, last_searched_at)
            VALUES (?, 'approved', 1, ?)
            ON CONFLICT(query) DO UPDATE SET
                search_count = search_count + 1,
                last_searched_at = ?
        """, (query, now, now))
        logger.debug("Updated search count for query: %s", query)


def create_api_user(username: str, email: Optional[str] = None) -> int:
    """Create a new API user. Returns user ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO api_users (username, email)
            VALUES (?, ?)
        """, (username, email))
        user_id = cursor.lastrowid
        logger.info("Created API user #%d: %s", user_id, username)
        return user_id


def create_api_token(
    user_id: int,
    token: str,
    name: str,
    rate_limit_per_day: int = 1000,
    expires_at: Optional[str] = None,
) -> int:
    """Create a new API token. Returns token ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        created_at = datetime.utcnow().isoformat()
        cursor.execute("""
            INSERT INTO api_tokens (user_id, token, name, rate_limit_per_day, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, token, name, rate_limit_per_day, expires_at, created_at))
        token_id = cursor.lastrowid
        logger.info("Created API token #%d for user #%d: %s", token_id, user_id, name)
        return token_id


def get_api_token(token_hash: str) -> Optional[Dict[str, Any]]:
    """Get API token by hash. Returns token info or None."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.id, t.user_id, t.token, t.name, t.rate_limit_per_day, 
                   t.created_at, t.expires_at, t.is_active, t.last_used_at,
                   u.username, u.email, u.is_active as user_is_active
            FROM api_tokens t
            JOIN api_users u ON t.user_id = u.id
            WHERE t.token = ? AND t.is_active = 1 AND u.is_active = 1
        """, (token_hash,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "token": row["token"],
            "name": row["name"],
            "rate_limit_per_day": row["rate_limit_per_day"],
            "created_at": datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            "expires_at": datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
            "is_active": bool(row["is_active"]),
            "last_used_at": datetime.fromisoformat(row["last_used_at"]) if row["last_used_at"] else None,
            "username": row["username"],
            "email": row["email"],
            "user_is_active": bool(row["user_is_active"]),
        }


def increment_token_usage(token_id: int) -> None:
    """Increment request count for a token today."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.utcnow()
        today = now.date().isoformat()
        now_iso = now.isoformat()
        
        cursor.execute("""
            INSERT INTO api_token_usage (token_id, date, request_count, last_request_at)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(token_id, date) DO UPDATE SET
                request_count = request_count + 1,
                last_request_at = ?
        """, (token_id, today, now_iso, now_iso))
        
        # Update last_used_at in api_tokens
        cursor.execute("""
            UPDATE api_tokens SET last_used_at = ? WHERE id = ?
        """, (now_iso, token_id))
        
        logger.debug("Incremented usage for token #%d", token_id)


def get_token_usage_today(token_id: int) -> int:
    """Get request count for a token today."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        today = datetime.utcnow().date().isoformat()
        cursor.execute("""
            SELECT request_count FROM api_token_usage
            WHERE token_id = ? AND date = ?
        """, (token_id, today))
        row = cursor.fetchone()
        return row["request_count"] if row else 0


def get_all_tokens(user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get all tokens, optionally filtered by user_id."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute("""
                SELECT t.id, t.user_id, t.name, t.rate_limit_per_day, 
                       t.created_at, t.expires_at, t.is_active, t.last_used_at,
                       u.username, u.email
                FROM api_tokens t
                JOIN api_users u ON t.user_id = u.id
                WHERE t.user_id = ?
                ORDER BY t.created_at DESC
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT t.id, t.user_id, t.name, t.rate_limit_per_day, 
                       t.created_at, t.expires_at, t.is_active, t.last_used_at,
                       u.username, u.email
                FROM api_tokens t
                JOIN api_users u ON t.user_id = u.id
                ORDER BY t.created_at DESC
            """)
        
        rows = cursor.fetchall()
        tokens = []
        for row in rows:
            tokens.append({
                "id": row["id"],
                "user_id": row["user_id"],
                "name": row["name"],
                "rate_limit_per_day": row["rate_limit_per_day"],
                "created_at": datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                "expires_at": datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
                "is_active": bool(row["is_active"]),
                "last_used_at": datetime.fromisoformat(row["last_used_at"]) if row["last_used_at"] else None,
                "username": row["username"],
                "email": row["email"],
            })
        return tokens


def revoke_token(token_id: int) -> None:
    """Revoke (deactivate) a token."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE api_tokens SET is_active = 0 WHERE id = ?
        """, (token_id,))
        logger.info("Revoked token #%d", token_id)


def get_all_users() -> List[Dict[str, Any]]:
    """Get all API users."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, created_at, is_active
            FROM api_users
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        users = []
        for row in rows:
            users.append({
                "id": row["id"],
                "username": row["username"],
                "email": row["email"],
                "created_at": datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                "is_active": bool(row["is_active"]),
            })
        return users


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
    "get_query_approvals",
    "approve_query",
    "reject_query",
    "delete_query",
    "get_query_stats",
    "update_query_search_count",
    "create_api_user",
    "create_api_token",
    "get_api_token",
    "increment_token_usage",
    "get_token_usage_today",
    "get_all_tokens",
    "revoke_token",
    "get_all_users",
]

