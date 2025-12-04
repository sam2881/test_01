"""
Hybrid Search Engine - Combines Semantic, Keyword, and Metadata Search
with configurable weights for optimal script/runbook retrieval.

Architecture:
    Query → [Semantic Search] → Score₁
         → [Keyword Search]  → Score₂  → Weighted Combination → Final Results
         → [Metadata Match]  → Score₃

Formula: Final_Score = (w₁ × Semantic) + (w₂ × Keyword) + (w₃ × Metadata)
"""

import os
import re
import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import structlog

logger = structlog.get_logger()


@dataclass
class SearchWeights:
    """Configurable weights for hybrid search components"""
    semantic: float = 0.6    # Vector similarity weight
    keyword: float = 0.3     # TF-IDF keyword weight
    metadata: float = 0.1    # Metadata exact match weight

    def __post_init__(self):
        total = self.semantic + self.keyword + self.metadata
        if abs(total - 1.0) > 0.01:
            # Normalize weights to sum to 1.0
            self.semantic /= total
            self.keyword /= total
            self.metadata /= total


@dataclass
class SearchResult:
    """Result from hybrid search with score breakdown"""
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    final_score: float
    score_breakdown: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "metadata": self.metadata,
            "final_score": self.final_score,
            "score_breakdown": self.score_breakdown
        }


class HybridSearchEngine:
    """
    Hybrid Search Engine combining three search strategies:
    1. Semantic Search - Vector similarity using embeddings
    2. Keyword Search - TF-IDF based keyword matching
    3. Metadata Search - Exact match on structured fields
    """

    def __init__(
        self,
        weights: Optional[SearchWeights] = None,
        embedding_model: str = "local"  # "local" or "openai"
    ):
        self.weights = weights or SearchWeights()
        self.embedding_model = embedding_model

        # TF-IDF vectorizer for keyword search
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=10000,
            stop_words='english',
            ngram_range=(1, 2),  # Unigrams and bigrams
            lowercase=True
        )

        # Storage for indexed documents
        self.documents: List[Dict[str, Any]] = []
        self.semantic_embeddings: Optional[np.ndarray] = None
        self.tfidf_matrix = None
        self.is_fitted = False

        # Local embedding model (lazy loaded)
        self._local_model = None

        logger.info(
            "hybrid_search_initialized",
            weights={"semantic": self.weights.semantic,
                    "keyword": self.weights.keyword,
                    "metadata": self.weights.metadata},
            embedding_model=embedding_model
        )

    @property
    def local_model(self):
        """Lazy load local embedding model"""
        if self._local_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._local_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("local_embedding_model_loaded", model="all-MiniLM-L6-v2")
            except ImportError:
                logger.warning("sentence_transformers_not_installed")
                self._local_model = None
        return self._local_model

    def index_documents(self, documents: List[Dict[str, Any]]) -> int:
        """
        Index documents for hybrid search.

        Args:
            documents: List of documents with 'content', 'metadata', and optional 'embedding'

        Returns:
            Number of documents indexed
        """
        self.documents = documents

        # Extract text content for TF-IDF
        texts = [self._prepare_text_for_search(doc) for doc in documents]

        # Fit TF-IDF vectorizer
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)

        # Generate semantic embeddings
        self.semantic_embeddings = self._generate_embeddings(texts)

        self.is_fitted = True

        logger.info(
            "documents_indexed",
            count=len(documents),
            tfidf_features=self.tfidf_matrix.shape[1] if self.tfidf_matrix is not None else 0
        )

        return len(documents)

    def _prepare_text_for_search(self, doc: Dict[str, Any]) -> str:
        """Prepare document text for search by combining content and metadata"""
        parts = [doc.get("content", "")]

        # Add searchable metadata fields
        metadata = doc.get("metadata", {})
        for field in ["name", "description", "keywords", "tags", "service", "action"]:
            if field in metadata:
                value = metadata[field]
                if isinstance(value, list):
                    parts.extend(value)
                else:
                    parts.append(str(value))

        return " ".join(parts)

    def _generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings using configured model"""
        if self.embedding_model == "local" and self.local_model:
            embeddings = self.local_model.encode(texts, show_progress_bar=True)
            return np.array(embeddings)
        else:
            # Fallback to mock embeddings if no model available
            logger.warning("using_mock_embeddings")
            return np.random.rand(len(texts), 384)

    def search(
        self,
        query: str,
        query_metadata: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        weights: Optional[SearchWeights] = None
    ) -> List[SearchResult]:
        """
        Perform hybrid search combining semantic, keyword, and metadata scores.

        Args:
            query: Search query text
            query_metadata: Optional metadata for filtering (cloud_provider, environment, etc.)
            top_k: Number of results to return
            weights: Optional custom weights for this search

        Returns:
            List of SearchResult objects with score breakdowns
        """
        if not self.is_fitted:
            logger.warning("search_on_unfitted_engine")
            return []

        weights = weights or self.weights
        query_metadata = query_metadata or {}

        # Calculate individual scores
        semantic_scores = self._calculate_semantic_scores(query)
        keyword_scores = self._calculate_keyword_scores(query)
        metadata_scores = self._calculate_metadata_scores(query_metadata)

        # Combine scores with weights
        final_scores = (
            weights.semantic * semantic_scores +
            weights.keyword * keyword_scores +
            weights.metadata * metadata_scores
        )

        # Get top-k indices
        top_indices = np.argsort(final_scores)[-top_k:][::-1]

        # Build results
        results = []
        for idx in top_indices:
            if final_scores[idx] > 0:
                doc = self.documents[idx]
                result = SearchResult(
                    chunk_id=doc.get("id", f"doc_{idx}"),
                    content=doc.get("content", ""),
                    metadata=doc.get("metadata", {}),
                    final_score=float(final_scores[idx]),
                    score_breakdown={
                        "semantic": float(semantic_scores[idx]),
                        "keyword": float(keyword_scores[idx]),
                        "metadata": float(metadata_scores[idx])
                    }
                )
                results.append(result)

        logger.info(
            "hybrid_search_complete",
            query_length=len(query),
            results_count=len(results),
            top_score=results[0].final_score if results else 0
        )

        return results

    def _calculate_semantic_scores(self, query: str) -> np.ndarray:
        """Calculate semantic similarity scores using embeddings"""
        if self.semantic_embeddings is None:
            return np.zeros(len(self.documents))

        # Generate query embedding
        query_embedding = self._generate_embeddings([query])[0]

        # Calculate cosine similarity
        similarities = cosine_similarity([query_embedding], self.semantic_embeddings)[0]

        # Normalize to 0-1 range
        return (similarities + 1) / 2

    def _calculate_keyword_scores(self, query: str) -> np.ndarray:
        """Calculate keyword match scores using TF-IDF"""
        if self.tfidf_matrix is None:
            return np.zeros(len(self.documents))

        # Transform query to TF-IDF vector
        query_vector = self.tfidf_vectorizer.transform([query])

        # Calculate cosine similarity
        similarities = cosine_similarity(query_vector, self.tfidf_matrix)[0]

        return similarities

    def _calculate_metadata_scores(self, query_metadata: Dict[str, Any]) -> np.ndarray:
        """Calculate metadata exact match scores"""
        if not query_metadata:
            return np.zeros(len(self.documents))

        scores = np.zeros(len(self.documents))
        match_fields = ["cloud_provider", "environment", "service", "resource_type", "action"]

        for idx, doc in enumerate(self.documents):
            doc_metadata = doc.get("metadata", {})
            matches = 0
            total_fields = 0

            for field in match_fields:
                if field in query_metadata:
                    total_fields += 1
                    query_val = str(query_metadata[field]).lower()
                    doc_val = str(doc_metadata.get(field, "")).lower()

                    if query_val == doc_val:
                        matches += 1
                    elif query_val in doc_val or doc_val in query_val:
                        matches += 0.5

            if total_fields > 0:
                scores[idx] = matches / total_fields

        return scores

    def adjust_weights(
        self,
        incident_type: str,
        severity: str = "medium"
    ) -> SearchWeights:
        """
        Dynamically adjust weights based on incident characteristics.

        Security incidents benefit from more keyword matching.
        Performance incidents benefit from more semantic matching.
        """
        weight_configs = {
            "security": SearchWeights(semantic=0.4, keyword=0.5, metadata=0.1),
            "performance": SearchWeights(semantic=0.7, keyword=0.2, metadata=0.1),
            "infrastructure": SearchWeights(semantic=0.5, keyword=0.3, metadata=0.2),
            "network": SearchWeights(semantic=0.5, keyword=0.35, metadata=0.15),
            "database": SearchWeights(semantic=0.6, keyword=0.3, metadata=0.1),
            "default": SearchWeights(semantic=0.6, keyword=0.3, metadata=0.1)
        }

        weights = weight_configs.get(incident_type.lower(), weight_configs["default"])

        # Boost metadata weight for high severity (more precise matching needed)
        if severity.lower() in ["high", "critical"]:
            weights.metadata += 0.1
            weights.semantic -= 0.1

        logger.info(
            "weights_adjusted",
            incident_type=incident_type,
            severity=severity,
            weights={"semantic": weights.semantic,
                    "keyword": weights.keyword,
                    "metadata": weights.metadata}
        )

        return weights


# Global instance
hybrid_search_engine = HybridSearchEngine()
