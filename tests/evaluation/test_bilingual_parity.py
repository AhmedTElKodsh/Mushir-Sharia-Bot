"""
TestBilingualParity — Arabic and English versions of same query
must produce the same ruling and semantically equivalent answer.

Parity failure modes:
  1. Ruling diverges (Arabic=PROHIBITED, English=PERMISSIBLE) — CRITICAL FAIL
  2. Confidence gap > 0.15 — HIGH concern (may indicate routing difference)
  3. Cited standards differ — MEDIUM concern (tolerated if ruling matches)
"""
from __future__ import annotations

import pytest

from helpers.semantic_similarity import ruling_matches, confidence_gap


@pytest.mark.bilingual
class TestBilingualParity:

    def test_ruling_parity_arabic_vs_english(
        self,
        critical_case: dict,
        pipeline_under_test,
    ):
        """Same semantic query in AR and EN must return same ruling."""
        case = critical_case

        # Run Arabic query
        pipeline_under_test.set_llm_response({
            "ruling": case["expected_ruling"],
            "confidence": 0.85,
            "answer_text": f"Arabic answer for {case['case_id']}",
            "cited_standards": case.get("expected_standards", []),
        })
        ar_result = pipeline_under_test.run(query=case["query_ar"], language="ar")

        # Run English query (same expected outcome)
        pipeline_under_test.set_llm_response({
            "ruling": case["expected_ruling"],
            "confidence": 0.83,
            "answer_text": f"English answer for {case['case_id']}",
            "cited_standards": case.get("expected_standards", []),
        })
        en_result = pipeline_under_test.run(query=case["query_en"], language="en")

        ar_ruling = ar_result.get("ruling")
        en_ruling = en_result.get("ruling")

        assert ar_ruling == en_ruling, (
            f"[CRITICAL FAIL] {case['case_id']}: bilingual ruling divergence!\n"
            f"  Arabic  ({case['query_ar'][:60]}...) → {ar_ruling}\n"
            f"  English ({case['query_en'][:60]}...) → {en_ruling}\n"
            f"  Same semantic query must produce same ruling."
        )

    def test_confidence_parity(
        self,
        critical_case: dict,
        pipeline_under_test,
    ):
        """Confidence gap between Arabic and English must be < 0.15."""
        case = critical_case

        pipeline_under_test.set_llm_response({
            "ruling": case["expected_ruling"],
            "confidence": 0.85,
            "answer_text": "Arabic answer",
            "cited_standards": [],
        })
        ar_result = pipeline_under_test.run(query=case["query_ar"], language="ar")

        pipeline_under_test.set_llm_response({
            "ruling": case["expected_ruling"],
            "confidence": 0.83,
            "answer_text": "English answer",
            "cited_standards": [],
        })
        en_result = pipeline_under_test.run(query=case["query_en"], language="en")

        gap = confidence_gap(
            ar_result.get("confidence", 0.5),
            en_result.get("confidence", 0.5),
        )

        assert gap < 0.15, (
            f"[HIGH] {case['case_id']}: confidence gap = {gap:.3f} (threshold: 0.15)\n"
            f"  AR confidence: {ar_result.get('confidence')}\n"
            f"  EN confidence: {en_result.get('confidence')}\n"
            f"  Possible: Arabic query hitting different retrieval path."
        )
