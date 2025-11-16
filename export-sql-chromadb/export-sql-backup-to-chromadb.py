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

# Import database functions for job tracking
try:
    # Add parent directory to path to import web_service modules
    sys.path.insert(0, str(Path(__file__).parent))
    from web_service.database import create_export_job, update_export_job, init_database
except ImportError:
    # If web_service is not available, job tracking will be disabled
    create_export_job = None
    update_export_job = None
    init_database = None

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
    
    The key insight: SQL strings come in as strings that may contain literal escape sequences.
    We need to handle them properly without breaking UTF-8 characters.
    """
    if value is None:
        return ""
    if value == "NULL":
        return ""
    
    # Check if string contains escape sequences (literal backslashes followed by special chars)
    has_escape_sequences = "\\n" in value or "\\r" in value or "\\t" in value or "\\\"" in value or "\\\\" in value or "\\u" in value
    
    if not has_escape_sequences:
        # No escape sequences, likely already decoded - just ensure it's valid UTF-8
        # If string contains Persian or other UTF-8 chars, it's already correct
        try:
            # Test if it's valid UTF-8 by encoding/decoding
            value.encode("utf-8").decode("utf-8")
            return value
        except (UnicodeEncodeError, UnicodeDecodeError):
            # If it's not valid UTF-8, it might be mojibake - try to fix
            # This handles double-encoded UTF-8 (common mojibake)
            try:
                # Try encoding as latin-1 and decoding as utf-8 (reverse mojibake)
                return value.encode("latin-1").decode("utf-8", errors="replace")
            except (UnicodeDecodeError, UnicodeEncodeError):
                return value
    
    # String contains escape sequences - need to decode them
    # We need to handle both ASCII escape sequences AND UTF-8 characters together
    try:
        import codecs
        # Use codecs.decode which can handle unicode_escape on strings with UTF-8 chars
        # This works by treating the string as a raw string literal representation
        # But we need to be careful: codecs.decode expects bytes for unicode_escape
        
        # Check if string is pure ASCII (can use standard method)
        if all(ord(c) < 128 for c in value):
            # Pure ASCII - safe to use standard decode
            decoded_str = value.encode("ascii").decode("unicode_escape")
            return decoded_str
        else:
            # String contains non-ASCII chars (like Persian) - need special handling
            # Replace escape sequences manually to preserve UTF-8
            import re
            
            # Replace common escape sequences first
            decoded = value
            decoded = decoded.replace("\\\\", "\x00BACKSLASH\x00")  # Temporary marker
            decoded = decoded.replace("\\n", "\n")
            decoded = decoded.replace("\\r", "\r")
            decoded = decoded.replace("\\t", "\t")
            decoded = decoded.replace('\\"', '"')
            decoded = decoded.replace("\\'", "'")
            decoded = decoded.replace("\x00BACKSLASH\x00", "\\")  # Restore actual backslashes
            
            # Handle \uXXXX sequences (Unicode escape sequences)
            def replace_unicode_escape(match):
                hex_str = match.group(1)
                try:
                    code_point = int(hex_str, 16)
                    return chr(code_point)
                except (ValueError, OverflowError):
                    return match.group(0)  # Return unchanged if invalid
            
            decoded = re.sub(r"\\u([0-9a-fA-F]{4})", replace_unicode_escape, decoded)
            
            # Handle \xXX sequences (hex escape sequences)
            def replace_hex_escape(match):
                hex_str = match.group(1)
                try:
                    byte_val = int(hex_str, 16)
                    return chr(byte_val)
                except (ValueError, OverflowError):
                    return match.group(0)
            
            decoded = re.sub(r"\\x([0-9a-fA-F]{2})", replace_hex_escape, decoded)
            
            # Ensure result is valid UTF-8
            try:
                decoded.encode("utf-8").decode("utf-8")
                return decoded
            except (UnicodeEncodeError, UnicodeDecodeError):
                # If not valid UTF-8, try to fix mojibake
                try:
                    return decoded.encode("latin-1").decode("utf-8", errors="replace")
                except (UnicodeDecodeError, UnicodeEncodeError):
                    return decoded
                    
    except Exception as exc:
        # Last resort: return value as-is
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

    # Expected 9 columns, but handle cases with more columns by taking only first 9
    expected_fields = 9
    if len(fields) < expected_fields:
        raise ValueError(
            f"Not enough columns ({len(fields)} < {expected_fields}) in line: {line[:120]}..."
        )
    
    # Take only first 9 columns if there are more
    if len(fields) > expected_fields:
        import sys
        print(
            f"⚠️  Warning: Line has {len(fields)} columns, using first {expected_fields} columns.",
            file=sys.stderr,
        )
        fields = fields[:expected_fields]

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


def count_records_and_books(sql_path: Path) -> Tuple[int, int]:
    """Count total records and unique books in SQL file."""
    print("📊 در حال شمارش رکوردها و کتاب‌ها...", flush=True)
    total_records = 0
    unique_books = set()
    
    for record in iter_book_pages(sql_path):
        total_records += 1
        unique_books.add(record.book_id)
    
    return total_records, len(unique_books)


def export_to_chroma(args: argparse.Namespace, job_id: Optional[int] = None) -> None:
    sql_path = Path(args.sql_path)
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")

    # Count total records and books first
    total_records_count, total_books_count = count_records_and_books(sql_path)
    print(f"📚 آمار کل:")
    print(f"   • کل رکوردها: {total_records_count:,}")
    print(f"   • کل کتاب‌ها: {total_books_count:,}")
    print(f"   • مدل امبدینگ: {args.embedding_provider}/{args.embedding_model}")
    print(f"   • اندازه بچ: {args.batch_size}")
    print("-" * 60, flush=True)

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

    processed_records = 0
    processed_books = set()
    total_segments = 0
    batch_number = 0

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
        batch_number += 1
        
        ids = [segment.document_id for segment in batch]
        documents = [segment.text for segment in batch]
        metadatas = [segment.metadata for segment in batch]

        # Track processed records and books
        for metadata in metadatas:
            record_id = metadata.get("record_id")
            if record_id:
                processed_records = max(processed_records, record_id)
            book_id = metadata.get("book_id")
            if book_id:
                processed_books.add(book_id)

        # Generate embeddings
        print(f"🔄 بچ #{batch_number}: در حال تولید امبدینگ برای {len(batch)} قطعه...", end=" ", flush=True)
        embeddings = embedding_provider.embed(documents)
        print("✅", flush=True)

        # Add to collection
        print(f"   💾 در حال ذخیره در ChromaDB...", end=" ", flush=True)
        add_kwargs = {"ids": ids, "documents": documents, "metadatas": metadatas}
        if embeddings is not None:
            add_kwargs["embeddings"] = embeddings

        collection.add(**add_kwargs)
        print("✅", flush=True)

        total_segments += len(batch)
        
        # Calculate progress
        remaining_records = total_records_count - processed_records
        processed_books_count = len(processed_books)
        remaining_books = total_books_count - processed_books_count
        progress_percent = (processed_records / total_records_count * 100) if total_records_count > 0 else 0
        
        print(f"   📊 پیشرفت:")
        print(f"      • رکوردها: {processed_records:,} / {total_records_count:,} ({progress_percent:.1f}%) - باقی‌مانده: {remaining_records:,}")
        print(f"      • کتاب‌ها: {processed_books_count} / {total_books_count} - باقی‌مانده: {remaining_books}")
        print(f"      • کل قطعات: {total_segments:,}")
        print("-" * 60, flush=True)

    # Get total documents in collection
    total_documents_in_collection = None
    try:
        total_documents_in_collection = collection.count()
    except Exception as exc:
        print(f"⚠️  Warning: Failed to get collection count: {exc}", file=sys.stderr)

    print(f"\n✅ ✅ ✅ Export completed successfully!")
    print(f"   • کل قطعات اضافه شده: {total_segments:,}")
    print(f"   • کل رکوردهای پردازش شده: {processed_records:,}")
    print(f"   • کل کتاب‌های پردازش شده: {len(processed_books)}")
    if total_documents_in_collection is not None:
        print(f"   • کل مستندات در کالکشن: {total_documents_in_collection:,}")
    print(f"   • کالکشن: {args.collection}", flush=True)

    # Update job status to completed
    if job_id is not None and update_export_job is not None:
        try:
            update_export_job(
                job_id,
                status="completed",
                total_records=processed_records,
                total_books=len(processed_books),
                total_segments=total_segments,
                total_documents_in_collection=total_documents_in_collection,
            )
            print(f"📝 Job #%d به‌روزرسانی شد: completed" % job_id, flush=True)
        except Exception as exc:
            print(f"⚠️  Warning: Failed to update job status: {exc}", file=sys.stderr)


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
    job_id = None
    
    # Initialize database and create job tracking record
    if init_database is not None:
        try:
            init_database()
            if create_export_job is not None:
                job_id = create_export_job(args)
                print(f"📝 Job #%d ثبت شد" % job_id, flush=True)
        except Exception as exc:
            print(f"⚠️  Warning: Failed to initialize job tracking: {exc}", file=sys.stderr)
            job_id = None
    
    try:
        export_to_chroma(args, job_id=job_id)
    except Exception as exc:
        # Update job status to failed
        if job_id is not None and update_export_job is not None:
            try:
                update_export_job(job_id, status="failed", error_message=str(exc))
                print(f"📝 Job #%d به‌روزرسانی شد: failed" % job_id, flush=True)
            except Exception:
                pass  # Don't fail if job update fails
        
        print(f"❌ Export failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

