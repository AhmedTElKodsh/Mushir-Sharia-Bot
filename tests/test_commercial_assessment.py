import pytest

from src.chatbot.commercial_assessment import (
    CommercialRuleEvaluator,
    EvidenceFamilyDetector,
    ScenarioExtractor,
    StandardsRouter,
    should_fail_closed_for_source_gap,
)
from src.chatbot.application_service import ApplicationService
from src.models.commercial import ContractFamily, QuestionType, SourceFamily
from src.models.ruling import ComplianceStatus
from src.models.schema import AAOIFICitation, SemanticChunk
from src.rag.query_preprocessor import QueryPreprocessor


pytestmark = pytest.mark.service


def test_scenario_extractor_structures_late_payment_murabaha_question():
    scenario = ScenarioExtractor().extract(
        "Is a murabaha car installment sale with a 5% late payment penalty permissible?"
    )

    assert scenario.question_type == QuestionType.PERMISSIBILITY
    assert scenario.contract_family == ContractFamily.MURABAHA
    assert scenario.asset == "car"
    assert scenario.late_payment_terms
    assert "penalty_beneficiary" in scenario.missing_facts
    assert "late_payment_penalty_requires_dedicated_rule_check" in scenario.uncertainties


def test_standards_router_uses_sharia_first_for_permissibility():
    scenario = ScenarioExtractor().extract("Is this murabaha structure halal?")
    route = StandardsRouter().route(scenario)

    assert route.primary == [SourceFamily.SHARIA_STANDARD]
    assert SourceFamily.FAS in route.secondary
    assert route.requires_rule_evaluation is True


def test_standards_router_uses_fas_first_for_accounting():
    query = "How should murabaha profit be recognized for accounting?"
    scenario = ScenarioExtractor().extract(query)
    route = StandardsRouter().route(scenario, query)

    assert scenario.question_type == QuestionType.ACCOUNTING
    assert route.primary == [SourceFamily.FAS]
    assert route.route_id == "murabaha-accounting"
    assert route.candidate_standards == ["FAS-28"]
    assert route.requires_rule_evaluation is False


def test_standards_router_does_not_leak_fas_seed_into_sharia_permissibility():
    query = "Is murabaha profit recognized under AAOIFI permissible if the bank never owns the car?"
    scenario = ScenarioExtractor().extract(query)
    route = StandardsRouter().route(scenario, query)

    assert scenario.question_type == QuestionType.PERMISSIBILITY
    assert route.primary == [SourceFamily.SHARIA_STANDARD]
    assert all(not standard.startswith("FAS-") for standard in route.candidate_standards)


def test_application_service_passes_query_to_standards_router_seed():
    class EmptyRetriever:
        def retrieve(self, query, k=5, threshold=0.3):
            return []

    answer = ApplicationService(retriever=EmptyRetriever()).answer(
        "How should murabaha profit be recognized for accounting?"
    )

    assert answer.status == ComplianceStatus.INSUFFICIENT_DATA
    assert answer.metadata["standards_route"]["route_id"] == "murabaha-accounting"
    assert answer.metadata["standards_route"]["candidate_standards"] == ["FAS-28"]


def test_source_gap_guard_blocks_permissibility_without_sharia_evidence():
    scenario = ScenarioExtractor().extract(
        "Is a murabaha car installment sale with a late payment penalty permissible?"
    )
    route = StandardsRouter().route(scenario)

    assert should_fail_closed_for_source_gap(scenario, route, {SourceFamily.FAS}) is True
    assert should_fail_closed_for_source_gap(scenario, route, {SourceFamily.SHARIA_STANDARD}) is False


def test_source_gap_guard_blocks_plain_installment_permissibility_without_sharia_evidence():
    scenario = ScenarioExtractor().extract(
        "Is a car installment sale with a 20% markup halal?"
    )
    route = StandardsRouter().route(scenario)

    assert should_fail_closed_for_source_gap(scenario, route, {SourceFamily.FAS}) is True


def test_source_gap_guard_does_not_block_non_permissibility_late_wording():
    scenario = ScenarioExtractor().extract(
        "My app default setting sends late reminder notifications."
    )
    route = StandardsRouter().route(scenario)

    assert should_fail_closed_for_source_gap(scenario, route, {SourceFamily.FAS}) is False


def test_generic_compliance_wording_without_commercial_context_stays_unknown():
    scenario = ScenarioExtractor().extract("Is this compliant?")
    route = StandardsRouter().route(scenario)

    assert scenario.question_type == QuestionType.UNKNOWN
    assert route.primary == [SourceFamily.FAS]
    assert should_fail_closed_for_source_gap(scenario, route, {SourceFamily.FAS}) is False


@pytest.mark.parametrize(
    "query",
    [
        "Is this allowed?",
        "Can we do this?",
        "Is it valid?",
        "Does this meet the standard?",
        "\u0647\u0644 \u0647\u0630\u0627 \u062c\u0627\u0626\u0632\u061f",
        "\u0647\u0644 \u064a\u0646\u0641\u0639\u061f",
        "\u0647\u0644 \u0647\u0630\u0627 \u0645\u0637\u0627\u0628\u0642\u061f",
    ],
)
def test_generic_permissibility_wording_without_commercial_context_does_not_source_gap(query):
    scenario = ScenarioExtractor().extract(query)
    route = StandardsRouter().route(scenario)

    assert scenario.question_type == QuestionType.UNKNOWN
    assert route.primary == [SourceFamily.FAS]
    assert should_fail_closed_for_source_gap(scenario, route, {SourceFamily.FAS}) is False


@pytest.mark.parametrize(
    ("query", "family"),
    [
        ("Can we charge 2% monthly penalty if the customer delays ijara payments?", ContractFamily.IJARAH),
        ("Is a sukuk with purchase undertaking at face value permissible?", ContractFamily.SUKUK),
        ("Can the bank guarantee capital in mudarabah?", ContractFamily.MUDARABA),
        ("Based only on the accounting standard, tell me if this murabaha is permissible.", ContractFamily.MURABAHA),
        ("We donate late fees to charity, so is the murabaha clause allowed?", ContractFamily.MURABAHA),
        ("Can we trade receivables from murabaha at a discount?", ContractFamily.MURABAHA),
        ("Is buy now pay later halal?", ContractFamily.MURABAHA),
        ("The bank gives cash and I repay more monthly. Is it halal?", ContractFamily.UNKNOWN),
        (
            "\u0647\u0644 \u064a\u062c\u0648\u0632 \u0641\u0631\u0636 \u063a\u0631\u0627\u0645\u0629 \u062a\u0623\u062e\u064a\u0631 \u0639\u0644\u0649 \u0627\u0644\u0639\u0645\u064a\u0644\u061f",
            ContractFamily.UNKNOWN,
        ),
        (
            "\u0647\u0644 \u0627\u0644\u0648\u0639\u062f \u0627\u0644\u0645\u0644\u0632\u0645 \u0641\u064a \u0627\u0644\u0645\u0631\u0627\u0628\u062d\u0647 \u0634\u0631\u0639\u064a\u061f",
            ContractFamily.MURABAHA,
        ),
        (
            "\u0644\u0648 \u0639\u0646\u062f\u064a ijara contract \u0648\u0641\u064a\u0647 late payment penalty, compliant \u0648\u0644\u0627 \u0644\u0627?",
            ContractFamily.IJARAH,
        ),
    ],
)
def test_commercial_permissibility_boundary_cases_route_to_sharia_family(query, family):
    scenario = ScenarioExtractor().extract(query)
    route = StandardsRouter().route(scenario)

    assert scenario.question_type == QuestionType.PERMISSIBILITY
    assert scenario.contract_family == family
    assert route.primary == [SourceFamily.SHARIA_STANDARD]
    assert should_fail_closed_for_source_gap(scenario, route, {SourceFamily.FAS}) is True


@pytest.mark.parametrize(
    "query",
    [
        "\u0645\u0631\u0627\u0628\u062d\u0647",
        "\u0627\u0644\u0645\u0631\u0627\u0628\u062d\u0647",
        "\u062a\u0642\u0633\u064a\u0637 \u0633\u064a\u0627\u0631\u0629",
        "\u0627\u0642\u0633\u0627\u0637 \u0633\u064a\u0627\u0631\u0629",
        "\u063a\u0631\u0627\u0645\u0647 \u062a\u0627\u062e\u064a\u0631",
        "\u0641\u0648\u0627\u0626\u062f \u062a\u0623\u062e\u064a\u0631",
        "hal el ta2seet da halal?",
        "riba on late payment",
    ],
)
def test_query_expansion_handles_arabic_dialect_spelling_and_transliteration(query):
    terms = QueryPreprocessor.expand_terms(query)

    assert terms & {"murabaha", "murabahah", "installment sale", "late payment", "late fee", "riba", "interest"}


def test_query_preprocessor_expands_bounded_arabizi_finance_terms():
    terms = QueryPreprocessor.expand_terms("hal el ta2seet 3ala el 3arabeya feeh gharamet ta2kheer?")

    assert {"installment sale", "late fee", "murabaha"} & terms
    assert "late payment" in terms


def test_murabaha_late_payment_rule_outputs_versioned_evidence_requirements():
    scenario = ScenarioExtractor().extract(
        "Is a murabaha car installment sale with a late payment penalty permissible?"
    )
    route = StandardsRouter().route(scenario)

    evaluation = CommercialRuleEvaluator().evaluate(scenario, route)

    payload = evaluation.to_dict()
    assert payload["rule_id"] == "murabaha-late-payment-v1"
    assert payload["rule_version"] == "2026-05-24"
    assert "penalty_beneficiary" in payload["missing_facts"]
    assert "sharia_standard_evidence" in payload["evidence_requirements"]
    assert "human_review_required" in payload["human_review_flags"]


def test_arabic_construction_penalty_routes_to_istisna_not_debt_or_charity():
    query = "\u0647\u0644 \u0634\u0631\u0637 \u063a\u0631\u0627\u0645\u0629 \u0627\u0644\u062a\u0622\u062e\u064a\u0631 \u0641\u064a \u0639\u0642\u0648\u062f \u0627\u0644\u0645\u0642\u0627\u0648\u0644\u0627\u062a \u0634\u0631\u0637 \u0631\u0628\u0648\u064a\u061f"

    scenario = ScenarioExtractor().extract(query)
    route = StandardsRouter().route(scenario, query)

    assert scenario.question_type == QuestionType.PERMISSIBILITY
    assert scenario.contract_family == ContractFamily.ISTISNA
    assert scenario.penalty_beneficiary is None
    assert "delay_responsible_party" in scenario.missing_facts
    assert route.primary == [SourceFamily.SHARIA_STANDARD]
    assert route.requires_rule_evaluation is True


@pytest.mark.parametrize(
    "query",
    [
        "Can we add liquidated damages if the contractor delays handover?",
        "Can the construction contract include delay damages for late completion?",
        "Does an LD clause in a muqawala contract count as riba?",
        "Is FIDIC delay damages wording permissible in an istisna construction contract?",
        "\u0647\u0644 \u0627\u0644\u0634\u0631\u0637 \u0627\u0644\u062c\u0632\u0627\u0626\u064a \u0641\u064a \u0639\u0642\u062f \u0645\u0642\u0627\u0648\u0644\u0629 \u0631\u0628\u0627\u061f",
    ],
)
def test_construction_delay_damage_variants_route_to_istisna_candidate_ss10(query):
    scenario = ScenarioExtractor().extract(query)
    route = StandardsRouter().route(scenario, query)

    assert scenario.question_type == QuestionType.PERMISSIBILITY
    assert scenario.contract_family == ContractFamily.ISTISNA
    assert scenario.late_payment_terms
    assert route.route_id == "istisna-penalty-clause"
    assert route.candidate_standards == ["SS-10"]


def test_arabic_delay_word_does_not_trigger_charity_beneficiary():
    scenario = ScenarioExtractor().extract(
        "\u063a\u0631\u0627\u0645\u0629 \u0627\u0644\u062a\u0623\u062e\u064a\u0631 \u0639\u0644\u0649 \u0627\u0644\u0645\u0642\u0627\u0648\u0644"
    )

    assert scenario.penalty_beneficiary is None


def test_explicit_charity_terms_still_trigger_charity_beneficiary():
    scenario = ScenarioExtractor().extract(
        "\u0627\u0644\u063a\u0631\u0627\u0645\u0629 \u062a\u0630\u0647\u0628 \u0625\u0644\u0649 \u062c\u0647\u0629 \u062e\u064a\u0631\u064a\u0629 \u0643\u062a\u0628\u0631\u0639"
    )

    assert scenario.penalty_beneficiary == "charity"


def test_istisna_late_penalty_rule_outputs_review_requirements():
    scenario = ScenarioExtractor().extract(
        "\u0647\u0644 \u0634\u0631\u0637 \u063a\u0631\u0627\u0645\u0629 \u0627\u0644\u062a\u0623\u062e\u064a\u0631 \u0641\u064a \u0639\u0642\u062f \u0645\u0642\u0627\u0648\u0644\u0629 \u062c\u0627\u0626\u0632\u061f"
    )
    route = StandardsRouter().route(scenario)

    evaluation = CommercialRuleEvaluator().evaluate(scenario, route)

    payload = evaluation.to_dict()
    assert payload["rule_id"] == "istisna-construction-penalty-v1"
    assert "delay_responsible_party" in payload["missing_facts"]
    assert "force_majeure_or_actual_loss_context" in payload["evidence_requirements"]
    assert "penalty_clause_review_required" in payload["human_review_flags"]


@pytest.mark.parametrize(
    ("query", "route_id", "standards"),
    [
        (
            "Can we impose a penalty if the contractor is late delivering the project?",
            "istisna-penalty-clause",
            {"SS-10"},
        ),
        (
            "Can the bank charge a late fee on a cash loan?",
            "debt-late-payment-penalty",
            {"SS-03", "SS-19"},
        ),
        (
            "Can we lock today's FX rate and settle next month?",
            "currency-sarf-settlement",
            {"SS-01"},
        ),
        (
            "\u0647\u0644 \u064a\u062c\u0648\u0632 \u0639\u0645\u0648\u0644\u0629 \u062e\u0637\u0627\u0628 \u0636\u0645\u0627\u0646 \u062d\u0633\u0628 \u0627\u0644\u0645\u0628\u0644\u063a \u0648\u0627\u0644\u0645\u062f\u0629\u061f",
            "guarantee-kafalah-fee",
            {"SS-05"},
        ),
    ],
)
def test_penalty_and_hard_case_family_routes_are_launch_blocking(query, route_id, standards):
    scenario = ScenarioExtractor().extract(query)
    route = StandardsRouter().route(scenario, query)

    assert scenario.question_type == QuestionType.PERMISSIBILITY
    assert route.primary == [SourceFamily.SHARIA_STANDARD]
    assert route.route_id == route_id
    assert set(route.candidate_standards) == standards
    assert should_fail_closed_for_source_gap(scenario, route, {SourceFamily.FAS}) is True


def test_query_expansion_does_not_infer_charity_from_delay_or_penalty():
    terms = QueryPreprocessor.expand_terms(
        "\u0647\u0644 \u063a\u0631\u0627\u0645\u0629 \u0627\u0644\u062a\u0623\u062e\u064a\u0631 \u0641\u064a \u0627\u0644\u0645\u0642\u0627\u0648\u0644\u0627\u062a \u0631\u0628\u0627\u061f"
    )

    assert "late payment" in terms
    assert "charity clause" not in terms
    assert {"construction", "istisna", "muqawala"} & terms


def test_query_expansion_adds_charity_only_for_explicit_charity_terms():
    terms = QueryPreprocessor.expand_terms("\u0627\u0644\u063a\u0631\u0627\u0645\u0629 \u0644\u062c\u0647\u0629 \u062e\u064a\u0631\u064a\u0629 \u0623\u0648 \u062a\u0628\u0631\u0639")

    assert "charity clause" in terms


def test_evidence_family_detector_classifies_fas_chunk():
    chunk = SemanticChunk(
        chunk_id="fas-28",
        text="Murabaha accounting excerpt",
        citation=AAOIFICitation(
            standard_id="FAS-28",
            section=None,
            page=8,
            source_file="AAOIFI_Standard_28_en_Financial_Accounting_Standard_2_8.md",
        ),
        score=0.8,
    )

    assert EvidenceFamilyDetector.family_for_chunk(chunk) == SourceFamily.FAS


def test_evidence_family_detector_trusts_explicit_sharia_family_metadata_after_admissibility():
    chunk = {
        "metadata": {"source_family": "sharia_standard"},
        "score": 0.8,
    }

    assert EvidenceFamilyDetector.family_for_chunk(chunk) == SourceFamily.SHARIA_STANDARD


def test_evidence_family_detector_requires_minimum_relevance_for_sharia_source():
    chunk = SemanticChunk(
        chunk_id="ss-low",
        text="Low-scoring Sharia standard excerpt",
        citation=AAOIFICitation(
            standard_id="SS-08",
            section="1",
            page=1,
            source_file="AAOIFI_Sharia_Standard_08_Murabaha.md",
        ),
        score=0.1,
    )

    assert EvidenceFamilyDetector.family_for_chunk(chunk) == SourceFamily.UNKNOWN


def test_evidence_family_detector_classifies_supported_sharia_standard_chunk():
    chunk = SemanticChunk(
        chunk_id="ss-08",
        text="Sharia standard excerpt",
        citation=AAOIFICitation(
            standard_id="SS-08",
            section="1",
            page=1,
            source_file="AAOIFI_Sharia_Standard_08_Murabaha.md",
        ),
        score=0.8,
    )

    assert EvidenceFamilyDetector.family_for_chunk(chunk) == SourceFamily.SHARIA_STANDARD
