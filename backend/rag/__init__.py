"""RAG (Retrieval Augmented Generation) components"""
from .weaviate_client import weaviate_client
from .neo4j_client import neo4j_client
from .hybrid_search import hybrid_rag

# Enhanced RAG components (v2.0)
from .hybrid_search_engine import hybrid_search_engine, HybridSearchEngine, SearchWeights
from .cross_encoder_reranker import cross_encoder_reranker, reranker_with_fallback
from .smart_chunker import smart_chunker, SmartChunker, Chunk
from .embedding_service import embedding_service, EmbeddingService
from .feedback_optimizer import feedback_optimizer, FeedbackOptimizer

__all__ = [
    # Core clients
    "weaviate_client",
    "neo4j_client",
    "hybrid_rag",
    # Enhanced search
    "hybrid_search_engine",
    "HybridSearchEngine",
    "SearchWeights",
    # Re-ranking
    "cross_encoder_reranker",
    "reranker_with_fallback",
    # Chunking
    "smart_chunker",
    "SmartChunker",
    "Chunk",
    # Embeddings
    "embedding_service",
    "EmbeddingService",
    # Feedback
    "feedback_optimizer",
    "FeedbackOptimizer",
]
