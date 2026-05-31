"""
ScholarReviewQueue: captures answers that must be sent to Sharia Scholar review.

Auto-enqueue triggers (from architecture agreement):
  1. pipeline.confidence < 0.75
  2. cross-family terminology detected in answer
  3. forbidden citation detected in answer OR cited standards
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


CONFIDENCE_THRESHOLD = 0.75

# Terms that signal cross-family ambiguity requiring scholar sign-off
CROSS_FAMILY_SIGNALS = {
    "tawarruq", "التورق",
    "bay al-wafa", "بيع الوفاء",
    "organised tawarruq", "التورق المنظم",
    "commodity murabaha", "مرابحة السلع",
}


@dataclass
class ReviewEntry:
    case_id: str
    query: str
    answer: dict[str, Any]
    trigger_reason: str
    confidence: float


class ScholarReviewQueue:
    def __init__(self) -> None:
        self.pending: list[ReviewEntry] = []

    def evaluate_and_enqueue(
        self,
        case_id: str,
        query: str,
        answer: dict[str, Any],
        forbidden_detected: bool = False,
    ) -> bool:
        """
        Returns True if enqueued, False if answer passed all thresholds.
        """
        confidence = answer.get("confidence", 1.0)
        answer_text = answer.get("answer_text", "").lower()
        cited = [s.lower() for s in answer.get("cited_standards", [])]

        reasons: list[str] = []

        if confidence < CONFIDENCE_THRESHOLD:
            reasons.append(f"low_confidence({confidence:.2f})")

        for signal in CROSS_FAMILY_SIGNALS:
            if signal.lower() in answer_text:
                reasons.append(f"cross_family_signal({signal})")
                break

        if forbidden_detected:
            reasons.append("forbidden_citation_detected")

        if reasons:
            self.pending.append(
                ReviewEntry(
                    case_id=case_id,
                    query=query,
                    answer=answer,
                    trigger_reason="|".join(reasons),
                    confidence=confidence,
                )
            )
            return True
        return False

    def consume(self) -> list[ReviewEntry]:
        items = self.pending.copy()
        self.pending.clear()
        return items

    def assert_enqueued(self, case_id: str) -> None:
        ids = [e.case_id for e in self.pending]
        assert case_id in ids, (
            f"Expected case {case_id} to be in scholar review queue, "
            f"but queue contains: {ids}"
        )

    def assert_not_enqueued(self, case_id: str) -> None:
        ids = [e.case_id for e in self.pending]
        assert case_id not in ids, (
            f"Case {case_id} was unexpectedly enqueued for scholar review. "
            f"Trigger: {next(e.trigger_reason for e in self.pending if e.case_id == case_id)}"
        )
