from unittest.mock import Mock

import pytest

from src.chatbot.application_service import ApplicationService
from src.chatbot.session_manager import SessionManager
from src.models.evidence import DecisionReviewRow
from src.models.ruling import ComplianceStatus

STORY = "I bought an iPhone, paid EGP 5,000 down, and owe EGP 3,000 monthly for 12 months. Is it halal?"


def service():
    return ApplicationService(retriever=Mock(), llm_client=Mock(), session_store=SessionManager(),
                              audit_store=Mock())


@pytest.mark.parametrize("text", [STORY, "عايز اشتري آيفون بمقدم ٥٠٠٠ جنيه و١٢ قسط كل قسط ٣٠٠٠ جنيه. حلال؟",
                                      "عايز iPhone بمقدم EGP 5000 و12 x EGP 3000"])
def test_real_answer_path_asks_exactly_one_financier_question(text):
    app = service()
    result = app.answer(text, session_id="s1")
    assert result.status == ComplianceStatus.CLARIFICATION_NEEDED
    assert result.answer.count("?") + result.answer.count("؟") == 1
    assert "store" in result.answer or "المحل" in result.answer
    review = DecisionReviewRow.model_validate(result.metadata["decision_review"])
    assert review.intent == "described_operation"
    facts = {fact.slot: fact for fact in review.fact_snapshot.facts}
    assert facts["cash_price"].status == "unknown"
    assert facts["instalment_count"].value == 12
    app.retriever.retrieve.assert_not_called()
    app.llm_client.generate.assert_not_called()
    app.audit_store.log_answer.assert_called_once()


def test_unknown_financier_followup_requests_document_and_abstains():
    app = service()
    app.answer(STORY, session_id="s1")
    result = app.answer("I don't know", session_id="s1")
    assert result.status == ComplianceStatus.INSUFFICIENT_DATA
    assert "repayment" in result.answer
    assert result.clarification_question is None
    state = app.session_store.get_session("s1")
    assert len(state.metadata["operation_review_rows"]) == 2
    review = DecisionReviewRow.model_validate(state.metadata["operation_review_rows"][-1])
    assert review.version == 2
    assert review.fact_snapshot.facts[0].source.turn_id != review.turn_id


def test_followup_financier_does_not_implicitly_become_murabaha():
    app = service()
    app.answer(STORY, session_id="s1")
    result = app.answer("The store itself", session_id="s1")
    assert result.status == ComplianceStatus.INSUFFICIENT_DATA
    facts = {item["slot"]: item for item in result.metadata["decision_review"]["fact_snapshot"]["facts"]}
    assert facts["financing_party"]["value"] == "The store itself"
    assert facts["contract_family"]["status"] == "unknown"
    assert result.metadata["approved_rule_evaluation"]["reason"] == "mechanism_unknown"


def test_unanswered_clarification_budget_never_marks_ready():
    app = service()
    app.answer(STORY, session_id="s1")
    second = app.answer("Please continue", session_id="s1")
    third = app.answer("Please continue", session_id="s1")
    assert second.status == ComplianceStatus.CLARIFICATION_NEEDED
    assert third.status == ComplianceStatus.INSUFFICIENT_DATA
    assert "agreement" in third.answer


def test_total_correction_preserves_conflict_and_asks_one_question():
    app = service()
    app.answer(STORY + " The total payable is EGP 41000.", session_id="s1")
    result = app.answer("The total payable is EGP 45000.", session_id="s1")
    assert result.status == ComplianceStatus.CLARIFICATION_NEEDED
    review = DecisionReviewRow.model_validate(result.metadata["decision_review"])
    total = next(fact for fact in review.fact_snapshot.facts if fact.slot == "financed_or_final_price")
    assert total.status == "conflicting"
    assert len(total.candidates) == 2


def test_sessions_keep_separate_snapshots():
    app = service()
    app.answer(STORY, session_id="s1")
    app.answer(STORY.replace("5,000", "6,000"), session_id="s2")
    one = app.session_store.get_session("s1").metadata["described_operation"]
    two = app.session_store.get_session("s2").metadata["described_operation"]
    assert one["transaction_id"] != two["transaction_id"]


def test_definition_during_pending_clarification_uses_its_own_path():
    app = service()
    app.answer(STORY, session_id="s1")
    cached = Mock()
    app._cached_answer = Mock(return_value=cached)
    app._handle_clarification_stage = Mock(return_value=None)
    assert app.answer("What is murabaha?", session_id="s1") is cached


def test_payment_arithmetic_flags_discrepancy_without_asserting_total():
    app = service()
    result = app.answer(STORY + " The financing party is Example Finance. The total payable is EGP 45000.", session_id="s1")
    assert result.status == ComplianceStatus.CLARIFICATION_NEEDED
    assert result.reasoning_summary == "payment_total_discrepancy"
    check = result.metadata["payment_consistency_check"]
    assert check["scheduled_subtotal"]["amount"] == "41000"
    review = DecisionReviewRow.model_validate(result.metadata["decision_review"])
    total = next(fact for fact in review.fact_snapshot.facts if fact.slot == "financed_or_final_price")
    assert total.status == "user_reported"
    assert total.value.amount == 45000


def test_explicit_new_transaction_does_not_inherit_asset_or_financier():
    app = service()
    first = app.answer(STORY + " The financing party is Shop A.", session_id="s1")
    second = app.answer("For a different transaction, I bought a laptop with deposit EGP 1000 and 6 x EGP 2000.", session_id="s1")
    before = DecisionReviewRow.model_validate(first.metadata["decision_review"])
    after = DecisionReviewRow.model_validate(second.metadata["decision_review"])
    assert before.fact_snapshot.facts[0].scope != after.fact_snapshot.facts[0].scope
    facts = {fact.slot: fact for fact in after.fact_snapshot.facts}
    assert facts["financing_party"].status == "unknown"
    assert facts["down_payment"].status == "user_reported"
    assert facts["asset"].value != "iPhone"


@pytest.mark.parametrize("name", ["Contact", "Example Finance", "كونتكت"])
def test_named_financier_reply_is_preserved_without_mechanism_inference(name):
    app = service()
    app.answer(STORY, session_id="s1")
    result = app.answer(name, session_id="s1")
    facts = {fact["slot"]: fact for fact in result.metadata["decision_review"]["fact_snapshot"]["facts"]}
    assert facts["financing_party"]["value"] == name
    assert facts["contract_family"]["status"] == "unknown"


def test_denial_of_transaction_followed_by_definition_is_not_personal_lane():
    from src.chatbot.described_operation import DescribedOperationService
    assert not DescribedOperationService.accepts("I do not have any instalments. What is murabaha?")


def test_session_serialization_preserves_exact_money_and_review_rows():
    import json
    from src.chatbot.redis_session_manager import RedisSessionManager
    from src.chatbot.described_operation import OperationConversation

    app = service()
    app.answer(STORY.replace("5,000", "5,000.25"), session_id="s1")
    encoded = json.dumps(app.session_store.get_session("s1").to_dict())
    restored = RedisSessionManager._decode(encoded)
    operation = OperationConversation.model_validate(restored.metadata["described_operation"])
    deposit = next(fact for fact in operation.snapshot.facts if fact.slot == "down_payment")
    assert str(deposit.value.amount) == "5000.25"
    assert len(restored.metadata["operation_review_rows"]) == 1
    app.session_store.update_session(restored)
    answer = app.answer("Contact", session_id="s1")
    assert answer.status == ComplianceStatus.INSUFFICIENT_DATA
    assert answer.metadata["decision_review"]["version"] == 2


def test_real_rest_multiturn_operation_retains_evidence():
    from fastapi.testclient import TestClient
    from src.api.dependencies import get_application_service
    from src.api.main import create_app

    app_service = service()
    app = create_app()
    app.dependency_overrides[get_application_service] = lambda: app_service
    with TestClient(app) as client:
        first = client.post("/api/v1/query", json={"query": STORY, "session_id": "operation-api",
                                                  "context": {"disclaimer_acknowledged": True}})
        second = client.post("/api/v1/query", json={"query": "I don't know", "session_id": "operation-api",
                                                   "context": {"disclaimer_acknowledged": True}})
    assert first.status_code == second.status_code == 200
    assert first.json()["status"] == "CLARIFICATION_NEEDED"
    assert second.json()["status"] == "INSUFFICIENT_DATA"
    assert len(app_service.session_store.get_session("operation-api").metadata["operation_review_rows"]) == 2
    app_service.llm_client.generate.assert_not_called()


def test_incomplete_operation_enqueues_real_scholar_review_record(tmp_path):
    from src.governance.scholar_review import ScholarReviewQueueStore

    app = service()
    app.scholar_review_queue_store = ScholarReviewQueueStore(tmp_path / "review.jsonl")
    app.answer(STORY, session_id="s1")
    assert app.scholar_review_queue_store.pending() == []
    app.answer("I don't know", session_id="s1", request_id="review-request")
    pending = app.scholar_review_queue_store.pending()
    assert len(pending) == 1
    assert pending[0].flag_reason == "typed_operation_evidence_incomplete"
    assert pending[0].request_id == "review-request"


def test_negated_new_transaction_marker_preserves_existing_scope():
    app = service()
    first = app.answer(STORY, session_id="s1")
    second = app.answer("This is not a new transaction. The financing party is Contact.", session_id="s1")
    before = DecisionReviewRow.model_validate(first.metadata["decision_review"])
    after = DecisionReviewRow.model_validate(second.metadata["decision_review"])
    assert before.fact_snapshot.facts[0].scope == after.fact_snapshot.facts[0].scope
    assert after.version == 2
    assert next(fact for fact in after.fact_snapshot.facts if fact.slot == "down_payment").value.amount == 5000


def test_denial_of_deposit_does_not_deny_the_whole_transaction():
    from src.chatbot.described_operation import DescribedOperationService
    assert DescribedOperationService.accepts("I do not have a deposit. I bought an iPhone with 12 x EGP 3000. Is it halal?")


@pytest.mark.parametrize("text", ["لا ادري", "لا أدري"])
def test_arabic_uncertainty_is_not_financier_identity(text):
    app = service()
    app.answer(STORY, session_id="s1")
    result = app.answer(text, session_id="s1")
    facts = {fact["slot"]: fact for fact in result.metadata["decision_review"]["fact_snapshot"]["facts"]}
    assert facts["financing_party"]["status"] == "unknown"
    assert result.status == ComplianceStatus.INSUFFICIENT_DATA


@pytest.mark.parametrize("confirmation", [
    "According to my repayment schedule, the total payable is EGP 41000.",
    "حسب جدول السداد، السعر النهائي 41000 جنيه.",
    "EGP 41000",
    "٤١٠٠٠ جنيه",
])
def test_explicit_schedule_confirmation_resolves_user_conflict_with_history(confirmation):
    app = service()
    app.answer(STORY + " The total payable is EGP 41000.", session_id="s1")
    app.answer("The total payable is EGP 45000.", session_id="s1")
    result = app.answer(confirmation, session_id="s1")
    review = DecisionReviewRow.model_validate(result.metadata["decision_review"])
    total = next(fact for fact in review.fact_snapshot.facts if fact.slot == "financed_or_final_price")
    assert total.status == "user_reported"
    assert total.value.amount == 41000
    assert total.source.exact_text == confirmation
    assert len(review.fact_resolutions) == 1
    assert [candidate.value.amount for candidate in review.fact_resolutions[0].previous_fact.candidates] == [41000, 45000]
    rows = app.session_store.get_session("s1").metadata["operation_review_rows"]
    old_total = next(fact for fact in rows[1]["fact_snapshot"]["facts"] if fact["slot"] == "financed_or_final_price")
    assert old_total["status"] == "conflicting"


@pytest.mark.parametrize("confirmation", [
    "The total payable is EGP 41000.",
    "This is not according to my repayment schedule. The total payable is EGP 41000.",
    "According to my repayment schedule, maybe the total payable is EGP 41000.",
    "According to my repayment schedule, the cash price is EGP 41000.",
    "According to my repayment schedule, the total payable is EGP 41000, I think.",
    "According to my schedule, the cash price is EGP 50000. I am guessing the total payable is EGP 41000.",
    "حسب جدول السداد، السعر النهائي 41000 جنيه تقريبا.",
])
def test_conflict_resolution_requires_explicit_confirmation_of_pending_field(confirmation):
    app = service()
    app.answer(STORY + " The total payable is EGP 41000.", session_id="s1")
    app.answer("The total payable is EGP 45000.", session_id="s1")
    result = app.answer(confirmation, session_id="s1")
    review = DecisionReviewRow.model_validate(result.metadata["decision_review"])
    total = next(fact for fact in review.fact_snapshot.facts if fact.slot == "financed_or_final_price")
    assert total.status == "conflicting"
    assert review.fact_resolutions == ()


def test_resolution_history_survives_storage_and_later_conflicts():
    import json
    from src.chatbot.redis_session_manager import RedisSessionManager
    from src.chatbot.described_operation import OperationConversation

    app = service()
    app.answer(STORY + " The total payable is EGP 41000.", session_id="s1")
    app.answer("The total payable is EGP 45000.", session_id="s1")
    app.answer("EGP 41000", session_id="s1")
    restored = RedisSessionManager._decode(json.dumps(app.session_store.get_session("s1").to_dict()))
    operation = OperationConversation.model_validate(restored.metadata["described_operation"])
    assert len(operation.resolutions) == 1
    app.session_store.update_session(restored)
    result = app.answer("The total payable is EGP 46000.", session_id="s1")
    row = DecisionReviewRow.model_validate(result.metadata["decision_review"])
    total = next(fact for fact in row.fact_snapshot.facts if fact.slot == "financed_or_final_price")
    assert total.status == "conflicting"
    assert [candidate.value.amount for candidate in total.candidates] == [41000, 46000]
    saved = OperationConversation.model_validate(app.session_store.get_session("s1").metadata["described_operation"])
    assert len(saved.resolutions) == 1
    assert [candidate.value.amount for candidate in saved.resolutions[0].previous_fact.candidates] == [41000, 45000]


def test_review_row_rejects_resolution_attached_to_the_wrong_turn():
    from pydantic import ValidationError

    app = service()
    app.answer(STORY + " The total payable is EGP 41000.", session_id="s1")
    app.answer("The total payable is EGP 45000.", session_id="s1")
    result = app.answer("EGP 41000", session_id="s1")
    row = DecisionReviewRow.model_validate(result.metadata["decision_review"])
    with pytest.raises(ValidationError, match="current review turn"):
        row.model_copy(update={"turn_id": "another-turn"})
