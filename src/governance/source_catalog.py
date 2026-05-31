"""Authoritative source-catalog records for answer admissibility."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from src.models.commercial import SourceFamily


class MetadataStatus(str, Enum):
    QUARANTINED_MISSING_CATALOG = "quarantined_missing_catalog"
    CATALOGED = "cataloged"
    CATALOGED_NOT_ANSWER_ADMISSIBLE = "cataloged_not_answer_admissible"


class SourceType(str, Enum):
    OFFICIAL_PAGE = "official_page"
    DERIVED_MARKDOWN = "derived_markdown"
    CONVERTED_PDF = "converted_pdf"
    MANUAL_TEXT = "manual_text"


class SourceCurrentness(str, Enum):
    CURRENT = "current"
    SUPERSEDED = "superseded"
    UNVERIFIED = "unverified"


class SourceReviewStatus(str, Enum):
    UNREVIEWED = "unreviewed"
    MACHINE_CHECKED = "machine_checked"
    HUMAN_REVIEWED = "human_reviewed"


class SourceConfidence(str, Enum):
    OFFICIAL = "official"
    DERIVED_FROM_OFFICIAL = "derived_from_official"
    UNVERIFIED = "unverified"


ANSWER_ADMISSIBLE_CONFIDENCE = {
    SourceConfidence.OFFICIAL.value,
    SourceConfidence.DERIVED_FROM_OFFICIAL.value,
}
ANSWER_ADMISSIBLE_REVIEW_STATUS = {
    SourceReviewStatus.MACHINE_CHECKED.value,
    SourceReviewStatus.HUMAN_REVIEWED.value,
}


def is_answer_admissible_metadata(
    metadata: Mapping[str, Any],
    *,
    require_governed_metadata: bool = False,
) -> bool:
    """Return whether retrieved chunk metadata may support an answer.

    Legacy indexes are allowed unless explicitly quarantined. When strict
    governance is enabled, catalog currentness, confidence, and review status
    become hard answer gates.
    """
    status = str(metadata.get("metadata_status") or "").strip().lower()
    if status == MetadataStatus.QUARANTINED_MISSING_CATALOG.value:
        return False
    if status == MetadataStatus.CATALOGED_NOT_ANSWER_ADMISSIBLE.value:
        return False
    if not require_governed_metadata:
        return True
    if status != MetadataStatus.CATALOGED.value:
        return False
    if str(metadata.get("source_currentness") or "").strip().lower() != SourceCurrentness.CURRENT.value:
        return False
    if str(metadata.get("source_confidence") or "").strip().lower() not in ANSWER_ADMISSIBLE_CONFIDENCE:
        return False
    if str(metadata.get("review_status") or "").strip().lower() not in ANSWER_ADMISSIBLE_REVIEW_STATUS:
        return False
    if str(metadata.get("superseded_by") or "").strip():
        return False
    return True


class SourceRelationshipType(str, Enum):
    SUPERSEDES = "supersedes"
    AMENDS = "amends"
    REPLACES = "replaces"
    CLARIFIES = "clarifies"
    CONTEXTUALIZES = "contextualizes"


@dataclass(frozen=True)
class SourceCatalogRecord:
    """Catalog entry that proves a chunk's authority lineage."""

    source_id: str
    source_family: SourceFamily
    standard_number: str
    title_en: str
    language: str
    official_url: str
    acquired_at: date
    extraction_method: str
    source_type: SourceType
    currentness: SourceCurrentness = SourceCurrentness.UNVERIFIED
    review_status: SourceReviewStatus = SourceReviewStatus.UNREVIEWED
    source_confidence: SourceConfidence = SourceConfidence.UNVERIFIED
    title_ar: Optional[str] = None
    derived_path: Optional[str] = None
    supersedes: List[str] = field(default_factory=list)
    superseded_by: List[str] = field(default_factory=list)
    paired_source_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id is required")
        if not self.standard_number.strip():
            raise ValueError("standard_number is required")
        if self.language not in {"en", "ar"}:
            raise ValueError("language must be 'en' or 'ar'")
        if not self.official_url.startswith(("https://", "http://")):
            raise ValueError("official_url must be an HTTP(S) URL")
        if self.currentness == SourceCurrentness.SUPERSEDED and not self.superseded_by:
            raise ValueError("superseded records must name superseded_by")

    @property
    def is_answer_admissible(self) -> bool:
        return (
            self.currentness == SourceCurrentness.CURRENT
            and self.source_confidence
            in {SourceConfidence.OFFICIAL, SourceConfidence.DERIVED_FROM_OFFICIAL}
            and self.review_status
            in {SourceReviewStatus.MACHINE_CHECKED, SourceReviewStatus.HUMAN_REVIEWED}
        )

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "SourceCatalogRecord":
        data = dict(payload)
        data["source_family"] = SourceFamily(data["source_family"])
        data["source_type"] = SourceType(data["source_type"])
        data["currentness"] = SourceCurrentness(data.get("currentness", SourceCurrentness.UNVERIFIED))
        data["review_status"] = SourceReviewStatus(data.get("review_status", SourceReviewStatus.UNREVIEWED))
        data["source_confidence"] = SourceConfidence(
            data.get("source_confidence", SourceConfidence.UNVERIFIED)
        )
        acquired = data["acquired_at"]
        data["acquired_at"] = date.fromisoformat(acquired) if isinstance(acquired, str) else acquired
        return cls(**data)

    def to_chunk_metadata(self, source_file: str, chunk_index: int, total_chunks: int) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_family": self.source_family.value,
            "standard_number": self.standard_number,
            "language": self.language,
            "source_language": self.language,
            "title_en": self.title_en,
            "title_ar": self.title_ar,
            "official_url": self.official_url,
            "source_file": source_file,
            "source_path": self.derived_path or source_file,
            "chunk_idx": chunk_index,
            "total_chunks": total_chunks,
            "source_currentness": self.currentness.value,
            "source_confidence": self.source_confidence.value,
            "review_status": self.review_status.value,
            "superseded_by": ",".join(self.superseded_by),
        }


@dataclass(frozen=True)
class DocumentVersionRecord:
    """Versioned extraction record tied to a catalog source."""

    document_id: str
    source_id: str
    corpus_version: str
    index_version: str
    extraction_hash: str
    version_status: SourceCurrentness
    acquired_at: date
    extraction_method: str
    effective_date: Optional[date] = None
    publication_date: Optional[date] = None
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            raise ValueError("document_id is required")
        if not self.source_id.strip():
            raise ValueError("source_id is required")
        if not self.corpus_version.strip():
            raise ValueError("corpus_version is required")
        if not self.index_version.strip():
            raise ValueError("index_version is required")
        if not self.extraction_hash.strip():
            raise ValueError("extraction_hash is required")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "DocumentVersionRecord":
        data = dict(payload)
        data["version_status"] = SourceCurrentness(data["version_status"])
        for key in ("acquired_at", "effective_date", "publication_date"):
            value = data.get(key)
            if isinstance(value, str):
                data[key] = date.fromisoformat(value)
        return cls(**data)


@dataclass(frozen=True)
class SourceRelationshipRecord:
    """Reviewed or candidate relationship between two source records."""

    relationship_id: str
    source_id: str
    related_source_id: str
    relationship_type: SourceRelationshipType
    review_status: SourceReviewStatus = SourceReviewStatus.UNREVIEWED
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.relationship_id.strip():
            raise ValueError("relationship_id is required")
        if not self.source_id.strip():
            raise ValueError("source_id is required")
        if not self.related_source_id.strip():
            raise ValueError("related_source_id is required")
        if self.source_id == self.related_source_id:
            raise ValueError("source relationship cannot point to itself")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "SourceRelationshipRecord":
        data = dict(payload)
        data["relationship_type"] = SourceRelationshipType(data["relationship_type"])
        data["review_status"] = SourceReviewStatus(
            data.get("review_status", SourceReviewStatus.UNREVIEWED)
        )
        return cls(**data)


class SourceCatalog:
    """In-memory source catalog with strict lookup helpers."""

    def __init__(
        self,
        records: Iterable[SourceCatalogRecord] = (),
        document_versions: Iterable[DocumentVersionRecord] = (),
        relationships: Iterable[SourceRelationshipRecord] = (),
    ) -> None:
        self._records: Dict[str, SourceCatalogRecord] = {}
        self._document_versions: Dict[str, DocumentVersionRecord] = {}
        self._relationships: Dict[str, SourceRelationshipRecord] = {}
        for record in records:
            self.add(record)
        for version in document_versions:
            self.add_document_version(version)
        for relationship in relationships:
            self.add_relationship(relationship)

    def add(self, record: SourceCatalogRecord) -> None:
        if record.source_id in self._records:
            raise ValueError(f"duplicate source_id: {record.source_id}")
        self._records[record.source_id] = record

    def add_document_version(self, version: DocumentVersionRecord) -> None:
        if version.source_id not in self._records:
            raise KeyError(f"unknown source_id: {version.source_id}")
        if version.document_id in self._document_versions:
            raise ValueError(f"duplicate document_id: {version.document_id}")
        self._document_versions[version.document_id] = version

    def add_relationship(self, relationship: SourceRelationshipRecord) -> None:
        for source_id in (relationship.source_id, relationship.related_source_id):
            if source_id not in self._records:
                raise KeyError(f"unknown source_id: {source_id}")
        if relationship.relationship_id in self._relationships:
            raise ValueError(f"duplicate relationship_id: {relationship.relationship_id}")
        self._relationships[relationship.relationship_id] = relationship

    def get(self, source_id: str) -> SourceCatalogRecord:
        try:
            return self._records[source_id]
        except KeyError as exc:
            raise KeyError(f"unknown source_id: {source_id}") from exc

    def document_version(self, document_id: str) -> DocumentVersionRecord:
        try:
            return self._document_versions[document_id]
        except KeyError as exc:
            raise KeyError(f"unknown document_id: {document_id}") from exc

    def document_versions_for_source(self, source_id: str) -> List[DocumentVersionRecord]:
        self.get(source_id)
        return [
            version
            for version in self._document_versions.values()
            if version.source_id == source_id
        ]

    def relationships_for_source(self, source_id: str) -> List[SourceRelationshipRecord]:
        self.get(source_id)
        return [
            relationship
            for relationship in self._relationships.values()
            if relationship.source_id == source_id
        ]

    def find_by_path(self, path: str | Path) -> SourceCatalogRecord:
        normalized = _normalize_catalog_path(path)
        matches = [
            record
            for record in self._records.values()
            if record.derived_path and _catalog_paths_match(record.derived_path, normalized)
        ]
        if not matches:
            raise KeyError(f"no catalog record for path: {normalized}")
        if len(matches) > 1:
            raise ValueError(f"multiple catalog records for path: {normalized}")
        return matches[0]

    def admissible_records(self, family: Optional[SourceFamily] = None) -> List[SourceCatalogRecord]:
        return [
            record
            for record in self._records.values()
            if record.is_answer_admissible and (family is None or record.source_family == family)
        ]

    def validate_chunk_metadata(self, metadata: Mapping[str, Any]) -> List[str]:
        problems: List[str] = []
        source_id = str(metadata.get("source_id") or "")
        if not source_id:
            return ["missing source_id"]
        try:
            record = self.get(source_id)
        except KeyError:
            return [f"unknown source_id: {source_id}"]
        expected = {
            "source_family": record.source_family.value,
            "standard_number": record.standard_number,
            "language": record.language,
            "source_currentness": record.currentness.value,
        }
        for key, value in expected.items():
            if metadata.get(key) != value:
                problems.append(f"{key} mismatch")
        if not record.is_answer_admissible:
            problems.append("source is not answer-admissible")
        return problems

    @classmethod
    def from_records(cls, payload: Iterable[Mapping[str, Any]]) -> "SourceCatalog":
        return cls(SourceCatalogRecord.from_mapping(item) for item in payload)

    @classmethod
    def from_payload(
        cls,
        *,
        records: Iterable[Mapping[str, Any]],
        document_versions: Iterable[Mapping[str, Any]] = (),
        relationships: Iterable[Mapping[str, Any]] = (),
    ) -> "SourceCatalog":
        return cls(
            (SourceCatalogRecord.from_mapping(item) for item in records),
            document_versions=(
                DocumentVersionRecord.from_mapping(item) for item in document_versions
            ),
            relationships=(
                SourceRelationshipRecord.from_mapping(item) for item in relationships
            ),
        )


def _normalize_catalog_path(path: str | Path) -> str:
    return str(path).replace("\\", "/").lstrip("./")


def _catalog_paths_match(record_path: str | Path, requested_path: str | Path) -> bool:
    record = _normalize_catalog_path(record_path)
    requested = _normalize_catalog_path(requested_path)
    return (
        record == requested
        or record.endswith(f"/{requested}")
        or requested.endswith(f"/{record}")
    )


def default_candidate_supersession_relationships() -> List[SourceRelationshipRecord]:
    """Unverified supersession candidates from the 2026-05-19 research pass."""
    return [
        SourceRelationshipRecord(
            relationship_id="candidate-fas-02-superseded-by-fas-28",
            source_id="aaoifi-fas-02-en",
            related_source_id="aaoifi-fas-28-en",
            relationship_type=SourceRelationshipType.SUPERSEDES,
            review_status=SourceReviewStatus.UNREVIEWED,
            notes="Candidate Murabaha supersession edge from research report; catalog verification required.",
        ),
        SourceRelationshipRecord(
            relationship_id="candidate-fas-20-contextualized-by-fas-32",
            source_id="aaoifi-fas-20-en",
            related_source_id="aaoifi-fas-32-en",
            relationship_type=SourceRelationshipType.CONTEXTUALIZES,
            review_status=SourceReviewStatus.UNREVIEWED,
            notes="Candidate Ijarah relationship from research report; catalog verification required.",
        ),
    ]
