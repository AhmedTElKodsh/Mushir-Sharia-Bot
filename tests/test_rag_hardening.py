import pytest


def _embedding(first_value: float):
    return [first_value] + [0.0] * 767


@pytest.mark.unit
def test_citation_validator_fails_closed_for_unsupported_citation():
    from src.chatbot.citation_validator import CitationValidator
    from src.models.schema import AAOIFICitation, SemanticChunk

    chunk = SemanticChunk(
        chunk_id="chunk-1",
        text="AAOIFI requires ownership and risk transfer before resale.",
        citation=AAOIFICitation(
            standard_id="FAS-01",
            section="1",
            page=None,
            source_file="FAS-01.md",
        ),
        score=0.9,
    )

    citations = CitationValidator().validate("COMPLIANT: See [FAS-99 §9].", [chunk])

    assert citations == []


@pytest.mark.service
def test_application_service_rewrites_unsupported_answer_to_insufficient_data():
    from src.chatbot.application_service import ApplicationService
    from src.models.ruling import ComplianceStatus
    from src.models.schema import AAOIFICitation, SemanticChunk

    class Retriever:
        def retrieve(self, query, k=5, threshold=0.3):
            return [
                SemanticChunk(
                    chunk_id="chunk-1",
                    text="AAOIFI requires ownership and risk transfer before resale.",
                    citation=AAOIFICitation(
                        standard_id="FAS-01",
                        section="1",
                        page=None,
                        source_file="FAS-01.md",
                    ),
                    score=0.9,
                )
            ]

    class LLM:
        model_name = "fake"

        def generate(self, prompt):
            return "COMPLIANT: This is allowed under [FAS-99 §9]."

    result = ApplicationService(retriever=Retriever(), llm_client=LLM()).answer("Is this allowed?")

    assert result.status == ComplianceStatus.INSUFFICIENT_DATA
    assert result.citations == []
    assert result.answer.startswith("INSUFFICIENT_DATA")


@pytest.mark.service
def test_application_service_bypasses_response_cache_in_eval_mode(monkeypatch):
    from src.chatbot.application_service import ApplicationService
    from src.models.schema import AAOIFICitation, SemanticChunk
    from src.storage.cache import InMemoryCacheStore

    class Retriever:
        def retrieve(self, query, k=5, threshold=0.3):
            return [
                SemanticChunk(
                    chunk_id="chunk-1",
                    text="AAOIFI requires ownership and risk transfer before resale.",
                    citation=AAOIFICitation(
                        standard_id="FAS-01",
                        section="1",
                        page=None,
                        source_file="FAS-01.md",
                    ),
                    score=0.9,
                )
            ]

    class LLM:
        model_name = "fake"

        def __init__(self):
            self.calls = 0

        def generate(self, prompt):
            self.calls += 1
            return "COMPLIANT: Supported by [FAS-01 §1]."

    llm = LLM()
    service = ApplicationService(
        retriever=Retriever(),
        llm_client=llm,
        cache_store=InMemoryCacheStore(),
    )

    service.answer("Is this compliant?")
    service.answer("Is this compliant?")
    monkeypatch.setenv("RAG_EVAL_MODE", "true")
    service.answer("Is this compliant?")

    assert llm.calls == 2


@pytest.mark.integration
def test_qdrant_vector_store_round_trips_chunks_in_memory():
    from src.models.chunk import SemanticChunk
    from src.rag.qdrant_store import QdrantVectorStore

    store = QdrantVectorStore(location=":memory:", collection_name="test_aaoifi", vector_size=768)
    chunks = [
        SemanticChunk(
            chunk_id="murabaha-ownership",
            document_id="doc-1",
            content="AAOIFI murabaha text requires ownership and risk transfer before resale.",
            chunk_index=0,
            token_count=80,
            embedding=_embedding(1.0),
            metadata={"standard_number": "FAS-01", "section_number": "1"},
        ),
        SemanticChunk(
            chunk_id="ijara-lease",
            document_id="doc-2",
            content="AAOIFI ijara text discusses usufruct and lease responsibilities.",
            chunk_index=0,
            token_count=80,
            embedding=[0.0, 1.0] + [0.0] * 766,
            metadata={"standard_number": "FAS-02", "section_number": "2"},
        ),
    ]

    store.store_chunks(chunks)
    results = store.similarity_search(_embedding(1.0), k=2, threshold=0.0)

    assert results[0]["chunk_id"] == "murabaha-ownership"
    assert results[0]["metadata"]["standard_number"] == "FAS-01"
    assert store.get_collection_stats()["chunk_count"] == 2


@pytest.mark.unit
def test_evaluate_retrieval_reports_hit_recall_and_mrr():
    from scripts.evaluate_rag import evaluate_retrieval

    class Pipeline:
        def retrieve(self, query, k=5, threshold=0.0):
            return [
                {"chunk_id": "wrong", "metadata": {}, "content": "", "similarity": 0.8},
                {
                    "chunk_id": "hashed-chunk-id",
                    "metadata": {"standard_number": "FAS-01"},
                    "content": "",
                    "similarity": 0.7,
                },
            ]

    report = evaluate_retrieval(
        [
            {
                "query": "murabaha ownership",
                "answerable": True,
                "required_source_ids": ["FAS-01"],
            }
        ],
        k=2,
        pipeline=Pipeline(),
    )

    assert report["hit_at_k"] == 1.0
    assert report["recall_at_k"] == 1.0
    assert report["mrr"] == 0.5
