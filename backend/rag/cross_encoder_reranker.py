"""
Cross-Encoder Re-ranking Module

Re-ranks search results using a cross-encoder model for improved precision.
Cross-encoders jointly encode query and document, providing more accurate
relevance scores than bi-encoder approaches.

Flow:
    Initial Results (Top 20) → Cross-Encoder Scoring → Re-ranked Results (Top 5)

Models:
    - ms-marco-MiniLM-L-6-v2: Fast, good accuracy
    - ms-marco-MiniLM-L-12-v2: Slower, better accuracy
"""

import os
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import structlog

logger = structlog.get_logger()


@dataclass
class RerankedResult:
    """Result after cross-encoder re-ranking"""
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    original_score: float
    rerank_score: float
    final_score: float
    rank_change: int  # Positive = moved up, Negative = moved down

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "metadata": self.metadata,
            "original_score": self.original_score,
            "rerank_score": self.rerank_score,
            "final_score": self.final_score,
            "rank_change": self.rank_change
        }


class CrossEncoderReranker:
    """
    Cross-Encoder Re-ranker for improving search result precision.

    Uses a cross-encoder model that jointly encodes query and document
    to produce more accurate relevance scores.
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        rerank_weight: float = 0.7,
        original_weight: float = 0.3,
        max_length: int = 512
    ):
        """
        Initialize the cross-encoder re-ranker.

        Args:
            model_name: HuggingFace model name for cross-encoder
            rerank_weight: Weight for cross-encoder score in final score
            original_weight: Weight for original score in final score
            max_length: Maximum sequence length for cross-encoder
        """
        self.model_name = model_name
        self.rerank_weight = rerank_weight
        self.original_weight = original_weight
        self.max_length = max_length
        self._model = None

        logger.info(
            "cross_encoder_reranker_initialized",
            model=model_name,
            rerank_weight=rerank_weight,
            original_weight=original_weight
        )

    @property
    def model(self):
        """Lazy load cross-encoder model"""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.model_name, max_length=self.max_length)
                logger.info("cross_encoder_model_loaded", model=self.model_name)
            except ImportError:
                logger.warning(
                    "cross_encoder_import_failed",
                    message="Install sentence-transformers: pip install sentence-transformers"
                )
            except Exception as e:
                logger.error("cross_encoder_load_failed", error=str(e))
        return self._model

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5,
        content_field: str = "content",
        score_field: str = "final_score"
    ) -> List[RerankedResult]:
        """
        Re-rank candidates using cross-encoder.

        Args:
            query: Search query
            candidates: List of candidate results with content and scores
            top_k: Number of results to return after re-ranking
            content_field: Field name containing document content
            score_field: Field name containing original score

        Returns:
            List of RerankedResult objects
        """
        if not candidates:
            return []

        # Store original ranks
        original_ranks = {
            self._get_id(c, i): i for i, c in enumerate(candidates)
        }

        # Get cross-encoder scores
        rerank_scores = self._get_rerank_scores(query, candidates, content_field)

        # Calculate final scores
        results = []
        for i, (candidate, rerank_score) in enumerate(zip(candidates, rerank_scores)):
            original_score = candidate.get(score_field, 0.0)

            # Normalize rerank score to 0-1 range (cross-encoder outputs can be negative)
            normalized_rerank = self._normalize_score(rerank_score)

            # Combine scores
            final_score = (
                self.rerank_weight * normalized_rerank +
                self.original_weight * original_score
            )

            chunk_id = self._get_id(candidate, i)

            results.append(RerankedResult(
                chunk_id=chunk_id,
                content=candidate.get(content_field, "")[:500],  # Truncate for response
                metadata=candidate.get("metadata", {}),
                original_score=original_score,
                rerank_score=normalized_rerank,
                final_score=final_score,
                rank_change=0  # Will be calculated after sorting
            ))

        # Sort by final score
        results.sort(key=lambda x: x.final_score, reverse=True)

        # Calculate rank changes
        for new_rank, result in enumerate(results):
            old_rank = original_ranks.get(result.chunk_id, new_rank)
            result.rank_change = old_rank - new_rank

        # Return top_k
        results = results[:top_k]

        logger.info(
            "reranking_complete",
            query_length=len(query),
            candidates=len(candidates),
            returned=len(results),
            avg_rank_change=np.mean([abs(r.rank_change) for r in results]) if results else 0
        )

        return results

    def _get_rerank_scores(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        content_field: str
    ) -> List[float]:
        """Get cross-encoder scores for query-document pairs"""
        if self.model is None:
            # Fallback: use original scores if model not available
            logger.warning("cross_encoder_not_available_using_fallback")
            return [c.get("final_score", 0.5) for c in candidates]

        # Prepare query-document pairs
        pairs = []
        for candidate in candidates:
            content = candidate.get(content_field, "")
            # Truncate content to avoid exceeding max_length
            content = content[:1000] if len(content) > 1000 else content
            pairs.append((query, content))

        try:
            # Get scores from cross-encoder
            scores = self.model.predict(pairs, show_progress_bar=False)
            return scores.tolist() if hasattr(scores, 'tolist') else list(scores)
        except Exception as e:
            logger.error("cross_encoder_predict_failed", error=str(e))
            return [0.5] * len(candidates)

    def _normalize_score(self, score: float) -> float:
        """Normalize cross-encoder score to 0-1 range using sigmoid"""
        # Cross-encoder scores can range from -10 to +10
        # Use sigmoid to normalize
        import math
        return 1 / (1 + math.exp(-score))

    def _get_id(self, candidate: Dict[str, Any], index: int) -> str:
        """Get or generate ID for candidate"""
        return candidate.get("chunk_id", candidate.get("id", f"candidate_{index}"))

    def batch_rerank(
        self,
        queries: List[str],
        candidates_list: List[List[Dict[str, Any]]],
        top_k: int = 5
    ) -> List[List[RerankedResult]]:
        """
        Batch re-ranking for multiple queries.

        Args:
            queries: List of search queries
            candidates_list: List of candidate lists (one per query)
            top_k: Number of results per query

        Returns:
            List of re-ranked result lists
        """
        results = []
        for query, candidates in zip(queries, candidates_list):
            reranked = self.rerank(query, candidates, top_k)
            results.append(reranked)

        logger.info(
            "batch_reranking_complete",
            queries=len(queries),
            total_candidates=sum(len(c) for c in candidates_list)
        )

        return results


class RerankerWithFallback:
    """
    Re-ranker with fallback to simple scoring if cross-encoder unavailable.
    """

    def __init__(self):
        self.cross_encoder = None
        self._init_attempted = False

    def _lazy_init(self):
        """Lazy initialize cross-encoder"""
        if self._init_attempted:
            return
        self._init_attempted = True

        try:
            self.cross_encoder = CrossEncoderReranker()
            # Test if model loads
            _ = self.cross_encoder.model
        except Exception as e:
            logger.warning("cross_encoder_init_failed_using_fallback", error=str(e))
            self.cross_encoder = None

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Re-rank with fallback to keyword boosting if cross-encoder unavailable.
        """
        self._lazy_init()

        if self.cross_encoder and self.cross_encoder.model:
            # Use cross-encoder
            results = self.cross_encoder.rerank(query, candidates, top_k)
            return [r.to_dict() for r in results]
        else:
            # Fallback: boost scores based on keyword overlap
            return self._keyword_boost_rerank(query, candidates, top_k)

    def _keyword_boost_rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Simple keyword-based re-ranking as fallback"""
        query_words = set(query.lower().split())

        for candidate in candidates:
            content = candidate.get("content", "").lower()
            content_words = set(content.split())

            # Calculate keyword overlap
            overlap = len(query_words & content_words)
            keyword_boost = overlap / len(query_words) if query_words else 0

            # Boost original score
            original_score = candidate.get("final_score", 0.5)
            candidate["rerank_score"] = keyword_boost
            candidate["final_score"] = 0.7 * original_score + 0.3 * keyword_boost

        # Sort by final score
        candidates.sort(key=lambda x: x.get("final_score", 0), reverse=True)

        logger.info("fallback_reranking_complete", method="keyword_boost")

        return candidates[:top_k]


# Global instances
cross_encoder_reranker = CrossEncoderReranker()
reranker_with_fallback = RerankerWithFallback()
