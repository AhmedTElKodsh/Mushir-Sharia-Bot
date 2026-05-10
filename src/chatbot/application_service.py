"""Application service for the L1 Sharia compliance answer flow."""
from typing import Any, Dict, List, Optional

from src.chatbot.citation_validator import CitationValidator
from src.chatbot.prompt_builder import PromptBuilder
from src.models.ruling import AnswerContract, ComplianceStatus
from src.rag.pipeline import RAGPipeline


class ApplicationService:
    """Coordinates retrieval, prompt building, LLM generation, and citation validation."""

    def __init__(
        self,
        retriever=None,
        llm_client=None,
        prompt_builder=None,
        citation_validator=None,
        clarification_service=None,
        session_store=None,
        audit_store=None,
        k: int = 5,
        threshold: float = 0.3,
    ):
        self.retriever = retriever
        self.llm_client = llm_client
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.citation_validator = citation_validator or CitationValidator()
        self.clarification_service = clarification_service
        self.session_store = session_store
        self.audit_store = audit_store
        self.k = k
        self.threshold = threshold

    def answer(self, query: str, session_id: Optional[str] = None, request_id: Optional[str] = None) -> AnswerContract:
        cleaned_query = query.strip()
        clarification = self._clarification_question(cleaned_query, session_id)
        if clarification:
            contract = AnswerContract(
                answer=clarification,
                status=ComplianceStatus.CLARIFICATION_NEEDED,
                clarification_question=clarification,
                reasoning_summary="Missing facts materially block a grounded AAOIFI answer.",
                metadata=self._metadata([], confidence=0.0),
            )
            self._audit(cleaned_query, contract, session_id, request_id)
            return contract

        if self.retriever is None:
            self.retriever = RAGPipeline()
        chunks = self.retriever.retrieve(cleaned_query, k=self.k, threshold=self.threshold)
        if not chunks:
            contract = AnswerContract(
                answer="Not addressed in retrieved AAOIFI standards.",
                status=ComplianceStatus.INSUFFICIENT_DATA,
                citations=[],
                reasoning_summary="No retrieved AAOIFI excerpts were available to ground an answer.",
                metadata=self._metadata([], confidence=0.0),
            )
            self._audit(cleaned_query, contract, session_id, request_id)
            return contract

        prompt = self.prompt_builder.build(
            cleaned_query,
            chunks,
            history=self._history(session_id),
        )
        if self.llm_client is None:
            from src.chatbot.llm_client import GeminiClient

            self.llm_client = GeminiClient()
        answer = self.llm_client.generate(prompt)
        citations = self.citation_validator.validate(answer, chunks)
        status = self._status_from_answer(answer, citations)
        contract = AnswerContract(
            answer=answer,
            status=status,
            citations=citations,
            reasoning_summary=self._reasoning_summary(answer),
            metadata=self._metadata(chunks, confidence=self._confidence(chunks)),
        )
        self._audit(cleaned_query, contract, session_id, request_id)
        return contract

    def _clarification_question(self, query: str, session_id: Optional[str]) -> Optional[str]:
        if not self.clarification_service:
            return None
        return self.clarification_service.ask_if_needed(query, session_id=session_id)

    def _history(self, session_id: Optional[str]) -> List[Dict[str, str]]:
        if not self.session_store:
            return []
        return self.session_store.history_for(session_id)

    def _audit(
        self,
        query: str,
        answer: AnswerContract,
        session_id: Optional[str],
        request_id: Optional[str],
    ) -> None:
        if not self.audit_store:
            return
        self.audit_store.log_answer(
            query=query,
            answer=answer,
            session_id=session_id,
            request_id=request_id,
        )

    def _metadata(self, chunks: List[Any], confidence: float) -> Dict[str, Any]:
        return {
            "model_name": getattr(self.llm_client, "model_name", None),
            "prompt_version": getattr(self.prompt_builder, "prompt_version", None),
            "retrieved_chunk_ids": [self._chunk_id(chunk) for chunk in chunks],
            "confidence": confidence,
        }

    @staticmethod
    def _chunk_id(chunk: Any) -> str:
        if isinstance(chunk, dict):
            return str(chunk.get("chunk_id") or chunk.get("id") or "")
        return str(getattr(chunk, "chunk_id", ""))

    @staticmethod
    def _confidence(chunks: List[Any]) -> float:
        if not chunks:
            return 0.0
        scores = []
        for chunk in chunks:
            if isinstance(chunk, dict):
                scores.append(float(chunk.get("similarity") or chunk.get("score") or 0.0))
            else:
                scores.append(float(getattr(chunk, "score", 0.0) or 0.0))
        return sum(scores) / len(scores)

    @staticmethod
    def _status_from_answer(answer: str, citations) -> ComplianceStatus:
        upper = answer.upper()
        if "INSUFFICIENT" in upper or not citations:
            return ComplianceStatus.INSUFFICIENT_DATA
        if "PARTIALLY_COMPLIANT" in upper or "PARTIALLY COMPLIANT" in upper or "PARTIALLY" in upper:
            return ComplianceStatus.PARTIALLY_COMPLIANT
        if "NON_COMPLIANT" in upper or "NON-COMPLIANT" in upper or "NON COMPLIANT" in upper:
            return ComplianceStatus.NON_COMPLIANT
        if "COMPLIANT" in upper:
            return ComplianceStatus.COMPLIANT
        return ComplianceStatus.INSUFFICIENT_DATA

    @staticmethod
    def _reasoning_summary(answer: str) -> str:
        return answer.strip().splitlines()[0][:300]
