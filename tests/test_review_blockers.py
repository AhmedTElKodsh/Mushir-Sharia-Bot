"""Regression tests for the 2026-09-30 review blockers (synthetic fixtures only)."""
import pytest

from src.chatbot.application_service import ApplicationService
from src.chatbot.commercial_assessment import QuestionType, ScenarioExtractor
from src.chatbot.described_operation import DescribedOperationService
from src.governance.scholar_review import ScholarReviewQueue, ScholarReviewQueueItem
from src.models.evidence import EvidenceScope, FactObservation, FactSnapshot, SourceProvenance
from src.models.ruling import AnswerContract, ComplianceStatus
from tests.test_approved_card_evaluator import card
from tests.test_l1_contracts import FakeLLM, FakeRetriever, _chunk

FIRST_TURN = ("I bought an iPhone from the store with deposit EGP 5000 and 12 x EGP 3000, "
              "total EGP 41000. Financed by the store itself.")


def _question_type(text):
    return ScenarioExtractor().extract(text).question_type


@pytest.mark.parametrize("text", [
    "What did the American bank publish about instalment reports?",
    "Please scan the disclosure section of the standard.",
])
def test_can_inside_a_word_is_not_a_permission_ask(text):
    assert _question_type(text) != QuestionType.PERMISSIBILITY


@pytest.mark.parametrize("text", ["Can we charge a late fee?", "can I buy this on instalments"])
def test_real_permission_asks_stay_permissibility(text):
    assert _question_type(text) == QuestionType.PERMISSIBILITY


@pytest.mark.parametrize("query", [
    "What is Islamic financing?",
    "What does AAOIFI FAS 28 say about financing?",
    "What does riba mean?",
])
def test_knowledge_questions_do_not_hit_the_approved_rule_gate(query):
    service = ApplicationService(
        retriever=FakeRetriever([_chunk(standard_id="SS-08", metadata={
            "source_family": "sharia_standard", "standard_number": "SS-08", "metadata_status": "cataloged"})]),
        llm_client=FakeLLM("Grounded explanation [SS-08]"))
    assert "approved_rule_gate" not in service.answer(query).metadata


def test_queue_item_without_a_score_does_not_invent_one():
    answer = AnswerContract(answer="needs review", status=ComplianceStatus.INSUFFICIENT_DATA)
    item = ScholarReviewQueueItem.from_answer(queue=ScholarReviewQueue.AUTO_FLAGGED, query="q",
                                              answer=answer, flag_reason="test")
    assert item.system_confidence is None
    assert item.to_dict()["system_confidence"] is None


def test_queue_item_keeps_and_clamps_a_real_score():
    item = ScholarReviewQueueItem(query_id="q", queue=ScholarReviewQueue.AUTO_FLAGGED,
                                  flag_reason="test", system_confidence=1.4)
    assert item.system_confidence == 1.0


def _documented_previous(conversation):
    scope = conversation.snapshot.facts[0].scope
    stamp = conversation.snapshot.recorded_at
    mechanism = FactObservation(
        slot="mechanism_archetype", value="fixture-arc", scope=scope, version=conversation.snapshot.version,
        recorded_at=stamp, status="observed",
        source=SourceProvenance(
            capture=dict(source_id="fx", url="https://example.org/fx", captured_at=stamp, sha256="a" * 64,
                         document_version="v1", content_type="text/plain", language="en", access_status="accessible"),
            document_class="transaction_specific_disclosure", exact_text="Synthetic fixture", span_id="fx", scope=scope))
    snapshot = FactSnapshot(snapshot_id=conversation.snapshot.snapshot_id, version=conversation.snapshot.version,
                            recorded_at=stamp, facts=(*conversation.snapshot.facts, mechanism))
    return conversation.model_copy(update={"snapshot": snapshot})


def test_evaluated_rule_is_withheld_without_asking_for_the_rule_again():
    _, conversation = DescribedOperationService([]).answer(
        FIRST_TURN, session_id="s1", request_id="r1", previous=None, language="en")
    party = next(fact for fact in conversation.snapshot.facts if fact.slot == "financing_party")
    approved = card(material_facts=["financing_party"],
                    outcomes=[dict(when={"financing_party": party.value}, outcome="no_issue_under_this_rule")])
    contract, _ = DescribedOperationService([approved]).answer(
        "The deposit was EGP 5000", session_id="s1", request_id="r2",
        previous=_documented_previous(conversation), language="en")
    review = contract.metadata["decision_review"]
    assert contract.metadata["approved_rule_evaluation"]["status"] == "evaluated"
    assert contract.status == ComplianceStatus.INSUFFICIENT_DATA
    assert contract.reasoning_summary == "approved_rule_evaluated_overall_gates_pending"
    assert "scholar-approved rule mapping" not in contract.answer
    gates = {gate["gate"]: gate["status"] for gate in review["decision"]["gates"]}
    assert gates["material_fact"] == "passed"
    assert gates["selective_answer"] == "blocked"
