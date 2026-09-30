from unittest.mock import Mock

import pytest

from src.chatbot.application_service import ApplicationService
from src.chatbot.session_manager import SessionManager
from src.models.ruling import AnswerContract, ComplianceStatus


def make_service(path):
    from src.storage.decision_review_store import SQLiteDecisionReviewStore
    return ApplicationService(retriever=Mock(), llm_client=Mock(), session_store=SessionManager(),
                              decision_store=SQLiteDecisionReviewStore(path))


def test_personal_decision_is_committed_before_answer_returns(tmp_path):
    from src.storage.decision_review_store import SQLiteDecisionReviewStore
    path = tmp_path / "reviews.sqlite3"
    app = make_service(path)
    answer = app.answer("I bought an iPhone with deposit EGP 5000 and 12 x EGP 3000.", session_id="s1", request_id="r1")
    row = SQLiteDecisionReviewStore(path).get(answer.metadata["review_receipt"]["review_id"])
    assert row.query.startswith("I bought")
    assert row.fact_coverage == "typed_snapshot"
    assert row.typed_review.session_id == "s1"
    assert len(row.gates) == 8
    assert row.response["answer"] == answer.answer
    assert row.request_id == "r1"


def test_cached_and_empty_answers_are_logged_without_fabricated_fact_extraction(tmp_path):
    app = make_service(tmp_path / "reviews.sqlite3")
    app._handle_clarification_stage = Mock(return_value=None)
    app._cached_answer = Mock(return_value=AnswerContract(answer="A sourced definition", status=ComplianceStatus.INSUFFICIENT_DATA))
    answer = app.answer("What is murabaha?", session_id="s1")
    row = app.decision_store.get(answer.metadata["review_receipt"]["review_id"])
    assert row.fact_coverage == "not_extracted"
    assert row.typed_review is None
    assert any(g.gate == "typed_extraction" and g.status == "blocked" for g in row.gates)
    empty = app.answer("")
    assert app.decision_store.get(empty.metadata["review_receipt"]["review_id"]).query == ""


def test_storage_failure_prevents_return_of_answer(tmp_path):
    app = make_service(tmp_path / "reviews.sqlite3")
    app.decision_store.append = Mock(side_effect=OSError("disk unavailable"))
    with pytest.raises(OSError):
        app.answer("Is banking Tawarruq permissible?", session_id="s1")


def test_structural_reply_raw_text_and_original_question_are_persisted(tmp_path):
    app = make_service(tmp_path / "reviews.sqlite3")
    app.answer("Is banking Tawarruq permissible?", session_id="s1")
    answer = app.answer("  The bank  ", session_id="s1")
    row = app.decision_store.get(answer.metadata["review_receipt"]["review_id"])
    assert row.query == "  The bank  "
    assert row.response["metadata"]["structure_clarification"]["original_query"] == "Is banking Tawarruq permissible?"


def test_concurrent_records_are_atomic_and_survive_reopening(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from src.models.decision_audit import prepare_decision_record
    from src.storage.decision_review_store import SQLiteDecisionReviewStore

    path = tmp_path / "reviews.sqlite3"
    store = SQLiteDecisionReviewStore(path)
    def write(index):
        answer = AnswerContract(answer="Review required", status=ComplianceStatus.INSUFFICIENT_DATA)
        row = prepare_decision_record(f"query {index}", answer, session_id=f"s{index}", request_id=f"r{index}")
        return store.append(row), index
    with ThreadPoolExecutor(max_workers=8) as pool:
        written = list(pool.map(write, range(24)))
    reopened = SQLiteDecisionReviewStore(path)
    for review_id, index in written:
        assert reopened.get(review_id).query == f"query {index}"


def test_record_cannot_be_overwritten(tmp_path):
    import sqlite3
    app = make_service(tmp_path / "reviews.sqlite3")
    answer = app.answer("Is banking Tawarruq permissible?")
    row = app.decision_store.get(answer.metadata["review_receipt"]["review_id"])
    with pytest.raises(sqlite3.IntegrityError):
        app.decision_store.append(row)
    assert app.decision_store.get(row.review_id) == row


def test_storage_failure_stream_has_error_and_no_answer_event(tmp_path):
    from fastapi.testclient import TestClient
    from src.api.dependencies import get_application_service
    from src.api.main import create_app

    service = make_service(tmp_path / "reviews.sqlite3")
    service.decision_store.append = Mock(side_effect=OSError("disk unavailable secret-detail"))
    app = create_app()
    app.dependency_overrides[get_application_service] = lambda: service
    with TestClient(app) as client:
        response = client.post("/api/v1/query/stream", json={"query": "Is banking Tawarruq permissible?"})
    assert "event: error" in response.text
    assert "event: token" not in response.text
    assert "event: done" not in response.text
    assert "secret-detail" not in response.text


def test_real_api_runtime_has_record_before_response(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from src.api.main import create_app
    from src.storage.decision_review_store import SQLiteDecisionReviewStore
    path = tmp_path / "reviews.sqlite3"
    monkeypatch.setenv("DECISION_REVIEW_DB_PATH", str(path))
    with TestClient(create_app()) as client:
        response = client.post("/api/v1/query", json={"query": "Is banking Tawarruq permissible?",
                                                     "context": {"disclaimer_acknowledged": True}})
    assert response.status_code == 200
    receipt = response.json()["metadata"]["review_receipt"]
    row = SQLiteDecisionReviewStore(path).get(receipt["review_id"])
    assert row.response["status"] == "CLARIFICATION_NEEDED"


def test_failed_write_does_not_advance_conversation(tmp_path):
    import copy
    app = make_service(tmp_path / "reviews.sqlite3")
    app.answer("I bought an iPhone with deposit EGP 5000 and 12 x EGP 3000.", session_id="s1")
    previous = copy.deepcopy(app.session_store.get_session("s1").metadata)
    app.decision_store.append = Mock(side_effect=OSError("disk unavailable"))
    with pytest.raises(OSError):
        app.answer("The bank", session_id="s1")
    assert app.session_store.get_session("s1").metadata == previous


def test_failed_initial_write_does_not_create_pending_question(tmp_path):
    app = make_service(tmp_path / "reviews.sqlite3")
    app.decision_store.append = Mock(side_effect=OSError("disk unavailable"))
    with pytest.raises(OSError):
        app.answer("Is banking Tawarruq permissible?", session_id="s1")
    assert app.session_store.get_session("s1") is None
