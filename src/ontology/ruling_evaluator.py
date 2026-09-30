"""Evaluate ontology contexts into conservative ruling results."""
from __future__ import annotations

from typing import Iterable, List

from src.models.commercial import ContractFamily
from src.models.ruling import PartyRole, RulingContext, RulingResult, Permissibility
from src.ontology.concept_ontology import ConceptOntology, ConditionalRuling


class RulingFunctionEvaluator:
    def __init__(self, ontology: ConceptOntology | None = None) -> None:
        self.ontology = ontology or ConceptOntology.load()

    def evaluate(self, context: RulingContext, source_chunks: Iterable[str] = ()) -> RulingResult:
        try:
            entry = self.ontology.get(context.concept)
        except KeyError:
            return RulingResult(permissibility=Permissibility.INSUFFICIENT_DATA,
                                requires_scholar_review=True, source_chunks=list(source_chunks))
        matches = [
            item
            for item in entry.conditional_rulings
            if self._matches(item, context)
        ]
        if not matches:
            return RulingResult(
                permissibility=Permissibility.INSUFFICIENT_DATA,
                requires_scholar_review=True,
                source_chunks=list(source_chunks),
            )
        required = list(dict.fromkeys(condition for rule in matches for condition in rule.conditions))
        conditions_met, conditions_unknown = self._condition_status(required, context.conditions)
        # Legacy ontology entries carry no versioned scholar signoff. Their
        # labels and standards remain useful for routing, never verdict authority.
        return RulingResult(
            permissibility=Permissibility.INSUFFICIENT_DATA,
            applicable_standards=list(dict.fromkeys(standard for rule in matches for standard in rule.applicable_standards)),
            conditions_met=conditions_met,
            conditions_unknown=conditions_unknown,
            requires_scholar_review=True,
            source_chunks=list(source_chunks),
        )

    @staticmethod
    def _matches(rule: ConditionalRuling, context: RulingContext) -> bool:
        if rule.contract_type not in {context.contract_type, ContractFamily.UNKNOWN}:
            return False
        if rule.party_role not in {context.party_role, PartyRole.UNKNOWN}:
            return False
        return True

    @staticmethod
    def _condition_status(required: List[str], provided: List[str]) -> tuple[List[str], List[str]]:
        provided_text = {condition.strip().casefold() for condition in provided}
        met = [condition for condition in required if condition.strip().casefold() in provided_text]
        unknown = [condition for condition in required if condition not in met]
        return met, unknown
