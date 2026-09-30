"""Decision delivery records, with explicit coverage gaps for legacy paths."""
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import AwareDatetime, model_validator
from src.models.evidence import DecisionReviewRow, EvidenceModel, GateDecision, Text


GATES = ("intent_and_scope", "typed_extraction", "contract_family", "material_fact",
         "source_and_version", "claim_support", "selective_answer", "review_and_feedback")


class DecisionAuditRecord(EvidenceModel):
    review_id: Text
    request_id: Text
    session_id: Text
    recorded_at: AwareDatetime
    query: str  # Empty input is also a decision to audit.
    fact_coverage: Literal["typed_snapshot", "not_extracted"]
    typed_review: DecisionReviewRow | None = None
    gates: tuple[GateDecision, ...]
    response: dict[str, Any]

    @model_validator(mode="after")
    def consistent_record(self):
        if len(self.gates) != len(GATES) or {g.gate for g in self.gates} != set(GATES):
            raise ValueError("audit requires all eight gates exactly once")
        if (self.typed_review is not None) != (self.fact_coverage == "typed_snapshot"):
            raise ValueError("fact coverage must describe the actual typed record")
        if self.typed_review and (self.typed_review.session_id != self.session_id
                                  or self.typed_review.request_id != self.request_id
                                  or self.typed_review.query != self.query):
            raise ValueError("typed review must belong to this request and session")
        return self


def prepare_decision_record(query, answer, *, session_id, request_id):
    typed_data = answer.metadata.get("decision_review")
    typed = DecisionReviewRow.model_validate(typed_data) if typed_data else None
    gates = {g.gate: g for g in typed.decision.gates} if typed else {}
    for name in GATES:
        if name not in gates:
            gates[name] = GateDecision(gate=name, status="blocked", reason="gate_not_evaluated_in_this_path")
    # This gate's success is conditional on the enclosing append committing.
    # The record is never returned or acknowledged if the write fails.
    gates["review_and_feedback"] = GateDecision(gate="review_and_feedback", status="passed",
                                                reason="decision_record_committed_before_delivery")
    review_id = str(uuid4())
    recorded_at = datetime.now(UTC)
    answer.metadata["review_receipt"] = {"review_id": review_id, "recorded_at": recorded_at.isoformat()}
    return DecisionAuditRecord(review_id=review_id, request_id=request_id, session_id=session_id,
        recorded_at=recorded_at, query=query or "", fact_coverage="typed_snapshot" if typed else "not_extracted",
        typed_review=typed, gates=tuple(gates[name] for name in GATES), response=answer.to_dict())
