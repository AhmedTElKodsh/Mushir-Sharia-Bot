import re
from typing import Optional, List, Dict
from src.models.ruling import ComplianceRuling, ComplianceStatus, AAOIFICitation
from src.models.session import SessionState
from src.rag.pipeline import RAGPipeline
from src.chatbot.llm_client import LLMClient, AAOIFI_ADHERENCE_SYSTEM_PROMPT
from src.config.logging_config import setup_logging

logger = setup_logging()

class ComplianceAnalyzer:
    """Analyzes financial operations for Sharia compliance."""

    def __init__(self, rag_pipeline: RAGPipeline, llm_client: LLMClient):
        self.rag_pipeline = rag_pipeline
        self.llm_client = llm_client

    def analyze(self, session_state: SessionState) -> ComplianceRuling:
        """Analyze operation and generate compliance ruling."""
        query = session_state.user_input
        variables = session_state.extracted_variables
        enhanced_query = self._build_query(query, variables)
        chunks = self.rag_pipeline.retrieve(enhanced_query, k=5, threshold=0.7)
        if not chunks:
            return self._insufficient_data_ruling(session_state)
        augmented_prompt = self.rag_pipeline.augment_prompt(enhanced_query, chunks)
        llm_response = self.llm_client.generate(AAOIFI_ADHERENCE_SYSTEM_PROMPT, augmented_prompt)
        ruling = self._parse_ruling(llm_response, session_state, chunks)
        logger.info(f"Generated ruling {ruling.ruling_id}: {ruling.status.value}")
        return ruling

    def _build_query(self, query: str, variables: dict) -> str:
        parts = [query]
        for key, value in variables.items():
            if key != "operation_type":
                parts.append(f"{key}: {value}")
        return " | ".join(parts)

    def _parse_ruling(self, llm_response: str, session_state: SessionState, chunks: list) -> ComplianceRuling:
        status = ComplianceStatus.INSUFFICIENT_DATA
        reasoning = llm_response
        citations = self._extract_citations(llm_response, chunks)
        recommendations = self._extract_section(llm_response, "RECOMMENDATIONS")
        warnings = self._extract_section(llm_response, "WARNINGS")
        if "COMPLIANT" in llm_response.upper():
            status = ComplianceStatus.COMPLIANT
        elif "NON_COMPLIANT" in llm_response.upper():
            status = ComplianceStatus.NON_COMPLIANT
        elif "PARTIALLY" in llm_response.upper():
            status = ComplianceStatus.PARTIALLY_COMPLIANT
        import uuid
        return ComplianceRuling(
            ruling_id=str(uuid.uuid4()),
            session_id=session_state.session_id,
            status=status,
            reasoning=reasoning,
            citations=citations,
            recommendations=recommendations,
            warnings=warnings,
        )

    def _extract_citations(self, text: str, chunks: list) -> List[AAOIFICitation]:
        citations = []
        pattern = r"FAS\s*(\d+)|Standard\s*(\d+)|\[([^\]]+)\]"
        found = re.findall(pattern, text)
        for match in found:
            std_num = match[0] or match[1] or match[2]
            if std_num:
                citations.append(AAOIFICitation(
                    document_id=f"FAS-{std_num}",
                    standard_number=std_num,
                    excerpt=text[:200],
                ))
        if not citations:
            for chunk in chunks:
                meta = chunk.get("metadata", {})
                std_num = meta.get("standard_number")
                if std_num:
                    citations.append(AAOIFICitation(
                        document_id=meta.get("document_id", "unknown"),
                        standard_number=std_num,
                        section_number=meta.get("section_number"),
                        section_title=meta.get("section_title"),
                        excerpt=chunk.get("content", "")[:200],
                    ))
        return citations[:5]

    def _extract_section(self, text: str, section_name: str) -> List[str]:
        pattern = rf"{section_name}:\s*(.*?)(?:\n\d+\.|$)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            items = [line.strip() for line in match.group(1).split("\n") if line.strip() and not line.strip().startswith(section_name)]
            return items[:5]
        return []

    def _insufficient_data_ruling(self, session_state: SessionState) -> ComplianceRuling:
        import uuid
        return ComplianceRuling(
            ruling_id=str(uuid.uuid4()),
            session_id=session_state.session_id,
            status=ComplianceStatus.INSUFFICIENT_DATA,
            reasoning="No relevant AAOIFI standards found for this query. Please ensure the query relates to AAOIFI FAS standards.",
            citations=[],
            recommendations=["Refine query to match AAOIFI FAS scope", "Consult with qualified Islamic finance scholar"],
            warnings=["System covers FAS series only"],
        )

    def validate_citations(self, ruling: ComplianceRuling, chunks: list) -> List[str]:
        """Validate citations against retrieved chunks."""
        warnings = []
        chunk_refs = {(c.get("metadata", {}).get("document_id"), c.get("metadata", {}).get("standard_number")) for c in chunks}
        for cit in ruling.citations:
            ref = (cit.document_id, cit.standard_number)
            if ref not in chunk_refs:
                warnings.append(f"Citation {cit.standard_number} not in retrieved chunks")
                logger.warning(f"Invalid citation: {cit.standard_number}")
        return warnings
