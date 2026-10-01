"""Public explanation of an observed decision, never model reasoning."""

from __future__ import annotations

from src.models.evidence import DecisionReviewRow, FACT_SLOTS, Money
from src.models.ruling import ComplianceStatus


_MATERIAL_SLOTS = FACT_SLOTS
_STRUCTURE_SLOTS = {"resale_arranger", "underlying_sukuk_contract"}
_DECISION_BASES = {
    "scope_refusal": "scope", "empty_request": "scope",
    "scholar_review_required": "review", "unsupported_asset": "source",
}


def _display_value(value):
    if isinstance(value, Money):
        return f"{value.amount} {value.currency}"
    if type(value) in (str, int):
        return str(value)[:100]
    return None


def build_decision_trace(answer) -> dict:
    """Use allowlisted typed state and final citations; never inspect answer prose."""
    metadata = answer.metadata or {}
    basis = metadata.get("decision_basis")
    language = metadata.get("response_language") if metadata.get("response_language") in {"en", "ar"} else "en"
    raw_review = metadata.get("decision_review")
    try:
        review = DecisionReviewRow.model_validate(raw_review) if raw_review else None
    except ValueError:
        review = None

    lane = "described_operation" if review else (
        "structure" if "structure_clarification" in metadata else
        "definition" if metadata.get("answer_kind") == "definition" else "general")
    known, missing, would_decide = [], [], []
    mechanism = "unknown"
    if review:
        for fact in review.fact_snapshot.facts:
            if fact.slot not in _MATERIAL_SLOTS:
                continue
            item = {"slot": fact.slot, "status": fact.status}
            if fact.status in {"observed", "user_reported"}:
                value = _display_value(fact.value)
                if value is not None:
                    item["value"] = value
                known.append(item)
                if fact.slot == "contract_family" and fact.status == "observed":
                    mechanism = value or "unknown"
            else:
                missing.append(item)
            would_decide.append({"condition": fact.slot, "state": fact.status})
    elif isinstance(metadata.get("structure_clarification"), dict):
        structure = metadata["structure_clarification"]
        slot = structure.get("slot")
        if slot in _STRUCTURE_SLOTS:
            # The legacy structure lane has not extracted/verified the reply.
            # Keep the slot unknown instead of treating arbitrary reply prose as a fact.
            missing.append({"slot": slot, "status": "unknown"})
            would_decide.append({"condition": slot, "state": "unknown"})

    sources = [{"document_id": c.document_id, "standard": c.standard_number,
                "section": c.section_number, "captured_at": c.to_dict()["captured_at"],
                "quote_start": str(c.quote_start) if c.quote_start is not None else None,
                "quote_end": str(c.quote_end) if c.quote_end is not None else None,
                "version": None}
               for c in answer.citations]
    if metadata.get("trace_unavailable"):
        gate, reason_code = "unavailable", "legacy_trace_unavailable"
    elif isinstance(basis, str) and basis in _DECISION_BASES:
        reason_code = basis
        gate = _DECISION_BASES[reason_code]
    elif review:
        gate = "clarification" if answer.status == ComplianceStatus.CLARIFICATION_NEEDED else "material_fact"
        reason = review.decision.reason
        # A review reason is a typed code. Never pass an arbitrary reason through to the client.
        allowed_reasons = {"financing_party_unknown", "conflicting_user_facts", "payment_total_discrepancy",
                           "mechanism_unknown", "approved_rule_evaluated_overall_gates_pending"}
        reason_code = reason if reason in allowed_reasons else "material_evidence_incomplete"
        if reason_code == "approved_rule_evaluated_overall_gates_pending":
            gate = "selective_answer"
    elif metadata.get("disclaimer_required"):
        gate, reason_code = "scope", "disclaimer_required"
    elif "structure_clarification" in metadata:
        if answer.status == ComplianceStatus.CLARIFICATION_NEEDED:
            gate, reason_code = "clarification", "structure_details_needed"
        else:
            gate, reason_code = "approved_rule", "structure_evidence_incomplete"
    elif metadata.get("approved_rule_gate", {}).get("status") == "blocked":
        gate, reason_code = "approved_rule", "approved_rule_missing"
    elif metadata.get("retrieval_status") == "unavailable":
        gate, reason_code = "retrieval", "retrieval_unavailable"
    elif metadata.get("retrieval_status") == "no_sources":
        gate, reason_code = "source", "no_sources"
    elif metadata.get("answer_kind") == "definition" and sources:
        gate, reason_code = "source", "definition_cited"
    elif answer.status == ComplianceStatus.CLARIFICATION_NEEDED:
        gate, reason_code = "clarification", "clarification_requested"
    elif sources and answer.status == ComplianceStatus.INSUFFICIENT_DATA:
        gate, reason_code = "source", "assessment_withheld"
    elif sources:
        gate, reason_code = "source", "cited_answer"
    else:
        gate, reason_code = "source", "no_sources"

    deterministic_question = bool(review or "structure_clarification" in metadata or metadata.get("disclaimer_required")
                                  or metadata.get("question_origin") == "deterministic")
    return {
        "understood_as": {"lane": lane, "language": language, "mechanism": mechanism},
        "known": known,
        "missing": missing,
        "question_asked": answer.clarification_question if deterministic_question else None,
        "sources": sources,
        "decided_by": {"gate": gate, "reason_code": reason_code},
        "would_decide": would_decide,
    }
