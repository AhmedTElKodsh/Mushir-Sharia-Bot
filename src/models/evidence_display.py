"""Descriptive evidence labels, never a probability of answer correctness."""
from datetime import UTC, datetime


def source_age(value, *, now=None):
    now = now or datetime.now(UTC)
    unknown = {"captured_at": None, "age_days": None}
    try:
        captured = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
        if not isinstance(captured, datetime) or captured.tzinfo is None or captured.utcoffset() is None:
            return unknown
        captured = captured.astimezone(UTC)
        if captured > now:
            return unknown
        return {"captured_at": captured.isoformat(), "age_days": (now - captured).days}
    except (ValueError, TypeError, OverflowError):
        return unknown


def without_answer_scores(value):
    if isinstance(value, dict):
        return {key: without_answer_scores(item) for key, item in value.items()
                if key not in {"confidence", "confidence_score", "system_confidence"}
                and not (isinstance(item, (int, float)) and ("confidence" in key or key in {"score", "similarity"}))}
    if isinstance(value, (list, tuple)):
        return [without_answer_scores(item) for item in value]
    return value


def evidence_summary(status, citations):
    sources = [{"document_id": item.document_id, **source_age(item.captured_at)} for item in citations]
    dated = sum(item["captured_at"] is not None for item in sources)
    age_status = "known" if sources and dated == len(sources) else "partial" if dated else "unknown"
    label = ("clarification_required" if status == "CLARIFICATION_NEEDED" else
             "insufficient_evidence" if status == "INSUFFICIENT_DATA" else
             "sources_available" if citations else "no_sources")
    return {"status": label, "source_age_status": age_status, "sources": sources}
