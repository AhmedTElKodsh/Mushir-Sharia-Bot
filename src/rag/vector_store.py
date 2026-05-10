import chromadb
from chromadb.config import Settings
from typing import List, Optional, Dict, Any
from src.models.chunk import SemanticChunk
from src.config.logging_config import setup_logging

logger = setup_logging()

COLLECTION_NAME = "aaoifi_standards"
DISTANCE_METRIC = "cosine"

class VectorStore:
    """Chroma vector database for AAOIFI standards."""

    def __init__(self, persist_dir: str = "./data/chroma"):
        self.client = chromadb.PersistentClient(path=persist_dir, settings=Settings(allow_reset=True))
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": DISTANCE_METRIC},
        )
        logger.info(f"Chroma store initialized: {persist_dir}")

    def store_chunks(self, chunks: List[SemanticChunk]) -> None:
        """Store chunks with embeddings."""
        ids = [c.chunk_id for c in chunks]
        embeddings = [c.embedding for c in chunks]
        documents = [c.content for c in chunks]
        metadatas = [
            {
                "document_id": c.document_id,
                "chunk_index": c.chunk_index,
                "token_count": c.token_count,
                **c.metadata,
            }
            for c in chunks
        ]
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(f"Stored {len(chunks)} chunks in Chroma")

    def similarity_search(
        self, query_embedding: List[float], k: int = 5, threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Retrieve top-k similar chunks."""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
        )
        chunks = []
        for i, (chunk_id, doc, meta, dist) in enumerate(
            zip(results["ids"][0], results["documents"][0], results["metadatas"][0], results["distances"][0])
        ):
            similarity = 1 - dist  # cosine distance to similarity
            if similarity >= threshold:
                chunks.append({
                    "chunk_id": chunk_id,
                    "content": doc,
                    "metadata": meta,
                    "similarity": similarity,
                })
        logger.info(f"Retrieved {len(chunks)} chunks (threshold={threshold})")
        return chunks

    def search_by_metadata(self, filters: Dict[str, Any], k: int = 10) -> List[Dict]:
        """Search chunks by metadata filters."""
        where = {}
        for key, value in filters.items():
            where[key] = value
        results = self.collection.get(where=where, limit=k)
        return [
            {"chunk_id": rid, "content": rdoc, "metadata": rmeta}
            for rid, rdoc, rmeta in zip(results["ids"], results["documents"], results["metadatas"])
        ]

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        count = self.collection.count()
        return {"collection": COLLECTION_NAME, "chunk_count": count}
