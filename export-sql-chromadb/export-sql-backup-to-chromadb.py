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

try:
    from transformers import AutoTokenizer, AutoModel
    import torch
    import numpy as np
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    AutoTokenizer = None  # type: ignore
    AutoModel = None  # type: ignore
    torch = None  # type: ignore
    np = None  # type: ignore

try:
    from google import genai
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False
    genai = None  # type: ignore


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


@dataclass
class ParagraphPayload:
    text: str
    line_count: int
    source_indices: List[int]
    is_title: bool = False


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


def looks_like_title(paragraph: str) -> bool:
    if not paragraph:
        return False
    stripped = paragraph.strip()
    if not stripped:
        return False
    lowered = stripped.lower()
    if any(tag in lowered for tag in ("<h1", "<h2", "<h3", "<h4", "<h5", "<h6")):
        return True
    if stripped.endswith((":", "؟", "!", "؛")):
        return True
    title_markers = ("عنوان", "فصل", "بخش", "درس", "chapter", "section")
    if any(marker in stripped for marker in title_markers):
        return True
    return len(stripped) <= 80 and stripped.isupper()


def extract_paragraph_payloads(text: str) -> List[ParagraphPayload]:
    if not text:
        return []
    raw_paragraphs = re.split(r"\n\s*\n+", text)
    payloads: List[ParagraphPayload] = []
    for idx, raw in enumerate(raw_paragraphs):
        cleaned = re.sub(r"\s+", " ", raw).strip()
        if not cleaned:
            continue
        non_empty_lines = [ln for ln in raw.split("\n") if ln.strip()]
        line_count = len(non_empty_lines) if non_empty_lines else 1
        payloads.append(
            ParagraphPayload(
                text=cleaned,
                line_count=line_count,
                source_indices=[idx],
                is_title=looks_like_title(raw),
            )
        )
    return payloads


def _merge_payloads(payloads: List[ParagraphPayload]) -> ParagraphPayload:
    text = "\n".join(p.text for p in payloads).strip()
    line_count = sum(p.line_count for p in payloads)
    indices: List[int] = []
    is_title = False
    for payload in payloads:
        indices.extend(payload.source_indices)
        is_title = is_title or payload.is_title
    return ParagraphPayload(
        text=text,
        line_count=line_count if line_count > 0 else len(payloads),
        source_indices=indices or [0],
        is_title=is_title,
    )


def prepare_paragraphs(text: str, min_lines: int) -> List[ParagraphPayload]:
    base_payloads = extract_paragraph_payloads(text)
    if min_lines <= 1:
        return base_payloads

    merged: List[ParagraphPayload] = []
    buffer: List[ParagraphPayload] = []
    buffered_lines = 0

    def flush_buffer():
        nonlocal buffer, buffered_lines
        if buffer:
            merged.append(_merge_payloads(buffer))
            buffer = []
            buffered_lines = 0

    for payload in base_payloads:
        if payload.is_title:
            flush_buffer()
            merged.append(payload)
            continue
        buffer.append(payload)
        buffered_lines += payload.line_count
        if buffered_lines >= min_lines:
            flush_buffer()

    flush_buffer()
    return merged


def segment_paragraph(
    paragraph: str,
    *,
    max_length: int,
    context_length: int,
) -> List[Tuple[str, Tuple[int, int]]]:
    """
    Split paragraph into segments of max_length characters.
    
    Returns list of (segment_text, (start, end)) tuples where:
    - segment_text: The actual segment text (paragraph[start:end]), exactly max_length chars
    - (start, end): Character positions in the original paragraph
    
    Note: context_length is stored in metadata but the actual stored text
    is the segment itself (max_length chars), not the context-extended version.
    """
    if len(paragraph) <= max_length:
        return [(paragraph, (0, len(paragraph)))]

    segments: List[Tuple[str, Tuple[int, int]]] = []
    # Calculate step size: move forward by (max_length - overlap)
    # Overlap is context_length on each side, so effective step is max_length - context_length
    step_size = max(1, max_length - context_length) if context_length > 0 else max_length
    
    start = 0
    while start < len(paragraph):
        end = min(start + max_length, len(paragraph))
        # Store the actual segment text (not context-extended)
        segment_text = paragraph[start:end]
        segments.append((segment_text, (start, end)))
        
        if end >= len(paragraph):
            break
        
        # Move to next segment with overlap
        start += step_size
    
    return segments


def clean_metadata_for_chroma(metadata: dict) -> dict:
    """Clean metadata to ensure all values are valid ChromaDB types (str, int, float, bool).
    
    ChromaDB only accepts str, int, float, bool, or None for metadata values.
    This function converts None to empty string and ensures all values are valid types.
    """
    cleaned = {}
    for key, value in metadata.items():
        if value is None:
            cleaned[key] = ""
        elif isinstance(value, (str, int, float, bool)):
            cleaned[key] = value
        elif isinstance(value, (list, dict)):
            # Convert lists/dicts to JSON string
            import json
            cleaned[key] = json.dumps(value, ensure_ascii=False)
        else:
            # Convert any other type to string
            cleaned[key] = str(value)
    return cleaned


def build_segments(
    record: BookPageRecord,
    *,
    max_length: int,
    context_length: int,
    min_paragraph_lines: int = 1,
    title_weight: float = 1.0,
    include_page_level: bool = False,
) -> List[Segment]:
    """
    Build Segment objects from a `book_pages` row.

    Current behaviour (2025-11) is optimised for Persian/Arabic sources:
      * `html_to_text` keeps intentional line breaks so we can derive
        paragraph lengths based on literal `\\n` counts later in the pipeline.
      * `normalize_paragraphs` collapses multiple blank lines but preserves
        inline spacing, which is important for short one-line duaa / poem
        fragments that appear frequently in the corpus.
      * Paragraphs are split strictly by `max_length` (characters) with
        symmetric `context_length` overlap; no sentence-boundary adjustment
        exists yet. The upcoming chunking improvements will hook in here.

    Any change to this logic should be reflected in `dataset_stats.py`
    so telemetry stays in sync with the exporter.
    """
    text = html_to_text(record.page_text_html)
    paragraphs = prepare_paragraphs(text, min_paragraph_lines)
    segments: List[Segment] = []

    for para_index, payload in enumerate(paragraphs):
        chunked = segment_paragraph(
            payload.text,
            max_length=max_length,
            context_length=context_length,
        )
        # Store full paragraph text if it's not too large (for context retrieval)
        paragraph_full_text = payload.text if len(payload.text) < 10000 else ""  # Max 10KB
        
        # Store full paragraph text if it's not too large (for context retrieval)
        paragraph_full_text = payload.text if len(payload.text) < 10000 else ""  # Max 10KB
        
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
                "paragraph_line_count": payload.line_count,
                "paragraph_is_title": payload.is_title,
                "paragraph_sources": ",".join(map(str, payload.source_indices)) if payload.source_indices else "",
                "importance": title_weight if payload.is_title else 1.0,
                "source_link": record.link,
                "record_id": record.id,
                "has_error": bool(record.error),
                "error": record.error or "",
            }
            # Add full paragraph text if available and not too large
            if paragraph_full_text:
                metadata["paragraph_full_text"] = paragraph_full_text
            # Add full paragraph text if available and not too large
            if paragraph_full_text:
                metadata["paragraph_full_text"] = paragraph_full_text
            # Clean metadata to ensure all values are valid ChromaDB types
            cleaned_metadata = clean_metadata_for_chroma(metadata)
            segments.append(
                Segment(
                    document_id=doc_id,
                    text=segment_text,
                    metadata=cleaned_metadata,
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
            "paragraph_line_count": text.count("\n") + 1,
            "paragraph_is_title": False,
            "paragraph_sources": "0",
            "importance": 1.0,
            "source_link": record.link,
            "record_id": record.id,
            "has_error": bool(record.error),
            "error": record.error or "",
        }
        # Clean metadata to ensure all values are valid ChromaDB types
        cleaned_metadata = clean_metadata_for_chroma(metadata)
        segments.append(Segment(document_id=fallback_id, text=text, metadata=cleaned_metadata))

    if include_page_level and text:
        page_doc_id = f"{record.book_id}-{record.page_id}-page-{uuid.uuid4().hex[:8]}"
        page_metadata = {
            "book_id": record.book_id,
            "book_title": record.book_title,
            "section_id": record.section_id,
            "section_title": record.section_title,
            "page_id": record.page_id,
            "paragraph_index": -1,  # Use -1 instead of None for page-level documents
            "segment_index": -1,
            "segment_start": 0,
            "segment_end": len(text),
            "segment_length": len(text),
            "page_level": True,
            "importance": 1.0,
            "source_link": record.link,
            "record_id": record.id,
            "has_error": bool(record.error),
            "error": record.error or "",
        }
        # Store full page text reference (hash for large pages)
        if len(text) < 50000:  # Store directly if < 50KB
            page_metadata["page_full_text"] = text
        else:
            # For large pages, store a hash that can be used to retrieve from SQL later
            import hashlib
            page_metadata["page_full_text_hash"] = hashlib.sha256(text.encode('utf-8')).hexdigest()
        # Clean metadata to ensure all values are valid ChromaDB types
        cleaned_page_metadata = clean_metadata_for_chroma(page_metadata)
        segments.append(Segment(document_id=page_doc_id, text=text, metadata=cleaned_page_metadata))

    return segments


class HuggingFaceEmbedder:
    """Custom embedding function for HuggingFace models like ParsBERT, AraBERT, etc."""
    
    def __init__(self, model_name: str, device: Optional[str] = None):
        if not TRANSFORMERS_AVAILABLE:
            raise RuntimeError(
                "transformers library is required for HuggingFace embeddings. "
                "Install it with: pip install transformers torch"
            )
        
        self.model_name = model_name
        # Handle empty string as None, then auto-detect device if None
        if device and device.strip():
            self.device = device
        else:
            self.device = "cuda" if torch is not None and torch.cuda.is_available() else "cpu"
        
        print(f"🔄 در حال بارگذاری مدل HuggingFace: {model_name}...", flush=True)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()  # Set to evaluation mode
        print(f"✅ مدل بارگذاری شد (device: {self.device})", flush=True)
    
    def __call__(self, texts: Sequence[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        if not texts:
            return []
        
        # Tokenize texts
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,  # Most BERT models have max_length of 512
            return_tensors="pt"
        )
        
        # Move to device
        encoded = {k: v.to(self.device) for k, v in encoded.items()}
        
        # Generate embeddings
        with torch.no_grad():
            outputs = self.model(**encoded)
            # Use mean pooling of the last hidden state
            # Shape: (batch_size, seq_len, hidden_size)
            embeddings = outputs.last_hidden_state
            # Mean pooling: average over sequence length dimension
            attention_mask = encoded["attention_mask"]
            # Expand attention mask to match embedding dimensions
            mask_expanded = attention_mask.unsqueeze(-1).expand(embeddings.size()).float()
            # Sum embeddings and divide by sum of mask (mean pooling)
            sum_embeddings = torch.sum(embeddings * mask_expanded, dim=1)
            sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
            embeddings = sum_embeddings / sum_mask
        
        # Convert to list of lists
        embeddings_list = embeddings.cpu().numpy().tolist()
        return embeddings_list


class GeminiEmbedder:
    """Custom embedding function for Gemini models like gemini-embedding-001, gemini-2.5-flash, etc."""
    
    def __init__(self, model_name: str, api_key: str):
        if not GOOGLE_GENAI_AVAILABLE:
            raise RuntimeError(
                "google-genai library is required for Gemini embeddings. "
                "Install it with: pip install google-genai"
            )
        
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required for Gemini embeddings.")
        
        self.model_name = model_name
        self.api_key = api_key
        
        print(f"🔄 در حال اتصال به Gemini API: {model_name}...", flush=True)
        try:
            self.client = genai.Client(api_key=api_key)
            print(f"✅ اتصال به Gemini API برقرار شد", flush=True)
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize Gemini client: {exc}") from exc
    
    def __call__(self, texts: Sequence[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        if not texts:
            return []
        
        try:
            # Use embed_content method from Gemini API
            response = self.client.models.embed_content(
                model=self.model_name,
                contents=list(texts)
            )
            
            # Extract embeddings from response
            # Response structure may vary: response.embeddings is a list of embedding objects
            # Each embedding object may have 'values', 'embedding', or be a list/dict directly
            embeddings_list = []
            if hasattr(response, 'embeddings'):
                embeddings = response.embeddings
            elif isinstance(response, list):
                embeddings = response
            elif isinstance(response, dict) and 'embeddings' in response:
                embeddings = response['embeddings']
            else:
                embeddings = [response]
            
            for embedding in embeddings:
                if isinstance(embedding, list):
                    embeddings_list.append(embedding)
                elif isinstance(embedding, dict):
                    # Try common keys
                    if 'values' in embedding:
                        embeddings_list.append(embedding['values'])
                    elif 'embedding' in embedding:
                        embeddings_list.append(embedding['embedding'])
                    else:
                        # Use first list-like value found
                        for val in embedding.values():
                            if isinstance(val, list):
                                embeddings_list.append(val)
                                break
                elif hasattr(embedding, 'values'):
                    embeddings_list.append(embedding.values)
                elif hasattr(embedding, 'embedding'):
                    embeddings_list.append(embedding.embedding)
                else:
                    # Last resort: try to convert to list
                    try:
                        embeddings_list.append(list(embedding))
                    except (TypeError, ValueError):
                        raise RuntimeError(f"Unable to extract embedding from response: {type(embedding)}")
            
            if len(embeddings_list) != len(texts):
                raise RuntimeError(
                    f"Expected {len(texts)} embeddings, but got {len(embeddings_list)}"
                )
            
            return embeddings_list
        except Exception as exc:
            raise RuntimeError(f"Failed to generate Gemini embeddings: {exc}") from exc


class EmbeddingProvider:
    def __init__(self, provider: str, model: str, api_key: Optional[str], device: Optional[str] = None, gemini_api_key: Optional[str] = None) -> None:
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.device = device
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
        elif provider == "huggingface":
            self.embedding_function = HuggingFaceEmbedder(model_name=model, device=device)
        elif provider == "gemini":
            self.embedding_function = GeminiEmbedder(model_name=model, api_key=gemini_api_key or "")
        elif provider == "none":
            self.embedding_function = None
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}. Supported: openai, huggingface, gemini, none")

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
        # Try to get existing collection
        existing_collection = client.get_collection(name)
        # If we get here, collection exists and reset=False
        # Append timestamp to avoid conflict
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = f"{name}_{timestamp}"
        print(f"⚠️  Warning: Collection '{name}' already exists. Using '{new_name}' instead.", flush=True)
        try:
            return client.get_collection(new_name)
        except NotFoundError:
            return client.create_collection(name=new_name, metadata=metadata)
    except NotFoundError:
        # Collection doesn't exist, create it with original name
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
            "min_paragraph_lines": args.min_paragraph_lines,
            "title_weight": args.title_weight,
            "embedding_provider": args.embedding_provider,
            "embedding_model": args.embedding_model,
        },
        reset=args.reset,
    )

    # Handle device: convert empty string to None
    device = getattr(args, 'device', None)
    if device and not device.strip():
        device = None
    
    # Get Gemini API key if provider is gemini
    gemini_api_key = getattr(args, 'gemini_api_key', None)
    if gemini_api_key and not gemini_api_key.strip():
        gemini_api_key = None
    
    embedding_provider = EmbeddingProvider(
        provider=args.embedding_provider,
        model=args.embedding_model,
        api_key=args.openai_api_key,
        device=device,
        gemini_api_key=gemini_api_key,
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
            min_paragraph_lines=args.min_paragraph_lines,
            title_weight=args.title_weight,
            include_page_level=not args.disable_page_level_docs,
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

        # Verify segment lengths (debug logging)
        if batch_number == 1:  # Log only first batch for debugging
            sample_lengths = [len(doc) for doc in documents[:5]]
            avg_length = sum(len(doc) for doc in documents) / len(documents) if documents else 0
            print(f"   📊 نمونه طول سگمنت‌ها: {sample_lengths} | میانگین: {avg_length:.1f} کاراکتر", flush=True)
        
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
        "--min-paragraph-lines",
        type=int,
        default=int(os.getenv("MIN_PARAGRAPH_LINES", "3")),
        help="Minimum number of lines before we stop merging short paragraphs.",
    )
    parser.add_argument(
        "--title-weight",
        type=float,
        default=float(os.getenv("TITLE_WEIGHT", "1.5")),
        help="Weight multiplier for title segments (stored in metadata).",
    )
    parser.add_argument(
        "--disable-page-level-docs",
        action="store_true",
        help="Disable adding a full-page document per record to Chroma.",
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
        choices=["openai", "huggingface", "gemini", "none"],
        default=os.getenv("EMBEDDING_PROVIDER", "openai"),
        help="Embedding backend to use for generating vectors. Options: openai, huggingface, gemini, none",
    )
    parser.add_argument(
        "--embedding-model",
        default=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        help=(
            "Embedding model identifier. "
            "For OpenAI: e.g., 'text-embedding-3-small', 'text-embedding-3-large'. "
            "For HuggingFace: e.g., 'HooshvareLab/bert-base-parsbert-uncased' (ParsBERT), "
            "'aubmindlab/bert-base-arabertv2' (AraBERT), or any other HuggingFace model. "
            "For Gemini: e.g., 'gemini-embedding-001', 'gemini-2.5-flash', or future Gemini 3 embedding models."
        ),
    )
    parser.add_argument(
        "--openai-api-key",
        default=os.getenv("OPENAI_API_KEY", ""),
        help="OpenAI API key. Overrides environment variable if provided. Required for OpenAI provider.",
    )
    parser.add_argument(
        "--gemini-api-key",
        default=os.getenv("GEMINI_API_KEY", ""),
        help="Gemini API key. Overrides environment variable if provided. Required for Gemini provider.",
    )
    parser.add_argument(
        "--device",
        choices=["cpu", "cuda"],
        default=os.getenv("EMBEDDING_DEVICE", ""),
        help=(
            "Device to use for HuggingFace models (cpu or cuda). "
            "If not specified, automatically uses CUDA if available, otherwise CPU."
        ),
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

