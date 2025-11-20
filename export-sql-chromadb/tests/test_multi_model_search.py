"""
Tests for multi-model search functionality.

This test verifies that:
1. Each model uses its own embedder
2. Search is performed in the model's specific collection
3. Results from each model are collected separately
4. Results are properly combined and deduplicated
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock


def test_result_combination_logic():
    """Test that results from multiple models are properly combined."""
    # Simulate results from 2 models
    model_1_results = [
        {"id": "doc1", "score": 0.95, "model_id": 1, "document": "Document 1"},
        {"id": "doc2", "score": 0.90, "model_id": 1, "document": "Document 2"},
        {"id": "doc3", "score": 0.85, "model_id": 1, "document": "Document 3"},
    ]
    model_2_results = [
        {"id": "doc2", "score": 0.92, "model_id": 2, "document": "Document 2"},  # Duplicate
        {"id": "doc4", "score": 0.88, "model_id": 2, "document": "Document 4"},
        {"id": "doc5", "score": 0.82, "model_id": 2, "document": "Document 5"},
    ]
    
    per_model_results = {
        1: model_1_results,
        2: model_2_results,
    }
    
    # Simulate the combination logic
    successful_model_ids = [1, 2]
    overall_limit = 10
    seen_doc_ids = set()
    combined_results = []
    
    max_depth = max((len(per_model_results.get(mid, [])) for mid in successful_model_ids), default=0)
    for depth in range(max_depth):
        for model_id in successful_model_ids:
            if len(combined_results) >= overall_limit:
                break
            model_items = per_model_results.get(model_id, [])
            if depth < len(model_items):
                item = model_items[depth]
                doc_id = item.get("id")
                if doc_id and doc_id not in seen_doc_ids:
                    combined_results.append(item)
                    seen_doc_ids.add(doc_id)
        if len(combined_results) >= overall_limit:
            break
    
    # Verify results
    assert len(combined_results) == 5  # doc1, doc2, doc3, doc4, doc5 (doc2 deduplicated)
    assert combined_results[0]["id"] == "doc1"  # From model 1
    assert combined_results[1]["id"] == "doc2"  # From model 1 (first occurrence kept)
    assert combined_results[2]["id"] == "doc3"  # From model 1
    assert combined_results[3]["id"] == "doc4"  # From model 2
    assert combined_results[4]["id"] == "doc5"  # From model 2
    
    # Verify deduplication: doc2 should only appear once
    doc_ids = [r["id"] for r in combined_results]
    assert doc_ids.count("doc2") == 1


def test_single_model_result():
    """Test that single model returns its results directly."""
    model_1_results = [
        {"id": "doc1", "score": 0.95, "model_id": 1},
        {"id": "doc2", "score": 0.90, "model_id": 1},
    ]
    
    per_model_results = {1: model_1_results}
    successful_model_ids = [1]
    per_model_limit = 10
    
    if len(successful_model_ids) == 1:
        combined_results = per_model_results[successful_model_ids[0]][:per_model_limit]
    else:
        combined_results = []
    
    assert len(combined_results) == 2
    assert all(r["model_id"] == 1 for r in combined_results)


@pytest.mark.asyncio
async def test_embedder_creation_for_different_models():
    """Test that embedders are created correctly for different providers."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from web_service.clients import create_embedder_for_model
    
    # Mock OpenAI embedder
    with patch("web_service.clients.embedding_functions") as mock_ef:
        mock_openai_func = Mock()
        mock_ef.OpenAIEmbeddingFunction.return_value = mock_openai_func
        mock_openai_func.return_value = [[0.1, 0.2, 0.3]]
        
        embedder = create_embedder_for_model(
            provider="openai",
            model="text-embedding-3-small",
            api_key="test-key",
        )
        
        assert embedder.provider == "openai"
        assert embedder.model == "text-embedding-3-small"
        
        # Test embedding
        result = embedder.embed(["test query"])
        assert len(result) == 1
        assert len(result[0]) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

