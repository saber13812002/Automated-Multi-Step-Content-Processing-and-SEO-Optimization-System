#!/usr/bin/env python3
"""
Script to list all OpenAI embeddings in ChromaDB.

This script connects to ChromaDB and lists all collections that were created
using OpenAI embeddings, showing their details including model, document count,
and job information.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings

# Add parent directory to path to import web_service modules
sys.path.insert(0, str(Path(__file__).parent))
try:
    from web_service.database import (
        get_db_connection,
        get_embedding_models,
        get_export_jobs,
    )
    from web_service.config import Settings as AppSettings, get_settings
except ImportError:
    print("⚠️  Warning: Could not import web_service modules. Some features may be limited.")
    get_db_connection = None
    get_embedding_models = None
    get_export_jobs = None


def create_chroma_client(host: Optional[str] = None, port: Optional[int] = None, 
                         persist_directory: Optional[str] = None, api_key: Optional[str] = None,
                         ssl: bool = False) -> chromadb.Client:
    """Create ChromaDB client."""
    telemetry = os.getenv("CHROMA_ANONYMIZED_TELEMETRY", "False")
    settings = Settings(anonymized_telemetry=telemetry.lower() in ("true", "1", "yes"))
    
    if persist_directory:
        persist_path = Path(persist_directory)
        persist_path.mkdir(parents=True, exist_ok=True)
        return chromadb.PersistentClient(path=str(persist_path), settings=settings)
    
    # Use provided host/port or environment variables
    final_host = host or os.getenv("CHROMA_HOST", "localhost")
    final_port = port or int(os.getenv("CHROMA_PORT", "8000"))
    final_ssl = ssl or os.getenv("CHROMA_SSL", "false").lower() in ("1", "true", "yes")
    final_api_key = api_key or os.getenv("CHROMA_API_KEY", "")
    
    headers = {"Authorization": final_api_key} if final_api_key else None
    
    return chromadb.HttpClient(
        host=final_host,
        port=final_port,
        ssl=final_ssl,
        headers=headers,
        settings=settings,
    )


def get_collection_info(client: chromadb.Client, collection_name: str) -> Optional[Dict[str, Any]]:
    """Get information about a collection."""
    try:
        collection = client.get_collection(collection_name)
        count = collection.count()
        metadata = collection.metadata or {}
        
        return {
            "name": collection_name,
            "count": count,
            "metadata": metadata,
        }
    except Exception as e:
        print(f"⚠️  Error getting collection '{collection_name}': {e}", file=sys.stderr)
        return None


def get_openai_collections_from_db() -> List[Dict[str, Any]]:
    """Get OpenAI collections from database (export_jobs and embedding_models)."""
    if not get_embedding_models:
        return []
    
    try:
        models = get_embedding_models(limit=100, active_only=False, ensure_sync=False)
        openai_models = [
            model for model in models
            if model.get("embedding_provider", "").lower() == "openai"
        ]
        return openai_models
    except Exception as e:
        print(f"⚠️  Error getting models from database: {e}", file=sys.stderr)
        return []


def get_openai_jobs_from_db() -> List[Dict[str, Any]]:
    """Get OpenAI export jobs from database."""
    if not get_export_jobs:
        return []
    
    try:
        jobs = get_export_jobs(limit=1000)
        openai_jobs = [
            job for job in jobs
            if job.get("embedding_provider", "").lower() == "openai"
        ]
        return openai_jobs
    except Exception as e:
        print(f"⚠️  Error getting jobs from database: {e}", file=sys.stderr)
        return []


def list_all_collections(client: chromadb.Client) -> List[str]:
    """List all collection names in ChromaDB."""
    try:
        collections = client.list_collections()
        return [col.name for col in collections]
    except Exception as e:
        print(f"❌ Error listing collections: {e}", file=sys.stderr)
        return []


def main():
    parser = argparse.ArgumentParser(
        description="List all OpenAI embeddings in ChromaDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List OpenAI embeddings using default settings
  python list_openai_embeddings.py

  # List with custom ChromaDB connection
  python list_openai_embeddings.py --host 192.168.1.68 --port 8000

  # List with database information
  python list_openai_embeddings.py --include-db-info

  # List only active models
  python list_openai_embeddings.py --active-only
        """
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="ChromaDB host (default: from CHROMA_HOST env or localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="ChromaDB port (default: from CHROMA_PORT env or 8000)",
    )
    parser.add_argument(
        "--persist-directory",
        type=str,
        default=None,
        help="Use persistent ChromaDB client with this directory",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="ChromaDB API key (default: from CHROMA_API_KEY env)",
    )
    parser.add_argument(
        "--ssl",
        action="store_true",
        help="Use HTTPS for ChromaDB connection",
    )
    parser.add_argument(
        "--include-db-info",
        action="store_true",
        help="Include information from database (jobs, models)",
    )
    parser.add_argument(
        "--active-only",
        action="store_true",
        help="Show only active embedding models",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed information for each collection",
    )
    
    args = parser.parse_args()
    
    print("🔍 Connecting to ChromaDB...")
    try:
        client = create_chroma_client(
            host=args.host,
            port=args.port,
            persist_directory=args.persist_directory,
            api_key=args.api_key,
            ssl=args.ssl,
        )
        print("✅ Connected to ChromaDB\n")
    except Exception as e:
        print(f"❌ Failed to connect to ChromaDB: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Get collections from ChromaDB
    print("📋 Listing all collections in ChromaDB...")
    all_collections = list_all_collections(client)
    print(f"   Found {len(all_collections)} collection(s)\n")
    
    # Get OpenAI collections from database
    openai_collections_info = []
    if args.include_db_info:
        print("📊 Getting OpenAI embedding information from database...")
        openai_models = get_openai_collections_from_db()
        openai_jobs = get_openai_jobs_from_db()
        
        # Create a mapping of collection names to model/job info
        collection_to_model = {model["collection"]: model for model in openai_models}
        collection_to_jobs = {}
        for job in openai_jobs:
            collection_name = job.get("collection", "")
            if collection_name not in collection_to_jobs:
                collection_to_jobs[collection_name] = []
            collection_to_jobs[collection_name].append(job)
        
        # Filter by active_only if requested
        if args.active_only:
            openai_models = [m for m in openai_models if m.get("is_active", False)]
        
        print(f"   Found {len(openai_models)} OpenAI model(s) in database\n")
        
        # Get collection info for each OpenAI model
        for model in openai_models:
            collection_name = model["collection"]
            if collection_name in all_collections:
                info = get_collection_info(client, collection_name)
                if info:
                    info["model_info"] = model
                    info["jobs"] = collection_to_jobs.get(collection_name, [])
                    openai_collections_info.append(info)
    else:
        # Just check all collections and try to identify OpenAI ones
        # (by checking if they have OpenAI-related metadata or names)
        print("🔍 Identifying OpenAI collections...")
        for collection_name in all_collections:
            # Check if collection name suggests OpenAI
            if "openai" in collection_name.lower():
                info = get_collection_info(client, collection_name)
                if info:
                    openai_collections_info.append(info)
    
    # Display results
    if not openai_collections_info:
        print("❌ No OpenAI embeddings found.")
        if not args.include_db_info:
            print("💡 Tip: Use --include-db-info to get information from database.")
        sys.exit(0)
    
    print("=" * 80)
    print(f"📊 Found {len(openai_collections_info)} OpenAI Embedding Collection(s)\n")
    print("=" * 80)
    
    for idx, info in enumerate(openai_collections_info, 1):
        print(f"\n[{idx}] Collection: {info['name']}")
        print(f"    Documents: {info['count']:,}")
        
        if "model_info" in info:
            model = info["model_info"]
            print(f"    Provider: {model.get('embedding_provider', 'N/A')}")
            print(f"    Model: {model.get('embedding_model', 'N/A')}")
            print(f"    Status: {'🟢 Active' if model.get('is_active') else '🔴 Inactive'}")
            print(f"    Color: {model.get('color', 'N/A')}")
            
            if model.get("completed_at"):
                print(f"    Last Completed: {model['completed_at']}")
            if model.get("total_documents_in_collection"):
                print(f"    Total Documents (from job): {model['total_documents_in_collection']:,}")
        
        if "jobs" in info and info["jobs"]:
            latest_job = info["jobs"][0]  # Jobs are usually sorted by date
            print(f"    Latest Job ID: {latest_job.get('id', 'N/A')}")
            print(f"    Job Status: {latest_job.get('status', 'N/A')}")
            if latest_job.get("started_at"):
                print(f"    Job Started: {latest_job['started_at']}")
        
        if args.detailed and info.get("metadata"):
            print(f"    Metadata: {info['metadata']}")
        
        print("-" * 80)
    
    # Summary
    total_documents = sum(info["count"] for info in openai_collections_info)
    active_count = sum(1 for info in openai_collections_info 
                      if info.get("model_info", {}).get("is_active", False))
    
    print(f"\n📈 Summary:")
    print(f"   Total Collections: {len(openai_collections_info)}")
    print(f"   Active Collections: {active_count}")
    print(f"   Total Documents: {total_documents:,}")
    print()


if __name__ == "__main__":
    main()

