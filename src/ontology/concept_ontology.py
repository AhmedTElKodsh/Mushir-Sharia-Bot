"""Loader for YAML concept ontology nodes."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, List, Mapping, Optional

import yaml

from src.models.commercial import ContractFamily
from src.models.ruling import PartyRole, Permissibility
from src.rag.query_preprocessor import QueryPreprocessor


DEFAULT_ONTOLOGY_DIR = Path("data/concept_ontology")


@dataclass(frozen=True)
class ConditionalRuling:
    contract_type: ContractFamily
    party_role: PartyRole = PartyRole.UNKNOWN
    ruling: Permissibility = Permissibility.INSUFFICIENT_DATA
    conditions: List[str] = field(default_factory=list)
    exceptions: List[Mapping[str, Any]] = field(default_factory=list)
    applicable_standards: List[str] = field(default_factory=list)
    key_question: Optional[str] = None
    scholar_notes: str = ""


@dataclass(frozen=True)
class ConceptOntologyEntry:
    concept_id: str
    labels_en: List[str] = field(default_factory=list)
    labels_ar: List[str] = field(default_factory=list)
    transliterations: List[str] = field(default_factory=list)
    synonyms: List[str] = field(default_factory=list)
    conditional_rulings: List[ConditionalRuling] = field(default_factory=list)

    @property
    def terms(self) -> set[str]:
        values = self.labels_en + self.labels_ar + self.transliterations + self.synonyms
        return {QueryPreprocessor.normalize(value).lower() for value in values if value.strip()}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ConceptOntologyEntry":
        concept_id = str(payload.get("concept_id") or "").strip()
        if not concept_id:
            raise ValueError("concept_id is required")
        contexts = []
        for item in payload.get("conditional_rulings") or payload.get("ruling_by_context") or []:
            context = item.get("context") or {}
            contexts.append(
                ConditionalRuling(
                    contract_type=_contract_family(context.get("contract_type")),
                    party_role=_party_role(context.get("party_role")),
                    ruling=_permissibility(item.get("ruling")),
                    conditions=_list(item, "conditions"),
                    exceptions=item.get("exceptions") or item.get("exception") or [],
                    applicable_standards=_list(item, "applicable_standards"),
                    key_question=item.get("key_question"),
                    scholar_notes=str(item.get("scholar_notes") or ""),
                )
            )
        return cls(
            concept_id=concept_id,
            labels_en=_list(payload, "labels_en"),
            labels_ar=_list(payload, "labels_ar") + _list(payload, "arabic_terms"),
            transliterations=_list(payload, "transliterations"),
            synonyms=_list(payload, "synonyms"),
            conditional_rulings=contexts,
        )


class ConceptOntology:
    def __init__(self, entries: Iterable[ConceptOntologyEntry]) -> None:
        self._entries = {entry.concept_id: entry for entry in entries}

    @classmethod
    def load(cls, directory: Path | str = DEFAULT_ONTOLOGY_DIR) -> "ConceptOntology":
        root = Path(directory)
        if not root.exists():
            return cls([])
        entries = [
            ConceptOntologyEntry.from_mapping(_read_yaml(path))
            for path in sorted(root.glob("*.yaml"))
        ]
        return cls(entries)

    def get(self, concept_id: str) -> ConceptOntologyEntry:
        return self._entries[concept_id]

    def all(self) -> List[ConceptOntologyEntry]:
        return list(self._entries.values())

    def match(self, query: str) -> List[ConceptOntologyEntry]:
        normalized = QueryPreprocessor.normalize(query or "").lower()
        expanded = QueryPreprocessor.expand_terms(query or "")
        matches: List[ConceptOntologyEntry] = []
        for entry in self._entries.values():
            if any(term in normalized or term in expanded for term in entry.terms):
                matches.append(entry)
        return matches

    def generate_domain_query_expansions(self) -> dict[str, tuple[str, ...]]:
        """Generate expansion dict for the QueryPreprocessor from ontology synonyms."""
        expansions = {}
        for entry in self.all():
            terms = entry.terms
            for term in terms:
                # Map every term to all terms in the concept cluster
                expansions[term] = tuple(sorted(list(terms)))
        return expansions


def _read_yaml(path: Path) -> Mapping[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, Mapping):
        raise ValueError(f"ontology node must be a mapping: {path}")
    return payload


def _list(payload: Mapping[str, Any], key: str) -> List[str]:
    value = payload.get(key) or []
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list")
    return [str(item) for item in value]


def _contract_family(value: Any) -> ContractFamily:
    if not value:
        return ContractFamily.UNKNOWN
    value = str(value).strip().lower()
    if value == "murabahah":
        value = "murabaha"
    return ContractFamily(value)


def _party_role(value: Any) -> PartyRole:
    return PartyRole(str(value or PartyRole.UNKNOWN.value).strip().lower())


def _permissibility(value: Any) -> Permissibility:
    return Permissibility(str(value or Permissibility.INSUFFICIENT_DATA.value).strip().upper())
