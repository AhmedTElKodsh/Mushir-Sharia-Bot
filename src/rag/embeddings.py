from typing import List, Optional
from src.config.logging_config import setup_logging

logger = setup_logging()

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
BATCH_SIZE = 32
EXPECTED_DIM = 768


class EmbeddingGenerator:
    """Generate embeddings. Delegates to EmbeddingService for consistency."""

    def __init__(self, model_name: str = MODEL_NAME):
        from src.rag.embedding_service import EmbeddingService

        self._service = EmbeddingService(model_name)

    @property
    def model(self):
        return self._service.model

    def embed_text(self, text: str) -> List[float]:
        return self._service.embed_text(text)

    def embed_batch(self, texts: List[str], batch_size: Optional[int] = None, show_progress: bool = True) -> List[List[float]]:
        try:
            return self._service.embed_batch(texts, batch_size=batch_size or BATCH_SIZE, show_progress=show_progress)
        except Exception as exc:
            logger.error("Embedding batch failed: %s", exc)
            return []

    def embed_chunks(self, chunks: list) -> list:
        from src.rag.embedding_service import EmbeddingService

        texts = [c.content for c in chunks]
        embeddings = self.embed_batch(texts)
        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding = emb
        logger.info(f"Embedded {len(chunks)} chunks")
        return chunks
