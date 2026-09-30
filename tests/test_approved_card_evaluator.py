"""Synthetic review metadata exercises mechanics; these are not approved rulings."""
import pytest

from src.governance.rule_cards import RuleCard
from src.models.evidence import EvidenceScope, FactObservation, FactSnapshot, UserTurnProvenance, SourceProvenance
from src.ontology.approved_card_evaluator import ApprovedCardEvaluator

NOW = "2026-09-30T12:00:00+02:00"
SCOPE = EvidenceScope(lane="personal", transaction_id="fixture", document_scope="schedule")


def card(**changes):
    data = dict(rule_id="synthetic-test-only", version=1, source_authority="client_rulebook",
                source_anchor="test fixture only", applies_to_archetypes=["fixture-arc"],
                material_facts=["fee"], outcomes=[dict(when={"fee": False}, outcome="no_issue_under_this_rule")],
                unknown_fact_question="Is there a fee?", precedence_note="fixture only",
                scholar_signoff=dict(reviewer_id="fixture-reviewer", date="2026-09-30", decision="approved"),
                status="approved")
    return RuleCard(**(data | changes))


def fact(slot, value, **changes):
    source = UserTurnProvenance(session_id="s1", turn_id="t1", exact_text="fixture assertion",
                                recorded_at=NOW, version=1, scope=SCOPE)
    status = "user_reported"
    if slot == "mechanism_archetype":
        # Synthetic documentary annotation for mechanics only, not real approval.
        source = SourceProvenance(capture=dict(source_id="fixture-mechanism", url="https://example.org/fixture",
            captured_at=NOW, sha256="a" * 64, document_version="v1", content_type="text/plain",
            language="en", access_status="accessible"), document_class="transaction_specific_disclosure",
            exact_text="Synthetic fixture mechanism description", span_id="fixture-mechanism", scope=SCOPE)
        status = "observed"
    return FactObservation(**(dict(slot=slot, value=value, scope=SCOPE, version=1,
                                   recorded_at=NOW, status=status, source=source) | changes))


def evaluate(*facts, cards=None, **changes):
    snapshot = FactSnapshot(snapshot_id="snapshot", version=1, recorded_at=NOW,
                            facts=(fact("mechanism_archetype", "fixture-arc"), *facts))
    return ApprovedCardEvaluator([card()] if cards is None else cards).evaluate(
        snapshot, scope=SCOPE, session_id="s1", expected_snapshot_version=1, **changes)


def test_complete_fixture_yields_only_rule_scoped_outcome():
    result = evaluate(fact("fee", False))
    assert result.status == "evaluated"
    assert result.outcome == "no_issue_under_this_rule"
    assert result.rule.rule_id == "synthetic-test-only"
    assert result.snapshot_version == 1


def test_user_reported_archetype_cannot_authorize_rule_selection():
    source = UserTurnProvenance(session_id="s1", turn_id="t1", exact_text="I call this fixture-arc",
                               recorded_at=NOW, version=1, scope=SCOPE)
    mechanism = fact("mechanism_archetype", "fixture-arc", source=source, status="user_reported")
    snapshot = FactSnapshot(snapshot_id="snapshot", version=1, recorded_at=NOW,
                            facts=(mechanism, fact("fee", False)))
    result = ApprovedCardEvaluator([card()]).evaluate(snapshot, scope=SCOPE, session_id="s1", expected_snapshot_version=1)
    assert result.status == "insufficient_data"
    assert result.reason == "mechanism_not_documented"
    assert result.outcome is None


@pytest.mark.parametrize("status", ["draft", "superseded"])
def test_ineligible_cards_never_evaluate(status):
    assert evaluate(fact("fee", False), cards=[card(status=status)]).status == "insufficient_data"


def test_missing_fact_unknown_not_false():
    result = evaluate()
    assert result.status == "clarification_needed"
    assert result.unknown_facts == ("fee",)
    assert result.outcome is None
    assert result.question == "Is there a fee?"


@pytest.mark.parametrize("value", [0, 0.0, "False", True])
def test_no_coercion_or_implicit_opposite_outcome(value):
    result = evaluate(fact("fee", value))
    assert result.status == "insufficient_data"
    assert result.outcome is None


def test_all_material_facts_required_even_when_branch_omits_one():
    result = evaluate(fact("fee", False), cards=[card(material_facts=["fee", "beneficiary"])])
    assert result.unknown_facts == ("beneficiary",)
    assert result.outcome is None
    assert result.question is None
    assert result.status == "insufficient_data"


def test_clarification_targets_remaining_unknown():
    result = evaluate(fact("fee", False), cards=[card(material_facts=["fee", "beneficiary"],
                      unknown_fact_questions={"beneficiary": "Who receives the fee?"})])
    assert result.question == "Who receives the fee?"
    assert result.status == "clarification_needed"
    assert result.question_slot == "beneficiary"


def test_question_slot_is_its_actual_target_not_first_unknown():
    result = evaluate(cards=[card(material_facts=["fee", "beneficiary"],
                      unknown_fact_questions={"beneficiary": "Who receives the fee?"})])
    assert result.unknown_facts == ("fee", "beneficiary")
    assert result.question_slot == "beneficiary"


def test_ambiguous_rules_do_not_pick_first():
    result = evaluate(fact("fee", False), cards=[card(), card(rule_id="another-fixture")])
    assert result.status == "insufficient_data"
    assert result.reason == "multiple_applicable_rules"


def test_cross_session_fact_rejected():
    item = fact("fee", False)
    item = item.model_copy(update={"source": item.source.model_copy(update={"session_id": "other"})})
    assert evaluate(item).reason == "invalid_fact_provenance"


def test_exhausted_clarification_abstains():
    assert evaluate(clarification_exhausted=True).status == "insufficient_data"


def test_future_fact_version_abstains():
    assert evaluate(fact("fee", False, version=2)).reason == "invalid_fact_provenance"


def test_unknown_archetype_does_not_match_by_card_order():
    snapshot = FactSnapshot(snapshot_id="snapshot", version=1, recorded_at=NOW, facts=(fact("fee", False),))
    result = ApprovedCardEvaluator([card()]).evaluate(snapshot, scope=SCOPE, session_id="s1", expected_snapshot_version=1)
    assert result.outcome is None
    assert result.reason == "mechanism_unknown"


def test_stale_snapshot_rejected():
    snapshot = FactSnapshot(snapshot_id="snapshot", version=2, recorded_at=NOW)
    result = ApprovedCardEvaluator([card()]).evaluate(snapshot, scope=SCOPE, session_id="s1", expected_snapshot_version=1)
    assert result.reason == "snapshot_version_mismatch"


def test_conflicting_fact_cannot_be_resolved_by_matching_one_candidate():
    item = fact("fee", False)
    conflict = item.model_copy(update={"status": "conflicting", "value": None, "source": None,
                                      "candidates": [dict(status="user_reported", value=value, source=item.source)
                                                     for value in (False, True)]})
    result = evaluate(conflict)
    assert result.reason == "conflicting_material_facts"
    assert result.conflicting_facts == ("fee",)


def test_other_transaction_cannot_fill_missing_fact():
    other = SCOPE.model_copy(update={"transaction_id": "other"})
    item = fact("fee", False)
    item = item.model_copy(update={"scope": other, "source": item.source.model_copy(update={"scope": other})})
    assert evaluate(item).unknown_facts == ("fee",)


def test_future_observation_cannot_support_outcome():
    assert evaluate(fact("fee", False, recorded_at="2026-10-01T00:00:00Z")).reason == "invalid_fact_provenance"


def test_arbitrary_outcome_text_is_not_a_verdict():
    result = evaluate(fact("fee", False), cards=[card(outcomes=[dict(when={"fee": False}, outcome="globally_halal")])])
    assert result.reason == "unsupported_outcome"


@pytest.mark.parametrize("change,reason", [
    ({"document_version": "v2"}, "mixed_source_versions"),
    ({"sha256": "b" * 64}, "inconsistent_capture_manifest"),
])
def test_inconsistent_sources_abstain(change, reason):
    capture = dict(source_id="fixture", url="https://example.org/fixture", captured_at=NOW,
                   sha256="a" * 64, document_version="v1", content_type="text/plain",
                   language="en", access_status="accessible")
    def observed(slot, value, changes):
        source = SourceProvenance(capture=capture | changes, document_class="transaction_specific_disclosure",
                                  exact_text="fixture", span_id=slot, scope=SCOPE)
        return fact(slot, value, source=source, status="observed")
    snapshot = FactSnapshot(snapshot_id="fixture", version=1, recorded_at=NOW, facts=(
        observed("mechanism_archetype", "fixture-arc", {}), observed("fee", False, change)))
    result = ApprovedCardEvaluator([card()]).evaluate(snapshot, scope=SCOPE, session_id="s1", expected_snapshot_version=1)
    assert result.reason == reason
