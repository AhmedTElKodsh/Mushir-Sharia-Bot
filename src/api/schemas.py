"""Typed L2 API request and response schemas."""
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.models.ruling import ComplianceStatus


class QueryRequest(BaseModel):
    """Query payload for REST and SSE endpoints.

    `content` is accepted for compatibility with the existing browser prototype.
    """

    model_config = ConfigDict(populate_by_name=True)

    query: str = Field(default="", min_length=1)
    content: Optional[str] = None
    session_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def accept_content_as_query(cls, data):
        if isinstance(data, dict) and not data.get("query") and data.get("content"):
            data = {**data, "query": data["content"]}
        return data

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("query cannot be empty")
        return stripped

    def resolved_session_id(self) -> Optional[str]:
        return self.session_id or self.context.get("session_id")


class Citation(BaseModel):
    document_id: str
    standard_number: str
    section_number: Optional[str] = None
    section_title: Optional[str] = None
    excerpt: Optional[str] = None
    confidence_score: Optional[float] = None
    quote_start: Optional[int] = None
    quote_end: Optional[int] = None


class QueryResponse(BaseModel):
    answer: str
    status: ComplianceStatus
    citations: List[Citation] = Field(default_factory=list)
    reasoning_summary: str
    limitations: str
    clarification_question: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def enforce_answer_contract(self):
        if self.status not in {
            ComplianceStatus.INSUFFICIENT_DATA,
            ComplianceStatus.CLARIFICATION_NEEDED,
        } and not self.citations:
            raise ValueError("grounded answers must include at least one citation")
        if self.status == ComplianceStatus.CLARIFICATION_NEEDED and not self.clarification_question:
            raise ValueError("clarification responses must include clarification_question")
        return self


class ClarificationResponse(QueryResponse):
    pass


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ErrorResponse(BaseModel):
    error: ErrorDetail

    def __init__(self, code: str, message: str, request_id: str):
        super().__init__(
            error=ErrorDetail(code=code, message=message, request_id=request_id)
        )


class StreamEvent(BaseModel):
    event: str
    data: Dict[str, Any]


# ---------------------------------------------------------------------------
# SSE event schemas — discriminated union for all 6 streaming event types
# ---------------------------------------------------------------------------


class StartedEvent(BaseModel):
    """Emitted once when streaming begins, carrying the request_id."""

    event: str = "started"
    request_id: str


class RetrievalEvent(BaseModel):
    """Emitted after retrieval with the confidence score."""

    event: str = "retrieval"
    confidence: float


class TokenEvent(BaseModel):
    """Carries a chunk of the generated answer text."""

    event: str = "token"
    text: str


class CitationEvent(BaseModel):
    """Carries a single AAOIFI citation reference."""

    event: str = "citation"
    document_id: str
    standard_number: str
    excerpt: Optional[str] = None


class DoneEvent(BaseModel):
    """Emitted when streaming completes, with status and full answer."""

    event: str = "done"
    status: str
    answer: str


class ErrorEvent(BaseModel):
    """Emitted when the service encounters an error during streaming."""

    event: str = "error"
    code: str
    message: str
