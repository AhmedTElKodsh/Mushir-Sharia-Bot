"""
TestScholarReviewQueue — auto-enqueue trigger validation.

Tests that the pipeline correctly identifies answers needing
Sharia Scholar review. Missing a review trigger = scholar bypass risk.

Enqueue triggers:
  1. confidence < 0.75
  2. cross-family terminology in answer
  3. forbidden citation detected
"""
from __future__ import annotations

import pytest

from fixtures.scholar_review import ScholarReviewQueue
from fixtures.citation_detector import ForbiddenCitationDetector


class TestScholarReviewQueue:

    def test_low_confidence_triggers_enqueue(
        self,
        any_gold_case: dict,
        pipeline_under_test,
        scholar_review_queue: ScholarReviewQueue,
        forbidden_citation_detector: ForbiddenCitationDetector,
    ):
        """confidence < 0.75 must auto-enqueue for scholar review."""
        case = any_gold_case

        pipeline_under_test.set_llm_response({
            "ruling": case["expected_ruling"],
            "confidence": 0.60,   # Below threshold
            "answer_text": "Uncertain answer text.",
            "cited_standards": [],
        })

        result = pipeline_under_test.run(query=case["query_ar"], language="ar")

        forbidden_detected = forbidden_citation_detector.detect(
            forbidden=case["forbidden_citations"],
            cited_standards=result.get("cited_standards", []),
            answer_text=result.get("answer_text", ""),
        ).has_violation

        enqueued = scholar_review_queue.evaluate_and_enqueue(
            case_id=case["case_id"],
            query=case["query_ar"],
            answer=result,
            forbidden_detected=forbidden_detected,
        )

        assert enqueued, (
            f"[FAIL] {case['case_id']}: confidence=0.60 should trigger "
            f"scholar review enqueue (threshold=0.75), but it did not."
        )
        scholar_review_queue.consume()

    def test_cross_family_term_triggers_enqueue(
        self,
        pipeline_under_test,
        scholar_review_queue: ScholarReviewQueue,
        forbidden_citation_detector: ForbiddenCitationDetector,
    ):
        """Answer containing cross-family signal (Tawarruq) must enqueue."""
        pipeline_under_test.set_llm_response({
            "ruling": "PERMISSIBLE",
            "confidence": 0.80,  # Above threshold — trigger is the term
            "answer_text": "This structure resembles tawarruq and requires further review.",
            "cited_standards": [],
        })

        result = pipeline_under_test.run(
            query="هل يجوز بيع سلعة في السوق ثم إعادة شرائها فوراً؟",
            language="ar",
        )

        enqueued = scholar_review_queue.evaluate_and_enqueue(
            case_id="CROSS_FAMILY_TEST",
            query="cross family signal test",
            answer=result,
            forbidden_detected=False,
        )

        assert enqueued, (
            "[FAIL] Cross-family signal 'tawarruq' in answer_text did not "
            "trigger scholar review enqueue. Scholar bypass risk detected."
        )
        scholar_review_queue.consume()

    def test_high_confidence_clear_ruling_not_enqueued(
        self,
        critical_case: dict,
        pipeline_under_test,
        scholar_review_queue: ScholarReviewQueue,
        forbidden_citation_detector: ForbiddenCitationDetector,
    ):
        """Clear high-confidence answers must NOT generate scholar noise."""
        case = critical_case
        if case["clarification_required"] or case["forbidden_citations"]:
            pytest.skip("Case has inherent review triggers")

        pipeline_under_test.set_llm_response({
            "ruling": case["expected_ruling"],
            "confidence": 0.91,
            "answer_text": "Clear and unambiguous ruling based on AAOIFI standard.",
            "cited_standards": case.get("expected_standards", []),
        })

        result = pipeline_under_test.run(query=case["query_ar"], language="ar")

        enqueued = scholar_review_queue.evaluate_and_enqueue(
            case_id=case["case_id"],
            query=case["query_ar"],
            answer=result,
            forbidden_detected=False,
        )

        assert not enqueued, (
            f"[FAIL] {case['case_id']}: high-confidence clear answer "
            f"was incorrectly enqueued for scholar review. "
            f"This creates scholar queue noise and alert fatigue."
        )
        scholar_review_queue.consume()
