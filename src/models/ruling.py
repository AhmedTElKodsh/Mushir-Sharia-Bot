from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import UTC, datetime
from enum import Enum

class ComplianceStatus(Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    PARTIALLY_COMPLIANT = "PARTIALLY_COMPLIANT"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    CLARIFICATION_NEEDED = "CLARIFICATION_NEEDED"

@dataclass
class AAOIFICitation:
    """Citation to AAOIFI standard."""
    document_id: str
    standard_number: str
    section_number: Optional[str] = None
    section_title: Optional[str] = None
    excerpt: Optional[str] = None
    confidence_score: Optional[float] = None
    quote_start: Optional[int] = None
    quote_end: Optional[int] = None

    def __post_init__(self):
        if not self.document_id or not self.document_id.strip():
            raise ValueError("Citation document_id cannot be empty")
        if not self.standard_number or not self.standard_number.strip():
            raise ValueError("Citation standard_number cannot be empty")

    def to_dict(self) -> Dict:
        return {
            "document_id": self.document_id,
            "standard_number": self.standard_number,
            "section_number": self.section_number,
            "section_title": self.section_title,
            "excerpt": self.excerpt,
            "confidence_score": self.confidence_score,
            "quote_start": self.quote_start,
            "quote_end": self.quote_end,
        }


@dataclass
class ComplianceRuling:
    """Compliance ruling for a financial operation."""
    ruling_id: str
    session_id: str
    status: ComplianceStatus
    reasoning: str
    citations: List[AAOIFICitation] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.reasoning or not self.reasoning.strip():
            raise ValueError("Ruling reasoning cannot be empty")
        if self.citations:
            self.validate()

    def validate(self) -> None:
        """Validate ruling has proper citations."""
        if not self.citations:
            raise ValueError("ComplianceRuling must have at least one citation")
        for citation in self.citations:
            if not citation.document_id or not citation.standard_number:
                raise ValueError("Each citation must have document_id and standard_number")

    def to_dict(self) -> Dict:
        return {
            "ruling_id": self.ruling_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "reasoning": self.reasoning,
            "citations": [c.to_dict() for c in self.citations],
            "recommendations": self.recommendations,
            "warnings": self.warnings,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class AnswerContract:
    """Canonical L1 answer shape shared by CLI, API, and future transports."""
    answer: str
    status: ComplianceStatus
    citations: List[AAOIFICitation] = field(default_factory=list)
    reasoning_summary: str = ""
    limitations: str = (
        "Informational guidance only; consult a qualified Sharia scholar for a binding ruling."
    )
    clarification_question: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.answer or not self.answer.strip():
            raise ValueError("AnswerContract answer cannot be empty")
        if self.status not in {
            ComplianceStatus.INSUFFICIENT_DATA,
            ComplianceStatus.CLARIFICATION_NEEDED,
        } and not self.citations:
            raise ValueError("Grounded answers must include at least one citation")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "status": self.status.value,
            "citations": [citation.to_dict() for citation in self.citations],
            "reasoning_summary": self.reasoning_summary,
            "limitations": self.limitations,
            "clarification_question": self.clarification_question,
            "metadata": self.metadata,
        }
