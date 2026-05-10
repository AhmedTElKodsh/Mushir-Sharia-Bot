from sentence_transformers import SentenceTransformer
from typing import List, Optional
import numpy as np
from src.config.logging_config import setup_logging

logger = setup_logging()

MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
BATCH_SIZE = 32
EXPECTED_DIM = 768

class EmbeddingGenerator:
    """Generate embeddings using sentence-transformers."""

    def __init__(self, model_name: str = MODEL_NAME):
        try:
            self.model = SentenceTransformer(model_name)
            actual_dim = self.model.get_sentence_embedding_dimension()
            if actual_dim != EXPECTED_DIM:
                logger.warning(f"Model dimension {actual_dim} != expected {EXPECTED_DIM}")
            logger.info(f"Loaded embedding model: {model_name} (dim={actual_dim})")
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for single text."""
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: List[str], batch_size: int = BATCH_SIZE) -> List[List[float]]:
        """Generate embeddings for batch of texts."""
        embeddings = self.model.encode(texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=True)
        return embeddings.tolist()

    def embed_chunks(self, chunks: list) -> list:
        """Embed semantic chunks and attach embeddings."""
        texts = [c.content for c in chunks]
        embeddings = self.embed_batch(texts)
        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding = emb
        logger.info(f"Embedded {len(chunks)} chunks")
        return chunks
