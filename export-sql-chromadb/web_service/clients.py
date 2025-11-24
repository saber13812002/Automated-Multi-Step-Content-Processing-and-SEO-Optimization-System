from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Sequence

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.errors import NotFoundError

try:
    from chromadb.utils import embedding_functions
except ImportError:  # pragma: no cover - compatibility with newer Chroma releases
    embedding_functions = None  # type: ignore

try:
    from google import genai
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False
    genai = None  # type: ignore

from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from .config import Settings, get_settings

logger = logging.getLogger(__name__)


class QueryEmbedder:
    """Thin wrapper around embedding functions for query embeddings."""

    def __init__(self, settings: Settings):
        self._provider = settings.embedding_provider
        self._model = settings.embedding_model
        self._api_key = settings.openai_api_key
        self._gemini_api_key = settings.gemini_api_key
        self._embedding_function = None

        if self._provider == "openai":
            if not self._api_key:
                raise RuntimeError("OPENAI_API_KEY is required for OpenAI embeddings.")
            if embedding_functions is None:
                raise RuntimeError(
                    "chromadb.utils.embedding_functions is unavailable. "
                    "Upgrade/downgrade chromadb to a compatible version."
                )
            self._embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_key=self._api_key,
                model_name=self._model,
            )
        elif self._provider == "huggingface":
            try:
                from transformers import AutoTokenizer, AutoModel
                import torch
            except ImportError:
                raise RuntimeError(
                    "transformers library is required for HuggingFace embeddings. "
                    "Install it with: pip install transformers torch"
                )
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info("Loading HuggingFace model %s on %s", self._model, self.device)
            self.tokenizer = AutoTokenizer.from_pretrained(self._model)
            self.model_obj = AutoModel.from_pretrained(self._model)
            self.model_obj.to(self.device)
            self.model_obj.eval()
            logger.info("HuggingFace model loaded successfully")
        elif self._provider == "gemini":
            if not GOOGLE_GENAI_AVAILABLE:
                raise RuntimeError(
                    "google-genai library is required for Gemini embeddings. "
                    "Install it with: pip install google-genai"
                )
            if not self._gemini_api_key:
                raise RuntimeError("GEMINI_API_KEY is required for Gemini embeddings.")
            logger.info("Initializing Gemini client for model %s", self._model)
            self.client = genai.Client(api_key=self._gemini_api_key)
            logger.info("Gemini client initialized successfully")
        elif self._provider == "none":
            self._embedding_function = None
        else:
            raise RuntimeError(f"Unsupported embedding provider: {self._provider}")

    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        if not texts:
            return []
        
        if self._provider == "openai":
            embeddings = self._embedding_function(texts)
        elif self._provider == "huggingface":
            import torch
            encoded = self.tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            )
            encoded = {k: v.to(self.device) for k, v in encoded.items()}
            with torch.no_grad():
                outputs = self.model_obj(**encoded)
                embeddings_tensor = outputs.last_hidden_state
                attention_mask = encoded["attention_mask"]
                mask_expanded = attention_mask.unsqueeze(-1).expand(embeddings_tensor.size()).float()
                sum_embeddings = torch.sum(embeddings_tensor * mask_expanded, dim=1)
                sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
                embeddings_tensor = sum_embeddings / sum_mask
            embeddings = embeddings_tensor.cpu().numpy().tolist()
        elif self._provider == "gemini":
            try:
                response = self.client.models.embed_content(
                    model=self._model,
                    contents=list(texts)
                )
                embeddings_list = []
                if hasattr(response, 'embeddings'):
                    response_embeddings = response.embeddings
                elif isinstance(response, list):
                    response_embeddings = response
                elif isinstance(response, dict) and 'embeddings' in response:
                    response_embeddings = response['embeddings']
                else:
                    response_embeddings = [response]
                
                for embedding in response_embeddings:
                    if isinstance(embedding, list):
                        embeddings_list.append(embedding)
                    elif isinstance(embedding, dict):
                        if 'values' in embedding:
                            embeddings_list.append(embedding['values'])
                        elif 'embedding' in embedding:
                            embeddings_list.append(embedding['embedding'])
                        else:
                            for val in embedding.values():
                                if isinstance(val, list):
                                    embeddings_list.append(val)
                                    break
                    elif hasattr(embedding, 'values'):
                        embeddings_list.append(embedding.values)
                    elif hasattr(embedding, 'embedding'):
                        embeddings_list.append(embedding.embedding)
                    else:
                        try:
                            embeddings_list.append(list(embedding))
                        except (TypeError, ValueError):
                            raise RuntimeError(f"Unable to extract embedding from response: {type(embedding)}")
                
                if len(embeddings_list) != len(texts):
                    raise RuntimeError(
                        f"Expected {len(texts)} embeddings, but got {len(embeddings_list)}"
                    )
                embeddings = embeddings_list
            except Exception as exc:
                raise RuntimeError(f"Failed to generate Gemini embeddings: {exc}") from exc
        elif self._provider == "none":
            return []
        else:
            raise RuntimeError(f"Unsupported provider: {self._provider}")
        
        logger.debug("Generated embeddings for %d text(s).", len(texts))
        return embeddings


class MultiModelEmbedder:
    """Embedder that supports multiple providers (OpenAI, HuggingFace, Gemini)."""
    
    def __init__(self, provider: str, model: str, api_key: str = "", device: str = "", gemini_api_key: str = ""):
        self.provider = provider
        self.model = model
        self._embedding_function = None
        
        if provider == "openai":
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY is required for OpenAI embeddings.")
            if embedding_functions is None:
                raise RuntimeError("chromadb.utils.embedding_functions is unavailable.")
            self._embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_key=api_key,
                model_name=model,
            )
        elif provider == "huggingface":
            try:
                from transformers import AutoTokenizer, AutoModel
                import torch
                import numpy as np
            except ImportError:
                raise RuntimeError(
                    "transformers library is required for HuggingFace embeddings. "
                    "Install it with: pip install transformers torch"
                )
            
            self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
            logger.info("Loading HuggingFace model %s on %s", model, self.device)
            self.tokenizer = AutoTokenizer.from_pretrained(model)
            self.model_obj = AutoModel.from_pretrained(model)
            self.model_obj.to(self.device)
            self.model_obj.eval()
            logger.info("HuggingFace model loaded successfully")
        elif provider == "gemini":
            if not GOOGLE_GENAI_AVAILABLE:
                raise RuntimeError(
                    "google-genai library is required for Gemini embeddings. "
                    "Install it with: pip install google-genai"
                )
            if not gemini_api_key:
                raise RuntimeError("GEMINI_API_KEY is required for Gemini embeddings.")
            logger.info("Initializing Gemini client for model %s", model)
            self.client = genai.Client(api_key=gemini_api_key)
            logger.info("Gemini client initialized successfully")
        else:
            raise RuntimeError(f"Unsupported embedding provider: {provider}")
    
    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        if not texts:
            return []
        
        if self.provider == "openai":
            return self._embedding_function(texts)
        elif self.provider == "huggingface":
            import torch
            # Tokenize
            encoded = self.tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            )
            encoded = {k: v.to(self.device) for k, v in encoded.items()}
            
            # Generate embeddings
            with torch.no_grad():
                outputs = self.model_obj(**encoded)
                embeddings = outputs.last_hidden_state
                attention_mask = encoded["attention_mask"]
                mask_expanded = attention_mask.unsqueeze(-1).expand(embeddings.size()).float()
                sum_embeddings = torch.sum(embeddings * mask_expanded, dim=1)
                sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
                embeddings = sum_embeddings / sum_mask
            
            return embeddings.cpu().numpy().tolist()
        elif self.provider == "gemini":
            try:
                response = self.client.models.embed_content(
                    model=self.model,
                    contents=list(texts)
                )
                embeddings_list = []
                if hasattr(response, 'embeddings'):
                    response_embeddings = response.embeddings
                elif isinstance(response, list):
                    response_embeddings = response
                elif isinstance(response, dict) and 'embeddings' in response:
                    response_embeddings = response['embeddings']
                else:
                    response_embeddings = [response]
                
                for embedding in response_embeddings:
                    if isinstance(embedding, list):
                        embeddings_list.append(embedding)
                    elif isinstance(embedding, dict):
                        if 'values' in embedding:
                            embeddings_list.append(embedding['values'])
                        elif 'embedding' in embedding:
                            embeddings_list.append(embedding['embedding'])
                        else:
                            for val in embedding.values():
                                if isinstance(val, list):
                                    embeddings_list.append(val)
                                    break
                    elif hasattr(embedding, 'values'):
                        embeddings_list.append(embedding.values)
                    elif hasattr(embedding, 'embedding'):
                        embeddings_list.append(embedding.embedding)
                    else:
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
        else:
            raise RuntimeError(f"Unsupported provider: {self.provider}")


def create_embedder_for_model(
    provider: str,
    model: str,
    api_key: str = "",
    device: str = "",
    gemini_api_key: str = "",
) -> MultiModelEmbedder:
    """Create an embedder for a specific model/provider combination."""
    settings = get_settings()
    # Use provided API key or fallback to settings
    final_api_key = api_key or settings.openai_api_key
    final_gemini_api_key = gemini_api_key or settings.gemini_api_key
    return MultiModelEmbedder(provider, model, final_api_key, device, final_gemini_api_key)


def get_chroma_client(settings: Settings | None = None):
    """Create or return ChromaDB client. Not cached to avoid unhashable Settings object.
    
    Uses EXACTLY the same logic as verify_chroma_export.py for consistency.
    This function mimics verify_chroma_export.py's create_client() exactly.
    """
    cfg = settings or get_settings()
    
    # EXACTLY like verify_chroma_export.py:
    telemetry = os.getenv("CHROMA_ANONYMIZED_TELEMETRY", "False")
    sdk_settings = ChromaSettings(anonymized_telemetry=telemetry.lower() in ("true", "1", "yes"))

    # EXACTLY like verify_chroma_export.py:
    if cfg.chroma_persist_directory:
        persist_path = Path(cfg.chroma_persist_directory)
        persist_path.mkdir(parents=True, exist_ok=True)
        logger.info(
            "Connecting to Chroma persistent client at %s", cfg.chroma_persist_directory
        )
        return chromadb.PersistentClient(path=str(persist_path), settings=sdk_settings)

    # EXACTLY like verify_chroma_export.py - direct return, no logging before creation
    # Use direct values from settings, ensuring types match
    host = str(cfg.chroma_host)
    port = int(cfg.chroma_port)
    ssl = bool(cfg.chroma_ssl)
    api_key = str(cfg.chroma_api_key) if cfg.chroma_api_key else ""
    
    logger.info(
        "Connecting to Chroma HTTP client at %s:%s (ssl=%s)",
        host,
        port,
        ssl,
    )
    
    # EXACTLY like verify_chroma_export.py line 24:
    headers = {"Authorization": api_key} if api_key else None
    
    # EXACTLY like verify_chroma_export.py line 20-25:
    return chromadb.HttpClient(
        host=host,
        port=port,
        ssl=ssl,
        headers=headers,
        settings=sdk_settings,
    )


def get_query_embedder(settings: Settings | None = None) -> QueryEmbedder:
    """Create or return query embedder. Not cached to avoid unhashable Settings object."""
    cfg = settings or get_settings()
    return QueryEmbedder(cfg)


def get_collection(settings: Settings | None = None):
    """Get ChromaDB collection. Not cached to avoid unhashable Settings object."""
    cfg = settings or get_settings()
    client = get_chroma_client(cfg)
    try:
        collection = client.get_collection(cfg.chroma_collection)
        logger.info("Connected to Chroma collection '%s'.", cfg.chroma_collection)
    except NotFoundError as exc:
        # List available collections to help user debug
        try:
            available_collections = client.list_collections()
            collection_names = [col.name for col in available_collections] if available_collections else []
            if collection_names:
                available_msg = f"Available collections: {', '.join(collection_names)}"
            else:
                available_msg = "No collections found in ChromaDB. Run the exporter first."
        except Exception as list_exc:
            logger.warning("Failed to list collections for error message: %s", list_exc)
            available_msg = "Could not list available collections."

        error_msg = (
            f"Chroma collection '{cfg.chroma_collection}' not found. "
            f"{available_msg} "
            f"Update CHROMA_COLLECTION in your .env file or run the exporter to create the collection."
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg) from exc
    return collection


def get_redis_client(settings: Settings | None = None) -> Redis:
    """Create or return Redis client. Not cached to avoid unhashable Settings object."""
    cfg = settings or get_settings()
    logger.info("Connecting to Redis at %s", cfg.redis_dsn)
    return Redis.from_url(cfg.redis_dsn, decode_responses=True)


def validate_chroma_connection(settings: Settings | None = None) -> tuple[bool, str]:
    """
    Validate ChromaDB connection and collection availability.
    Returns (is_valid, error_message).
    """
    cfg = settings or get_settings()
    
    try:
        logger.info("🔍 Validating ChromaDB connection at %s:%s", cfg.chroma_host, cfg.chroma_port)
        client = get_chroma_client(cfg)
        
        # Check heartbeat
        try:
            heartbeat = client.heartbeat()
            logger.info("✅ ChromaDB heartbeat successful: %s", heartbeat)
        except Exception as exc:
            error_msg = (
                f"❌ ChromaDB server is not responding at {cfg.chroma_host}:{cfg.chroma_port}. "
                f"Check if ChromaDB is running. Error: {exc}"
            )
            logger.error(error_msg)
            return False, error_msg
        
        # Check if collection exists
        try:
            collection = client.get_collection(cfg.chroma_collection)
            count = collection.count()
            logger.info("✅ Collection '%s' found with %d documents", cfg.chroma_collection, count)
            return True, ""
        except NotFoundError:
            # List available collections
            try:
                available_collections = client.list_collections()
                collection_names = [col.name for col in available_collections] if available_collections else []
                if collection_names:
                    available_msg = f"Available collections: {', '.join(collection_names)}"
                else:
                    available_msg = "No collections found in ChromaDB. Run the exporter first."
            except Exception as list_exc:
                logger.warning("Failed to list collections: %s", list_exc)
                available_msg = "Could not list available collections."
            
            error_msg = (
                f"❌ Collection '{cfg.chroma_collection}' not found in ChromaDB. "
                f"{available_msg} "
                f"Please update CHROMA_COLLECTION in your .env file or run the exporter to create it."
            )
            logger.error(error_msg)
            return False, error_msg
        
    except Exception as exc:
        error_msg = (
            f"❌ Failed to connect to ChromaDB at {cfg.chroma_host}:{cfg.chroma_port}. "
            f"Check network connectivity and ChromaDB server status. Error: {exc}"
        )
        logger.error(error_msg)
        return False, error_msg


def validate_redis_connection(settings: Settings | None = None) -> tuple[bool, str]:
    """
    Validate Redis connection.
    Returns (is_valid, error_message).
    """
    cfg = settings or get_settings()
    
    try:
        logger.info("🔍 Validating Redis connection at %s", cfg.redis_dsn)
        redis_client = get_redis_client(cfg)
        pong = redis_client.ping()
        if pong:
            logger.info("✅ Redis connection successful")
            return True, ""
        else:
            error_msg = "❌ Redis ping returned unexpected response"
            logger.error(error_msg)
            return False, error_msg
    except RedisConnectionError as exc:
        error_msg = (
            f"❌ Cannot connect to Redis at {cfg.redis_dsn}. "
            f"Check if Redis is running and the connection details are correct. Error: {exc}"
        )
        logger.error(error_msg)
        return False, error_msg
    except Exception as exc:
        error_msg = f"❌ Redis connection error: {exc}"
        logger.error(error_msg)
        return False, error_msg


def validate_embedder_config(settings: Settings | None = None) -> tuple[bool, str]:
    """
    Validate embedding provider configuration.
    Returns (is_valid, error_message).
    """
    cfg = settings or get_settings()
    
    if cfg.embedding_provider == "openai":
        if not cfg.openai_api_key:
            error_msg = (
                "❌ OPENAI_API_KEY is not set. "
                "Please set OPENAI_API_KEY in your .env file to enable embedding generation."
            )
            logger.error(error_msg)
            return False, error_msg
    elif cfg.embedding_provider == "gemini":
        if not cfg.gemini_api_key:
            error_msg = (
                "❌ GEMINI_API_KEY is not set. "
                "Please set GEMINI_API_KEY in your .env file to enable embedding generation."
            )
            logger.error(error_msg)
            return False, error_msg
    elif cfg.embedding_provider == "huggingface":
        # HuggingFace doesn't require API key, but we should check if transformers is available
        try:
            import transformers
        except ImportError:
            error_msg = (
                "❌ transformers library is not installed. "
                "Please install it with: pip install transformers torch"
            )
            logger.error(error_msg)
            return False, error_msg
    elif cfg.embedding_provider == "none":
        # No validation needed for "none" provider
        pass
    else:
        error_msg = f"❌ Unsupported embedding provider: {cfg.embedding_provider}"
        logger.error(error_msg)
        return False, error_msg
    
    logger.info("✅ Embedding configuration valid (provider: %s, model: %s)", 
                cfg.embedding_provider, cfg.embedding_model)
    return True, ""


__all__ = [
    "create_embedder_for_model",
    "get_chroma_client",
    "get_collection",
    "get_query_embedder",
    "get_redis_client",
    "MultiModelEmbedder",
    "QueryEmbedder",
    "validate_chroma_connection",
    "validate_redis_connection",
    "validate_embedder_config",
]

