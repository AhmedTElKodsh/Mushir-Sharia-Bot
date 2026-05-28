"""Structured parent/child chunk metadata for governed ingestion."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from src.governance.source_catalog import SourceCatalogRecord


def _join_values(values: Sequence[str]) -> str:
    return ", ".join(value for value in values if value)


@dataclass(frozen=True)
class ParentChildChunkMetadataBuilder:
    """Build Chroma-compatible metadata for source-governed child chunks."""

    source_file: str
    standard_number: str
    language: str
    embedding_model: str
    embedding_normalized: bool
    total_chunks: int
    catalog_record: Optional[SourceCatalogRecord] = None
    document_version_id: str = ""
    source_language: Optional[str] = None
    source_path: str = ""
    supersession_status: str = "unverified"
    operation_tags: List[str] = field(default_factory=list)

    def child_metadata(
        self,
        *,
        chunk_index: int,
        section_path: Sequence[str],
        operation_tags: Sequence[str] = (),
        citation_anchor: str = "",
    ) -> Dict[str, Any]:
        base = self.catalog_record.to_chunk_metadata(
            self.source_file,
            chunk_index,
            self.total_chunks,
        ) if self.catalog_record else self._uncataloged_base(chunk_index)
        section_parts = [part.strip() for part in section_path if part and part.strip()]
        parent_chunk_id = self.parent_chunk_id(section_parts)
        tags = list(self.operation_tags) + list(operation_tags)
        # Resolve contract_family from standard_number using query_intent hints
        from src.models.query_intent import AAOIFI_HINTS_BY_CONTRACT
        contract_family = "UNKNOWN"
        for classification, standards in AAOIFI_HINTS_BY_CONTRACT.items():
            if self.standard_number in standards:
                contract_family = classification.value
                break
                
        base.update(
            {
                "document_version_id": self.document_version_id,
                "parent_chunk_id": parent_chunk_id,
                "child_chunk_id": f"{parent_chunk_id}:{chunk_index}",
                "section_path": " > ".join(section_parts),
                "section_depth": len(section_parts),
                "citation_anchor": citation_anchor,
                "operation_tags": _join_values(tags),
                "embedding_model": self.embedding_model,
                "embedding_normalized": self.embedding_normalized,
                "metadata_status": self._metadata_status(),
                "contract_family": contract_family,
            }
        )
        return base

    def parent_chunk_id(self, section_path: Sequence[str]) -> str:
        stable_source = Path(self.source_file).stem
        stable_section = "-".join(
            part.strip().replace(" ", "-").replace("/", "-") for part in section_path if part.strip()
        )
        return f"{stable_source}:{stable_section or 'full-document'}"

    def _uncataloged_base(self, chunk_index: int) -> Dict[str, Any]:
        return {
            "source_id": "",
            "source_family": "",
            "standard_number": self.standard_number,
            "language": self.language,
            "source_language": self.source_language or self.language,
            "source_file": self.source_file,
            "source_path": self.source_path or self.source_file,
            "chunk_idx": chunk_index,
            "total_chunks": self.total_chunks,
            "source_currentness": self.supersession_status,
            "source_confidence": "unverified",
            "review_status": "unreviewed",
            "superseded_by": "",
        }

    def _metadata_status(self) -> str:
        if not self.catalog_record:
            return "quarantined_missing_catalog"
        if self.catalog_record.is_answer_admissible:
            return "cataloged"
        return "cataloged_not_answer_admissible"
