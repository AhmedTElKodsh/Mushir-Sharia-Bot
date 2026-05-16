"""SSE event schema validation tests.

Validates that each Pydantic SSE event model serialises correctly and that
the ``_sse()`` helper produces the expected ``event:`` and ``data:`` lines.
"""
import json

import pytest

from src.api.schemas import (
    CitationEvent,
    DoneEvent,
    ErrorEvent,
    RetrievalEvent,
    StartedEvent,
    TokenEvent,
)
from src.api.routes import _sse


# ---------------------------------------------------------------------------
# Pydantic model creation & serialisation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSSEEventSchemas:
    """Pydantic model creation and serialisation for every SSE event type."""

    def test_started_event(self):
        event = StartedEvent(request_id="req-abc-123")
        data = event.model_dump(mode="json")
        assert data["event"] == "started"
        assert data["request_id"] == "req-abc-123"

    def test_retrieval_event(self):
        event = RetrievalEvent(confidence=0.87)
        data = event.model_dump(mode="json")
        assert data["event"] == "retrieval"
        assert data["confidence"] == 0.87

    def test_token_event(self):
        event = TokenEvent(text="The transaction complies")
        data = event.model_dump(mode="json")
        assert data["event"] == "token"
        assert data["text"] == "The transaction complies"

    def test_citation_event_with_excerpt(self):
        event = CitationEvent(
            document_id="FAS-01.md",
            standard_number="FAS-01",
            excerpt="Murabahah requires disclosure",
        )
        data = event.model_dump(mode="json")
        assert data["event"] == "citation"
        assert data["document_id"] == "FAS-01.md"
        assert data["standard_number"] == "FAS-01"
        assert data["excerpt"] == "Murabahah requires disclosure"

    def test_citation_event_without_excerpt(self):
        event = CitationEvent(
            document_id="FAS-02.md",
            standard_number="FAS-02",
        )
        data = event.model_dump(mode="json")
        assert data["event"] == "citation"
        assert data["excerpt"] is None

    def test_done_event(self):
        event = DoneEvent(status="COMPLIANT", answer="The transaction is compliant.")
        data = event.model_dump(mode="json")
        assert data["event"] == "done"
        assert data["status"] == "COMPLIANT"
        assert data["answer"] == "The transaction is compliant."

    def test_error_event(self):
        event = ErrorEvent(code="SERVICE_ERROR", message="Something went wrong")
        data = event.model_dump(mode="json")
        assert data["event"] == "error"
        assert data["code"] == "SERVICE_ERROR"
        assert data["message"] == "Something went wrong"


# ---------------------------------------------------------------------------
# _sse() wire-format assertions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSSEFormatting:
    """Verify that ``_sse()`` produces the correct wire format per event type."""

    def test_started_sse_line(self):
        event = StartedEvent(request_id="req-1")
        output = _sse("started", event.model_dump(mode="json"))
        assert "event: started" in output
        assert '"request_id": "req-1"' in output
        assert output.endswith("\n\n")

    def test_retrieval_sse_line(self):
        event = RetrievalEvent(confidence=0.75)
        output = _sse("retrieval", event.model_dump(mode="json"))
        assert "event: retrieval" in output
        assert '"confidence": 0.75' in output

    def test_token_sse_line(self):
        event = TokenEvent(text="Sharia-compliant")
        output = _sse("token", event.model_dump(mode="json"))
        assert "event: token" in output
        assert '"text": "Sharia-compliant"' in output

    def test_citation_sse_line(self):
        event = CitationEvent(
            document_id="FAS-01.md",
            standard_number="FAS-01",
            excerpt="Key requirement",
        )
        output = _sse("citation", event.model_dump(mode="json"))
        assert "event: citation" in output
        assert '"document_id": "FAS-01.md"' in output
        assert '"excerpt": "Key requirement"' in output

    def test_done_sse_line(self):
        event = DoneEvent(status="PARTIALLY_COMPLIANT", answer="Most requirements met")
        output = _sse("done", event.model_dump(mode="json"))
        assert "event: done" in output
        assert '"status": "PARTIALLY_COMPLIANT"' in output

    def test_error_sse_line(self):
        event = ErrorEvent(code="RATE_LIMIT", message="Too many requests")
        output = _sse("error", event.model_dump(mode="json"))
        assert "event: error" in output
        assert '"code": "RATE_LIMIT"' in output

    def test_sse_accepts_bare_dict(self):
        """``_sse()`` is format-only — schema validation is the model's job."""
        output = _sse("started", {"request_id": "req-1"})
        assert output.startswith("event: started")
        assert '"request_id": "req-1"' in output
