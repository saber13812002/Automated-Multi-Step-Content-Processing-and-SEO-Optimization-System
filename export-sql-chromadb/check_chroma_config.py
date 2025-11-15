import argparse
import os
from pathlib import Path
from typing import Optional, Sequence

import chromadb
from chromadb.config import Settings
from chromadb.errors import NotFoundError
from dotenv import load_dotenv

# Load .env file for consistency with web_service
_PROJECT_ROOT = Path(__file__).resolve().parent
_DEFAULT_ENV_PATH = _PROJECT_ROOT / ".env"
if _DEFAULT_ENV_PATH.exists():
    load_dotenv(dotenv_path=_DEFAULT_ENV_PATH, override=False)


def create_client(args: argparse.Namespace):
    telemetry = os.getenv("CHROMA_ANONYMIZED_TELEMETRY", "False")
    settings = Settings(anonymized_telemetry=telemetry.lower() in ("true", "1", "yes"))

    if args.persist_directory:
        persist_path = Path(args.persist_directory)
        persist_path.mkdir(parents=True, exist_ok=True)
        return chromadb.PersistentClient(path=str(persist_path), settings=settings)

    return chromadb.HttpClient(
        host=args.host,
        port=args.port,
        ssl=args.ssl,
        headers={"Authorization": args.api_key} if args.api_key else None,
        settings=settings,
    )


def print_config(args: argparse.Namespace) -> None:
    """Print current configuration settings for comparison."""
    print("=" * 80)
    print("📋 Current Configuration Settings")
    print("=" * 80)
    print(f"ChromaDB Host:          {args.host}")
    print(f"ChromaDB Port:          {args.port}")
    print(f"ChromaDB SSL:           {args.ssl}")
    print(f"ChromaDB API Key:       {'***SET***' if args.api_key else '(not set)'}")
    print(f"ChromaDB Collection:    {args.collection}")
    print(f"ChromaDB Persist Dir:   {args.persist_directory or '(not set)'}")
    print(f"ChromaDB Telemetry:     {os.getenv('CHROMA_ANONYMIZED_TELEMETRY', 'False')}")
    print("=" * 80)
    print()


def check_collection(args: argparse.Namespace) -> None:
    """Check if ChromaDB connection works and collection exists."""
    print_config(args)
    
    print("🔍 Checking ChromaDB connection...")
    try:
        client = create_client(args)
        
        # Test heartbeat
        try:
            heartbeat = client.heartbeat()
            print(f"✅ ChromaDB connection successful (heartbeat: {heartbeat})")
        except Exception as exc:
            print(f"❌ ChromaDB server is not responding at {args.host}:{args.port}")
            print(f"   Error: {exc}")
            raise SystemExit(1)
        
        # List all collections
        print("\n📚 Available collections in ChromaDB:")
        try:
            collections = client.list_collections()
            if collections:
                for idx, col in enumerate(collections, 1):
                    try:
                        count = col.count() if hasattr(col, 'count') else None
                        if count is not None:
                            print(f"  [{idx}] {col.name} ({count} documents)")
                        else:
                            print(f"  [{idx}] {col.name}")
                    except Exception:
                        print(f"  [{idx}] {col.name} (could not get count)")
            else:
                print("  (no collections found)")
        except Exception as exc:
            print(f"  ⚠️  Could not list collections: {exc}")
        
        # Check target collection
        print(f"\n🎯 Checking target collection: '{args.collection}'")
        try:
            collection = client.get_collection(args.collection)
            count = collection.count()
            print(f"✅ Collection '{args.collection}' exists!")
            print(f"   Documents: {count}")
            
            # Show sample metadata if available
            if count > 0:
                try:
                    sample = collection.peek(limit=1)
                    if sample.get("metadatas") and sample["metadatas"]:
                        metadata_keys = list(sample["metadatas"][0].keys()) if sample["metadatas"][0] else []
                        if metadata_keys:
                            print(f"   Metadata fields: {', '.join(metadata_keys[:10])}")
                            if len(metadata_keys) > 10:
                                print(f"   ... and {len(metadata_keys) - 10} more")
                except Exception:
                    pass
        except NotFoundError:
            print(f"❌ Collection '{args.collection}' NOT FOUND!")
            print("\n💡 Possible solutions:")
            print(f"   1. Check the collection name in CHROMA_COLLECTION")
            print(f"   2. Run the exporter to create the collection:")
            print(f"      python export-sql-backup-to-chromadb.py --collection {args.collection}")
            raise SystemExit(1)
        
        print("\n" + "=" * 80)
        print("✅ Configuration check completed successfully!")
        print("=" * 80)
        
    except Exception as exc:
        print(f"\n❌ Error during configuration check: {exc}")
        raise SystemExit(1)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check ChromaDB configuration and collection existence.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--collection",
        default=os.getenv("CHROMA_COLLECTION", "book_pages"),
        help="Target ChromaDB collection.",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("CHROMA_HOST", "localhost"),
        help="ChromaDB host.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("CHROMA_PORT", "8000")),
        help="ChromaDB port.",
    )
    parser.add_argument(
        "--ssl",
        action="store_true",
        default=os.getenv("CHROMA_SSL", "false").lower() in ("1", "true", "yes"),
        help="Use HTTPS when connecting to ChromaDB.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("CHROMA_API_KEY", ""),
        help="API key header value for secured ChromaDB instances.",
    )
    parser.add_argument(
        "--persist-directory",
        default=os.getenv("CHROMA_PERSIST_DIR", ""),
        help="Optional local persist directory (for embedded Chroma).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    check_collection(args)


if __name__ == "__main__":
    main()

