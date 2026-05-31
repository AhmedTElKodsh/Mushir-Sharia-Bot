"""
ForbiddenCitationDetector: scans answer text + cited_standards for forbidden SS numbers.

A CRITICAL FAIL occurs if:
  - Any forbidden_citation appears in the cited_standards list, OR
  - Any forbidden_citation string appears literally in the answer_text

This is a session-scoped stateless helper.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class DetectionResult:
    has_violation: bool
    found_in_citations: list[str]
    found_in_text: list[str]

    @property
    def violated_standards(self) -> list[str]:
        return list(set(self.found_in_citations + self.found_in_text))


class ForbiddenCitationDetector:

    def detect(
        self,
        forbidden: list[str],
        cited_standards: list[str],
        answer_text: str,
    ) -> DetectionResult:
        """
        Returns DetectionResult. Caller decides how to fail.
        """
        found_in_citations: list[str] = []
        found_in_text: list[str] = []

        normalized_cited = [s.upper().strip() for s in cited_standards]
        normalized_text = answer_text.upper()

        for f in forbidden:
            f_norm = f.upper().strip()

            # Check cited standards list (exact match)
            if f_norm in normalized_cited:
                found_in_citations.append(f)

            # Check answer text (word-boundary match to avoid SS-1 matching SS-10)
            pattern = r"\b" + re.escape(f_norm) + r"\b"
            if re.search(pattern, normalized_text):
                found_in_text.append(f)

        return DetectionResult(
            has_violation=bool(found_in_citations or found_in_text),
            found_in_citations=found_in_citations,
            found_in_text=found_in_text,
        )

    def assert_no_violations(
        self,
        forbidden: list[str],
        cited_standards: list[str],
        answer_text: str,
        case_id: str,
    ) -> None:
        result = self.detect(forbidden, cited_standards, answer_text)
        assert not result.has_violation, (
            f"[CRITICAL FAIL] {case_id}: forbidden citations detected!\n"
            f"  Found in cited_standards: {result.found_in_citations}\n"
            f"  Found in answer_text: {result.found_in_text}\n"
            f"  This is a production gate failure (0% tolerance)."
        )
