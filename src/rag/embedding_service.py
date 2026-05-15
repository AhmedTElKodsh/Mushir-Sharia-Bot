"""Embedding generation service."""
from typing import List, Optional
from functools import lru_cache


class EmbeddingService:
    """Handles text embedding generation with caching."""

    BATCH_SIZE = 32

    def __init__(self, model_name: str):
        """Initialize embedding service with a specific model."""
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        """Lazy-load the embedding model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            print(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_text(self, text: str, normalize: bool = True) -> List[float]:
        """Generate embedding for a single text string."""
        if not text:
            return []
        return self.model.encode(text, normalize_embeddings=normalize).tolist()

    def embed_batch(self, texts: List[str], batch_size: Optional[int] = None, show_progress: bool = False) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        if not texts:
            return []
        batch = batch_size or self.BATCH_SIZE
        embeddings = self.model.encode(texts, batch_size=batch, normalize_embeddings=True, show_progress_bar=show_progress)
        return embeddings.tolist()

    @lru_cache(maxsize=500)
    def embed_query_cached(self, query: str) -> tuple:
        """Cache embeddings for frequently repeated queries."""
        embedding = self.embed_text(query, normalize=True)
        return tuple(embedding)

    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a query with caching."""
        return list(self.embed_query_cached(query))

    @staticmethod
    def is_multilingual(model_name: str) -> bool:
        """Check if a model supports multilingual embeddings."""
        return "multilingual" in model_name.lower()
