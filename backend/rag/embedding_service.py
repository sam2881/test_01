"""
Embedding Service - Unified embedding generation with local and cloud options

Supports:
1. Local: SentenceTransformers (all-MiniLM-L6-v2) - FREE, fast, offline
2. Cloud: OpenAI (text-embedding-3-small) - Better quality, requires API

Automatically falls back if primary provider unavailable.
"""

import os
import hashlib
import json
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import structlog

logger = structlog.get_logger()


@dataclass
class EmbeddingConfig:
    """Configuration for embedding service"""
    provider: str = "local"  # "local" or "openai"
    local_model: str = "all-MiniLM-L6-v2"
    openai_model: str = "text-embedding-3-small"
    cache_enabled: bool = True
    cache_dir: str = "./data/embeddings_cache"
    batch_size: int = 32
    normalize: bool = True


class EmbeddingService:
    """
    Unified embedding service supporting multiple providers.

    Features:
    - Local embeddings with SentenceTransformers (no API cost)
    - Cloud embeddings with OpenAI (better quality)
    - Automatic fallback between providers
    - Caching to avoid recomputation
    - Batch processing for efficiency
    """

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        self.config = config or EmbeddingConfig()
        self._local_model = None
        self._openai_client = None
        self._cache: Dict[str, np.ndarray] = {}

        # Ensure cache directory exists
        if self.config.cache_enabled:
            Path(self.config.cache_dir).mkdir(parents=True, exist_ok=True)

        logger.info(
            "embedding_service_initialized",
            provider=self.config.provider,
            cache_enabled=self.config.cache_enabled
        )

    @property
    def local_model(self):
        """Lazy load local SentenceTransformer model"""
        if self._local_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._local_model = SentenceTransformer(self.config.local_model)
                logger.info("local_model_loaded", model=self.config.local_model)
            except ImportError:
                logger.warning(
                    "sentence_transformers_not_installed",
                    message="pip install sentence-transformers"
                )
            except Exception as e:
                logger.error("local_model_load_failed", error=str(e))
        return self._local_model

    @property
    def openai_client(self):
        """Lazy initialize OpenAI client"""
        if self._openai_client is None:
            try:
                import openai
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    self._openai_client = openai.OpenAI(api_key=api_key)
                    logger.info("openai_client_initialized")
                else:
                    logger.warning("openai_api_key_not_set")
            except ImportError:
                logger.warning("openai_not_installed")
            except Exception as e:
                logger.error("openai_init_failed", error=str(e))
        return self._openai_client

    def embed(
        self,
        texts: Union[str, List[str]],
        provider: Optional[str] = None
    ) -> np.ndarray:
        """
        Generate embeddings for text(s).

        Args:
            texts: Single text or list of texts
            provider: Override default provider ("local" or "openai")

        Returns:
            numpy array of embeddings (N x D)
        """
        # Normalize input
        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            return np.array([])

        provider = provider or self.config.provider

        # Check cache first
        if self.config.cache_enabled:
            cached, missing_indices, missing_texts = self._check_cache(texts)
            if not missing_texts:
                return cached
        else:
            missing_indices = list(range(len(texts)))
            missing_texts = texts
            cached = None

        # Generate embeddings for missing texts
        if provider == "local":
            new_embeddings = self._embed_local(missing_texts)
        elif provider == "openai":
            new_embeddings = self._embed_openai(missing_texts)
        else:
            # Try local first, fallback to openai
            new_embeddings = self._embed_with_fallback(missing_texts)

        # Update cache
        if self.config.cache_enabled and new_embeddings is not None:
            self._update_cache(missing_texts, new_embeddings)

        # Combine cached and new embeddings
        if cached is not None and new_embeddings is not None:
            result = np.zeros((len(texts), new_embeddings.shape[1]))
            for i, idx in enumerate(missing_indices):
                result[idx] = new_embeddings[i]
            cached_idx = 0
            for i in range(len(texts)):
                if i not in missing_indices:
                    result[i] = cached[cached_idx]
                    cached_idx += 1
            return result
        elif new_embeddings is not None:
            return new_embeddings
        elif cached is not None:
            return cached
        else:
            # Fallback to random embeddings
            logger.error("all_embedding_methods_failed")
            return np.random.rand(len(texts), 384)

    def _embed_local(self, texts: List[str]) -> Optional[np.ndarray]:
        """Generate embeddings using local SentenceTransformer"""
        if self.local_model is None:
            return None

        try:
            embeddings = self.local_model.encode(
                texts,
                batch_size=self.config.batch_size,
                show_progress_bar=len(texts) > 10,
                normalize_embeddings=self.config.normalize
            )
            logger.info("local_embeddings_generated", count=len(texts))
            return np.array(embeddings)
        except Exception as e:
            logger.error("local_embedding_failed", error=str(e))
            return None

    def _embed_openai(self, texts: List[str]) -> Optional[np.ndarray]:
        """Generate embeddings using OpenAI API"""
        if self.openai_client is None:
            return None

        try:
            # OpenAI API has limits, process in batches
            all_embeddings = []
            for i in range(0, len(texts), self.config.batch_size):
                batch = texts[i:i + self.config.batch_size]
                response = self.openai_client.embeddings.create(
                    model=self.config.openai_model,
                    input=batch
                )
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

            embeddings = np.array(all_embeddings)

            # Normalize if configured
            if self.config.normalize:
                norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                embeddings = embeddings / norms

            logger.info("openai_embeddings_generated", count=len(texts))
            return embeddings
        except Exception as e:
            logger.error("openai_embedding_failed", error=str(e))
            return None

    def _embed_with_fallback(self, texts: List[str]) -> Optional[np.ndarray]:
        """Try local first, then OpenAI as fallback"""
        # Try local first (free, fast)
        embeddings = self._embed_local(texts)
        if embeddings is not None:
            return embeddings

        # Fallback to OpenAI
        logger.info("falling_back_to_openai")
        embeddings = self._embed_openai(texts)
        if embeddings is not None:
            return embeddings

        return None

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        return hashlib.md5(text.encode()).hexdigest()

    def _check_cache(
        self,
        texts: List[str]
    ) -> tuple:
        """
        Check cache for existing embeddings.

        Returns:
            (cached_embeddings, missing_indices, missing_texts)
        """
        cached = []
        missing_indices = []
        missing_texts = []

        for i, text in enumerate(texts):
            key = self._get_cache_key(text)
            if key in self._cache:
                cached.append(self._cache[key])
            else:
                # Check disk cache
                cache_file = Path(self.config.cache_dir) / f"{key}.npy"
                if cache_file.exists():
                    try:
                        embedding = np.load(cache_file)
                        self._cache[key] = embedding
                        cached.append(embedding)
                        continue
                    except:
                        pass

                missing_indices.append(i)
                missing_texts.append(text)

        cached_array = np.array(cached) if cached else None
        return cached_array, missing_indices, missing_texts

    def _update_cache(self, texts: List[str], embeddings: np.ndarray):
        """Update cache with new embeddings"""
        for text, embedding in zip(texts, embeddings):
            key = self._get_cache_key(text)
            self._cache[key] = embedding

            # Save to disk
            cache_file = Path(self.config.cache_dir) / f"{key}.npy"
            try:
                np.save(cache_file, embedding)
            except Exception as e:
                logger.warning("cache_save_failed", error=str(e))

    def similarity(
        self,
        query_embedding: np.ndarray,
        document_embeddings: np.ndarray
    ) -> np.ndarray:
        """Calculate cosine similarity between query and documents"""
        # Normalize if not already normalized
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        doc_norms = document_embeddings / np.linalg.norm(
            document_embeddings, axis=1, keepdims=True
        )

        similarities = np.dot(doc_norms, query_norm)
        return similarities

    def get_embedding_dimension(self) -> int:
        """Get the embedding dimension for the current model"""
        if self.config.provider == "local" or self.local_model:
            return 384  # all-MiniLM-L6-v2 dimension
        else:
            return 1536  # text-embedding-3-small dimension

    def clear_cache(self):
        """Clear embedding cache"""
        self._cache.clear()
        cache_dir = Path(self.config.cache_dir)
        if cache_dir.exists():
            for f in cache_dir.glob("*.npy"):
                f.unlink()
        logger.info("embedding_cache_cleared")


class HybridEmbeddingService:
    """
    Hybrid embedding service that can combine multiple embedding types.

    Used for advanced hybrid search combining:
    - Semantic embeddings (SentenceTransformer)
    - Sparse embeddings (TF-IDF)
    """

    def __init__(self):
        self.semantic_service = EmbeddingService(
            EmbeddingConfig(provider="local")
        )
        self._tfidf = None

    @property
    def tfidf(self):
        """Lazy load TF-IDF vectorizer"""
        if self._tfidf is None:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._tfidf = TfidfVectorizer(
                max_features=10000,
                ngram_range=(1, 2),
                stop_words='english'
            )
        return self._tfidf

    def fit_tfidf(self, texts: List[str]):
        """Fit TF-IDF on corpus"""
        self.tfidf.fit(texts)
        logger.info("tfidf_fitted", vocab_size=len(self.tfidf.vocabulary_))

    def embed_hybrid(
        self,
        texts: Union[str, List[str]]
    ) -> Dict[str, np.ndarray]:
        """
        Generate both semantic and sparse embeddings.

        Returns:
            Dict with 'semantic' and 'sparse' embeddings
        """
        if isinstance(texts, str):
            texts = [texts]

        semantic = self.semantic_service.embed(texts)

        try:
            sparse = self.tfidf.transform(texts).toarray()
        except:
            sparse = np.zeros((len(texts), 10000))

        return {
            "semantic": semantic,
            "sparse": sparse
        }


# Global instances
embedding_service = EmbeddingService()
hybrid_embedding_service = HybridEmbeddingService()
