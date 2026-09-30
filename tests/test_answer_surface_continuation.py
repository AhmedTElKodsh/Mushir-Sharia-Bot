"""Client boundaries use synthetic rule evidence, never production scholar approval."""
import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import get_application_service
from src.api.main import create_app
from src.chatbot.application_service import ApplicationService
from src.chatbot.described_operation import DescribedOperationService
from src.chatbot.session_manager import SessionManager
from src.storage.decision_review_store import SQLiteDecisionReviewStore
from tests.test_api_streaming import _events
from tests.test_approved_card_evaluator import card
from tests.test_l1_contracts import FakeLLM, FakeRetriever
from tests.test_review_blockers import FIRST_TURN, _documented_previous


@pytest.mark.parametrize("endpoint", ["/query", "/query/stream"])
@pytest.mark.parametrize("blocked_by", ["payment_total_discrepancy", "conflicting_user_facts"])
def test_earlier_gate_cannot_publish_a_withheld_rule_result(tmp_path, monkeypatch, endpoint, blocked_by):
    monkeypatch.setenv("DECISION_REVIEW_DB_PATH", str(tmp_path / "startup.sqlite3"))
    story = FIRST_TURN.replace("total EGP", "total payable EGP")
    if blocked_by == "payment_total_discrepancy":
        story = story.replace("41000", "42000")
    _, conversation = DescribedOperationService([]).answer(
        story, session_id="s1", request_id="r1", previous=None, language="en")
    party = next(f for f in conversation.snapshot.facts if f.slot == "financing_party")
    approved = card(material_facts=["financing_party"],
                    outcomes=[dict(when={"financing_party": party.value}, outcome="no_issue_under_this_rule")])
    sessions = SessionManager()
    state = sessions.create_session("s1")
    state.metadata["described_operation"] = _documented_previous(conversation).model_dump(mode="json")
    service = ApplicationService(retriever=FakeRetriever([]), llm_client=FakeLLM("unused"),
        session_store=sessions, approved_rule_cards=[approved],
        decision_store=SQLiteDecisionReviewStore(tmp_path / "decisions.sqlite3"))
    app = create_app()
    app.dependency_overrides[get_application_service] = lambda: service
    reply = "The deposit is EGP 5000" if blocked_by == "payment_total_discrepancy" else "The deposit is EGP 6000"
    with TestClient(app) as client:
        response = client.post("/api/v1" + endpoint, json={"query": reply, "session_id": "s1",
            "context": {"disclaimer_acknowledged": True}})
    assert response.status_code == 200
    body = next(e["data"] for e in _events(response.text) if e["event"] == "done") if endpoint.endswith("stream") else response.json()
    assert body["status"] == "CLARIFICATION_NEEDED"
    assert body["reasoning_summary"] == blocked_by
    assert body["metadata"]["approved_rule_evaluation"]["status"] == "evaluated"
    assert "outcome" not in body["metadata"]["approved_rule_evaluation"]
    assert "supporting_facts" not in body["metadata"]["approved_rule_evaluation"]
    assert "decision_review" not in body["metadata"]
    assert service.decision_store.get(body["metadata"]["review_receipt"]["review_id"]).typed_review is not None
