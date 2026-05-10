from dataclasses import dataclass, field
from typing import Optional
from datetime import UTC, datetime

@dataclass
class AAOIFIDocument:
    """AAOIFI standard document model."""
    document_id: str
    title: str
    content: str
    standard_number: Optional[str] = None
    standard_type: str = "FAS"
    source_url: Optional[str] = None
    acquired_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: str = "1.0"
    status: str = "active"
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.content or not self.content.strip():
            raise ValueError("Document content cannot be empty")
        if not self.document_id or not self.document_id.strip():
            raise ValueError("Document ID cannot be empty")
        if not self.title or not self.title.strip():
            raise ValueError("Document title cannot be empty")

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "title": self.title,
            "content": self.content,
            "standard_number": self.standard_number,
            "standard_type": self.standard_type,
            "source_url": self.source_url,
            "acquired_at": self.acquired_at.isoformat(),
            "version": self.version,
            "status": self.status,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AAOIFIDocument":
        data["acquired_at"] = datetime.fromisoformat(data["acquired_at"])
        return cls(**data)
