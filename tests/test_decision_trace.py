"""The showcase trace describes observed state without publishing private diagnostics."""

import json
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import get_application_service
from src.api.main import create_app
from src.chatbot.application_service import ApplicationService
from src.chatbot.session_manager import SessionManager
from src.models.decision_audit import prepare_decision_record
from src.models.ruling import AAOIFICitation, AnswerContract, ComplianceStatus
from src.storage.decision_review_store import SQLiteDecisionReviewStore, configured_decision_store
from tests.test_api_streaming import _events


STORY = "I bought an iPhone with deposit EGP 5000 and 12 x EGP 3000. Is it halal?"


def service(tmp_path):
    return ApplicationService(retriever=Mock(), llm_client=Mock(model_name="fixture"), session_store=SessionManager(),
                              decision_store=SQLiteDecisionReviewStore(tmp_path / "reviews.sqlite3"))


def test_described_answer_has_typed_trace_and_committed_same_trace(tmp_path):
    app = service(tmp_path)
    answer = app.answer(STORY, session_id="trace-one")
    trace = answer.metadata["decision_trace"]
    assert trace["understood_as"] == {"lane": "described_operation", "language": "en", "mechanism": "unknown"}
    assert trace["decided_by"] == {"gate": "clarification", "reason_code": "financing_party_unknown"}
    assert trace["question_asked"] == answer.clarification_question
    assert {row["slot"]: row["value"] for row in trace["known"] if "value" in row}["instalment_count"] == "12"
    assert any(row["slot"] == "financing_party" and row["status"] == "unknown" for row in trace["missing"])
    assert trace["sources"] == []
    assert all(row["state"] in {"unknown", "conflicting", "observed", "user_reported"}
               for row in trace["would_decide"])
    stored = app.decision_store.get(answer.metadata["review_receipt"]["review_id"])
    assert stored.response["metadata"]["decision_trace"] == trace


def test_arabic_trace_follows_user_reply_and_guarded_judgment(tmp_path):
    app = service(tmp_path)
    first = app.answer("عايز اشتري آيفون بمقدم ٥٠٠٠ جنيه و١٢ قسط كل قسط ٣٠٠٠ جنيه. حلال؟", session_id="ar-one")
    assert first.metadata["decision_trace"]["understood_as"]["language"] == "ar"
    second = app.answer("لا أدري", session_id="ar-one")
    assert second.status == ComplianceStatus.INSUFFICIENT_DATA
    assert second.metadata["decision_trace"]["decided_by"]["gate"] == "material_fact"
    assert second.metadata["decision_trace"]["sources"] == []


def test_unavailable_retrieval_is_explained_without_fabricating_sources(tmp_path):
    app = service(tmp_path)
    app._handle_clarification_stage = Mock(return_value=None)
    app.llm_client.model_name = "fixture"
    app.retriever.retrieve.side_effect = TimeoutError("provider unavailable")
    answer = app.answer("What is murabaha?", session_id="retrieval-down")
    assert answer.status == ComplianceStatus.INSUFFICIENT_DATA
    assert answer.metadata["decision_trace"]["decided_by"] == {
        "gate": "retrieval", "reason_code": "retrieval_unavailable"}
    assert answer.metadata["decision_trace"]["sources"] == []


def test_trace_uses_final_citations_not_retrieval_candidates_or_llm_text():
    citation = AAOIFICitation(document_id="official-8", standard_number="SS-08", section_number="3/1")
    answer = AnswerContract(answer="A definition [SS-08]", status=ComplianceStatus.INSUFFICIENT_DATA,
                            citations=[citation], reasoning_summary="private generated explanation",
                            metadata={"response_language": "en", "answer_kind": "definition",
                                      "retrieved_chunk_ids": ["unused", "SS-08:3/1"]})
    trace = ApplicationService._attach_decision_trace(answer).metadata["decision_trace"]
    assert trace["understood_as"]["lane"] == "definition"
    assert trace["decided_by"]["reason_code"] == "definition_cited"
    assert trace["sources"] == [{"document_id": "official-8", "standard": "SS-08",
                                 "section": "3/1", "captured_at": None,
                                 "quote_start": None, "quote_end": None, "version": None}]
    assert "unused" not in json.dumps(trace)
    assert "private generated" not in json.dumps(trace)


def test_llm_clarification_does_not_copy_generated_question_into_trace():
    answer = AnswerContract(answer="Could you share the contract?", status=ComplianceStatus.CLARIFICATION_NEEDED,
                            clarification_question="Could you share the contract?")
    trace = ApplicationService._attach_decision_trace(answer).metadata["decision_trace"]
    assert trace["question_asked"] is None
    assert trace["decided_by"]["reason_code"] == "clarification_requested"
    assert "Could you" not in json.dumps(trace)


def test_legacy_cached_response_marks_execution_history_unavailable():
    answer = AnswerContract(answer="Previously cached", status=ComplianceStatus.INSUFFICIENT_DATA,
                            metadata={"trace_unavailable": True})
    trace = ApplicationService._attach_decision_trace(answer).metadata["decision_trace"]
    assert trace["decided_by"] == {"gate": "unavailable", "reason_code": "legacy_trace_unavailable"}


def test_response_cache_saves_trace_before_outer_answer_returns():
    app = ApplicationService(retriever=Mock(), llm_client=Mock(), cache_store=Mock())
    app.llm_client.model_name = "fixture"
    answer = AnswerContract(answer="Source-based definition", status=ComplianceStatus.INSUFFICIENT_DATA,
                            citations=[AAOIFICitation(document_id="d8", standard_number="SS-08")],
                            metadata={"answer_kind": "definition", "response_language": "ar"})
    app._cache_answer("ما هي المرابحة؟", answer)
    saved = app.cache_store.set_json.call_args.args[2]
    assert saved["metadata"]["decision_trace"]["decided_by"]["reason_code"] == "definition_cited"
    app.cache_store.get_json.return_value = saved
    restored = app._attach_decision_trace(app._cached_answer("ما هي المرابحة؟"))
    assert restored.metadata["decision_trace"] == saved["metadata"]["decision_trace"]
    assert "trace_unavailable" not in restored.metadata


@pytest.mark.parametrize("query", ["Is a murabaha purchase permissible?", "هل شراء السيارة بالمرابحة جائز؟"])
def test_real_unapproved_judgment_trace_names_the_blocking_gate(query):
    from tests.test_approved_application_gate import judgment_service
    app = judgment_service()
    app._handle_clarification_stage = Mock(return_value=None)
    answer = app.answer(query)
    assert answer.status == ComplianceStatus.INSUFFICIENT_DATA
    assert answer.metadata["decision_trace"]["decided_by"] == {
        "gate": "approved_rule", "reason_code": "approved_rule_missing"}
    assert app.llm_client.prompts == []


def test_router_weights_are_private_but_survive_in_review_record():
    answer = AnswerContract(answer="Who finances it?", status=ComplianceStatus.CLARIFICATION_NEEDED,
                            clarification_question="Who finances it?",
                            metadata={"router_signals": {"surface:murabaha": 0.4},
                                      "retrieval_threshold": "0.3", "source_confidence": "official"})
    answer = ApplicationService._attach_decision_trace(answer)
    record = prepare_decision_record("query", answer, session_id="s", request_id="r")
    public = answer.to_dict()
    assert record.internal_signals["router_signals"] == {"surface:murabaha": 0.4}
    assert "router_signals" not in public["metadata"]
    assert "retrieval_threshold" not in public["metadata"]
    assert public["metadata"]["source_confidence"] == "official"
    assert "0.4" not in json.dumps(public["metadata"]["decision_trace"])


def test_real_router_clarification_assigns_private_signals_at_decision_site():
    app = ApplicationService(retriever=Mock(), llm_client=Mock())
    app._scenario_clarification_question = Mock(return_value="Which party delayed?")
    app._remember_scenario_clarification = Mock()
    contract = app._handle_clarification_stage(
        "question", None, None, Mock(signals={"candidate_weight": 0.7}), None,
        "s", "r", "en")
    assert contract.internal_signals["router_signals"] == {"candidate_weight": 0.7}
    assert app._attach_decision_trace(contract).metadata["decision_trace"]["question_asked"] == "Which party delayed?"
    assert "router_signals" not in contract.to_dict()["metadata"]
    record = prepare_decision_record("question", app._attach_decision_trace(contract), session_id="s", request_id="r")
    assert record.internal_signals["router_signals"] == {"candidate_weight": 0.7}


@pytest.mark.parametrize("endpoint", ["/api/v1/query", "/api/v1/query/stream"])
def test_rest_and_sse_done_include_same_safe_trace(tmp_path, endpoint):
    app_service = service(tmp_path)
    app = create_app()
    app.dependency_overrides[get_application_service] = lambda: app_service
    with TestClient(app) as client:
        result = client.post(endpoint, json={"query": STORY, "session_id": "api-" + endpoint,
                                             "context": {"disclaimer_acknowledged": True}})
    assert result.status_code == 200
    body = next(row["data"] for row in _events(result.text) if row["event"] == "done") if endpoint.endswith("stream") else result.json()
    trace = body["metadata"]["decision_trace"]
    assert trace["decided_by"]["reason_code"] == "financing_party_unknown"
    assert "router_signals" not in body["metadata"]
    assert "decision_review" not in body["metadata"]
    stored = app_service.decision_store.get(body["metadata"]["review_receipt"]["review_id"])
    assert stored.response["metadata"]["decision_trace"] == trace


def test_strict_mirror_requires_valid_remote_configuration(monkeypatch):
    monkeypatch.setenv("DECISION_REVIEW_REQUIRE_MIRROR", "true")
    with pytest.raises(RuntimeError, match="requires a valid PostgreSQL URL"):
        configured_decision_store()
    monkeypatch.setenv("DECISION_REVIEW_DATABASE_URL", "postgresql://no-database-host")
    with pytest.raises(RuntimeError, match="configuration is invalid"):
        configured_decision_store()


@pytest.mark.parametrize("variable", ["SPACE_ID", "SPACE_HOST"])
def test_space_requires_mirror_despite_explicit_false(variable, monkeypatch):
    from src.storage import postgres_decision_review_store as pg
    monkeypatch.setenv(variable, "fixture-space")
    monkeypatch.setenv("DECISION_REVIEW_REQUIRE_MIRROR", "false")
    with pytest.raises(RuntimeError, match="requires a valid PostgreSQL URL"):
        configured_decision_store()
    monkeypatch.setenv("DECISION_REVIEW_DATABASE_URL", "postgresql://fixture.invalid/db")
    monkeypatch.setattr(pg, "PostgresDecisionReviewStore", Mock(return_value=Mock()))
    assert configured_decision_store().require_mirror is True


@pytest.mark.parametrize("url", ["postgresql://host:abc/db", "postgresql://host:65536/db", "postgresql://[bad/db"])
def test_malformed_mirror_url_fails_configuration_before_opening_stores(monkeypatch, url):
    monkeypatch.setenv("DECISION_REVIEW_DATABASE_URL", url)
    with pytest.raises(RuntimeError, match="configuration is invalid"):
        configured_decision_store()


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", "inf", "1e-3", "0.7%"])
def test_encoded_internal_numbers_are_scrubbed(value):
    from src.models.evidence_display import without_answer_scores
    assert without_answer_scores({"retrieval_score": value, "threshold": value,
                                  "source_confidence": "official"}) == {"source_confidence": "official"}


def test_actual_scope_refusal_and_empty_request_have_scope_explanations(tmp_path):
    app = service(tmp_path)
    refusal = app.answer("Give me a binding fatwa", session_id="scope")
    assert refusal.metadata["decision_trace"]["decided_by"] == {"gate": "scope", "reason_code": "scope_refusal"}
    assert app.answer(" ").metadata["decision_trace"]["decided_by"] == {"gate": "scope", "reason_code": "empty_request"}


@pytest.mark.parametrize("query,reply", [("Is tawarruq halal?", "The bank"), ("هل التورق حلال؟", "البنك")])
def test_structural_reply_keeps_unverified_slot_and_explains_terminal_gate(tmp_path, query, reply):
    app = service(tmp_path)
    first = app.answer(query, session_id="structure")
    assert first.metadata["decision_trace"]["would_decide"] == [{"condition": "resale_arranger", "state": "unknown"}]
    final = app.answer(reply, session_id="structure")
    assert final.status == ComplianceStatus.INSUFFICIENT_DATA
    trace = final.metadata["decision_trace"]
    assert trace["decided_by"] == {"gate": "approved_rule", "reason_code": "structure_evidence_incomplete"}
    assert trace["question_asked"] is None
    assert trace["known"] == []  # The structure lane has not verified/extracted the free-text reply.


def test_evaluated_rule_trace_names_selective_answer_blocker():
    from tests.test_review_blockers import FIRST_TURN, _documented_previous
    from tests.test_approved_card_evaluator import card
    from src.chatbot.described_operation import DescribedOperationService
    _, state = DescribedOperationService([]).answer(FIRST_TURN, session_id="s1", request_id="r1", previous=None, language="en")
    party = next(f for f in state.snapshot.facts if f.slot == "financing_party")
    approved = card(material_facts=["financing_party"], outcomes=[dict(when={"financing_party": party.value}, outcome="no_issue_under_this_rule")])
    answer, _ = DescribedOperationService([approved]).answer("The deposit was EGP 5000", session_id="s1", request_id="r2",
                                                          previous=_documented_previous(state), language="en")
    trace = ApplicationService._attach_decision_trace(answer).metadata["decision_trace"]
    assert trace["decided_by"] == {"gate": "selective_answer", "reason_code": "approved_rule_evaluated_overall_gates_pending"}
    assert "no_issue_under_this_rule" not in json.dumps(trace)
    from src.models.evidence import FACT_SLOTS
    assert {x["condition"] for x in trace["would_decide"]} == set(FACT_SLOTS)


def test_trace_preserves_passage_offsets_and_explicit_unknown_version():
    citation = AAOIFICitation(document_id="d8", standard_number="SS-08", quote_start=12, quote_end=67)
    answer = AnswerContract(answer="definition", status=ComplianceStatus.INSUFFICIENT_DATA, citations=[citation])
    ref = ApplicationService._attach_decision_trace(answer).metadata["decision_trace"]["sources"][0]
    assert (ref["quote_start"], ref["quote_end"], ref["version"]) == ("12", "67", None)
