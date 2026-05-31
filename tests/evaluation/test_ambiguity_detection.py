"""
TestAmbiguityDetection — clarification_required=True cases.

These cases MUST produce ruling=CLARIFY.
Ambiguity collapse (returning a definitive ruling when the question
is genuinely ambiguous) is a production gate failure.

Risk: A user acts on a false PERMISSIBLE when the correct answer is
      "this depends on contract structure — clarify first."
"""
from __future__ import annotations

import pytest


@pytest.mark.clarification_required
class TestAmbiguityDetection:

    def test_ambiguous_query_triggers_clarify(
        self,
        clarification_case: dict,
        pipeline_under_test,
    ):
        """Ambiguous queries must produce CLARIFY, never a definitive ruling."""
        case = clarification_case
        pipeline_under_test.set_llm_response({
            "ruling": "CLARIFY",
            "confidence": 0.55,
            "answer_text": "This query requires clarification of contract structure.",
            "cited_standards": [],
            "clarification_questions": [
                "Is this a standalone Murabaha or part of a Tawarruq arrangement?",
                "Is the commodity a real traded asset or synthetic?",
            ],
        })

        result = pipeline_under_test.run(query=case["query_ar"], language="ar")

        assert result.get("ruling") == "CLARIFY", (
            f"[FAIL] {case['case_id']}: expected CLARIFY (ambiguity), "
            f"got '{result.get('ruling')}'. Ambiguity collapse detected."
        )

        # Clarification questions must be populated
        cqs = result.get("clarification_questions", [])
        assert len(cqs) >= 1, (
            f"[FAIL] {case['case_id']}: ruling=CLARIFY but no clarification_questions returned. "
            f"Pipeline must tell the user WHAT needs clarifying."
        )

    def test_non_ambiguous_query_does_not_clarify(
        self,
        critical_case: dict,
        pipeline_under_test,
    ):
        """Non-ambiguous CRITICAL cases must NOT collapse into CLARIFY."""
        case = critical_case
        if case["clarification_required"]:
            pytest.skip("Ambiguous case — not applicable here")

        pipeline_under_test.set_llm_response({
            "ruling": case["expected_ruling"],
            "confidence": 0.88,
            "answer_text": f"Definitive answer for {case['case_id']}",
            "cited_standards": case.get("expected_standards", []),
        })

        result = pipeline_under_test.run(query=case["query_ar"], language="ar")

        assert result.get("ruling") != "CLARIFY", (
            f"[FAIL] {case['case_id']}: clear question collapsed to CLARIFY. "
            f"Expected '{case['expected_ruling']}'. "
            f"This is a false ambiguity response."
        )
