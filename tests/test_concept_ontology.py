import pytest

from src.models.commercial import ContractFamily
from src.models.ruling import PartyRole, RulingContext, Permissibility
from src.ontology import ConceptOntology, ConceptOntologyRouter, RulingFunctionEvaluator


pytestmark = pytest.mark.service


def test_concept_ontology_loads_seed_nodes():
    ontology = ConceptOntology.load()

    assert len(ontology.all()) >= 10
    assert ontology.get("late_penalty").concept_id == "late_penalty"


def test_concept_ontology_matches_arabic_construction_penalty_terms():
    ontology = ConceptOntology.load()

    matches = ontology.match(
        "\u0647\u0644 \u0634\u0631\u0637 \u063a\u0631\u0627\u0645\u0629 \u0627\u0644\u062a\u0623\u062e\u064a\u0631 "
        "\u0641\u064a \u0639\u0642\u0648\u062f \u0627\u0644\u0645\u0642\u0627\u0648\u0644\u0627\u062a \u0631\u0628\u0648\u064a\u061f"
    )

    assert {match.concept_id for match in matches} >= {"late_penalty"}


def test_concept_router_returns_current_eligible_standards_and_conditions():
    ontology = ConceptOntology.load()
    concepts = [ontology.get("late_penalty")]

    route = ConceptOntologyRouter(ontology).route(ContractFamily.ISTISNA, concepts)

    assert route.concepts == ["late_penalty"]
    assert route.standard_ids == ["SS-05", "SS-11"]
    assert "contractor is the delaying party" in route.ruling_conditions
    assert PartyRole.CONTRACTOR in route.party_roles


def test_ruling_evaluator_flags_unmet_conditions_for_scholar_review():
    result = RulingFunctionEvaluator().evaluate(
        RulingContext(
            concept="late_penalty",
            contract_type=ContractFamily.ISTISNA,
            party_role=PartyRole.CONTRACTOR,
            conditions=["contractor is the delaying party"],
        ),
        source_chunks=["chunk-ss-11"],
    )

    assert result.permissibility == Permissibility.CONDITIONAL
    assert result.applicable_standards == ["SS-11", "SS-05"]
    assert "contractor is the delaying party" in result.conditions_met
    assert "penalty represents actual damage" in result.conditions_violated
    assert result.requires_scholar_review is True
    assert result.source_chunks == ["chunk-ss-11"]
