from unittest.mock import Mock

import pytest

from src.chatbot.application_service import ApplicationService
from src.chatbot.session_manager import SessionManager
from src.models.ruling import ComplianceStatus

QUERIES = [
    "What is the ruling on banking Tawarruq?",
    "ما حكم التورق المصرفي؟",
    "What is the difference between Commodity Murabaha and Tawarruq, and do they share the same ruling?",
    "ما الفرق بين المرابحة السلعية والتورق المصرفي وهل لهما نفس الحكم؟",
    "Are Sukuk that distribute fixed periodic income compliant with profit sharing?",
    "هل الصكوك التي توزع دخلا ثابتا دوريا متوافقة مع المشاركة في الأرباح؟",
]


def service():
    return ApplicationService(retriever=Mock(), llm_client=Mock(), session_store=SessionManager())


@pytest.mark.parametrize("query", QUERIES)
def test_variant_ambiguity_asks_one_structural_question_before_retrieval(query):
    app = service()
    answer = app.answer(query, session_id="s1")
    assert answer.status == ComplianceStatus.CLARIFICATION_NEEDED
    assert answer.answer.count("?") + answer.answer.count("؟") == 1
    assert answer.metadata["structure_clarification"]["slot"] in {"resale_arranger", "underlying_sukuk_contract"}
    app.retriever.retrieve.assert_not_called()
    app.llm_client.generate.assert_not_called()


@pytest.mark.parametrize("reply", ["The bank", "I don't know", "البنك", "لا أعرف"])
def test_followup_cannot_turn_structure_label_into_approved_verdict(reply):
    app = service()
    app.answer(QUERIES[0], session_id="s1")
    answer = app.answer(reply, session_id="s1")
    assert answer.status == ComplianceStatus.INSUFFICIENT_DATA
    assert answer.metadata["structure_clarification"]["reply"] == reply
    assert answer.metadata["needed_documents_or_reviews"]
    app.llm_client.generate.assert_not_called()


def test_unanswered_structure_question_stops_at_turn_limit():
    app = service()
    app.answer(QUERIES[0], session_id="s1")
    second = app.answer("Please continue", session_id="s1")
    third = app.answer("Please continue", session_id="s1")
    assert second.status == ComplianceStatus.CLARIFICATION_NEEDED
    assert third.status == ComplianceStatus.INSUFFICIENT_DATA


def test_new_definition_is_not_swallowed_by_pending_structural_question():
    app = service()
    app.answer(QUERIES[0], session_id="s1")
    app._handle_clarification_stage = Mock(return_value=None)
    cached = Mock()
    app._cached_answer = Mock(return_value=cached)
    assert app.answer("What is murabaha?", session_id="s1") is cached


def test_pure_definition_does_not_require_transaction_details():
    app = service()
    app._handle_clarification_stage = Mock(return_value=None)
    cached = Mock()
    app._cached_answer = Mock(return_value=cached)
    assert app.answer("What is tawarruq?") is cached


def test_changed_structure_topic_starts_its_own_question():
    app = service()
    app.answer(QUERIES[0], session_id="s1")
    answer = app.answer("Can fixed income Sukuk be halal?", session_id="s1")
    assert answer.metadata["structure_clarification"]["slot"] == "underlying_sukuk_contract"
    assert answer.metadata["structure_clarification"]["asked_count"] == 1


@pytest.mark.parametrize("query", ["Define murabaha", "Tell me about murabaha", "عرف المرابحة"])
def test_definition_commands_leave_pending_structure(query):
    app = service()
    app.answer(QUERIES[0], session_id="s1")
    app._handle_clarification_stage = Mock(return_value=None)
    cached = Mock()
    app._cached_answer = Mock(return_value=cached)
    assert app.answer(query, session_id="s1") is cached


def test_personal_story_clears_old_structure_question():
    app = service()
    app.answer(QUERIES[0], session_id="s1")
    app.answer("I bought an iPhone with deposit EGP 5000 and 12 x EGP 3000.", session_id="s1")
    assert "pending_structure_clarification" not in app.session_store.get_session("s1").metadata


def test_structure_question_suspends_personal_pending_reply():
    app = service()
    app.answer("I bought an iPhone with deposit EGP 5000 and 12 x EGP 3000.", session_id="s1")
    answer = app.answer("Is Tawarruq permissible", session_id="s1")
    assert answer.metadata["structure_clarification"]["slot"] == "resale_arranger"
    answer = app.answer("The bank", session_id="s1")
    assert answer.metadata["structure_clarification"]["reply"] == "The bank"


def test_pending_structure_is_session_local_and_json_roundtrips():
    import json

    app = service()
    app.answer(QUERIES[0], session_id="s1")
    state = app.session_store.get_session("s1")
    state.metadata = json.loads(json.dumps(state.metadata))
    other = app.answer(QUERIES[4], session_id="s2")
    assert other.metadata["structure_clarification"]["slot"] == "underlying_sukuk_contract"
    answer = app.answer("The bank?", session_id="s1")
    assert answer.metadata["structure_clarification"]["slot"] == "resale_arranger"
    assert answer.metadata["structure_clarification"]["reply"] == "The bank?"


def test_terminal_structure_reply_is_audited_and_enqueued(tmp_path):
    from src.governance.scholar_review import ScholarReviewQueueStore

    app = service()
    app.audit_store = Mock()
    app.scholar_review_queue_store = ScholarReviewQueueStore(tmp_path / "structure-review.jsonl")
    app.answer(QUERIES[0], session_id="s1")
    result = app.answer("  The bank  ", session_id="s1", request_id="reply-1")
    assert result.metadata["structure_clarification"]["reply"] == "  The bank  "
    assert "confidence" not in result.metadata
    assert app.audit_store.log_answer.call_args.kwargs["request_id"] == "reply-1"
    rows = app.scholar_review_queue_store.pending()
    assert len(rows) == 1
    assert rows[0].flag_reason == "structure_evidence_incomplete"


def test_structural_reply_cannot_update_suspended_personal_transaction():
    import copy

    app = service()
    app.answer("I bought an iPhone with deposit EGP 5000 and 12 x EGP 3000.", session_id="s1")
    app.answer("Is Tawarruq permissible?", session_id="s1")
    before = copy.deepcopy(app.session_store.get_session("s1").metadata["described_operation"])
    reply = "The onward sale is arranged by the bank. The financing party is Bank B."
    answer = app.answer(reply, session_id="s1")
    assert answer.metadata["structure_clarification"]["reply"] == reply
    assert app.session_store.get_session("s1").metadata["described_operation"] == before
