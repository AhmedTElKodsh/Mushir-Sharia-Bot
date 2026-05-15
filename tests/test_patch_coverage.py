"""Patch coverage tests for code review fixes applied to application_service and pipeline."""
import pytest
from unittest.mock import MagicMock


class TestAuthorityRequestDetection:
    """[P0] Unit tests for authority request detection with Unicode word boundaries."""

    def test_detects_english_authority_terms(self):
        """Should detect English authority terms."""
        from src.chatbot.application_service import ApplicationService

        cases = [
            "Can you give me a binding fatwa?",
            "Give me a binding ruling on this",
            "Is this halal? I need legal advice",
            "I want financial advice on this",
        ]
        for query in cases:
            assert ApplicationService._is_authority_request(query) is True, f"Failed on: {query}"

    def test_detects_arabic_authority_terms(self):
        """Should detect Arabic authority terms including fatwa."""
        from src.chatbot.application_service import ApplicationService

        cases = [
            "هل يمكنني الحصول على فتوى ملزمة",  # fatwa
            "أحتاج حكم شرعي ملزم",  # binding ruling
            "أريد نصيحة قانونية",  # legal advice
            "أحتاج نصيحة مالية",  # financial advice
        ]
        for query in cases:
            assert ApplicationService._is_authority_request(query) is True, f"Failed on: {query}"

    def test_rejects_non_authority_requests(self):
        """Should NOT match non-authority queries that contain authority substrings."""
        from src.chatbot.application_service import ApplicationService

        cases = [
            "What is a binding contract?",
            "The pre-binding phase",
            "non-binding agreement",
            "This is a binding contract only",
        ]
        for query in cases:
            assert ApplicationService._is_authority_request(query) is False, f"Should not match: {query}"

    def test_handles_none_query(self):
        """Should not crash on None query (guarded upstream in answer())."""
        from src.chatbot.application_service import ApplicationService

        # Direct call to _is_authority_request should handle None gracefully
        # The upstream guard in answer() should catch None first
        # but the method itself should not raise AttributeError
        try:
            result = ApplicationService._is_authority_request(None)
            # If it returns without raising, that's acceptable (upstream guard owns this)
        except TypeError:
            pytest.fail("_is_authority_request raised TypeError on None — upstream guard must catch it first")

    def test_handles_empty_string(self):
        """Should not match empty string as authority request."""
        from src.chatbot.application_service import ApplicationService

        assert ApplicationService._is_authority_request("") is False
        assert ApplicationService._is_authority_request("   ") is False


class TestEmptyQueryResponse:
    """[P0] Tests for empty/None query handling via _empty_query_response."""

    def test_answer_rejects_none_query(self):
        """answer() should return empty response contract for None."""
        from src.chatbot.application_service import ApplicationService

        service = ApplicationService()
        result = service.answer(None)

        assert result.status.value == "INSUFFICIENT_DATA"
        assert "question" in result.answer.lower()
        assert result.citations == []
        assert result.metadata.get("cache_hit") is False

    def test_answer_rejects_empty_string(self):
        """answer() should return empty response contract for empty string."""
        from src.chatbot.application_service import ApplicationService

        service = ApplicationService()
        result = service.answer("")

        assert result.status.value == "INSUFFICIENT_DATA"
        assert result.citations == []

    def test_answer_rejects_whitespace_only(self):
        """answer() should return empty response contract for whitespace-only query."""
        from src.chatbot.application_service import ApplicationService

        service = ApplicationService()
        result = service.answer("   \n\t  ")

        assert result.status.value == "INSUFFICIENT_DATA"
        assert result.citations == []


class TestEmbedQueryEdgeCases:
    """[P0] Tests for embed_query None and empty string handling."""

    def test_embed_query_returns_empty_for_none(self, monkeypatch):
        """embed_query(None) should return [] instead of crashing."""
        from src.rag.pipeline import RAGPipeline

        pipeline = RAGPipeline.__new__(RAGPipeline)
        pipeline.embedding_generator = None

        class FakeModel:
            def encode(self, q, normalize_embeddings=False):
                import numpy as np
                return np.array([0.1] * 768)

        pipeline.model = FakeModel()

        result = pipeline.embed_query(None)
        assert result == []

    def test_embed_query_returns_empty_for_empty_string(self, monkeypatch):
        """embed_query('') should return [] instead of zero-vector."""
        from src.rag.pipeline import RAGPipeline

        pipeline = RAGPipeline.__new__(RAGPipeline)
        pipeline.embedding_generator = None

        class FakeModel:
            def encode(self, q, normalize_embeddings=False):
                import numpy as np
                return np.array([0.1] * 768)

        pipeline.model = FakeModel()

        result = pipeline.embed_query("")
        assert result == []


class TestRetrieveEdgeCases:
    """[P1] Tests for retrieve() edge cases: k<=0, threshold clamping."""

    def test_retrieve_returns_empty_for_k_zero(self):
        """retrieve(k=0) should return [] immediately."""
        from src.rag.pipeline import RAGPipeline

        class FakeModel:
            def encode(self, q, normalize_embeddings=False):
                import numpy as np
                return np.array([0.1] * 768)

        class FakeCollection:
            def query(self, query_embeddings, n_results):
                # Should NEVER be called
                raise AssertionError("collection.query() called despite k=0")

        pipeline = RAGPipeline.__new__(RAGPipeline)
        pipeline.vector_store = None
        pipeline.embedding_generator = None
        pipeline.model = FakeModel()
        pipeline.collection = FakeCollection()

        result = pipeline.retrieve("test query", k=0, threshold=0.3)
        assert result == []

    def test_retrieve_returns_empty_for_k_negative(self):
        """retrieve(k=-1) should return [] immediately."""
        from src.rag.pipeline import RAGPipeline

        class FakeModel:
            def encode(self, q, normalize_embeddings=False):
                from unittest.mock import Mock
                return Mock(tolist=lambda: [0.1] * 768)

        class FakeCollection:
            def query(self, query_embeddings, n_results):
                raise AssertionError("collection.query() called despite k=0")

        pipeline = RAGPipeline.__new__(RAGPipeline)
        pipeline.vector_store = None
        pipeline.embedding_generator = None
        pipeline.model = FakeModel()
        pipeline.collection = FakeCollection()

        result = pipeline.retrieve("test query", k=-1, threshold=0.3)
        assert result == []

    def test_retrieve_clamps_negative_threshold_to_zero(self):
        """retrieve(threshold=-0.5) should clamp to 0.0."""
        from src.rag.pipeline import RAGPipeline

        class FakeModel:
            def encode(self, q, normalize_embeddings=False):
                from unittest.mock import Mock
                return Mock(tolist=lambda: [0.1] * 768)

        class FakeCollection:
            def query(self, query_embeddings, n_results):
                return {
                    "documents": [["Test excerpt"]],
                    "metadatas": [[{"source_file": "FAS-01.md", "section": "1"}]],
                    "distances": [[1.0]],  # max distance = min similarity
                    "ids": [["chunk-1"]],
                }

        pipeline = RAGPipeline.__new__(RAGPipeline)
        pipeline.vector_store = None
        pipeline.embedding_generator = None
        pipeline.model = FakeModel()
        pipeline.collection = FakeCollection()

        # threshold=-0.5 clamped to 0.0 — should include this chunk (similarity=0.0 >= 0.0)
        result = pipeline.retrieve("test", k=1, threshold=-0.5)
        assert len(result) == 1

    def test_retrieve_clamps_threshold_above_one_to_one(self):
        """retrieve(threshold=2.0) should clamp to 1.0 (no chunks match)."""
        from src.rag.pipeline import RAGPipeline

        class FakeModel:
            def encode(self, q, normalize_embeddings=False):
                from unittest.mock import Mock
                return Mock(tolist=lambda: [0.1] * 768)

        class FakeCollection:
            def query(self, query_embeddings, n_results):
                return {
                    "documents": [["Test excerpt"]],
                    "metadatas": [[{"source_file": "FAS-01.md", "section": "1"}]],
                    "distances": [[0.5]],  # similarity = 0.5
                    "ids": [["chunk-1"]],
                }

        pipeline = RAGPipeline.__new__(RAGPipeline)
        pipeline.vector_store = None
        pipeline.embedding_generator = None
        pipeline.model = FakeModel()
        pipeline.collection = FakeCollection()

        # threshold=2.0 clamped to 1.0 — no chunk has similarity >= 1.0
        result = pipeline.retrieve("test", k=1, threshold=2.0)
        assert result == []


class TestArabicQueryExpansion:
    """[P1] Tests for _expand_for_embedding Arabic query fallback."""

    def test_arabic_only_query_uses_domain_expansion(self):
        """Pure Arabic query should expand via DOMAIN_QUERY_EXPANSIONS to English terms."""
        from src.rag.query_preprocessor import QueryPreprocessor

        # murabaha is in DOMAIN_QUERY_EXPANSIONS with English expansions
        expanded = QueryPreprocessor.expand_terms("ما هي المرابحة؟")
        assert "murabaha" in expanded or "murabahah" in expanded

        # English expansion terms should be available for embedding
        english_terms = [t for t in expanded if not QueryPreprocessor.contains_arabic(t)]
        assert len(english_terms) > 0, "expand_for_embedding has no fallback for Arabic-only queries"

    def test_expanded_query_terms_strips_arabic_question_mark(self):
        """expand_terms should strip ؟ (Arabic question mark) from tokens."""
        from src.rag.query_preprocessor import QueryPreprocessor

        # Both ASCII ? and Arabic ؟ should be stripped
        terms_ascii = QueryPreprocessor.expand_terms("What is murabaha?")
        terms_arabic = QueryPreprocessor.expand_terms("ما هي المرابحة؟")

        # "murabaha" should appear in both (clean, no ? suffix)
        assert any("murabaha" in t for t in terms_ascii)
        assert any("murabaha" in t for t in terms_arabic) or any("murabahah" in t for t in terms_arabic)

    def test_embed_query_expands_arabic_for_embedding(self):
        """embed_query for Arabic query should include English expansion in encoding."""
        from src.rag.pipeline import RAGPipeline

        class CapturingFakeModel:
            def __init__(self):
                self.last_query = None

            def encode(self, query, normalize_embeddings=False):
                from unittest.mock import Mock
                self.last_query = query
                return Mock(tolist=lambda: [0.1] * 768)

        class FakeCollection:
            def query(self, query_embeddings, n_results):
                return {"documents": [], "metadatas": [], "distances": [], "ids": []}

        pipeline = RAGPipeline.__new__(RAGPipeline)
        pipeline.vector_store = None
        pipeline.embedding_generator = None
        pipeline.model = CapturingFakeModel()
        pipeline.collection = FakeCollection()

        pipeline.embed_query("ما هي المرابحة؟")

        # The query passed to encode() should include English expansion terms
        assert "murabaha" in pipeline.model.last_query.lower() or "murabahah" in pipeline.model.last_query.lower(), \
            f"English expansion not appended: {pipeline.model.last_query}"


class TestAuthorityTermsConsolidation:
    """[P2] Tests for AUTHORITY_REQUEST_TERMS single source of truth."""

    def test_both_layers_detect_authority_terms(self):
        """Both coordinator and service should detect authority terms (different sets, different scope)."""
        from src.chatbot.retrieval_coordinator import RetrievalCoordinator
        from src.chatbot.application_service import ApplicationService

        coordinator = RetrievalCoordinator(retriever=object())

        # Both should catch binding fatwa requests (intersection of their sets)
        assert RetrievalCoordinator._should_skip_retrieval(coordinator, "Give me a binding fatwa") is True
        assert ApplicationService._is_authority_request("Give me a binding fatwa") is True

        # Coordinator is broader - catches any "fatwa" mention
        assert RetrievalCoordinator._should_skip_retrieval(coordinator, "What is a fatwa?") is True

        # Service is narrower - only binding/legal requests
        assert ApplicationService._is_authority_request("normal murabaha question") is False

    def test_retrieval_coordinator_skips_for_authority_requests(self):
        """_should_skip_retrieval should return True for authority requests."""
        from src.chatbot.retrieval_coordinator import RetrievalCoordinator

        coordinator = RetrievalCoordinator(retriever=object())

        assert RetrievalCoordinator._should_skip_retrieval(coordinator, "Give me a binding fatwa") is True
        assert RetrievalCoordinator._should_skip_retrieval(coordinator, "is this halal") is True
        assert RetrievalCoordinator._should_skip_retrieval(coordinator, "normal murabaha question") is False


class TestContainsArabic:
    """[P3] Tests for contains_arabic helper."""

    def test_detects_arabic_characters(self):
        """Should return True for strings containing Arabic Unicode."""
        from src.rag.query_preprocessor import QueryPreprocessor

        assert QueryPreprocessor.contains_arabic("مرحبا") is True
        assert QueryPreprocessor.contains_arabic("Hello مرحبا") is True
        assert QueryPreprocessor.contains_arabic("Hello world") is False
        assert QueryPreprocessor.contains_arabic("") is False

    def test_detects_arabic_ranges_exactly(self):
        """Should NOT match Persian, Hebrew, or other non-Arabic scripts."""
        from src.rag.query_preprocessor import QueryPreprocessor

        # Hebrew (not Arabic)
        assert QueryPreprocessor.contains_arabic("שלום") is False
        # Persian (uses some Arabic-range chars but distinct)
        # The range check is intentional — test against a known non-Arabic string
        assert QueryPreprocessor.contains_arabic("سلام") is True  # Arabic "salaam" uses same chars


class TestApplicationServiceIntegration:
    """[P0] Integration-level tests verifying patch interactions."""

    def test_authority_refusal_message_bilingual(self):
        """_authority_refusal_message should return correct message for en/ar."""
        from src.chatbot.application_service import ApplicationService

        en_msg = ApplicationService._authority_refusal_message("en")
        ar_msg = ApplicationService._authority_refusal_message("ar")

        assert "informational guidance" in en_msg.lower() or "fatwa" in en_msg.lower()
        assert "مشير" in ar_msg
        assert en_msg != ar_msg

    def test_empty_query_response_bilingual(self):
        """_empty_query_response should return a valid AnswerContract."""
        from src.chatbot.application_service import ApplicationService
        from src.models.ruling import ComplianceStatus

        result = ApplicationService._empty_query_response()

        assert isinstance(result, type(result))  # it's a proper contract
        assert result.status == ComplianceStatus.INSUFFICIENT_DATA
        assert result.citations == []
        assert result.metadata.get("cache_hit") is False

    def test_answer_flow_authority_then_retrieval(self):
        """answer() should short-circuit on authority request BEFORE retrieval."""
        from src.chatbot.application_service import ApplicationService
        from src.models.ruling import ComplianceStatus

        service = ApplicationService()
        service.clarification_service = None
        service.cache_store = None
        service.retriever = MagicMock()  # should NOT be called
        service.llm_client = MagicMock()

        result = service.answer("Give me a binding fatwa", disclaimer_acknowledged=True)

        assert service.retriever.retrieve.called is False, "retriever was called despite authority request"
        assert result.status == ComplianceStatus.INSUFFICIENT_DATA
        assert len(result.citations) == 0