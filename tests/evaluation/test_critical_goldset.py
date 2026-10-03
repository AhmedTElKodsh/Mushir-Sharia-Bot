"""
TestCriticalGoldSet — zero-tolerance tier.

Any single failure here = CRITICAL FAIL for the entire build.
These cases represent the highest-risk Sharia rulings where incorrect
output produces real-world harm (false fatwa, prohibited transaction
presented as permissible).

Risk calculation: P(harm) × severity × frequency
  CRITICAL cases: severity=10, P(harm)=0.9 (high consequence sector)
  → Risk score > 9.0 → zero-tolerance boundary

Run: pytest tests/evaluation/test_critical_goldset.py -m critical_goldset -x
"""
from __future__ import annotations

import re

import pytest

from fixtures.citation_detector import ForbiddenCitationDetector
from fixtures.scholar_review import ScholarReviewQueue
from fixtures.pipeline import build_pipeline_under_test


@pytest.mark.critical_goldset
class TestCriticalGoldSet:
    """
    Zero-tolerance: any failure = CRITICAL FAIL.
    The `-x` flag must be set in CI for this class.
    """

    def test_ruling_correctness(
        self,
        critical_case: dict,
        pipeline_under_test,
        forbidden_citation_detector: ForbiddenCitationDetector,
        confidence_calibration_bucket,
    ):
        """
        With a scholar-approved rule card: the exact expected_ruling, no partial credit.
        Without one: correct abstention at the approved-rule gate (a V1.6 feature).
        """
        case = critical_case
        # Clarification-required cases are verified in test_clarification_trigger.
        # In a single-turn run, the pipeline correctly returns CLARIFY; the
        # expected_ruling (e.g., DISPUTED) reflects the scholar's ruling once
        # clarification has been provided, not the first-turn response.
        if case.get("clarification_required"):
            pytest.skip("Clarification case — covered by test_clarification_trigger")

        pipeline_under_test.set_llm_response(
            _scripted_response_for(case)
        )

        result = pipeline_under_test.run(query=case["query_ar"], language="ar")

        # The gold set tests features (user decision, 2026-10-01). Until a scholar-approved
        # rule card covers the case, the feature under test is correct abstention; the
        # developer-written expected_ruling stays in the YAML as the scholar-pending target.
        if not _approved_card_covers(case, pipeline_under_test):
            _assert_abstains_for_the_right_reason(case, result)
            forbidden_citation_detector.assert_no_violations(
                forbidden=case["forbidden_citations"],
                cited_standards=result.get("cited_standards", []),
                answer_text=result.get("answer_text", ""),
                case_id=case["case_id"],
            )
            return

        # 1. Ruling must match exactly
        actual_ruling = result.get("ruling")
        assert actual_ruling == case["expected_ruling"], (
            f"[CRITICAL FAIL] {case['case_id']}: "
            f"expected ruling '{case['expected_ruling']}', "
            f"got '{actual_ruling}'.\n"
            f"Query: {case['query_ar']}\n"
            f"This is a FALSE FATWA — production gate failure."
        )

        # 2. Forbidden citations must not appear
        forbidden_citation_detector.assert_no_violations(
            forbidden=case["forbidden_citations"],
            cited_standards=result.get("cited_standards", []),
            answer_text=result.get("answer_text", ""),
            case_id=case["case_id"],
        )

        # 3. Record calibration data
        is_correct = actual_ruling == case["expected_ruling"]
        confidence_calibration_bucket.record(
            case_id=case["case_id"],
            predicted_confidence=result.get("confidence", result.get("metadata", {}).get("confidence", 0.95)),
            actual_correct=is_correct,
        )

    def test_clarification_trigger(
        self,
        critical_case: dict,
        pipeline_under_test,
        scholar_review_queue: ScholarReviewQueue,
        forbidden_citation_detector: ForbiddenCitationDetector,
    ):
        """
        If clarification_required=True, pipeline MUST return ruling=CLARIFY.
        If clarification_required=False, pipeline MUST NOT return CLARIFY.
        """
        case = critical_case
        if not case["clarification_required"]:
            pytest.skip("Not a clarification case")

        pipeline_under_test.set_llm_response(_scripted_response_for(case))
        result = pipeline_under_test.run(query=case["query_ar"], language="ar")

        assert result.get("ruling") == "CLARIFY", (
            f"[CRITICAL FAIL] {case['case_id']}: "
            f"clarification_required=True but ruling='{result.get('ruling')}'. "
            f"Ambiguity collapse — production gate failure."
        )

        # Clarification cases must also land in scholar review queue
        forbidden_detected = forbidden_citation_detector.detect(
            forbidden=case["forbidden_citations"],
            cited_standards=result.get("cited_standards", []),
            answer_text=result.get("answer_text", ""),
        ).has_violation

        scholar_review_queue.evaluate_and_enqueue(
            case_id=case["case_id"],
            query=case["query_ar"],
            answer=result,
            forbidden_detected=forbidden_detected,
        )
        scholar_review_queue.assert_enqueued(case["case_id"])
        scholar_review_queue.consume()  # consume so teardown passes


_ARABIC = re.compile(r"[؀-ۿ]")


def _approved_card_covers(case: dict, pipeline_under_test) -> bool:
    """A case is verdict-eligible only when it names a rule card the runtime holds as approved."""
    rule_card = case.get("rule_card")
    if not rule_card:
        return False
    cards = pipeline_under_test.pipeline.described_operations.evaluator.cards
    return any(card.rule_id == rule_card for card in cards)


def _assert_abstains_for_the_right_reason(case: dict, result: dict) -> None:
    """Abstention is a feature only when it is the approved-rule gate that stopped the answer:
    the question was understood as a judgment, its sources are shown, it answers in the
    user's language, and it is queued for the scholar."""
    case_id = case["case_id"]
    assert result.get("ruling") == "INSUFFICIENT_DATA", (
        f"[CRITICAL FAIL] {case_id}: no approved rule card covers this case, "
        f"yet the runtime returned '{result.get('ruling')}'. This is an unearned verdict."
    )
    metadata = result.get("metadata") or {}
    decided_by = (metadata.get("decision_trace") or {}).get("decided_by") or {}
    assert decided_by == {"gate": "approved_rule", "reason_code": "approved_rule_missing"}, (
        f"{case_id}: abstained at {decided_by}, not at the approved-rule gate"
    )
    assert metadata.get("requires_scholar_review") is True, f"{case_id}: not queued for scholar review"
    assert result.get("cited_standards"), f"{case_id}: abstention shows no supporting sources"
    assert _ARABIC.search(result.get("answer_text", "")), f"{case_id}: Arabic question not answered in Arabic"


def _scripted_response_for(case: dict) -> dict:
    """
    Build the mock LLM response the pipeline will return for this case.
    In real tests, this drives from the case's expected values.
    Used to test that the routing + validation layers process it correctly.
    """
    ruling = "CLARIFY" if case.get("clarification_required") else case["expected_ruling"]
    confidence = 0.60 if ruling == "CLARIFY" else 0.82
    return {
        "ruling": ruling,
        "confidence": confidence,
        "answer_text": f"Mock answer for {case['case_id']}",
        "cited_standards": case.get("expected_standards", []),
    }


def test_pipeline_fixture_does_not_backfill_scripted_ruling_when_runtime_differs():
    pipeline = build_pipeline_under_test()
    try:
        pipeline.set_llm_response(
            {
                "ruling": "PERMISSIBLE",
                "confidence": 0.91,
                "answer_text": "scripted value must not be copied into result",
                "cited_standards": [],
            }
        )
        result = pipeline.run("What is an unrelated undefined concept?", language="en")
    finally:
        pipeline.teardown()

    assert result["ruling"] != "PERMISSIBLE"
    assert result.get("cited_standards", []) == []
