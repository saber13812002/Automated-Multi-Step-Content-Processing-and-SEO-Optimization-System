<!-- e2e517dd-b4eb-498a-b011-22e162f5932d 57b1d556-8081-4305-acfc-85ebb55ab80d -->
# Plan: Enhanced Text Storage and Context Display System

## Overview

This plan enhances the embedding system to:

1. Store full paragraph and page text for later retrieval
2. Optimize character limits and segmentation parameters
3. Implement smart context retrieval in search results
4. Improve result display with full paragraph/page context

## Phase 0: Fix Short Text Display Issue (CRITICAL)

### 0.1 Analyze Current Segmentation Problem

**Files**: `export-sql-backup-to-chromadb.py`, `web_service/app.py`

- **Problem**: Results show ~100-200 chars instead of ~500 chars
- **Root Cause Analysis**:

1. Check `segment_paragraph()`: Does it create segments with proper `max_length`?
2. Check ChromaDB storage: Are full segments being stored?
3. Check retrieval: Are documents being truncated during query?
4. Check context_length: Is it reducing the actual segment size?

### 0.2 Fix Segmentation Algorithm

**File**: `export-sql-backup-to-chromadb.py`

- **Issue in line 375**: `context_chunk = paragraph[context_start:context_end]`
- This creates segments with context, but the actual segment (start:end) is only `max_length`
- The stored text should be the full segment, not just context_chunk
- **Fix**: Store the actual segment text (start:end) which is `max_length` chars
- **Verify**: Each segment should be exactly `max_length` characters (or less if paragraph is shorter)

### 0.3 Verify ChromaDB Storage

**File**: `export-sql-backup-to-chromadb.py`

- Ensure `segment_text` in line 439 is the full segment, not truncated
- Add logging to verify segment lengths during export
- Check if `segment_length` in metadata matches actual text length

### 0.4 Fix Search Result Retrieval

**File**: `web_service/app.py`

- Verify that `documents[index]` returns full segment text
- Check if ChromaDB is truncating results
- Ensure no post-processing truncates the text
- Add debug logging to show actual document lengths

### 0.5 Add Diagnostic Endpoint

**File**: `web_service/app.py`

- Add `GET /admin/debug/segment-info/{doc_id}` endpoint
- Returns: stored text length, metadata segment_length, actual retrieved length
- Helps diagnose where truncation occurs

## Phase 1: Enhanced Text Storage in Metadata

### 1.1 Store Full Paragraph Text

**File**: `export-sql-backup-to-chromadb.py`

- Modify `build_segments()` to store full paragraph text in metadata
- Add `paragraph_full_text` field to each segment's metadata
- Store as JSON string if needed (ChromaDB limitation)
- Size consideration: Store only if paragraph < 10KB to avoid metadata bloat

### 1.2 Store Full Page Text Reference

**File**: `export-sql-backup-to-chromadb.py`

- Add `page_full_text_hash` or `page_full_text_id` to metadata
- Option A: Store full page text in a separate "text_cache" collection
- Option B: Store page text hash and retrieve from original SQL on-demand
- Option C: Store in metadata as compressed/base64 if < 50KB

### 1.3 Add Text Storage Configuration

**File**: `export-sql-backup-to-chromadb.py`

- Add CLI args: `--store-full-paragraphs`, `--store-full-pages`, `--max-stored-text-size`
- Default: Store paragraphs < 5KB, pages < 20KB
- Add compression option for larger texts

## Phase 2: Optimize Character Limits and Segmentation

### 2.1 Dynamic Segmentation Based on Content

**File**: `export-sql-backup-to-chromadb.py`

- Implement sentence-aware segmentation (not just character-based)
- Respect paragraph boundaries better
- Add `--smart-segmentation` flag
- For Persian/Arabic: detect sentence endings (., !, ?, ؛, ؟)

### 2.2 Tune Default Parameters

**Files**: `export-sql-backup-to-chromadb.py`, `web_service/config.py`

- Update default `max_length` from 200 to 500 (already done in docs)
- Update default `batch_size` from 48 to 64 (already done in docs)
- Add `--adaptive-context` that adjusts context_length based on paragraph size
- Context should be 10-20% of max_length, not fixed 100

### 2.3 Add Paragraph-Level Embeddings Option

**File**: `export-sql-backup-to-chromadb.py`

- Add `--include-paragraph-level` flag
- Store each complete paragraph as a single document (in addition to segments)
- Useful for longer paragraphs that shouldn't be split

## Phase 3: Smart Context Retrieval in Search

### 3.1 Enhanced Search Endpoint

**File**: `web_service/app.py`

- Add `include_full_context: bool = False` to `SearchRequest` schema
- When True: For each result segment, fetch and combine all segments from same paragraph
- Use ChromaDB `get()` with where clause: `book_id`, `page_id`, `paragraph_index`
- Sort by `segment_index` and combine text

### 3.2 Paragraph Context Retrieval Function

**File**: `web_service/app.py`

- Create `get_paragraph_context(collection, book_id, page_id, paragraph_index) -> str`
- Fetches all segments, sorts, combines
- Returns full paragraph text
- Cache results in request scope to avoid duplicate queries

### 3.3 Page Context Retrieval Function

**File**: `web_service/app.py`

- Create `get_page_context(collection, book_id, page_id) -> str`
- Option A: Query page-level document if exists
- Option B: Combine all paragraphs from page
- Option C: Retrieve from text cache if stored separately

### 3.4 Multi-Model Search Context

**File**: `web_service/app.py`

- Extend multi-model search to support context retrieval
- Each model's results get context from its own collection
- Combine context per model for comparison

## Phase 4: Enhanced Result Display

### 4.1 Frontend Context Toggle

**File**: `web_service/static/index.html`

- Add UI toggle: "Show Full Paragraph" / "Show Full Page" / "Show Segment Only"
- Default: "Show Full Paragraph" for better context
- When toggled, fetch context via new API endpoint or include in search response

### 4.2 Context Display Component

**File**: `web_service/static/index.html`

- Enhance `renderDocumentWithContext()` to show:
- Segment text (highlighted)
- Full paragraph text (expandable)
- Full page text (expandable, lazy-loaded)
- Add "Show more context" button
- Visual indicator: segment vs paragraph vs page

### 4.3 Context API Endpoint

**File**: `web_service/app.py`

- Add `GET /search/context/{result_id}` endpoint
- Returns full paragraph or page text for a given result
- Accepts query params: `type=paragraph|page`
- Caches responses

## Phase 5: Performance and Optimization

### 5.1 Caching Strategy

**Files**: `web_service/app.py`, `web_service/database.py`

- Cache paragraph/page text in Redis
- Key format: `paragraph:{book_id}:{page_id}:{para_index}`
- TTL: 24 hours
- Invalidate on collection update

### 5.2 Batch Context Retrieval

**File**: `web_service/app.py`

- When multiple results from same paragraph/page, fetch once
- Group results by `(book_id, page_id, paragraph_index)`
- Batch fetch contexts
- Reduce ChromaDB queries

### 5.3 Text Compression

**File**: `export-sql-backup-to-chromadb.py`

- For large texts in metadata, use compression
- Add `--compress-stored-text` flag
- Use gzip/base64 for storage
- Decompress on retrieval

## Phase 6: Database Schema Updates

### 6.1 Text Cache Table (Optional)

**File**: `web_service/database.py`

- If storing texts separately, create `text_cache` table:
- `cache_key` (hash of book_id+page_id+para_index)
- `text_type` (paragraph|page)
- `text_content` (TEXT)
- `created_at`, `updated_at`
- Index on `cache_key` for fast lookup

### 6.2 Update Export Jobs Schema

**File**: `web_service/database.py`

- Add columns to track text storage settings:
- `store_full_paragraphs` (BOOLEAN)
- `store_full_pages` (BOOLEAN)
- `max_stored_text_size` (INTEGER)

## Phase 7: Testing and Validation

### 7.1 Unit Tests

**File**: `tests/test_context_retrieval.py`

- Test paragraph context retrieval
- Test page context retrieval
- Test text combination and sorting
- Test caching behavior

### 7.2 Integration Tests

**File**: `tests/test_enhanced_search.py`

- Test search with `include_full_context=True`
- Test multi-model search with context
- Test performance with large datasets
- Test memory usage with full texts

### 7.3 Benchmarking

**File**: `tools/benchmark_context_retrieval.py`

- Measure query time with/without context
- Measure memory usage
- Compare segment-only vs paragraph vs page display
- Document performance impact

## Implementation Order

1. **Phase 1.1-1.2**: Store full paragraph/page text (backward compatible)
2. **Phase 2.1-2.2**: Optimize segmentation parameters
3. **Phase 3.1-3.2**: Implement paragraph context retrieval
4. **Phase 4.1-4.2**: Update frontend to show context
5. **Phase 3.3-3.4**: Add page context and multi-model support
6. **Phase 5**: Performance optimization
7. **Phase 6**: Database enhancements (if needed)
8. **Phase 7**: Testing

## Configuration Summary

### New CLI Arguments

- `--store-full-paragraphs`: Store full paragraph text in metadata
- `--store-full-pages`: Store full page text (separate collection or metadata)
- `--max-stored-text-size`: Max size for stored text (default 5000 for para, 20000 for page)
- `--include-paragraph-level`: Also embed complete paragraphs as single documents
- `--smart-segmentation`: Use sentence-aware segmentation
- `--adaptive-context`: Adjust context_length dynamically

### New API Parameters

- `include_full_context: bool`: Return full paragraph context in search results
- `context_type: str`: "segment" | "paragraph" | "page"

### New Environment Variables

- `STORE_FULL_PARAGRAPHS=true/false`
- `STORE_FULL_PAGES=true/false`
- `MAX_STORED_TEXT_SIZE=5000`
- `ENABLE_CONTEXT_CACHE=true/false`