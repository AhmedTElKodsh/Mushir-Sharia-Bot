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
        matches = [
            item
            for item in self.ontology.get(context.concept).conditional_rulings
            if self._matches(item, context)
        ]
        if not matches:
            return RulingResult(
                permissibility=Permissibility.INSUFFICIENT_DATA,
                confidence=0.0,
                requires_scholar_review=True,
                source_chunks=list(source_chunks),
            )
        rule = matches[0]
        conditions_met, conditions_violated = self._condition_status(rule.conditions, context.conditions)
        confidence = 0.82 if not conditions_violated else 0.62
        return RulingResult(
            permissibility=rule.ruling,
            confidence=confidence,
            applicable_standards=rule.applicable_standards,
            conditions_met=conditions_met,
            conditions_violated=conditions_violated,
            requires_scholar_review=confidence < 0.75 or rule.ruling == Permissibility.DISPUTED,
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
        provided_text = " | ".join(provided).lower()
        met = [condition for condition in required if condition.lower() in provided_text]
        violated = [condition for condition in required if condition not in met]
        return met, violated
