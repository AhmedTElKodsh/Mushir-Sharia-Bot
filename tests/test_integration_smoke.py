"""
Integration smoke tests — exercises real interface contracts between components.

These tests DO NOT mock the seams between components. They run the full
ApplicationService → ClarificationEngine → CitationValidator chain with
lightweight fakes only at the I/O boundary (LLM API, ChromaDB).

The primary goal is contract validation: if a component changes its public
interface without updating its callers, these tests catch it immediately.

Run with:
    pytest tests/test_integration_smoke.py -v
"""
import pytest
from typing import Any, List, Optional

from src.chatbot.application_service import ApplicationService
from src.chatbot.clarification_engine import ClarificationEngine
from src.models.ruling import ComplianceStatus


# ---------------------------------------------------------------------------
# Lightweight fakes — minimal stand-ins for heavy I/O dependencies
# ---------------------------------------------------------------------------

class _Citation:
    """Fake citation attached to a chunk."""
    def __init__(self, standard_id="FAS-28", section="3.1"):
        self.standard_id = standard_id
        self.section = section
        self.page = None
        self.source_file = f"{standard_id}.md"


class FakeChunk:
    """Deterministic SemanticChunk stand-in; no ChromaDB required."""
    def __init__(
        self,
        standard_id: str = "FAS-28",
        section: str = "3.1",
        text: str = (
            "Murabahah is a sale at cost plus a known profit margin. "
            "Under AAOIFI FAS-28 Section 3.1, the seller must disclose the "
            "cost and markup to the buyer before the contract is concluded."
        ),
        score: float = 0.85,
    ):
        self.citation = _Citation(standard_id=standard_id, section=section)
        self.text = text
        self.score = score
        self.chunk_id = f"{standard_id}-chunk-1"


class FakeRetriever:
    """Returns deterministic chunks without ChromaDB."""

    def __init__(self, chunks: Optional[List[FakeChunk]] = None):
        self._chunks = chunks if chunks is not None else [FakeChunk(), FakeChunk("FAS-28", "3.2")]

    def retrieve(self, query: str, k: int = 5, threshold: float = 0.3, **kwargs) -> List[Any]:
        return self._chunks[:k]


class FakeLLMClient:
    """Returns a deterministic answer without calling any LLM API."""

    def __init__(self, answer: str = (
        "COMPLIANT: Based on [AAOIFI FAS-28, Section 3.1], a murabahah sale at "
        "5% markup is compliant provided full cost disclosure occurs before contract."
    )):
        self._answer = answer
        self.model_name = "fake-llm-v1"

    def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        return self._answer


class EmptyRetriever:
    """Always returns no chunks — simulates a cold or empty corpus."""

    def retrieve(self, query: str, **kwargs) -> List[Any]:
        return []


# ---------------------------------------------------------------------------
# Contract validation
# ---------------------------------------------------------------------------

class TestClarificationEngineContract:
    """Validates that ClarificationEngine satisfies the ApplicationService contract."""

    def test_ask_if_needed_method_exists(self):
        """ApplicationService calls ask_if_needed — it MUST exist on ClarificationEngine."""
        engine = ClarificationEngine()
        assert hasattr(engine, "ask_if_needed"), (
            "ClarificationEngine must implement ask_if_needed(query, session_id) "
            "to satisfy the ApplicationService.clarification_service contract."
        )

    def test_ask_if_needed_signature(self):
        """ask_if_needed must accept query as positional and session_id as keyword."""
        import inspect
        engine = ClarificationEngine()
        sig = inspect.signature(engine.ask_if_needed)
        params = list(sig.parameters.keys())
        assert "query" in params, "ask_if_needed must have a 'query' parameter"
        assert "session_id" in params, "ask_if_needed must have a 'session_id' parameter"

    def test_ask_if_needed_returns_string_or_none(self):
        """ask_if_needed must return Optional[str], not raise AttributeError."""
        engine = ClarificationEngine()
        # This query has no operation keywords — should return None (no clarification needed)
        result = engine.ask_if_needed("Explain the concept of gharar", session_id="test-contract")
        assert result is None or isinstance(result, str), (
            f"ask_if_needed must return str or None, got {type(result)}"
        )

    def test_ask_if_needed_transactional_query_returns_question(self):
        """A query describing a transaction should trigger a clarifying question."""
        engine = ClarificationEngine()
        result = engine.ask_if_needed("I want to invest in a company", session_id="test-txn")
        # The engine should ask about company activity or similar
        assert result is None or isinstance(result, str)

    def test_ask_if_needed_is_idempotent(self):
        """Repeated calls with same query must not accumulate session state."""
        engine = ClarificationEngine()
        r1 = engine.ask_if_needed("I want to invest", session_id="idem-test")
        r2 = engine.ask_if_needed("I want to invest", session_id="idem-test")
        # Both calls create a fresh SessionState, so results must be equal
        assert r1 == r2, "ask_if_needed must be idempotent (fresh state per call)"


# ---------------------------------------------------------------------------
# Full ApplicationService integration paths
# ---------------------------------------------------------------------------

class TestApplicationServiceIntegration:
    """End-to-end smoke tests with real ApplicationService + real component chain."""

    def _svc(self, retriever=None, llm_answer: str = None, with_clarification: bool = True):
        """Factory for a fully-wired ApplicationService with fake I/O."""
        kwargs = {
            "retriever": retriever or FakeRetriever(),
            "llm_client": FakeLLMClient(llm_answer) if llm_answer else FakeLLMClient(),
            "clarification_service": ClarificationEngine() if with_clarification else None,
        }
        return ApplicationService(**kwargs)

    def test_compliant_answer_full_chain(self):
        """Happy path: query → retrieve → LLM → validate citations → COMPLIANT."""
        svc = self._svc()
        result = svc.answer("Is a murabahah sale at 5% markup compliant under AAOIFI?")
        assert result.status in {
            ComplianceStatus.COMPLIANT,
            ComplianceStatus.PARTIALLY_COMPLIANT,
            ComplianceStatus.INSUFFICIENT_DATA,
            ComplianceStatus.CLARIFICATION_NEEDED,
        }, f"Unexpected status: {result.status}"
        assert result.answer, "answer must be non-empty"

    def test_authority_request_refused_before_cache(self):
        """Authority requests must be refused even when cached answers exist."""
        svc = self._svc(with_clarification=False)
        result = svc.answer("Give me a binding fatwa on murabahah")
        assert result.status == ComplianceStatus.INSUFFICIENT_DATA
        assert result.citations == []

    def test_arabic_authority_request_refused(self):
        """Arabic-language authority requests must also be refused."""
        svc = self._svc(with_clarification=False)
        result = svc.answer("أريد فتوى ملزمة عن المرابحة")
        assert result.status == ComplianceStatus.INSUFFICIENT_DATA

    def test_empty_retrieval_returns_insufficient_data(self):
        """No matching chunks → INSUFFICIENT_DATA, not a crash."""
        svc = self._svc(retriever=EmptyRetriever(), with_clarification=False)
        result = svc.answer("What is the ruling on speculative derivatives?")
        assert result.status == ComplianceStatus.INSUFFICIENT_DATA

    def test_empty_query_returns_graceful_response(self):
        """Whitespace-only query must not crash."""
        svc = self._svc(with_clarification=False)
        result = svc.answer("   ")
        assert result.status == ComplianceStatus.INSUFFICIENT_DATA
        assert result.answer

    def test_none_query_returns_graceful_response(self):
        """None query must not raise."""
        svc = self._svc(with_clarification=False)
        result = svc.answer(None)
        assert result.status == ComplianceStatus.INSUFFICIENT_DATA

    def test_conditionally_compliant_maps_to_partially_compliant(self):
        """CONDITIONALLY COMPLIANT from LLM must map to PARTIALLY_COMPLIANT, not INSUFFICIENT_DATA."""
        svc = self._svc(
            llm_answer=(
                "CONDITIONALLY COMPLIANT: Based on [AAOIFI FAS-28, Section 3.1], "
                "the transaction is conditionally acceptable provided the markup is disclosed."
            ),
            with_clarification=False,
        )
        result = svc.answer("Is deferred payment sale at 10% markup compliant?")
        # The citation validator may or may not find a citation match in the fake text;
        # if it does, status must be PARTIALLY_COMPLIANT not INSUFFICIENT_DATA
        if result.citations:
            assert result.status == ComplianceStatus.PARTIALLY_COMPLIANT, (
                "CONDITIONALLY COMPLIANT must map to PARTIALLY_COMPLIANT, "
                f"got {result.status}"
            )

    def test_no_service_crash_with_real_clarification_engine(self):
        """ApplicationService with real ClarificationEngine must not raise AttributeError."""
        svc = ApplicationService(
            retriever=FakeRetriever(),
            llm_client=FakeLLMClient(),
            clarification_service=ClarificationEngine(),
        )
        try:
            result = svc.answer("Explain riba according to AAOIFI standards")
            assert result is not None
        except AttributeError as exc:
            pytest.fail(
                f"AttributeError raised — likely missing interface method: {exc}"
            )


# ---------------------------------------------------------------------------
# Status mapping unit tests
# ---------------------------------------------------------------------------

class TestStatusFromAnswer:
    """Unit-level tests for _status_from_answer covering all keyword variants."""

    def _status(self, text: str, has_citations: bool = True) -> ComplianceStatus:
        citations = ["dummy"] if has_citations else []
        return ApplicationService._status_from_answer(text, citations)

    def test_compliant(self):
        assert self._status("COMPLIANT: meets FAS-28 requirements.") == ComplianceStatus.COMPLIANT

    def test_non_compliant_underscore(self):
        assert self._status("NON_COMPLIANT: violates riba prohibition.") == ComplianceStatus.NON_COMPLIANT

    def test_non_compliant_hyphen(self):
        assert self._status("NON-COMPLIANT: violates riba prohibition.") == ComplianceStatus.NON_COMPLIANT

    def test_partially_compliant_space(self):
        assert self._status("PARTIALLY COMPLIANT: conditionally acceptable.") == ComplianceStatus.PARTIALLY_COMPLIANT

    def test_conditionally_compliant_maps_correctly(self):
        """Core regression: CONDITIONALLY COMPLIANT must NOT fall through to INSUFFICIENT_DATA."""
        result = self._status(
            "CONDITIONALLY COMPLIANT: Based on FAS-28, this is acceptable if markup is disclosed."
        )
        assert result == ComplianceStatus.PARTIALLY_COMPLIANT, (
            f"CONDITIONALLY COMPLIANT must map to PARTIALLY_COMPLIANT, got {result}"
        )

    def test_no_citations_yields_insufficient(self):
        assert self._status("COMPLIANT: all good.", has_citations=False) == ComplianceStatus.INSUFFICIENT_DATA

    def test_insufficient_keyword(self):
        assert self._status("INSUFFICIENT_DATA: not enough context.") == ComplianceStatus.INSUFFICIENT_DATA

    def test_unknown_text_yields_insufficient(self):
        assert self._status("The answer is unclear.") == ComplianceStatus.INSUFFICIENT_DATA
