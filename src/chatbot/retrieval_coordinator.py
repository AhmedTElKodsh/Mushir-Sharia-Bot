"""Coordinates retrieval with caching and query filtering."""
import json
from typing import Any, List, Optional
from src.rag.query_preprocessor import QueryPreprocessor
from src.storage.cache import CacheStore


# Terms that should skip retrieval
AUTHORITY_REQUEST_TERMS = (
    "fatwa", "fatwah", "ruling", "legal opinion", "binding opinion",
    "is this halal", "is this haram", "give me a fatwa",
    "فتوى", "حكم شرعي", "رأي ملزم",
)

META_EVALUATION_TERMS = ("what if the answer cites", "retrieved sources only contain")

UNDER_SPECIFIED_INVESTMENT_TERMS = (
    ("do not know", "business activity"),
    ("do not know", "debt ratios"),
    ("unknown", "business activity"),
    ("unknown", "debt ratios"),
)

ARABIC_UNDER_SPECIFIED_TERMS = (
    ("لم تكن", "النشاط"),
    ("غير معروفة", "النشاط"),
)


class RetrievalCoordinator:
    """Coordinates retrieval with caching and query filtering."""

    def __init__(
        self,
        retriever,
        cache_store: Optional[CacheStore] = None,
        enable_query_cache: bool = True,
        query_cache_ttl: int = 3600,
    ):
        """Initialize retrieval coordinator.
        
        Args:
            retriever: RAG pipeline instance
            cache_store: Optional cache store for query results
            enable_query_cache: Whether to cache query results
            query_cache_ttl: TTL for cached query results in seconds
        """
        self.retriever = retriever
        self.cache_store = cache_store
        self.enable_query_cache = enable_query_cache
        self.query_cache_ttl = query_cache_ttl

    def retrieve(
        self,
        query: str,
        k: int = 5,
        threshold: float = 0.3,
        allow_low_confidence_fallback: bool = False,
    ) -> List[Any]:
        """Retrieve chunks with caching and filtering.
        
        Args:
            query: User query
            k: Number of chunks to retrieve
            threshold: Minimum similarity threshold
            allow_low_confidence_fallback: Allow low-confidence results for diagnostics
            
        Returns:
            List of retrieved chunks
        """
        # Check if query should skip retrieval
        if self._should_skip_retrieval(query):
            return []

        # Check cache first
        if self.enable_query_cache and self.cache_store:
            cached = self._get_cached_results(query, k, threshold)
            if cached is not None:
                return cached

        # Retrieve from vector store
        chunks = self.retriever.retrieve(
            query,
            k=k,
            threshold=threshold,
            allow_low_confidence_fallback=allow_low_confidence_fallback,
        )

        # Cache results
        if self.enable_query_cache and self.cache_store and chunks:
            self._cache_results(query, k, threshold, chunks)

        return chunks

    def _should_skip_retrieval(self, query: str) -> bool:
        """Check if query should skip retrieval (needs refusal or clarification)."""
        lowered = query.lower()
        
        # Authority requests
        if any(term in lowered for term in AUTHORITY_REQUEST_TERMS):
            return True
        
        # Meta-evaluation queries
        if any(term in lowered for term in META_EVALUATION_TERMS):
            return True
        
        # Under-specified investment queries
        if any(all(term in lowered for term in terms) for terms in UNDER_SPECIFIED_INVESTMENT_TERMS):
            return True
        
        # Arabic under-specified queries
        if any(all(term in query for term in terms) for terms in ARABIC_UNDER_SPECIFIED_TERMS):
            return True
        
        return False

    def _get_cached_results(self, query: str, k: int, threshold: float) -> Optional[List[Any]]:
        """Get cached retrieval results."""
        cache_key = self._cache_key(query, k, threshold)
        cached_json = self.cache_store.get_json("retrieval", cache_key)
        
        if not cached_json:
            return None
        
        # Reconstruct chunks from cached data
        from src.models.schema import SemanticChunk, AAOIFICitation
        
        chunks = []
        for chunk_data in cached_json:
            citation = AAOIFICitation(
                standard_id=chunk_data["citation"]["standard_id"],
                section=chunk_data["citation"].get("section"),
                page=chunk_data["citation"].get("page"),
                source_file=chunk_data["citation"]["source_file"],
            )
            chunk = SemanticChunk(
                chunk_id=chunk_data["chunk_id"],
                text=chunk_data["text"],
                citation=citation,
                score=chunk_data["score"],
            )
            chunks.append(chunk)
        
        return chunks

    def _cache_results(self, query: str, k: int, threshold: float, chunks: List[Any]) -> None:
        """Cache retrieval results."""
        cache_key = self._cache_key(query, k, threshold)
        
        # Serialize chunks to JSON
        chunks_data = []
        for chunk in chunks:
            chunk_data = {
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "citation": {
                    "standard_id": chunk.citation.standard_id,
                    "section": chunk.citation.section,
                    "page": chunk.citation.page,
                    "source_file": chunk.citation.source_file,
                },
                "score": chunk.score,
            }
            chunks_data.append(chunk_data)
        
        self.cache_store.set_json("retrieval", cache_key, chunks_data, self.query_cache_ttl)

    def _cache_key(self, query: str, k: int, threshold: float) -> str:
        """Generate cache key for retrieval results."""
        # Normalize query for consistent caching
        normalized = QueryPreprocessor.normalize(query.strip().lower())
        
        payload = {
            "query": normalized,
            "k": k,
            "threshold": threshold,
            "retriever": type(self.retriever).__name__,
        }
        
        return CacheStore.stable_key(json.dumps(payload, sort_keys=True))
