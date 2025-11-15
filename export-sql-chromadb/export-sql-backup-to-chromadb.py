import argparse
import csv
import os
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence, Tuple

import chromadb
from bs4 import BeautifulSoup
from chromadb.config import Settings

try:
    from chromadb.errors import InvalidCollectionException, NotFoundError
except ImportError:  # pragma: no cover - compatibility with newer Chroma releases
    from chromadb.errors import NotFoundError

    InvalidCollectionException = None  # type: ignore[assignment]

try:
    from chromadb.utils import embedding_functions
except ImportError:  # pragma: no cover - fallback when utils ref changes
    embedding_functions = None  # type: ignore


SQL_INSERT_PREFIX = "INSERT INTO `book_pages` VALUES "


@dataclass
class BookPageRecord:
    id: int
    book_id: int
    book_title: str
    section_id: int
    section_title: str
    page_id: int
    page_text_html: str
    link: str
    error: str


@dataclass
class Segment:
    document_id: str
    text: str
    metadata: dict


def decode_sql_string(value: Optional[str]) -> str:
    """Decode SQL string with proper UTF-8 handling for Persian text.
    
    SQL strings may contain escape sequences (like \\n, \\r, \\") that need to be decoded.
    This function ensures proper UTF-8 encoding for Persian/Farsi text.
    
    The original code used `bytes(value, "utf-8")` which is incorrect.
    We need to encode to bytes first, then decode with unicode_escape.
    """
    if value is None:
        return ""
    if value == "NULL":
        return ""
    
    # Normalize escaped sequences (e.g., \" \r\n \n \t)
    # The correct way: encode string to bytes, then decode with unicode_escape
    try:
        # Step 1: Encode string to bytes using latin-1 (preserves all byte values 0-255)
        # This is necessary because unicode_escape decoder expects bytes
        # latin-1 is a 1:1 mapping (each character maps to its byte value)
        encoded_bytes = value.encode("latin-1")
        
        # Step 2: Decode unicode escape sequences (e.g., \n becomes newline, \uXXXX becomes Unicode char)
        decoded_str = encoded_bytes.decode("unicode_escape")
        
        # Step 3: Ensure result is valid UTF-8
        # If decoded_str is already valid UTF-8, encode/decode will work fine
        # If it contains mojibake (double-encoded UTF-8), we try to fix it
        try:
            # Test if it's valid UTF-8 by trying to encode/decode
            test_bytes = decoded_str.encode("utf-8")
            test_str = test_bytes.decode("utf-8")
            return test_str
        except UnicodeEncodeError:
            # If encoding fails, it might contain invalid characters
            # Try to fix potential mojibake (double-encoding)
            try:
                # If string was double-encoded, encode as latin-1 then decode as utf-8
                fixed = decoded_str.encode("latin-1").decode("utf-8", errors="replace")
                return fixed
            except (UnicodeDecodeError, UnicodeEncodeError):
                # Last resort: return decoded string with error replacement
                return decoded_str.encode("utf-8", errors="replace").decode("utf-8")
        except UnicodeDecodeError:
            # If decoding fails, return with error replacement
            return decoded_str.encode("utf-8", errors="replace").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError, AttributeError, TypeError) as exc:
        # Fallback: return value as-is if all decoding methods fail
        # Log warning for debugging
        import sys
        print(f"Warning: Failed to decode SQL string: {exc}", file=sys.stderr)
        return value


def parse_insert_values(line: str) -> Optional[BookPageRecord]:
    if not line.startswith(SQL_INSERT_PREFIX):
        return None

    payload = line[len(SQL_INSERT_PREFIX) :].strip()
    if payload.endswith(";"):
        payload = payload[:-1]
    if payload.startswith("(") and payload.endswith(")"):
        payload = payload[1:-1]

    reader = csv.reader(
        [payload],
        delimiter=",",
        quotechar="'",
        escapechar="\\",
        doublequote=False,
        skipinitialspace=False,
    )
    try:
        fields = next(reader)
    except Exception as exc:  # pragma: no cover - defensive logging
        raise ValueError(f"Failed to parse INSERT line: {line[:120]}...") from exc

    if len(fields) != 9:
        raise ValueError(f"Unexpected number of columns ({len(fields)}) in line: {line[:120]}...")

    (
        id_val,
        book_id,
        book_title,
        section_id,
        section_title,
        page_id,
        page_text,
        link,
        error,
    ) = fields

    return BookPageRecord(
        id=int(id_val),
        book_id=int(book_id),
        book_title=decode_sql_string(book_title).strip(),
        section_id=int(section_id),
        section_title=decode_sql_string(section_title).strip(),
        page_id=int(page_id),
        page_text_html=decode_sql_string(page_text),
        link=decode_sql_string(link).strip(),
        error=decode_sql_string(error).strip(),
    )


def iter_book_pages(sql_path: Path) -> Iterator[BookPageRecord]:
    with sql_path.open("r", encoding="utf-8") as sql_file:
        for line in sql_file:
            line = line.strip()
            if not line or not line.startswith("INSERT INTO"):
                continue
            record = parse_insert_values(line)
            if record:
                yield record


def html_to_text(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n")
    text = text.replace("\r", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_paragraphs(text: str) -> List[str]:
    if not text:
        return []
    paragraphs = re.split(r"\n\s*\n+", text)
    cleaned = [re.sub(r"\s+", " ", p).strip() for p in paragraphs]
    return [p for p in cleaned if p]


def segment_paragraph(
    paragraph: str,
    *,
    max_length: int,
    context_length: int,
) -> List[Tuple[str, Tuple[int, int]]]:
    if len(paragraph) <= max_length:
        return [(paragraph, (0, len(paragraph)))]

    segments: List[Tuple[str, Tuple[int, int]]] = []
    for start in range(0, len(paragraph), max_length):
        end = min(start + max_length, len(paragraph))
        context_start = max(0, start - context_length)
        context_end = min(len(paragraph), end + context_length)
        context_chunk = paragraph[context_start:context_end]
        segments.append((context_chunk, (start, end)))
        if end == len(paragraph):
            break
    return segments


def build_segments(
    record: BookPageRecord,
    *,
    max_length: int,
    context_length: int,
) -> List[Segment]:
    text = html_to_text(record.page_text_html)
    paragraphs = normalize_paragraphs(text)
    segments: List[Segment] = []

    for para_index, paragraph in enumerate(paragraphs):
        chunked = segment_paragraph(
            paragraph,
            max_length=max_length,
            context_length=context_length,
        )
        for segment_index, (segment_text, (start, end)) in enumerate(chunked):
            doc_id = f"{record.book_id}-{record.page_id}-{para_index}-{segment_index}-{uuid.uuid4().hex[:8]}"
            metadata = {
                "book_id": record.book_id,
                "book_title": record.book_title,
                "section_id": record.section_id,
                "section_title": record.section_title,
                "page_id": record.page_id,
                "paragraph_index": para_index,
                "segment_index": segment_index,
                "segment_start": start,
                "segment_end": end,
                "segment_length": len(segment_text),
                "source_link": record.link,
                "record_id": record.id,
                "has_error": bool(record.error),
                "error": record.error,
            }
            segments.append(
                Segment(
                    document_id=doc_id,
                    text=segment_text,
                    metadata=metadata,
                )
            )

    if not segments and text:
        fallback_id = f"{record.book_id}-{record.page_id}-0-0-{uuid.uuid4().hex[:8]}"
        metadata = {
            "book_id": record.book_id,
            "book_title": record.book_title,
            "section_id": record.section_id,
            "section_title": record.section_title,
            "page_id": record.page_id,
            "paragraph_index": 0,
            "segment_index": 0,
            "segment_start": 0,
            "segment_end": len(text),
            "segment_length": len(text),
            "source_link": record.link,
            "record_id": record.id,
            "has_error": bool(record.error),
            "error": record.error,
        }
        segments.append(Segment(document_id=fallback_id, text=text, metadata=metadata))

    return segments


class EmbeddingProvider:
    def __init__(self, provider: str, model: str, api_key: Optional[str]) -> None:
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.embedding_function = None

        if provider == "openai":
            if embedding_functions is None:
                raise RuntimeError("chromadb.utils.embedding_functions is unavailable.")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY is required for OpenAI embeddings.")
            self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_key=api_key,
                model_name=model,
            )
        elif provider == "none":
            self.embedding_function = None
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")

    def embed(self, texts: Sequence[str]) -> Optional[Sequence[Sequence[float]]]:
        if not texts:
            return []
        if not self.embedding_function:
            return None
        return self.embedding_function(texts)


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


def get_collection(client, name: str, metadata: dict, reset: bool):
    if reset:
        ignored_exceptions = (NotFoundError,)
        if InvalidCollectionException is not None:
            ignored_exceptions = ignored_exceptions + (InvalidCollectionException,)
        try:
            client.delete_collection(name)
        except ignored_exceptions:
            pass

    try:
        return client.get_collection(name)
    except NotFoundError:
        return client.create_collection(name=name, metadata=metadata)


def batched(iterable: Iterable[Segment], batch_size: int) -> Iterator[List[Segment]]:
    batch: List[Segment] = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def export_to_chroma(args: argparse.Namespace) -> None:
    sql_path = Path(args.sql_path)
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")

    client = create_client(args)
    collection = get_collection(
        client,
        args.collection,
        metadata={
            "source": "book_pages_sql_export",
            "max_length": args.max_length,
            "context_length": args.context,
        },
        reset=args.reset,
    )

    embedding_provider = EmbeddingProvider(
        provider=args.embedding_provider,
        model=args.embedding_model,
        api_key=args.openai_api_key,
    )

    total_records = 0
    total_segments = 0

    segments_iter = (
        segment
        for record in iter_book_pages(sql_path)
        for segment in build_segments(
            record,
            max_length=args.max_length,
            context_length=args.context,
        )
    )

    for batch in batched(segments_iter, args.batch_size):
        ids = [segment.document_id for segment in batch]
        documents = [segment.text for segment in batch]
        metadatas = [segment.metadata for segment in batch]

        embeddings = embedding_provider.embed(documents)
        add_kwargs = {"ids": ids, "documents": documents, "metadatas": metadatas}
        if embeddings is not None:
            add_kwargs["embeddings"] = embeddings

        collection.add(**add_kwargs)

        total_segments += len(batch)
        total_records = max(total_records, metadatas[-1]["record_id"])

    print(f"✅ Export completed. Segments added: {total_segments}")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export book_pages SQL backup into ChromaDB with paragraph segments.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--sql-path",
        default=os.getenv("BOOK_PAGES_SQL", "book_pages.sql"),
        help="Path to the SQL dump file.",
    )
    parser.add_argument(
        "--collection",
        default=os.getenv("CHROMA_COLLECTION", "book_pages"),
        help="Target ChromaDB collection name.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=int(os.getenv("CHROMA_BATCH_SIZE", "48")),
        help="Number of segments to send per batch.",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=int(os.getenv("CHUNK_MAX_LENGTH", "200")),
        help="Maximum characters per primary segment.",
    )
    parser.add_argument(
        "--context",
        type=int,
        default=int(os.getenv("CHUNK_CONTEXT_LENGTH", "100")),
        help="Number of overlap characters around each segment.",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("CHROMA_HOST", "localhost"),
        help="ChromaDB host when using HTTP client.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("CHROMA_PORT", "8000")),
        help="ChromaDB port when using HTTP client.",
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
        help="Optional local directory for persistent ChromaDB client.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop the collection before uploading new documents.",
    )
    parser.add_argument(
        "--embedding-provider",
        choices=["openai", "none"],
        default=os.getenv("EMBEDDING_PROVIDER", "openai"),
        help="Embedding backend to use for generating vectors.",
    )
    parser.add_argument(
        "--embedding-model",
        default=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        help="Embedding model identifier.",
    )
    parser.add_argument(
        "--openai-api-key",
        default=os.getenv("OPENAI_API_KEY", ""),
        help="OpenAI API key. Overrides environment variable if provided.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    try:
        export_to_chroma(args)
    except Exception as exc:
        print(f"❌ Export failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

