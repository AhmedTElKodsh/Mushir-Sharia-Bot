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
def test_error_response_contains_request_id():
    from src.api.schemas import ErrorResponse

    payload = ErrorResponse(code="SERVICE_ERROR", message="failed", request_id="req-1")

    assert payload.model_dump()["error"]["request_id"] == "req-1"
