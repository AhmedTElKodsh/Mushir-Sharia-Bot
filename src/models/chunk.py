from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class SemanticChunk:
    """Semantic chunk of AAOIFI standard document."""
    chunk_id: str
    document_id: str
    content: str
    chunk_index: int
    token_count: int
    embedding: Optional[List[float]] = None
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.content or not self.content.strip():
            raise ValueError("Chunk content cannot be empty")
        if self.token_count < 50 or self.token_count > 512:
            raise ValueError(f"Token count {self.token_count} outside valid range [50, 512]")
        if self.embedding and len(self.embedding) != 768:
            raise ValueError(f"Embedding dimension {len(self.embedding)} != 768")

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "content": self.content,
            "chunk_index": self.chunk_index,
            "token_count": self.token_count,
            "embedding": self.embedding,
            "metadata": self.metadata,
        }
