"""Generic market descriptions must not become evidenced contract mechanisms."""
import pytest

from src.chatbot.contract_classifier import ContractTypeClassifier
from src.chatbot.contract_family_router import ContractFamilyRouter, ContractFamily as RoutingFamily
from src.chatbot.commercial_assessment import ScenarioExtractor
from src.models.commercial import ContractFamily
from src.rag.query_preprocessor import QueryPreprocessor


GENERIC = [
    "installment sale", "instalment sale", "buy now pay later", "BNPL", "deferred sale",
    "تقسيط", "بيع بالتقسيط", "أقساط", "ta2seet", "taqseet", "2osoot", "تمويل",
    "real estate financing", "تمويل عقاري", "تقسيط مع هامش الربح", "Contact installment plan",
    "BNPL with markup", "تقسيط مع غرامة التأخير", "installments with late payment penalties",
    "interest-free installment sale", "BNPL with no interest", "BNPL with insurance",
    "financing a manufactured phone", "deferred payment with markup cost-plus", "pay in four with markup",
    "BNPL, not murabaha", "installment sale without wakala",
    "installment sale that is not an Islamic murabaha", "تقسيط من تاجر مسلم",
    "تقسيط ليس مرابحة", "تقسيط من شركة لا تقدم مرابحة",
]


@pytest.mark.parametrize("query", GENERIC)
def test_generic_terms_leave_commercial_family_unknown(query):
    result = ContractTypeClassifier().classify(query)
    assert result is None or result.contract_family == ContractFamily.UNKNOWN
    assert ScenarioExtractor().extract(query).contract_family == ContractFamily.UNKNOWN


@pytest.mark.parametrize("query", GENERIC)
def test_generic_queries_do_not_route_to_an_islamic_family(query):
    result = ContractFamilyRouter().classify(query)
    assert result.primary_family in {RoutingFamily.AMBIGUOUS, RoutingFamily.GENERAL_SHARIA}


@pytest.mark.parametrize("query", [q for q in GENERIC if "murabaha" not in q.lower() and "مرابحة" not in q])
def test_query_expansion_does_not_supply_an_unstated_murabaha_label(query):
    terms = " ".join(QueryPreprocessor.expand_terms(query)).lower()
    assert "murabaha" not in terms
    assert "مرابح" not in terms


def test_explicit_named_concept_remains_a_retrieval_topic_without_probability():
    result = ContractTypeClassifier().classify("What is murabaha?")
    assert result.contract_family == ContractFamily.MURABAHA
    assert not hasattr(result, "confidence")


def test_generic_plan_does_not_inherit_session_family():
    result = ContractFamilyRouter().classify("BNPL plan", session_family=RoutingFamily.MURABAHA,
                                              session_confirmation_turns=2)
    assert result.primary_family == RoutingFamily.AMBIGUOUS


def test_negated_name_does_not_win_over_affirmed_retrieval_topic():
    query = "BNPL is not murabaha but ijara"
    assert ContractTypeClassifier().classify(query).contract_family == ContractFamily.IJARAH
    assert ScenarioExtractor().extract(query).contract_family == ContractFamily.IJARAH
    assert ContractFamilyRouter().classify(query).primary_family == RoutingFamily.IJARA


def test_prompt_does_not_translate_generic_plans_to_murabaha():
    from src.chatbot.prompt_builder import PromptBuilder
    prompt = PromptBuilder().build("What is BNPL?", [])
    assert "بيع تقسيط → مرابحة" not in prompt
    assert "تمويل → تمويل إسلامي" not in prompt
    assert "Generic instalment" in prompt


@pytest.mark.parametrize("query", ["Is BNPL with insurance halal?", "هل التقسيط من تاجر مسلم جائز؟"])
def test_real_answer_path_keeps_generic_mechanism_unknown(query):
    from unittest.mock import Mock
    from src.chatbot.application_service import ApplicationService
    from src.models.ruling import ComplianceStatus
    from tests.test_l1_contracts import FakeRetriever

    llm = Mock()
    result = ApplicationService(retriever=FakeRetriever([]), llm_client=llm).answer(query)
    assert result.status in {ComplianceStatus.CLARIFICATION_NEEDED, ComplianceStatus.INSUFFICIENT_DATA}
    assert result.metadata["transaction_scenario"]["contract_family"] == "unknown"
    llm.generate.assert_not_called()


def test_user_murabaha_label_and_configured_card_do_not_fill_personal_mechanism():
    from unittest.mock import Mock
    from src.chatbot.application_service import ApplicationService
    from tests.test_approved_card_evaluator import card

    app = ApplicationService(retriever=Mock(), llm_client=Mock(), approved_rule_cards=[card()])
    result = app.answer("I bought an iPhone in my Murabaha installment plan, deposit EGP 5000 and 12 x EGP 3000.")
    assert result.metadata["approved_rule_evaluation"]["reason"] == "mechanism_unknown"
    facts = result.metadata["decision_review"]["fact_snapshot"]["facts"]
    assert next(f for f in facts if f["slot"] == "contract_family")["status"] == "unknown"
    app.llm_client.generate.assert_not_called()
