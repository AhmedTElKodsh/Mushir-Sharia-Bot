"""Route ontology concepts to eligible Shari'ah standards."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Mapping, Optional

import yaml

from src.models.commercial import ContractFamily
from src.models.ruling import PartyRole
from src.ontology.concept_ontology import ConceptOntology, ConceptOntologyEntry, ConditionalRuling


DEFAULT_SOURCE_CATALOG = Path("data/source_registry/aaoifi-source-catalog.yaml")


@dataclass(frozen=True)
class OntologyRouteResult:
    concepts: List[str] = field(default_factory=list)
    standard_ids: List[str] = field(default_factory=list)
    ruling_conditions: List[str] = field(default_factory=list)
    party_roles: List[PartyRole] = field(default_factory=list)
    key_questions: List[str] = field(default_factory=list)


class ConceptOntologyRouter:
    def __init__(
        self,
        ontology: Optional[ConceptOntology] = None,
        source_catalog_path: Path | str = DEFAULT_SOURCE_CATALOG,
    ) -> None:
        self.ontology = ontology or ConceptOntology.load()
        self._current_standards = _current_standards(Path(source_catalog_path))

    def route(
        self,
        contract_type: ContractFamily,
        concepts: List[ConceptOntologyEntry],
    ) -> OntologyRouteResult:
        matched_contexts: List[tuple[ConceptOntologyEntry, ConditionalRuling]] = []
        for concept in concepts:
            for context in concept.conditional_rulings:
                if context.contract_type in {contract_type, ContractFamily.UNKNOWN}:
                    matched_contexts.append((concept, context))
        return OntologyRouteResult(
            concepts=sorted({concept.concept_id for concept, _ in matched_contexts}),
            standard_ids=sorted({
                standard
                for _, context in matched_contexts
                for standard in context.applicable_standards
                if standard in self._current_standards
            }),
            ruling_conditions=sorted({
                condition
                for _, context in matched_contexts
                for condition in context.conditions
            }),
            party_roles=sorted(
                {context.party_role for _, context in matched_contexts},
                key=lambda role: role.value,
            ),
            key_questions=[
                context.key_question
                for _, context in matched_contexts
                if context.key_question
            ],
        )

    def route_query(self, query: str, contract_type: ContractFamily) -> OntologyRouteResult:
        return self.route(contract_type, self.ontology.match(query))


def _current_standards(path: Path) -> set[str]:
    if not path.exists():
        return set()
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    records = payload.get("records") or []
    standards = set()
    for record in records:
        if not isinstance(record, Mapping):
            continue
        if str(record.get("currentness") or "").lower() != "current":
            continue
        if str(record.get("source_family") or "").lower() != "sharia_standard":
            continue
        standards.add(str(record.get("standard_number") or ""))
    return standards
