"""Only an evaluated, scholar-approved rule may deliver a compliance verdict.

GC-004/011/018 once passed because permissibility questions were routed to FAS
accounting standards (requires_rule_evaluation=False) and the LLM's own verdict
text became the ruling. The final guard must hold regardless of route or cache.
"""
from pathlib import Path

import pytest
import yaml

from src.chatbot.application_service import ApplicationService
from src.models.ruling import AAOIFICitation, AnswerContract, ComplianceStatus

VERDICTS = [ComplianceStatus.COMPLIANT, ComplianceStatus.NON_COMPLIANT, ComplianceStatus.PARTIALLY_COMPLIANT]
GOLD = Path(__file__).parent / "evaluation" / "gold_set" / "critical"


def _service_returning(contract, store=None):
    service = ApplicationService(llm_client=object(), retriever=object())
    service.decision_store = store
    service._answer = lambda *args, **kwargs: contract
    return service


def _generated_verdict(status, language="en"):
    return AnswerContract(
        answer=f"{status.value}: generated verdict [SS-13]",
        status=status,
        citations=[AAOIFICitation(document_id="SS-13", standard_number="SS-13", excerpt="literal text")],
        metadata={"response_language": language, "decision_basis": "literal_passage_cited",
                  "standards_route": {"route_id": "mudaraba-accounting", "requires_rule_evaluation": False}},
    )


class _Store:
    def __init__(self):
        self.records = []

    def append(self, record):
        self.records.append(record)
        return record.review_id


@pytest.mark.parametrize("status", VERDICTS)
@pytest.mark.parametrize("language", ["en", "ar"])
@pytest.mark.parametrize("committed", [False, True])
def test_verdict_without_approved_rule_is_withheld_on_every_delivery_path(status, language, committed):
    store = _Store() if committed else None
    answer = _service_returning(_generated_verdict(status, language), store).answer("question")

    assert answer.status == ComplianceStatus.INSUFFICIENT_DATA
    assert answer.citations == []
    assert status.value not in answer.answer.replace("INSUFFICIENT_DATA", "")
    assert answer.metadata["approved_rule_gate"] == {"status": "blocked", "reason": "verdict_without_approved_rule"}
    trace = answer.metadata["decision_trace"]
    assert trace["decided_by"] == {"gate": "approved_rule", "reason_code": "approved_rule_missing"}
    assert trace["sources"] == []
    if committed:
        # The committed review record must show the withheld status, never the generated verdict.
        assert len(store.records) == 1
        assert store.records[0].response["status"] == "INSUFFICIENT_DATA"


@pytest.mark.parametrize("evaluation", [None, {}, {"status": "blocked"}, {"status": "EVALUATED"}, "evaluated"])
def test_only_exact_evaluated_status_counts_as_approval(evaluation):
    contract = _generated_verdict(ComplianceStatus.COMPLIANT)
    if evaluation is not None:
        contract.metadata["approved_rule_evaluation"] = evaluation
    assert _service_returning(contract).answer("question").status == ComplianceStatus.INSUFFICIENT_DATA


def test_evaluated_approved_rule_verdict_passes_unchanged():
    contract = _generated_verdict(ComplianceStatus.NON_COMPLIANT)
    contract.metadata["approved_rule_evaluation"] = {"status": "evaluated"}
    answer = _service_returning(contract).answer("question")
    assert answer.status == ComplianceStatus.NON_COMPLIANT
    assert len(answer.citations) == 1


@pytest.mark.parametrize("case_id", ["GC-004", "GC-011", "GC-018"])
def test_arabic_permissibility_question_with_literal_quote_verdict_is_withheld(case_id):
    """Worst case: the writer quotes the retrieved passage exactly and prefixes a verdict.

    These questions once routed to FAS accounting (deferred-work item 8). They now route to
    rule evaluation, and the verdict is still withheld without an approved rule card.
    """
    from tests.evaluation.fixtures.pipeline import build_pipeline_under_test

    case = yaml.safe_load((GOLD / f"{case_id}.yaml").read_text(encoding="utf-8"))
    pipeline = build_pipeline_under_test()
    try:
        response = {"ruling": case["expected_ruling"], "answer_text": "", "cited_standards": case["expected_standards"]}
        pipeline.set_llm_response(response)
        standard = case["expected_standards"][0]
        quote = (f"AAOIFI {standard} fixture evidence. This retrieved excerpt supports "
                 f"the deterministic evaluation response for {standard}.")
        prefix = {"PROHIBITED": "NON_COMPLIANT", "PERMISSIBLE": "COMPLIANT"}[case["expected_ruling"]]
        pipeline.mock_llm.generate.return_value = f"{prefix}: {quote} [{standard}]"
        result = pipeline.run(case["query_ar"], language="ar")
    finally:
        pipeline.teardown()

    assert result["metadata"]["standards_route"]["requires_rule_evaluation"] is True
    assert result["ruling"] == "INSUFFICIENT_DATA"
    assert result["metadata"]["decision_trace"]["decided_by"]["gate"] == "approved_rule"
