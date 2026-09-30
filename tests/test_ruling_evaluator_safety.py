"""Legacy ontology content is routing evidence, not scholar-approved authority."""
from src.models.commercial import ContractFamily
from src.models.ruling import PartyRole, Permissibility, RulingContext
from src.ontology import ConceptOntology, ConceptOntologyEntry, ConditionalRuling, RulingFunctionEvaluator


def evaluator():
    return RulingFunctionEvaluator(ConceptOntology([ConceptOntologyEntry(
        concept_id="fixture", conditional_rulings=[ConditionalRuling(
            contract_type=ContractFamily.ISTISNA, party_role=PartyRole.CONTRACTOR,
            ruling=Permissibility.CONDITIONAL,
            conditions=["contractor delayed", "actual damage established"],
            applicable_standards=["SS-11"],
        )],
    )]))


def test_legacy_rule_cannot_issue_verdict_even_with_all_conditions():
    result = evaluator().evaluate(RulingContext(
        concept="fixture", contract_type=ContractFamily.ISTISNA, party_role=PartyRole.CONTRACTOR,
        conditions=["contractor delayed", "actual damage established"],
    ))
    assert result.permissibility == Permissibility.INSUFFICIENT_DATA
    assert result.requires_scholar_review


def test_missing_condition_is_unknown_not_violated():
    result = evaluator().evaluate(RulingContext(
        concept="fixture", contract_type=ContractFamily.ISTISNA, party_role=PartyRole.CONTRACTOR,
        conditions=["contractor delayed"],
    ))
    assert result.conditions_met == ["contractor delayed"]
    assert result.conditions_unknown == ["actual damage established"]
    assert result.conditions_violated == []


def test_negated_substring_never_satisfies_condition():
    result = evaluator().evaluate(RulingContext(
        concept="fixture", contract_type=ContractFamily.ISTISNA, party_role=PartyRole.CONTRACTOR,
        conditions=["not contractor delayed"],
    ))
    assert result.conditions_met == []
    assert result.permissibility == Permissibility.INSUFFICIENT_DATA


def test_missing_ontology_concept_abstains_instead_of_crashing():
    result = evaluator().evaluate(RulingContext(concept="absent"))
    assert result.permissibility == Permissibility.INSUFFICIENT_DATA
