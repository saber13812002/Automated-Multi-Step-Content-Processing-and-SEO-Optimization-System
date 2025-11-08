import argparse
import os
from pathlib import Path
from typing import Optional, Sequence

import chromadb
from chromadb.config import Settings
from chromadb.errors import NotFoundError


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


def run_query(args: argparse.Namespace) -> None:
    client = create_client(args)

    try:
        collection = client.get_collection(args.collection)
    except NotFoundError:
        raise SystemExit(f"Collection '{args.collection}' not found. Run the exporter first.")

    results = collection.query(
        query_texts=[args.query],
        n_results=args.top_k,
        include=["documents", "metadatas", "distances"],
    )

    ids = results.get("ids", [[]])[0]
    if not ids:
        print("No results returned. Check that the collection contains documents.")
        return

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    print(f"Query: {args.query}")
    print(f"Top {len(ids)} results from collection '{args.collection}':")
    for idx, doc_id in enumerate(ids):
        metadata = metadatas[idx] if idx < len(metadatas) else {}
        distance = distances[idx] if idx < len(distances) else None
        document_preview = documents[idx][:200].replace("\n", " ")

        print("-" * 80)
        print(f"[{idx + 1}] ID: {doc_id}")
        if distance is not None:
            print(f"Distance: {distance:.4f}")
        print(f"Book: {metadata.get('book_title')} (#{metadata.get('book_id')})")
        print(
            f"Section: {metadata.get('section_title')} (#{metadata.get('section_id')}), "
            f"Page: {metadata.get('page_id')}, Paragraph: {metadata.get('paragraph_index')}, "
            f"Segment: {metadata.get('segment_index')}"
        )
        print(f"Link: {metadata.get('source_link')}")
        print(f"Preview: {document_preview}")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query ChromaDB collection to verify exported book segments.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--collection",
        default=os.getenv("CHROMA_COLLECTION", "book_pages"),
        help="Target ChromaDB collection.",
    )
    parser.add_argument(
        "--query",
        default=os.getenv("CHROMA_TEST_QUERY", "آموزش عقاید چیست"),
        help="Text query to search for.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=int(os.getenv("CHROMA_TEST_TOP_K", "5")),
        help="Number of results to return.",
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
    run_query(args)


if __name__ == "__main__":
    main()

