"""Qdrant vector store adapter for L3 production retrieval."""
from __future__ import annotations

import os
import re
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
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        try:
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                limit=self._query_limit(k, filters),
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
            if filters and not self._metadata_matches_filters(payload, filters):
                continue
            content = str(payload.pop("content", ""))
            chunk_id = str(payload.pop("chunk_id", point.id))
            payload = self._normalized_payload_metadata(payload)
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "content": content,
                    "metadata": payload,
                    "similarity": score,
                }
            )
        logger.info(f"Retrieved {len(chunks)} Qdrant chunks (threshold={threshold})")
        return chunks[:k]

    @classmethod
    def _normalized_payload_metadata(cls, metadata: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(metadata)
        family = normalized.get("source_family") or cls._infer_source_family(normalized)
        if family:
            normalized["source_family"] = family
        aliases = cls._standard_aliases(normalized)
        normalized_standard = next(
            (alias for alias in aliases if re.fullmatch(r"(SS|FAS)-\d{2,3}", str(alias))),
            None,
        )
        if normalized_standard:
            normalized.setdefault("raw_standard_number", normalized.get("standard_number"))
            normalized["standard_number"] = normalized_standard
        if "source_language" not in normalized and normalized.get("language"):
            normalized["source_language"] = normalized["language"]
        return normalized

    @staticmethod
    def _query_limit(k: int, filters: Optional[Dict[str, Any]]) -> int:
        if not filters:
            return k
        return max(k * int(os.getenv("QDRANT_FILTER_OVERFETCH_MULTIPLIER", "5")), k)

    @staticmethod
    def _metadata_matches_filters(metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        for key, expected in filters.items():
            actual = QdrantVectorStore._filter_value(metadata, key)
            if actual is None:
                return False
            if isinstance(expected, (list, tuple, set, frozenset)):
                actual_values = {str(value).lower() for value in QdrantVectorStore._as_values(actual)}
                expected_values = {str(value).lower() for value in expected}
                if actual_values.isdisjoint(expected_values):
                    return False
                continue
            if str(actual).lower() != str(expected).lower():
                return False
        return True

    @staticmethod
    def _filter_value(metadata: Dict[str, Any], key: str) -> Any:
        if key == "source_family":
            return metadata.get(key) or QdrantVectorStore._infer_source_family(metadata)
        if key == "standard_number":
            return QdrantVectorStore._standard_aliases(metadata)
        actual = metadata.get(key)
        if actual is not None:
            return actual
        return None

    @staticmethod
    def _as_values(value: Any) -> List[Any]:
        if isinstance(value, (list, tuple, set, frozenset)):
            return list(value)
        return [value]

    @staticmethod
    def _infer_source_family(metadata: Dict[str, Any]) -> Optional[str]:
        haystack = " ".join(
            str(metadata.get(key, ""))
            for key in ("standard_number", "source_file", "document_title")
        ).lower()
        if "sharia" in haystack or "shari" in haystack:
            return "sharia_standard"
        if "financial_accounting" in haystack or "accounting" in haystack or "fas" in haystack:
            return "fas"
        return None

    @staticmethod
    def _standard_aliases(metadata: Dict[str, Any]) -> List[str]:
        raw_values = [
            str(metadata.get(key, ""))
            for key in ("standard_number", "source_file", "document_title")
            if metadata.get(key)
        ]
        aliases = set(raw_values)
        for raw in raw_values:
            upper = raw.upper()
            explicit = re.search(r"\b(SS|FAS)[-_\s]*0*(\d{1,3})\b", upper)
            if explicit:
                aliases.add(f"{explicit.group(1)}-{int(explicit.group(2)):02d}")
                continue
            numeric = re.search(r"AAOIFI_STANDARD_0*(\d{1,3})_", upper)
            if numeric:
                family = QdrantVectorStore._infer_source_family(
                    {**metadata, "standard_number": raw}
                )
                prefix = "SS" if family == "sharia_standard" else "FAS" if family == "fas" else None
                if prefix:
                    aliases.add(f"{prefix}-{int(numeric.group(1)):02d}")
        return sorted(aliases)

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
