#!/usr/bin/env python3
"""
اسکریپت کپی/انتقال داده‌های SQLite از یک Instance به Instance دیگر

این اسکریپت داده‌های SQLite (search_history.db) را از source instance 
(مثلاً staging) به destination instance (مثلاً production) منتقل می‌کند.

استفاده:
    # کپی کامل database (overwrite)
    python copy_sqlite_db.py \
        --source-path /path/to/staging/export-sql-chromadb \
        --dest-path /path/to/production/export-sql-chromadb \
        --mode copy

    # Merge داده‌ها (اضافه کردن به destination)
    python copy_sqlite_db.py \
        --source-path /path/to/staging/export-sql-chromadb \
        --dest-path /path/to/production/export-sql-chromadb \
        --mode merge

    # فقط backup از destination
    python copy_sqlite_db.py \
        --dest-path /path/to/production/export-sql-chromadb \
        --mode backup
"""

import argparse
import logging
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DB_NAME = "search_history.db"


def get_db_path(project_path: Path) -> Path:
    """Get SQLite database path for a project."""
    return project_path / DB_NAME


def backup_database(db_path: Path) -> Path:
    """Create a backup of database file."""
    if not db_path.exists():
        logger.warning(f"Database file {db_path} does not exist, skipping backup")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.parent / f"{db_path.stem}_backup_{timestamp}.db"
    
    logger.info(f"📦 Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)
    logger.info(f"✅ Backup created: {backup_path}")
    return backup_path


def copy_database(source_path: Path, dest_path: Path, create_backup: bool = True) -> None:
    """
    Copy database file from source to destination (overwrite).
    
    Args:
        source_path: Path to source database file
        dest_path: Path to destination database file
        create_backup: Whether to backup destination before overwriting
    """
    if not source_path.exists():
        logger.error(f"❌ Source database not found: {source_path}")
        sys.exit(1)
    
    # Create backup of destination if it exists
    if dest_path.exists() and create_backup:
        backup_database(dest_path)
    
    # Copy database file
    logger.info(f"📋 Copying database from {source_path} to {dest_path}")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, dest_path)
    logger.info(f"✅ Database copied successfully")


def merge_databases(source_path: Path, dest_path: Path, create_backup: bool = True) -> None:
    """
    Merge data from source database into destination database.
    
    This function:
    - Creates backup of destination
    - Copies all data from source tables to destination
    - Handles conflicts (keeps destination data or appends)
    
    Args:
        source_path: Path to source database file
        dest_path: Path to destination database file
        create_backup: Whether to backup destination before merging
    """
    if not source_path.exists():
        logger.error(f"❌ Source database not found: {source_path}")
        sys.exit(1)
    
    # Create backup of destination if it exists
    if dest_path.exists() and create_backup:
        backup_database(dest_path)
    
    # Connect to databases
    logger.info(f"📋 Merging data from {source_path} to {dest_path}")
    
    source_conn = sqlite3.connect(str(source_path))
    source_conn.row_factory = sqlite3.Row
    
    # Create destination database if it doesn't exist
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_conn = sqlite3.connect(str(dest_path))
    dest_conn.row_factory = sqlite3.Row
    
    try:
        # Initialize destination database (create tables if needed)
        # We'll create tables manually to avoid import issues
        dest_cursor = dest_conn.cursor()
        
        # Create tables if they don't exist (same schema as database.py)
        dest_cursor.execute("""
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
        dest_cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON search_history(timestamp DESC)
        """)
        dest_cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_query ON search_history(query)
        """)
        
        dest_cursor.execute("""
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
        dest_cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_export_jobs_started_at ON export_jobs(started_at DESC)
        """)
        dest_cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_export_jobs_status ON export_jobs(status)
        """)
        
        dest_cursor.execute("""
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
        dest_cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_approvals_status ON query_approvals(status)
        """)
        
        dest_cursor.execute("""
            CREATE TABLE IF NOT EXISTS embedding_models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                embedding_provider TEXT NOT NULL,
                embedding_model TEXT NOT NULL,
                collection TEXT NOT NULL,
                job_id INTEGER NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                color TEXT NOT NULL DEFAULT '#3B82F6',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_completed_job_at DATETIME,
                FOREIGN KEY(job_id) REFERENCES export_jobs(id)
            )
        """)
        dest_cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_embedding_models_unique
            ON embedding_models(embedding_provider, embedding_model, collection)
        """)
        dest_cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_embedding_models_active
            ON embedding_models(is_active)
        """)
        
        dest_cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guest_user_id TEXT NOT NULL,
                query TEXT NOT NULL,
                model_id INTEGER,
                result_id TEXT,
                vote_type TEXT NOT NULL CHECK(vote_type IN ('like', 'dislike')),
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(model_id) REFERENCES embedding_models(id)
            )
        """)
        dest_cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_search_votes_guest_user
            ON search_votes(guest_user_id)
        """)
        dest_cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_search_votes_query
            ON search_votes(query)
        """)
        dest_cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_search_votes_unique
            ON search_votes(guest_user_id, query, COALESCE(model_id, -1), COALESCE(result_id, ''))
        """)
        
        dest_cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN NOT NULL DEFAULT 1
            )
        """)
        dest_cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_users_username ON api_users(username)
        """)
        
        dest_cursor.execute("""
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
        dest_cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_tokens_token ON api_tokens(token)
        """)
        dest_cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_tokens_user_id ON api_tokens(user_id)
        """)
        
        dest_cursor.execute("""
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
        dest_cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_token_usage_token_date ON api_token_usage(token_id, date DESC)
        """)
        
        dest_conn.commit()
        
        # Get list of tables from source
        source_cursor = source_conn.cursor()
        source_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in source_cursor.fetchall()]
        
        logger.info(f"📊 Found {len(tables)} tables to merge: {', '.join(tables)}")
        
        dest_cursor = dest_conn.cursor()
        
        for table in tables:
            if table == "sqlite_master":
                continue
            
            logger.info(f"🔄 Merging table: {table}")
            
            # Get all data from source table
            source_cursor.execute(f"SELECT * FROM {table}")
            rows = source_cursor.fetchall()
            
            if not rows:
                logger.info(f"  ⏭️  Table {table} is empty, skipping")
                continue
            
            # Get column names
            column_names = [description[0] for description in source_cursor.description]
            placeholders = ",".join(["?" for _ in column_names])
            columns_str = ",".join(column_names)
            
            # Get existing IDs/keys to avoid duplicates
            # Try to find primary key or unique constraint
            try:
                # For tables with 'id' as primary key
                if "id" in column_names:
                    dest_cursor.execute(f"SELECT id FROM {table}")
                    existing_ids = {row[0] for row in dest_cursor.fetchall()}
                    
                    # Insert only new rows
                    new_rows = [row for row in rows if row["id"] not in existing_ids]
                    if new_rows:
                        values = [tuple(row) for row in new_rows]
                        dest_cursor.executemany(
                            f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})",
                            values,
                        )
                        logger.info(f"  ✅ Added {len(new_rows)} new rows to {table} (skipped {len(rows) - len(new_rows)} duplicates)")
                    else:
                        logger.info(f"  ⏭️  All {len(rows)} rows already exist in {table}, skipping")
                else:
                    # For tables without 'id', use INSERT OR IGNORE
                    values = [tuple(row) for row in rows]
                    dest_cursor.executemany(
                        f"INSERT OR IGNORE INTO {table} ({columns_str}) VALUES ({placeholders})",
                        values,
                    )
                    logger.info(f"  ✅ Merged {len(rows)} rows into {table} (duplicates ignored)")
            except sqlite3.OperationalError as exc:
                # If table structure is different, try to insert what we can
                logger.warning(f"  ⚠️  Could not merge {table}: {exc}")
                continue
        
        dest_conn.commit()
        logger.info("✅ Database merge completed successfully")
        
    except Exception as exc:
        dest_conn.rollback()
        logger.error(f"❌ Error merging databases: {exc}")
        raise
    finally:
        source_conn.close()
        dest_conn.close()


def show_database_info(db_path: Path) -> None:
    """Show information about database."""
    if not db_path.exists():
        logger.warning(f"Database file {db_path} does not exist")
        return
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Get table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        logger.info(f"📊 Database: {db_path}")
        logger.info(f"📋 Tables: {len(tables)}")
        
        # Get row counts for each table
        for table in tables:
            if table == "sqlite_master":
                continue
            try:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                count = cursor.fetchone()["count"]
                logger.info(f"  - {table}: {count} rows")
            except Exception as exc:
                logger.warning(f"  - {table}: Error counting rows ({exc})")
    
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Copy or merge SQLite databases between instances",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    parser.add_argument(
        "--source-path",
        type=str,
        help="Path to source project directory (e.g., /path/to/staging/export-sql-chromadb)",
    )
    parser.add_argument(
        "--dest-path",
        type=str,
        required=True,
        help="Path to destination project directory (e.g., /path/to/production/export-sql-chromadb)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["copy", "merge", "backup", "info"],
        default="merge",
        help="Operation mode: copy (overwrite), merge (add data), backup (backup only), info (show info)",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backup before operation",
    )
    parser.add_argument(
        "--show-source-info",
        action="store_true",
        help="Show information about source database",
    )
    parser.add_argument(
        "--show-dest-info",
        action="store_true",
        help="Show information about destination database",
    )
    
    args = parser.parse_args()
    
    # Convert paths
    dest_project_path = Path(args.dest_path).resolve()
    dest_db_path = get_db_path(dest_project_path)
    
    # Show info if requested
    if args.show_dest_info:
        show_database_info(dest_db_path)
    
    if args.show_source_info and args.source_path:
        source_project_path = Path(args.source_path).resolve()
        source_db_path = get_db_path(source_project_path)
        show_database_info(source_db_path)
    
    if args.show_source_info or args.show_dest_info:
        return
    
    # Execute operation
    if args.mode == "backup":
        if not dest_db_path.exists():
            logger.error(f"❌ Database not found: {dest_db_path}")
            sys.exit(1)
        backup_database(dest_db_path)
        logger.info("✅ Backup completed")
        return
    
    if args.mode == "info":
        show_database_info(dest_db_path)
        if args.source_path:
            source_project_path = Path(args.source_path).resolve()
            source_db_path = get_db_path(source_project_path)
            logger.info("")
            show_database_info(source_db_path)
        return
    
    if not args.source_path:
        parser.error("--source-path is required for copy and merge modes")
    
    source_project_path = Path(args.source_path).resolve()
    source_db_path = get_db_path(source_project_path)
    
    if not source_db_path.exists():
        logger.error(f"❌ Source database not found: {source_db_path}")
        sys.exit(1)
    
    # Execute operation
    try:
        if args.mode == "copy":
            copy_database(
                source_path=source_db_path,
                dest_path=dest_db_path,
                create_backup=not args.no_backup,
            )
        elif args.mode == "merge":
            merge_databases(
                source_path=source_db_path,
                dest_path=dest_db_path,
                create_backup=not args.no_backup,
            )
        
        logger.info("✅ Operation completed successfully!")
        
        # Show final info
        logger.info("")
        logger.info("📊 Destination database info:")
        show_database_info(dest_db_path)
        
    except Exception as exc:
        logger.error(f"❌ Operation failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

