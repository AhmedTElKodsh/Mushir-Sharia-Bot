"""Rule loading validates metadata without approving or evaluating rules."""
from copy import deepcopy

import pytest
import yaml
from pydantic import ValidationError

from src.governance.rule_cards import RuleCard, approved_rule_cards, load_rule_cards


def card(**changes):
    data = dict(rule_id="riba-late-payment-benefit-v1", version=1,
                source_authority="client_rulebook", source_anchor="file section paragraph",
                applies_to_archetypes=["ARC-CF", "ARC-SELLER", "ARC-BANK-ISL"],
                material_facts=["late_fee_exists", "late_fee_beneficiary", "late_fee_basis"],
                outcomes=[dict(when={"late_fee_exists": False}, outcome="no_issue_under_this_rule"),
                          dict(when={"late_fee_exists": True, "late_fee_beneficiary": "financier"}, outcome="impermissible_under_this_rule"),
                          dict(when={"late_fee_exists": True, "late_fee_beneficiary": "charity"}, outcome="conditional")],
                unknown_fact_question="Who receives the fee?", precedence_note=None,
                scholar_signoff=dict(reviewer_id=None, date=None, decision="pending"), status="draft")
    data.update(changes)
    return data


def approved(**changes):
    data = card(status="approved", precedence_note="Explicit reviewed relation to source rules",
                scholar_signoff=dict(reviewer_id="scholar-1", date="2026-09-30", decision="approved"))
    data.update(changes)
    return data


def test_pending_and_superseded_load_without_runtime_eligibility():
    data = [card(), card(version=2, status="superseded")]
    assert len(load_rule_cards(data)) == 2
    assert approved_rule_cards(data) == ()
    assert data[0]["scholar_signoff"]["decision"] == "pending"


@pytest.mark.parametrize("questions", [
    {"undeclared": "What is missing?"},
    {"late_fee_exists": "First? Second?"},
    {"late_fee_exists": "First?\nSecond"},
])
def test_slot_questions_require_material_target_and_one_question(questions):
    with pytest.raises(ValidationError):
        load_rule_cards(card(unknown_fact_questions=questions))


def test_slot_question_mapping_is_immutable():
    loaded = load_rule_cards(card(unknown_fact_questions={"late_fee_exists": "Is there a late fee?"}))[0]
    with pytest.raises(TypeError):
        loaded.unknown_fact_questions["late_fee_exists"] = "Replacement?"


def test_approved_metadata_round_trip_and_version_history(tmp_path):
    data = [card(status="superseded"), approved(version=2)]
    path = tmp_path / "cards.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    cards = load_rule_cards(path)
    assert len(cards) == 2
    assert approved_rule_cards(path) == (cards[1],)
    assert RuleCard.model_validate_json(cards[1].model_dump_json()) == cards[1]
    assert cards[1].outcomes[0].when["late_fee_exists"] is False


@pytest.mark.parametrize("changes", [
    {"status": "approved"}, {"version": 0}, {"version": True}, {"version": "1"},
    {"source_authority": "provider_claim"}, {"source_anchor": " "},
    {"material_facts": []}, {"extra": "do not drop"},
    {"outcomes": [dict(when={"undeclared": True}, outcome="conditional")]},
    {"scholar_signoff": dict(reviewer_id=None, date=None, decision="approved")},
])
def test_malformed_cards_fail(changes):
    with pytest.raises(ValidationError):
        load_rule_cards(card(**changes))


@pytest.mark.parametrize("changes", [
    {"precedence_note": None}, {"precedence_note": " "},
    {"scholar_signoff": dict(reviewer_id="scholar", date="2026-09-30", decision="pending")},
    {"scholar_signoff": dict(reviewer_id="auto", date="2026-09-30", decision="approved")},
    {"scholar_signoff": dict(reviewer_id="scholar", date=None, decision="approved")},
])
def test_approved_cards_require_full_signoff_and_precedence(changes):
    with pytest.raises(ValidationError):
        load_rule_cards(approved(**changes))


def test_duplicate_versions_and_ambiguous_approved_history_fail():
    for data in ([card(), card()], [approved(), approved(version=2)]):
        with pytest.raises(ValueError):
            load_rule_cards(data)


@pytest.mark.parametrize("text", [
    "rule_id: one\nrule_id: two\n", "when: {fee: true, fee: false}",
    "base: &base {version: 1}\ncard: {<<: *base}\n", "when: {true: 1, 1: 2}",
    "!!python/object/apply:os.system ['echo unsafe']", "null", "123", "[one, two]",
])
def test_unsafe_or_ambiguous_yaml_fails(tmp_path, text):
    path = tmp_path / "bad.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises((ValueError, yaml.YAMLError)):
        load_rule_cards(path)


def test_immutable_nested_conditions_and_validated_copy():
    original = card()
    before = deepcopy(original)
    item = load_rule_cards(original)[0]
    original["outcomes"][0]["when"]["late_fee_exists"] = True
    assert item.outcomes[0].when["late_fee_exists"] is False
    assert item.model_dump()["outcomes"][0]["when"] == before["outcomes"][0]["when"]
    with pytest.raises(TypeError):
        item.outcomes[0].when["late_fee_exists"] = True
    with pytest.raises(ValidationError):
        item.model_copy(update={"status": "approved"})


def test_zero_and_bool_conditions_survive_without_coercion():
    item = load_rule_cards(card(material_facts=["fee"], outcomes=[dict(when={"fee": 0}, outcome="placeholder")]))[0]
    restored = RuleCard.model_validate_json(item.model_dump_json())
    assert type(restored.outcomes[0].when["fee"]) is int


def test_overlapping_outcomes_cannot_be_resolved_by_row_order():
    with pytest.raises(ValidationError, match="overlapping"):
        load_rule_cards(card(material_facts=["fee", "beneficiary"], outcomes=[
            dict(when={"fee": True}, outcome="first"),
            dict(when={"fee": True, "beneficiary": "financier"}, outcome="second"),
        ]))


@pytest.mark.parametrize("ambiguity", ["top", "condition", "merge"])
def test_complete_yaml_cards_reject_ambiguity_at_parser(tmp_path, ambiguity):
    path = tmp_path / "complete.yaml"
    valid = yaml.safe_dump(card())
    path.write_text(valid, encoding="utf-8")
    assert len(load_rule_cards(path)) == 1
    if ambiguity == "top":
        invalid = valid + "status: approved\n"
        error = "duplicate YAML key: status"
    elif ambiguity == "condition":
        invalid = valid.replace("late_fee_exists: false", "late_fee_exists: false\n    late_fee_exists: true")
        error = "duplicate YAML key: late_fee_exists"
    else:
        invalid = "<<: {status: approved}\n" + valid
        error = "YAML merge keys"
    path.write_text(invalid, encoding="utf-8")
    with pytest.raises(ValueError, match=error):
        load_rule_cards(path)
