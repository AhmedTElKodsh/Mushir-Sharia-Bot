"""Evaluate one approved rule against scoped evidence, never a global verdict.

Callers supply trusted, locally loaded cards and a reconciled fact snapshot.
Review metadata is not authentication. No extraction or precedence is invented.
"""
from __future__ import annotations

from typing import Iterable, Literal

from src.governance.rule_cards import RuleCard, load_rule_cards
from src.models.evidence import (
    EvidenceModel, EvidenceScope, FactObservation, FactSnapshot, RuleReference,
    SourceProvenance, Text, UserTurnProvenance, Version,
)


class RuleEvaluation(EvidenceModel):
    status: Literal["evaluated", "clarification_needed", "insufficient_data"]
    reason: Text
    snapshot_id: Text
    snapshot_version: Version
    rule: RuleReference | None = None
    outcome: Literal["no_issue_under_this_rule", "impermissible_under_this_rule", "conditional"] | None = None
    unknown_facts: tuple[Text, ...] = ()
    conflicting_facts: tuple[Text, ...] = ()
    question: Text | None = None
    question_slot: Text | None = None
    supporting_facts: tuple[FactObservation, ...] = ()


class ApprovedCardEvaluator:
    def __init__(self, cards: Iterable[RuleCard] = ()):
        # Revalidate even in-memory inputs, including duplicate approved versions.
        self.cards = tuple(card for card in load_rule_cards(
            [card.model_dump() for card in cards]) if card.runtime_eligible)

    def evaluate(self, snapshot: FactSnapshot, *, scope: EvidenceScope,
                 session_id: str, expected_snapshot_version: int,
                 clarification_exhausted: bool = False) -> RuleEvaluation:
        snapshot = FactSnapshot.model_validate(snapshot)
        scope = EvidenceScope.model_validate(scope)

        def result(reason, status="insufficient_data", **details):
            return RuleEvaluation(status=status, reason=reason, snapshot_id=snapshot.snapshot_id,
                                  snapshot_version=snapshot.version, **details)

        if type(expected_snapshot_version) is not int or snapshot.version != expected_snapshot_version:
            return result("snapshot_version_mismatch")
        facts = {fact.slot: fact for fact in snapshot.facts if fact.scope == scope}

        def valid(fact):
            if fact.version > snapshot.version or fact.recorded_at > snapshot.recorded_at:
                return False
            source = fact.source
            if isinstance(source, UserTurnProvenance):
                return (source.session_id == session_id and source.version <= fact.version
                        and source.recorded_at <= fact.recorded_at)
            if isinstance(source, SourceProvenance):
                return (source.capture.captured_at <= fact.recorded_at
                        and source.document_class in {"provider_standard_terms", "transaction_specific_disclosure",
                                                      "user_supplied_schedule", "donated_agreement"})
            return False

        mechanism = facts.get("mechanism_archetype")
        if mechanism is None or mechanism.status == "unknown":
            return result("mechanism_unknown")
        if mechanism.status == "conflicting":
            return result("mechanism_conflicting", conflicting_facts=("mechanism_archetype",))
        if not valid(mechanism) or type(mechanism.value) is not str:
            return result("invalid_fact_provenance")
        if (mechanism.status != "observed" or not isinstance(mechanism.source, SourceProvenance)
                or mechanism.source.document_class not in {
                    "provider_standard_terms", "transaction_specific_disclosure", "donated_agreement"}):
            return result("mechanism_not_documented")
        applicable = [card for card in self.cards if mechanism.value in card.applies_to_archetypes]
        if not applicable:
            return result("no_approved_applicable_rule")
        if len(applicable) != 1:
            return result("multiple_applicable_rules")
        card = applicable[0]
        reference = RuleReference(rule_id=card.rule_id, version=card.version)
        unknown = tuple(slot for slot in card.material_facts
                        if slot not in facts or facts[slot].status == "unknown")
        conflicts = tuple(slot for slot in card.material_facts
                          if slot in facts and facts[slot].status == "conflicting")
        if conflicts:
            return result("conflicting_material_facts", rule=reference, unknown_facts=unknown,
                          conflicting_facts=conflicts)
        known = [facts[slot] for slot in card.material_facts if slot not in unknown]
        if any(not valid(fact) for fact in known):
            return result("invalid_fact_provenance", rule=reference)
        manifests = {}
        source_versions = {}
        for fact in (mechanism, *known):
            if isinstance(fact.source, SourceProvenance):
                capture = fact.source.capture
                identity = (capture.source_id, capture.captured_at, capture.document_version)
                if identity in manifests and manifests[identity] != capture:
                    return result("inconsistent_capture_manifest", rule=reference)
                if capture.source_id in source_versions and source_versions[capture.source_id] != capture.document_version:
                    return result("mixed_source_versions", rule=reference)
                manifests[identity] = capture
                source_versions[capture.source_id] = capture.document_version
        if unknown:
            question_slot = next((slot for slot in unknown if slot in card.unknown_fact_questions), None)
            question = card.unknown_fact_questions[question_slot] if question_slot else None
            if question is None and len(card.material_facts) == 1:
                question = card.unknown_fact_question
                question_slot = unknown[0]
            if question is not None and (question.count("?") + question.count("؟") != 1
                                         or "\n" in question or "\r" in question):
                question = None
            return result("missing_material_facts", rule=reference, unknown_facts=unknown,
                          status="insufficient_data" if clarification_exhausted or question is None else "clarification_needed",
                          question=None if clarification_exhausted else question,
                          question_slot=question_slot if question is not None and not clarification_exhausted else None)
        matches = [outcome for outcome in card.outcomes if all(
            type(facts[slot].value) is type(expected) and facts[slot].value == expected
            for slot, expected in outcome.when.items())]
        if len(matches) != 1:
            return result("no_unique_outcome", rule=reference)
        outcome = matches[0].outcome
        if outcome not in {"no_issue_under_this_rule", "impermissible_under_this_rule", "conditional"}:
            return result("unsupported_outcome", rule=reference)
        return result("approved_rule_evaluated", status="evaluated", rule=reference, outcome=outcome,
                      supporting_facts=(mechanism, *known))
