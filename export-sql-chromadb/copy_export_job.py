#!/usr/bin/env python3
"""
اسکریپت تعاملی برای کپی Export Job موفق و ارتباطاتش از یک Instance به Instance دیگر

این اسکریپت:
1. به source و destination database متصل می‌شود
2. لیست export jobs موفق را نمایش می‌دهد
3. کاربر یکی را انتخاب می‌کند
4. آن job و embedding_models مرتبط را کپی می‌کند

استفاده:
    python copy_export_job.py \
        --source-path /path/to/staging/export-sql-chromadb \
        --dest-path /path/to/production/export-sql-chromadb
"""

import argparse
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DB_NAME = "search_history.db"


def get_db_path(project_path: Path) -> Path:
    """Get SQLite database path for a project."""
    return project_path / DB_NAME


def test_connection(db_path: Path, label: str) -> bool:
    """Test database connection and return True if successful."""
    if not db_path.exists():
        logger.error(f"❌ {label}: Database file not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Test query
        cursor.execute("SELECT COUNT(*) as count FROM export_jobs")
        count = cursor.fetchone()["count"]
        
        conn.close()
        logger.info(f"✅ {label}: Connection successful (found {count} export jobs)")
        return True
    except Exception as exc:
        logger.error(f"❌ {label}: Connection failed: {exc}")
        return False


def get_completed_jobs(db_path: Path) -> List[Dict]:
    """Get list of completed export jobs from database."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                id,
                collection,
                embedding_provider,
                embedding_model,
                started_at,
                completed_at,
                duration_seconds,
                total_records,
                total_books,
                total_segments,
                total_documents_in_collection
            FROM export_jobs
            WHERE status = 'completed' AND completed_at IS NOT NULL
            ORDER BY completed_at DESC
        """)
        
        rows = cursor.fetchall()
        jobs = []
        for row in rows:
            jobs.append({
                "id": row["id"],
                "collection": row["collection"],
                "embedding_provider": row["embedding_provider"],
                "embedding_model": row["embedding_model"],
                "started_at": row["started_at"],
                "completed_at": row["completed_at"],
                "duration_seconds": row["duration_seconds"],
                "total_records": row["total_records"],
                "total_books": row["total_books"],
                "total_segments": row["total_segments"],
                "total_documents_in_collection": row["total_documents_in_collection"],
            })
        
        return jobs
    finally:
        conn.close()


def get_embedding_models_for_job(db_path: Path, job_id: int) -> List[Dict]:
    """Get embedding models related to a job."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                id,
                embedding_provider,
                embedding_model,
                collection,
                is_active,
                color,
                created_at,
                updated_at,
                last_completed_job_at
            FROM embedding_models
            WHERE job_id = ?
        """, (job_id,))
        
        rows = cursor.fetchall()
        models = []
        for row in rows:
            models.append({
                "id": row["id"],
                "embedding_provider": row["embedding_provider"],
                "embedding_model": row["embedding_model"],
                "collection": row["collection"],
                "is_active": bool(row["is_active"]),
                "color": row["color"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "last_completed_job_at": row["last_completed_job_at"],
            })
        
        return models
    finally:
        conn.close()


def get_job_details(db_path: Path, job_id: int) -> Optional[Dict]:
    """Get full details of an export job."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT *
            FROM export_jobs
            WHERE id = ?
        """, (job_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return dict(row)
    finally:
        conn.close()


def copy_job_and_models(
    source_path: Path,
    dest_path: Path,
    job_id: int,
    create_backup: bool = True,
) -> bool:
    """Copy export job and related embedding models from source to destination."""
    import shutil
    
    # Create backup if requested
    if create_backup and dest_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = dest_path.parent / f"{dest_path.stem}_backup_{timestamp}.db"
        logger.info(f"📦 Creating backup: {backup_path}")
        shutil.copy2(dest_path, backup_path)
        logger.info(f"✅ Backup created")
    
    # Connect to databases
    source_conn = sqlite3.connect(str(source_path))
    source_conn.row_factory = sqlite3.Row
    
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_conn = sqlite3.connect(str(dest_path))
    dest_conn.row_factory = sqlite3.Row
    
    try:
        # Initialize destination database tables if needed
        dest_cursor = dest_conn.cursor()
        
        # Create tables if they don't exist
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
        
        dest_conn.commit()
        
        # Get job from source
        source_cursor = source_conn.cursor()
        source_cursor.execute("SELECT * FROM export_jobs WHERE id = ?", (job_id,))
        job_row = source_cursor.fetchone()
        
        if not job_row:
            logger.error(f"❌ Job {job_id} not found in source database")
            return False
        
        job_data = dict(job_row)
        
        # Check if job already exists in destination
        dest_cursor.execute("SELECT id FROM export_jobs WHERE id = ?", (job_id,))
        existing_job = dest_cursor.fetchone()
        
        if existing_job:
            logger.warning(f"⚠️  Job {job_id} already exists in destination. Skipping job copy.")
            new_job_id = job_id
        else:
            # Insert job (without the original ID to get new auto-increment ID)
            job_columns = [k for k in job_data.keys() if k != "id"]
            job_values = [job_data[k] for k in job_columns]
            placeholders = ",".join(["?" for _ in job_columns])
            columns_str = ",".join(job_columns)
            
            dest_cursor.execute(
                f"INSERT INTO export_jobs ({columns_str}) VALUES ({placeholders})",
                job_values,
            )
            new_job_id = dest_cursor.lastrowid
            logger.info(f"✅ Copied export job: {job_id} -> {new_job_id}")
        
        # Get embedding models for this job
        source_cursor.execute(
            "SELECT * FROM embedding_models WHERE job_id = ?",
            (job_id,),
        )
        model_rows = source_cursor.fetchall()
        
        if model_rows:
            logger.info(f"📋 Found {len(model_rows)} embedding model(s) to copy")
            
            for model_row in model_rows:
                model_data = dict(model_row)
                
                # Check if model already exists (by unique constraint)
                dest_cursor.execute("""
                    SELECT id FROM embedding_models 
                    WHERE embedding_provider = ? 
                      AND embedding_model = ? 
                      AND collection = ?
                """, (
                    model_data["embedding_provider"],
                    model_data["embedding_model"],
                    model_data["collection"],
                ))
                existing_model = dest_cursor.fetchone()
                
                if existing_model:
                    # Update existing model to point to new job
                    dest_cursor.execute("""
                        UPDATE embedding_models
                        SET job_id = ?,
                            last_completed_job_at = ?,
                            updated_at = ?
                        WHERE id = ?
                    """, (
                        new_job_id,
                        model_data.get("last_completed_job_at"),
                        datetime.utcnow().isoformat(),
                        existing_model["id"],
                    ))
                    logger.info(
                        f"  ✅ Updated existing embedding model: "
                        f"{model_data['embedding_provider']}/{model_data['embedding_model']}"
                    )
                else:
                    # Insert new model with new job_id
                    model_columns = [k for k in model_data.keys() if k != "id"]
                    model_values = [model_data[k] for k in model_columns]
                    # Replace job_id with new_job_id
                    job_id_idx = model_columns.index("job_id")
                    model_values[job_id_idx] = new_job_id
                    
                    placeholders = ",".join(["?" for _ in model_columns])
                    columns_str = ",".join(model_columns)
                    
                    dest_cursor.execute(
                        f"INSERT INTO embedding_models ({columns_str}) VALUES ({placeholders})",
                        model_values,
                    )
                    logger.info(
                        f"  ✅ Copied embedding model: "
                        f"{model_data['embedding_provider']}/{model_data['embedding_model']}"
                    )
        else:
            logger.info("ℹ️  No embedding models found for this job")
        
        dest_conn.commit()
        logger.info(f"🎉 Successfully copied job {job_id} and related models!")
        return True
        
    except Exception as exc:
        dest_conn.rollback()
        logger.error(f"❌ Error copying job: {exc}")
        raise
    finally:
        source_conn.close()
        dest_conn.close()


def display_jobs(jobs: List[Dict], source_label: str = "Source") -> None:
    """Display list of jobs in a formatted table."""
    if not jobs:
        logger.warning(f"⚠️  No completed jobs found in {source_label}")
        return
    
    print(f"\n{'='*100}")
    print(f"📋 Completed Export Jobs in {source_label} ({len(jobs)} jobs)")
    print(f"{'='*100}")
    print(f"{'#':<4} {'ID':<6} {'Collection':<25} {'Provider':<12} {'Model':<30} {'Completed':<20}")
    print(f"{'-'*100}")
    
    for idx, job in enumerate(jobs, 1):
        completed = job["completed_at"][:19] if job["completed_at"] else "N/A"
        print(
            f"{idx:<4} {job['id']:<6} {job['collection'][:24]:<25} "
            f"{job['embedding_provider'][:11]:<12} {job['embedding_model'][:29]:<30} {completed:<20}"
        )
    
    print(f"{'='*100}\n")


def display_job_details(job: Dict, models: List[Dict]) -> None:
    """Display detailed information about a job."""
    print(f"\n{'='*100}")
    print(f"📊 Job Details")
    print(f"{'='*100}")
    print(f"ID:                    {job['id']}")
    print(f"Collection:            {job['collection']}")
    print(f"Embedding Provider:    {job['embedding_provider']}")
    print(f"Embedding Model:       {job['embedding_model']}")
    print(f"Started At:            {job['started_at']}")
    print(f"Completed At:          {job['completed_at']}")
    print(f"Duration:              {job['duration_seconds']:.2f} seconds")
    print(f"Total Records:         {job['total_records']}")
    print(f"Total Books:           {job['total_books']}")
    print(f"Total Segments:        {job['total_segments']}")
    print(f"Documents in Collection: {job['total_documents_in_collection']}")
    
    if models:
        print(f"\n📋 Related Embedding Models ({len(models)}):")
        for model in models:
            status = "✅ Active" if model["is_active"] else "❌ Inactive"
            print(f"  - {model['embedding_provider']}/{model['embedding_model']} "
                  f"(Collection: {model['collection']}) {status}")
    
    print(f"{'='*100}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Copy export job and related models between instances",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    parser.add_argument(
        "--source-path",
        type=str,
        required=True,
        help="Path to source project directory",
    )
    parser.add_argument(
        "--dest-path",
        type=str,
        required=True,
        help="Path to destination project directory",
    )
    parser.add_argument(
        "--job-id",
        type=int,
        help="Specific job ID to copy (skip interactive selection)",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backup before operation",
    )
    parser.add_argument(
        "--no-connection-test",
        action="store_true",
        help="Skip connection test",
    )
    
    args = parser.parse_args()
    
    # Convert paths
    source_project_path = Path(args.source_path).resolve()
    dest_project_path = Path(args.dest_path).resolve()
    source_db_path = get_db_path(source_project_path)
    dest_db_path = get_db_path(dest_project_path)
    
    # Test connections
    if not args.no_connection_test:
        print("\n🔍 Testing connections...")
        source_ok = test_connection(source_db_path, "Source")
        dest_ok = test_connection(dest_db_path, "Destination")
        
        if not source_ok or not dest_ok:
            logger.error("❌ Connection test failed. Please fix the issues above.")
            sys.exit(1)
        
        print("✅ Both connections successful!\n")
    
    # Get completed jobs from source
    logger.info("📋 Fetching completed jobs from source...")
    jobs = get_completed_jobs(source_db_path)
    
    if not jobs:
        logger.error("❌ No completed jobs found in source database")
        sys.exit(1)
    
    # Display jobs
    display_jobs(jobs, "Source")
    
    # Select job
    if args.job_id:
        selected_job = next((j for j in jobs if j["id"] == args.job_id), None)
        if not selected_job:
            logger.error(f"❌ Job {args.job_id} not found in completed jobs")
            sys.exit(1)
        job_id = args.job_id
    else:
        # Interactive selection
        while True:
            try:
                choice = input(f"Select job number (1-{len(jobs)}) or 'q' to quit: ").strip()
                
                if choice.lower() == 'q':
                    logger.info("Operation cancelled by user")
                    sys.exit(0)
                
                job_num = int(choice)
                if 1 <= job_num <= len(jobs):
                    selected_job = jobs[job_num - 1]
                    job_id = selected_job["id"]
                    break
                else:
                    print(f"❌ Please enter a number between 1 and {len(jobs)}")
            except ValueError:
                print("❌ Please enter a valid number or 'q' to quit")
    
    # Get job details and related models
    logger.info(f"📊 Fetching details for job {job_id}...")
    job_details = get_job_details(source_db_path, job_id)
    if not job_details:
        logger.error(f"❌ Job {job_id} not found")
        sys.exit(1)
    
    models = get_embedding_models_for_job(source_db_path, job_id)
    
    # Display details
    display_job_details(selected_job, models)
    
    # Confirm
    if not args.job_id:
        confirm = input("Copy this job and related models to destination? (y/n): ").strip().lower()
        if confirm != 'y':
            logger.info("Operation cancelled by user")
            sys.exit(0)
    
    # Copy job and models
    try:
        success = copy_job_and_models(
            source_path=source_db_path,
            dest_path=dest_db_path,
            job_id=job_id,
            create_backup=not args.no_backup,
        )
        
        if success:
            logger.info("✅ Operation completed successfully!")
        else:
            logger.error("❌ Operation failed")
            sys.exit(1)
    except Exception as exc:
        logger.error(f"❌ Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

