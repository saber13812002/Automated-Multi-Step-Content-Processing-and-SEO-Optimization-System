#!/usr/bin/env python3
"""
اسکریپت انتقال Collection های ChromaDB از یک Instance به Instance دیگر

این اسکریپت collection ها را از source instance (مثلاً staging) به destination instance 
(مثلاً production) کپی می‌کند بدون اینکه روی داده‌های موجود تأثیر بگذارد.

استفاده:
    python copy_collections.py \
        --source-host localhost --source-port 8000 \
        --dest-host localhost --dest-port 8000 \
        --collection book_pages \
        --dest-collection book_pages_prod

یا برای کپی از PersistentClient به HttpClient:
    python copy_collections.py \
        --source-persist-dir /path/to/source/chroma \
        --dest-host localhost --dest-port 8000 \
        --collection book_pages
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.errors import NotFoundError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    persist_directory: Optional[str] = None,
    ssl: bool = False,
    api_key: Optional[str] = None,
) -> chromadb.Client:
    """Create ChromaDB client (HttpClient or PersistentClient)."""
    telemetry = ChromaSettings(anonymized_telemetry=False)
    
    if persist_directory:
        persist_path = Path(persist_directory)
        persist_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using PersistentClient at {persist_directory}")
        return chromadb.PersistentClient(path=str(persist_path), settings=telemetry)
    
    if not host or not port:
        raise ValueError("host and port are required when not using persist_directory")
    
    headers = {"Authorization": api_key} if api_key else None
    logger.info(f"Using HttpClient at {host}:{port} (ssl={ssl})")
    return chromadb.HttpClient(
        host=host,
        port=port,
        ssl=ssl,
        headers=headers,
        settings=telemetry,
    )


def copy_collection(
    source_client: chromadb.Client,
    dest_client: chromadb.Client,
    source_collection_name: str,
    dest_collection_name: str,
    batch_size: int = 1000,
) -> None:
    """
    Copy collection from source to destination.
    
    Args:
        source_client: ChromaDB client for source
        dest_client: ChromaDB client for destination
        source_collection_name: Name of source collection
        dest_collection_name: Name of destination collection (can be same or different)
        batch_size: Batch size for copying documents
    """
    logger.info(f"📋 Starting collection copy: '{source_collection_name}' -> '{dest_collection_name}'")
    
    # Get source collection
    try:
        source_collection = source_client.get_collection(source_collection_name)
        source_count = source_collection.count()
        logger.info(f"✅ Source collection '{source_collection_name}' found with {source_count} documents")
    except NotFoundError:
        logger.error(f"❌ Source collection '{source_collection_name}' not found")
        sys.exit(1)
    
    # Get or create destination collection
    try:
        dest_collection = dest_client.get_collection(dest_collection_name)
        dest_count = dest_collection.count()
        logger.warning(
            f"⚠️  Destination collection '{dest_collection_name}' already exists with {dest_count} documents. "
            f"Data will be added to existing collection (no overwrite)."
        )
    except NotFoundError:
        # Create new collection with same metadata as source
        source_metadata = source_collection.metadata if hasattr(source_collection, 'metadata') else {}
        dest_collection = dest_client.create_collection(
            name=dest_collection_name,
            metadata=source_metadata,
        )
        logger.info(f"✅ Created destination collection '{dest_collection_name}'")
    
    # Copy data in batches
    total_copied = 0
    offset = 0
    
    while offset < source_count:
        # Get batch from source
        batch_end = min(offset + batch_size, source_count)
        logger.info(f"📦 Copying batch {offset + 1} to {batch_end} of {source_count}...")
        
        try:
            # Fetch batch from source
            results = source_collection.get(
                limit=batch_size,
                offset=offset,
                include=["documents", "metadatas", "embeddings"] if hasattr(source_collection, 'get') else ["documents", "metadatas"],
            )
            
            if not results.get("ids") or len(results["ids"]) == 0:
                logger.warning(f"⚠️  No more documents to copy at offset {offset}")
                break
            
            ids = results["ids"]
            documents = results.get("documents", [])
            metadatas = results.get("metadatas", [])
            embeddings = results.get("embeddings")
            
            # Add to destination
            if embeddings:
                dest_collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=embeddings,
                )
            else:
                # If no embeddings, ChromaDB will generate them if collection has embedding function
                dest_collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                )
            
            batch_size_actual = len(ids)
            total_copied += batch_size_actual
            offset += batch_size_actual
            
            logger.info(f"✅ Copied {batch_size_actual} documents (total: {total_copied}/{source_count})")
            
        except Exception as exc:
            logger.error(f"❌ Error copying batch at offset {offset}: {exc}")
            raise
    
    # Verify final count
    final_count = dest_collection.count()
    logger.info(
        f"🎉 Collection copy completed! "
        f"Source: {source_count} documents, Destination: {final_count} documents"
    )
    
    if final_count != source_count:
        logger.warning(
            f"⚠️  Document count mismatch: source has {source_count}, destination has {final_count}"
        )


def list_collections(client: chromadb.Client) -> list[str]:
    """List all collections in client."""
    collections = client.list_collections()
    return [col.name for col in collections] if collections else []


def main():
    parser = argparse.ArgumentParser(
        description="Copy ChromaDB collections between instances",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    # Source configuration
    source_group = parser.add_argument_group("Source Configuration")
    source_group.add_argument(
        "--source-host",
        type=str,
        help="Source ChromaDB host (required if not using --source-persist-dir)",
    )
    source_group.add_argument(
        "--source-port",
        type=int,
        help="Source ChromaDB port (required if not using --source-persist-dir)",
    )
    source_group.add_argument(
        "--source-persist-dir",
        type=str,
        help="Source ChromaDB persist directory (alternative to host/port)",
    )
    source_group.add_argument(
        "--source-ssl",
        action="store_true",
        help="Use SSL for source connection",
    )
    source_group.add_argument(
        "--source-api-key",
        type=str,
        help="Source ChromaDB API key",
    )
    
    # Destination configuration
    dest_group = parser.add_argument_group("Destination Configuration")
    dest_group.add_argument(
        "--dest-host",
        type=str,
        help="Destination ChromaDB host (required if not using --dest-persist-dir)",
    )
    dest_group.add_argument(
        "--dest-port",
        type=int,
        help="Destination ChromaDB port (required if not using --dest-persist-dir)",
    )
    dest_group.add_argument(
        "--dest-persist-dir",
        type=str,
        help="Destination ChromaDB persist directory (alternative to host/port)",
    )
    dest_group.add_argument(
        "--dest-ssl",
        action="store_true",
        help="Use SSL for destination connection",
    )
    dest_group.add_argument(
        "--dest-api-key",
        type=str,
        help="Destination ChromaDB API key",
    )
    
    # Collection configuration
    parser.add_argument(
        "--collection",
        type=str,
        required=True,
        help="Source collection name",
    )
    parser.add_argument(
        "--dest-collection",
        type=str,
        help="Destination collection name (default: same as source)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for copying (default: 1000)",
    )
    
    # Utility options
    parser.add_argument(
        "--list-source",
        action="store_true",
        help="List all collections in source and exit",
    )
    parser.add_argument(
        "--list-dest",
        action="store_true",
        help="List all collections in destination and exit",
    )
    
    args = parser.parse_args()
    
    # Validate source configuration
    if not args.source_persist_dir and (not args.source_host or not args.source_port):
        parser.error("Either --source-persist-dir or both --source-host and --source-port are required")
    
    # Validate destination configuration
    if not args.dest_persist_dir and (not args.dest_host or not args.dest_port):
        parser.error("Either --dest-persist-dir or both --dest-host and --dest-port are required")
    
    # Create clients
    try:
        source_client = create_client(
            host=args.source_host,
            port=args.source_port,
            persist_directory=args.source_persist_dir,
            ssl=args.source_ssl,
            api_key=args.source_api_key,
        )
        
        dest_client = create_client(
            host=args.dest_host,
            port=args.dest_port,
            persist_directory=args.dest_persist_dir,
            ssl=args.dest_ssl,
            api_key=args.dest_api_key,
        )
    except Exception as exc:
        logger.error(f"❌ Failed to create clients: {exc}")
        sys.exit(1)
    
    # List collections if requested
    if args.list_source:
        collections = list_collections(source_client)
        logger.info(f"📋 Source collections: {', '.join(collections) if collections else '(none)'}")
        return
    
    if args.list_dest:
        collections = list_collections(dest_client)
        logger.info(f"📋 Destination collections: {', '.join(collections) if collections else '(none)'}")
        return
    
    # Determine destination collection name
    dest_collection_name = args.dest_collection or args.collection
    
    # Copy collection
    try:
        copy_collection(
            source_client=source_client,
            dest_client=dest_client,
            source_collection_name=args.collection,
            dest_collection_name=dest_collection_name,
            batch_size=args.batch_size,
        )
        logger.info("✅ Collection copy completed successfully!")
    except Exception as exc:
        logger.error(f"❌ Collection copy failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

