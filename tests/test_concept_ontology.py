import pytest
import yaml

from src.models.commercial import ContractFamily
from src.models.ruling import PartyRole, RulingContext, Permissibility
from src.ontology import ConceptOntology, ConceptOntologyRouter, RulingFunctionEvaluator
from tests.ontology_fixtures import late_penalty_payload


pytestmark = pytest.mark.service


@pytest.fixture
def ontology(tmp_path):
    path = tmp_path / "late_penalty.yaml"
    path.write_text(yaml.safe_dump(late_penalty_payload(), allow_unicode=True), encoding="utf-8")
    return ConceptOntology.load(tmp_path)


def test_concept_ontology_loads_explicit_yaml_fixture(ontology):
    assert len(ontology.all()) == 1
    assert ontology.get("late_penalty").concept_id == "late_penalty"


def test_missing_ontology_does_not_manufacture_seed_nodes(tmp_path):
    assert ConceptOntology.load(tmp_path / "absent").all() == []


def test_concept_ontology_matches_arabic_construction_penalty_terms(ontology):

    matches = ontology.match(
        "\u0647\u0644 \u0634\u0631\u0637 \u063a\u0631\u0627\u0645\u0629 \u0627\u0644\u062a\u0623\u062e\u064a\u0631 "
        "\u0641\u064a \u0639\u0642\u0648\u062f \u0627\u0644\u0645\u0642\u0627\u0648\u0644\u0627\u062a \u0631\u0628\u0648\u064a\u061f"
    )

    assert {match.concept_id for match in matches} >= {"late_penalty"}


def test_concept_router_returns_current_eligible_standards_and_conditions(ontology, tmp_path):
    concepts = [ontology.get("late_penalty")]
    catalog = tmp_path / "catalog.yaml"
    catalog.write_text(yaml.safe_dump({"records": [
        {"standard_number": "SS-11", "source_family": "sharia_standard", "currentness": "current"},
        {"standard_number": "SS-05", "source_family": "sharia_standard", "currentness": "superseded"},
    ]}), encoding="utf-8")

    route = ConceptOntologyRouter(ontology, source_catalog_path=catalog).route(ContractFamily.ISTISNA, concepts)

    assert route.concepts == ["late_penalty"]
    assert route.standard_ids == ["SS-11"]
    assert "contractor is the delaying party" in route.ruling_conditions
    assert PartyRole.CONTRACTOR in route.party_roles


def test_unsigned_ontology_requires_review_and_missing_conditions_are_unknown(ontology):
    result = RulingFunctionEvaluator(ontology).evaluate(
        RulingContext(
            concept="late_penalty",
            contract_type=ContractFamily.ISTISNA,
            party_role=PartyRole.CONTRACTOR,
            conditions=["contractor is the delaying party"],
        ),
        source_chunks=["chunk-ss-11"],
    )

    assert result.permissibility == Permissibility.INSUFFICIENT_DATA
    assert result.applicable_standards == ["SS-11", "SS-05"]
    assert "contractor is the delaying party" in result.conditions_met
    assert "penalty represents actual damage" in result.conditions_unknown
    assert result.conditions_violated == []
    assert result.requires_scholar_review is True
    assert result.source_chunks == ["chunk-ss-11"]
