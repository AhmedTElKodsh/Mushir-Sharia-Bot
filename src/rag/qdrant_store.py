"""Qdrant vector store adapter for L3 production retrieval."""
from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List, Optional

from src.config.logging_config import setup_logging
from src.models.chunk import SemanticChunk

logger = setup_logging()

DEFAULT_COLLECTION = "aaoifi_standards"
DEFAULT_VECTOR_SIZE = 768


class QdrantVectorStore:
    """Production vector store with the same interface as the Chroma adapter."""

    def __init__(
        self,
        location: Optional[str] = None,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        collection_name: Optional[str] = None,
        vector_size: int = DEFAULT_VECTOR_SIZE,
    ):
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
        except ImportError as exc:
            raise RuntimeError("qdrant-client is required when VECTOR_DB_TYPE=qdrant") from exc

        self.collection_name = collection_name or os.getenv("QDRANT_COLLECTION", DEFAULT_COLLECTION)
        self.vector_size = int(os.getenv("QDRANT_VECTOR_SIZE", str(vector_size)))
        client_location = location or os.getenv("QDRANT_LOCATION")
        if client_location:
            self.client = QdrantClient(
                location=client_location,
                api_key=api_key or os.getenv("QDRANT_API_KEY") or None,
                timeout=float(os.getenv("QDRANT_TIMEOUT_SECONDS", "10")),
            )
        else:
            self.client = QdrantClient(
                url=url or os.getenv("QDRANT_URL", "http://localhost:6333"),
                api_key=api_key or os.getenv("QDRANT_API_KEY") or None,
                timeout=float(os.getenv("QDRANT_TIMEOUT_SECONDS", "10")),
            )
        try:
            self.client.get_collection(self.collection_name)
        except Exception:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            )
        logger.info(f"Qdrant store initialized: collection={self.collection_name}")

    def store_chunks(self, chunks: List[SemanticChunk]) -> None:
        from qdrant_client.models import PointStruct

        points = [
            PointStruct(
                id=self._point_id(chunk.chunk_id),
                vector=chunk.embedding or [],
                payload={
                    "chunk_id": chunk.chunk_id,
                    "content": chunk.content,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "token_count": chunk.token_count,
                    **chunk.metadata,
                },
            )
            for chunk in chunks
        ]
        self.client.upsert(collection_name=self.collection_name, points=points)
        logger.info(f"Stored {len(points)} chunks in Qdrant")

    def similarity_search(
        self,
        query_embedding: List[float],
        k: int = 5,
        threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        try:
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                limit=k,
            )
        except Exception as exc:
            logger.error(f"Qdrant similarity search failed: {exc}")
            raise RuntimeError("Qdrant retrieval failed") from exc

        chunks: List[Dict[str, Any]] = []
        for point in results.points:
            score = float(point.score or 0.0)
            if score < threshold:
                continue
            payload = dict(point.payload or {})
            content = str(payload.pop("content", ""))
            chunk_id = str(payload.pop("chunk_id", point.id))
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "content": content,
                    "metadata": payload,
                    "similarity": score,
                }
            )
        logger.info(f"Retrieved {len(chunks)} Qdrant chunks (threshold={threshold})")
        return chunks

    def get_collection_stats(self) -> Dict[str, Any]:
        info = self.client.get_collection(self.collection_name)
        return {
            "collection": self.collection_name,
            "chunk_count": int(info.points_count or 0),
            "backend": "qdrant",
        }

    @staticmethod
    def _point_id(chunk_id: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"mushir:aaoifi:{chunk_id}"))
