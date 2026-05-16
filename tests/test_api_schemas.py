import pytest
from pydantic import ValidationError

from src.models.ruling import ComplianceStatus


@pytest.mark.unit
def test_query_request_rejects_empty_query():
    from src.api.schemas import QueryRequest

    with pytest.raises(ValidationError):
        QueryRequest(query="   ")


@pytest.mark.unit
def test_query_response_serializes_l1_answer_contract():
    from src.api.schemas import Citation, QueryResponse

    response = QueryResponse(
        answer="Supported by AAOIFI [FAS-01 §1].",
        status=ComplianceStatus.COMPLIANT,
        citations=[
            Citation(
                document_id="FAS-01.md",
                standard_number="FAS-01",
                section_number="1",
                excerpt="excerpt",
            )
        ],
        reasoning_summary="Supported by retrieved excerpts.",
        limitations="Informational guidance only.",
        metadata={"confidence": 0.9},
    )

    payload = response.model_dump(mode="json")

    assert payload["status"] == "COMPLIANT"
    assert payload["citations"][0]["standard_number"] == "FAS-01"
    assert payload["metadata"]["confidence"] == 0.9


@pytest.mark.unit
def test_query_response_rejects_grounded_status_without_citations():
    from src.api.schemas import QueryResponse

    with pytest.raises(ValidationError, match="grounded answers must include"):
        QueryResponse(
            answer="COMPLIANT",
            status=ComplianceStatus.COMPLIANT,
            citations=[],
            reasoning_summary="No source.",
            limitations="Informational only.",
        )


@pytest.mark.unit
def test_query_response_requires_question_for_clarification_status():
    from src.api.schemas import QueryResponse

    with pytest.raises(ValidationError, match="clarification_question"):
        QueryResponse(
            answer="More facts are needed.",
            status=ComplianceStatus.CLARIFICATION_NEEDED,
            citations=[],
            reasoning_summary="Missing facts.",
            limitations="Informational only.",
        )


@pytest.mark.unit
def test_query_response_rejects_crowded_clarification_questions():
    from src.api.schemas import QueryResponse

    with pytest.raises(ValidationError, match="exactly one concise question"):
        QueryResponse(
            answer="More facts are needed.",
            status=ComplianceStatus.CLARIFICATION_NEEDED,
            citations=[],
            clarification_question="1. What is the company activity?\n2. What percentage is non-compliant?",
            reasoning_summary="Missing facts.",
            limitations="Informational only.",
        )


@pytest.mark.unit
def test_error_response_contains_request_id():
    from src.api.schemas import ErrorResponse

    payload = ErrorResponse(code="SERVICE_ERROR", message="failed", request_id="req-1")

    assert payload.model_dump()["error"]["request_id"] == "req-1"
