<!-- bb360061-1d65-41cf-a87a-d9ee0774bd39 70ccf3ba-8d08-46a6-a981-04a419c9a47b -->
# Add Gemini Embedding Support to Export Script

## Overview

Add support for Gemini embedding models to `export-sql-backup-to-chromadb.py` by implementing a Gemini embedder class and integrating it into the existing embedding provider system.

## Implementation Steps

### 1. Add Gemini Embedder Class

- Create `GeminiEmbedder` class in `export-sql-backup-to-chromadb.py` (similar to `HuggingFaceEmbedder`)
- Location: After `HuggingFaceEmbedder` class (around line 621)
- Use `google-genai` library with `genai.Client` and `generate_embeddings` method
- Handle API key initialization and batch processing
- Support models like `gemini-embedding-001`, `gemini-2.5-flash`, and future Gemini 3 embedding models
- Add proper error handling and Persian language output messages

### 2. Update EmbeddingProvider Class

- Add "gemini" to supported providers in `EmbeddingProvider.__init__` (line 623-645)
- Initialize `GeminiEmbedder` when provider is "gemini"
- Update error message to include "gemini" in supported providers list
- Pass Gemini API key to the embedder (separate from OpenAI API key)

### 3. Add Command-Line Arguments

- Add `--gemini-api-key` argument to `parse_args` function (around line 969)
- Default to `GEMINI_API_KEY` environment variable
- Add help text explaining it's required for Gemini provider
- Update `--embedding-provider` choices to include "gemini" (line 950)

### 4. Update EmbeddingProvider Initialization

- In `export_to_chroma` function (line 760), pass Gemini API key when provider is "gemini"
- Use `args.gemini_api_key` for Gemini provider, keep `args.openai_api_key` for OpenAI

### 5. Handle Import Dependencies

- Add try/except block for `google.genai` import (similar to transformers import, around line 38)
- Set `GOOGLE_GENAI_AVAILABLE` flag
- Raise helpful error if library is missing when Gemini provider is selected

## Files to Modify

- `export-sql-chromadb/export-sql-backup-to-chromadb.py`: Main implementation

## Dependencies

- New Python package: `google-genai` (will need to be installed via `pip install google-genai`)

## Notes

- Gemini API key is separate from OpenAI API key
- The implementation follows the same pattern as HuggingFace embedder for consistency
- Supports batch processing for efficiency
- Error messages should be in Persian to match existing code style

### To-dos

- [ ] Add google-genai import with try/except block and availability flag
- [ ] Create GeminiEmbedder class with batch processing support
- [ ] Update EmbeddingProvider to support 'gemini' provider option
- [ ] Add --gemini-api-key command-line argument and update --embedding-provider choices
- [ ] Update export_to_chroma function to pass Gemini API key to EmbeddingProvider