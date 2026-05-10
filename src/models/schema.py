"""
Data models for L0 RAG pipeline.
Minimal schema for proving the RAG loop works end-to-end.
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AAOIFICitation:
    """Citation to an AAOIFI standard section."""
    standard_id: str          # e.g. "FAS-28"
    section: Optional[str]    # e.g. "3.2"
    page: Optional[int]
    source_file: str


@dataclass
class SemanticChunk:
    """A semantically coherent chunk of AAOIFI text."""
    chunk_id: str
    text: str
    citation: AAOIFICitation
    score: float = 0.0


@dataclass
class ComplianceRuling:
    """Final compliance ruling with citations."""
    question: str
    answer: str
    chunks: List[SemanticChunk] = field(default_factory=list)
    confidence: float = 0.0
