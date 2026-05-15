"""Analyzes compliance status and validates citations."""
from typing import Any, List
from src.models.ruling import ComplianceStatus


def derive_compliance_status(answer: str, citations: List[Any]) -> ComplianceStatus:
    """Derive compliance status from LLM answer text — single source of truth.

    Keyword order matters: more specific phrases (PARTIALLY, NON) are
    checked before the generic COMPLIANT substring to avoid false positives.
    CONDITIONALLY COMPLIANT (from prompt template) maps to PARTIALLY_COMPLIANT.
    """
    upper = answer.upper()

    if "INSUFFICIENT" in upper or not citations:
        return ComplianceStatus.INSUFFICIENT_DATA

    if (
        "PARTIALLY_COMPLIANT" in upper
        or "PARTIALLY COMPLIANT" in upper
        or "CONDITIONALLY COMPLIANT" in upper
    ):
        return ComplianceStatus.PARTIALLY_COMPLIANT

    if "NON_COMPLIANT" in upper or "NON-COMPLIANT" in upper or "NON COMPLIANT" in upper:
        return ComplianceStatus.NON_COMPLIANT

    if "COMPLIANT" in upper:
        return ComplianceStatus.COMPLIANT

    return ComplianceStatus.INSUFFICIENT_DATA


class ComplianceAnalyzer:
    """Analyzes compliance status and validates citations."""

    def __init__(self, citation_validator):
        """Initialize compliance analyzer.
        
        Args:
            citation_validator: Citation validator instance
        """
        self.citation_validator = citation_validator

    def analyze(self, answer: str, chunks: List[Any]) -> tuple:
        """Analyze answer and return status and validated citations.
        
        Args:
            answer: Generated answer text
            chunks: Retrieved chunks used for answer
            
        Returns:
            Tuple of (ComplianceStatus, List[AAOIFICitation])
        """
        citations = self.citation_validator.validate(answer, chunks)
        status = derive_compliance_status(answer, citations)
        return status, citations

    @staticmethod
    def extract_reasoning_summary(answer: str, max_length: int = 300) -> str:
        """Extract reasoning summary from answer."""
        lines = answer.strip().splitlines()
        return lines[0][:max_length] if lines else ""
