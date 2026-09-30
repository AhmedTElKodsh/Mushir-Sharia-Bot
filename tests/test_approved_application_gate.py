"""The public answer path must not authorize judgments using legacy cache/LLM."""
from unittest.mock import Mock

import pytest

from src.chatbot.application_service import ApplicationService
from src.models.ruling import AnswerContract, ComplianceStatus
from src.models.commercial import RuleEvaluation
from tests.test_l1_contracts import FakeRetriever, FakeLLM, _chunk


def judgment_service():
    service = ApplicationService(retriever=FakeRetriever([_chunk(
        standard_id="SS-08", metadata={"source_family": "sharia_standard", "standard_number": "SS-08",
                                      "metadata_status": "cataloged"})]), llm_client=FakeLLM("unused"))
    # Exercise the otherwise-generating branch: empty legacy trace is not approval.
    service.rule_evaluator = Mock()
    service.rule_evaluator.evaluate.return_value = RuleEvaluation()
    return service


@pytest.mark.parametrize("query", [
    "Is a murabaha purchase permissible?",
    "هل شراء السيارة بالمرابحة جائز؟",
    "Is this compliant?",
    "هل هذه المعاملة متوافقة؟",
])
def test_judgment_gate_runs_before_cache_and_generation(query):
    service = judgment_service()
    service._cached_answer = Mock(return_value=AnswerContract(answer="Legacy cached judgment",
                                                             status=ComplianceStatus.INSUFFICIENT_DATA))
    service._handle_clarification_stage = Mock(return_value=None)
    result = service.answer(query, session_id="fixture-session")
    assert result.status == ComplianceStatus.INSUFFICIENT_DATA
    assert result.metadata["approved_rule_gate"]["reason"] == "approved_evidence_not_available"
    service._cached_answer.assert_not_called()
    assert service.retriever.queries
    assert service.llm_client.prompts == []


def test_grounded_definition_path_remains_available():
    service = ApplicationService(retriever=Mock(), llm_client=Mock())
    cached = AnswerContract(answer="Murabaha is a disclosed cost and profit sale.",
                            status=ComplianceStatus.INSUFFICIENT_DATA)
    service._cached_answer = Mock(return_value=cached)
    service._handle_clarification_stage = Mock(return_value=None)
    assert service.answer("What is murabaha?") is cached


@pytest.mark.parametrize("query", [
    "Explain whether my contract is valid.",
    "What is murabaha and is my agreement haram?",
    "Explain why my loan is usurious.",
])
def test_mixed_definition_and_judgment_cannot_use_cache_or_generate(query):
    service = judgment_service()
    service._cached_answer = Mock()
    service._handle_clarification_stage = Mock(return_value=None)
    result = service.answer(query)
    assert result.status == ComplianceStatus.INSUFFICIENT_DATA
    service._cached_answer.assert_not_called()
    assert service.llm_client.prompts == []


def test_useful_clarification_precedes_rule_insufficiency():
    service = ApplicationService(retriever=Mock(), llm_client=Mock())
    service._cached_answer = Mock()
    clarification = AnswerContract(answer="Who finances the purchase?", clarification_question="Who finances the purchase?",
                                   status=ComplianceStatus.CLARIFICATION_NEEDED)
    service._handle_clarification_stage = Mock(return_value=clarification)
    assert service.answer("Is buying a car in installments halal?") is clarification
    service._cached_answer.assert_not_called()


def test_real_rest_path_preserves_clarification_without_generating_judgment():
    from fastapi.testclient import TestClient
    from src.api.dependencies import get_application_service
    from src.api.main import create_app

    service = judgment_service()
    app = create_app()
    app.dependency_overrides[get_application_service] = lambda: service
    with TestClient(app) as client:
        response = client.post("/api/v1/query", json={"query": "Is a murabaha purchase permissible?",
                                                     "context": {"disclaimer_acknowledged": True}})
    assert response.status_code == 200
    assert response.json()["status"] == "CLARIFICATION_NEEDED"
    assert response.json()["clarification_question"]
    assert service.llm_client.prompts == []


def test_blocked_approval_gate_enqueues_review_without_numeric_confidence(tmp_path):
    from src.governance.scholar_review import ScholarReviewQueueStore

    service = judgment_service()
    service.scholar_review_queue_store = ScholarReviewQueueStore(tmp_path / "review.jsonl")
    service._handle_clarification_stage = Mock(return_value=None)
    result = service.answer("Is a murabaha purchase permissible?")
    assert "confidence" not in result.metadata
    assert result.metadata["requires_scholar_review"] is True
    records = service.scholar_review_queue_store.pending()
    assert len(records) == 1
    assert records[0].flag_reason == "approved_rule_evidence_unavailable"
