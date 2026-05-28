from unittest.mock import Mock
from types import SimpleNamespace

import pytest


pytestmark = pytest.mark.unit


def test_rag_pipeline_retrieve():
    """Test RAG pipeline retrieval."""
    mock_vector_store = Mock()
    mock_embedding_gen = Mock()
    mock_embedding_gen.embed_text.return_value = [0.1] * 768
    mock_vector_store.similarity_search.return_value = [
        {"chunk_id": "chunk1", "content": "test", "metadata": {}, "similarity": 0.95}
    ]
    from src.rag.pipeline import RAGPipeline

    pipeline = RAGPipeline(mock_vector_store, mock_embedding_gen)
    chunks = pipeline.retrieve("test query", k=3, threshold=0.7)
    assert len(chunks) == 1
    assert chunks[0]["chunk_id"] == "chunk1"


def test_rag_pipeline_augment_prompt():
    """Test prompt augmentation."""
    mock_vector_store = Mock()
    mock_embedding_gen = Mock()
    from src.rag.pipeline import RAGPipeline

    pipeline = RAGPipeline(mock_vector_store, mock_embedding_gen)
    chunks = [
        {"content": "Standard content here", "metadata": {"standard_number": "FAS 1", "section_title": "Scope"}}
    ]
    prompt = pipeline.augment_prompt("Is this compliant?", chunks)
    assert "FAS 1" in prompt
    assert "Standard content here" in prompt
    assert "AAOIFI standards context" in prompt


def test_rag_pipeline_returns_no_chunks_when_threshold_filters_all():
    """User-facing retrieval should fail closed when all evidence is weak."""
    from src.rag.pipeline import RAGPipeline

    class FakeModel:
        def encode(self, query, normalize_embeddings=False):
            return Mock(tolist=lambda: [0.1, 0.2, 0.3])

    class FakeCollection:
        def query(self, query_embeddings, n_results):
            return {
                "documents": [["Weak unrelated excerpt"]],
                "metadatas": [[{"source_file": "FAS-screening.md", "section": "2"}]],
                "distances": [[0.85]],
                "ids": [["chunk-low-score"]],
            }

    pipeline = RAGPipeline.__new__(RAGPipeline)
    pipeline.vector_store = None
    pipeline.embedding_generator = None
    pipeline.model = FakeModel()
    pipeline.collection = FakeCollection()

    chunks = pipeline.retrieve("zzzz", k=1, threshold=0.3)

    assert chunks == []


def test_rag_pipeline_can_return_low_confidence_chunks_for_diagnostics():
    """Diagnostics can opt into low-confidence candidates without changing answer safety."""
    from src.rag.pipeline import RAGPipeline

    class FakeModel:
        def encode(self, query, normalize_embeddings=False):
            return Mock(tolist=lambda: [0.1, 0.2, 0.3])

    class FakeCollection:
        def query(self, query_embeddings, n_results):
            return {
                "documents": [["Weak unrelated excerpt"]],
                "metadatas": [[{"source_file": "FAS-screening.md", "section": "2"}]],
                "distances": [[0.85]],
                "ids": [["chunk-low-score"]],
            }

    pipeline = RAGPipeline.__new__(RAGPipeline)
    pipeline.vector_store = None
    pipeline.embedding_generator = None
    pipeline.model = FakeModel()
    pipeline.collection = FakeCollection()

    chunks = pipeline.retrieve(
        "zzzz",
        k=1,
        threshold=0.3,
        allow_low_confidence_fallback=True,
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_id == "chunk-low-score"


def test_rag_pipeline_reranks_bilingual_chroma_candidates_with_domain_terms():
    """Arabic queries should be able to lift cross-lingual Murabaha evidence."""
    from src.rag.pipeline import RAGPipeline

    class FakeModel:
        def encode(self, query, normalize_embeddings=False):
            assert normalize_embeddings is True
            return Mock(tolist=lambda: [0.1, 0.2, 0.3])

    class FakeCollection:
        def __init__(self):
            self.n_results = None

        def query(self, query_embeddings, n_results):
            self.n_results = n_results
            return {
                "documents": [
                    [
                        "General Arabic finance excerpt",
                        "Murabaha and other deferred payment sales require careful recognition.",
                    ]
                ],
                "metadatas": [
                    [
                        {"source_file": "conceptual-ar.md", "section": "1", "source_language": "ar"},
                        {"source_file": "FAS-murabaha-en.md", "section": "2", "source_language": "en"},
                    ]
                ],
                "distances": [[0.20, 0.22]],
                "ids": [["chunk-general", "chunk-murabaha"]],
            }

    collection = FakeCollection()
    pipeline = RAGPipeline.__new__(RAGPipeline)
    pipeline.vector_store = None
    pipeline.embedding_generator = None
    pipeline.model = FakeModel()
    pipeline.collection = collection

    chunks = pipeline.retrieve("ما حكم المرابحة؟", k=1, threshold=0.3)

    assert collection.n_results == 3
    assert chunks[0].chunk_id == "chunk-murabaha"


def test_query_preprocessor_expands_arabic_installment_and_late_penalty_terms():
    from src.rag.query_preprocessor import QueryPreprocessor

    query = "هل يجوز شراء سيارة بالتقسيط مع غرامة تأخير؟"
    terms = QueryPreprocessor.expand_terms(query)

    assert QueryPreprocessor.detect_language(query) == "ar"
    assert "murabaha" in terms
    assert "late fee" in terms


def test_rag_pipeline_filters_quarantined_chunks_and_exposes_trace_metadata():
    """Answer retrieval must not admit explicitly quarantined source chunks."""
    from src.rag.pipeline import RAGPipeline

    class FakeModel:
        def encode(self, query, normalize_embeddings=False):
            return Mock(tolist=lambda: [0.1, 0.2, 0.3])

    class FakeCollection:
        def query(self, query_embeddings, n_results, where=None):
            return {
                "documents": [["Poisoned unofficial text", "Cataloged FAS-28 evidence"]],
                "metadatas": [[
                    {
                        "source_file": "unofficial.md",
                        "standard_number": "FAS-99",
                        "metadata_status": "quarantined_missing_catalog",
                        "source_family": "fas",
                    },
                    {
                        "source_file": "fas-28.md",
                        "standard_number": "FAS-28",
                        "metadata_status": "cataloged",
                        "source_family": "fas",
                        "parent_chunk_id": "fas-28:section-1",
                        "child_chunk_id": "fas-28:section-1:0",
                        "section_path": "FAS-28 > Murabaha",
                        "citation_anchor": "p1",
                    },
                ]],
                "distances": [[0.05, 0.08]],
                "ids": [["poison", "fas-28-child"]],
            }

    pipeline = RAGPipeline.__new__(RAGPipeline)
    pipeline.vector_store = None
    pipeline.embedding_generator = None
    pipeline.model = FakeModel()
    pipeline.collection = FakeCollection()

    chunks = pipeline.retrieve(
        "murabaha",
        k=2,
        threshold=0.0,
        filters={"source_family": "fas"},
        mode="dense",
    )

    assert [chunk.chunk_id for chunk in chunks] == ["fas-28-child"]
    assert chunks[0].metadata["metadata_status"] == "cataloged"
    assert chunks[0].metadata["retrieval_mode"] == "dense"
    assert chunks[0].metadata["score_components"]["dense_similarity"] > 0
    assert chunks[0].metadata["parent_chunk_id"] == "fas-28:section-1"


def test_rag_pipeline_does_not_broaden_when_filtered_chroma_query_is_empty():
    """Source-family routing is an authority boundary, not a soft preference."""
    from src.rag.pipeline import RAGPipeline

    class FakeModel:
        def encode(self, query, normalize_embeddings=False):
            return Mock(tolist=lambda: [0.1, 0.2, 0.3])

    class FakeCollection:
        def __init__(self):
            self.calls = []

        def query(self, query_embeddings, n_results, where=None):
            self.calls.append(where)
            return {
                "documents": [["Accounting-only FAS text"]],
                "metadatas": [[
                    {
                        "source_file": "fas-28.md",
                        "standard_number": "FAS-28",
                        "metadata_status": "cataloged",
                        "source_family": "fas",
                    }
                ]],
                "distances": [[0.05]],
                "ids": [["fas-only"]],
            }

    collection = FakeCollection()
    pipeline = RAGPipeline.__new__(RAGPipeline)
    pipeline.vector_store = None
    pipeline.embedding_generator = None
    pipeline.model = FakeModel()
    pipeline.collection = collection

    chunks = pipeline.retrieve(
        "is this murabaha transaction permissible?",
        k=2,
        threshold=0.0,
        filters={"source_family": "sharia_standard"},
    )

    assert chunks == []
    assert collection.calls == [{"source_family": "sharia_standard"}]


def test_rag_pipeline_translates_list_filters_for_chroma_candidate_standards():
    from src.rag.pipeline import RAGPipeline

    class FakeModel:
        def encode(self, query, normalize_embeddings=False):
            return Mock(tolist=lambda: [0.1, 0.2, 0.3])

    class FakeCollection:
        def __init__(self):
            self.calls = []

        def query(self, query_embeddings, n_results, where=None):
            self.calls.append(where)
            return {
                "documents": [["Default evidence", "Qard evidence"]],
                "metadatas": [[
                    {
                        "source_file": "ss-03.md",
                        "standard_number": "SS-03",
                        "metadata_status": "cataloged",
                        "source_family": "sharia_standard",
                    },
                    {
                        "source_file": "ss-19.md",
                        "standard_number": "SS-19",
                        "metadata_status": "cataloged",
                        "source_family": "sharia_standard",
                    },
                ]],
                "distances": [[0.05, 0.06]],
                "ids": [["ss-03", "ss-19"]],
            }

    collection = FakeCollection()
    pipeline = RAGPipeline.__new__(RAGPipeline)
    pipeline.vector_store = None
    pipeline.embedding_generator = None
    pipeline.model = FakeModel()
    pipeline.collection = collection

    chunks = pipeline.retrieve(
        "cash loan late fee",
        k=2,
        threshold=0.0,
        filters={"source_family": "sharia_standard", "standard_number": ["SS-03", "SS-19"]},
    )

    assert [chunk.metadata["standard_number"] for chunk in chunks] == ["SS-03", "SS-19"]
    assert collection.calls == [
        {
            "$and": [
                {"source_family": "sharia_standard"},
                {"standard_number": {"$in": ["SS-03", "SS-19"]}},
            ]
        }
    ]


def test_rag_pipeline_vector_store_branch_applies_filters_and_quarantine():
    """Qdrant/vector adapters must not bypass governance filtering."""
    from src.rag.pipeline import RAGPipeline

    class FakeEmbeddingService:
        def embed_text(self, query):
            return [0.1, 0.2, 0.3]

    class FakeVectorStore:
        def similarity_search(self, query_embedding, k=5, threshold=0.3, filters=None):
            return [
                {
                    "chunk_id": "wrong-family",
                    "content": "Sharia standard text",
                    "metadata": {"source_family": "sharia_standard", "metadata_status": "cataloged"},
                    "similarity": 0.95,
                },
                {
                    "chunk_id": "quarantined",
                    "content": "Unofficial FAS text",
                    "metadata": {"source_family": "fas", "metadata_status": "quarantined_missing_catalog"},
                    "similarity": 0.94,
                },
                {
                    "chunk_id": "fas-cataloged",
                    "content": "Cataloged FAS text",
                    "metadata": {"source_family": "fas", "metadata_status": "cataloged"},
                    "similarity": 0.93,
                },
            ]

    pipeline = RAGPipeline.__new__(RAGPipeline)
    pipeline.vector_store = FakeVectorStore()
    pipeline.embedding_service = FakeEmbeddingService()

    chunks = pipeline.retrieve("murabaha", filters={"source_family": "fas"})

    assert [chunk["chunk_id"] for chunk in chunks] == ["fas-cataloged"]


def test_qdrant_vector_store_overfetches_before_client_side_filtering(monkeypatch):
    from src.rag.qdrant_store import QdrantVectorStore

    class FakeClient:
        def __init__(self):
            self.limit = None

        def query_points(self, collection_name, query, limit):
            self.limit = limit
            return SimpleNamespace(
                points=[
                    SimpleNamespace(
                        id=f"wrong-{index}",
                        score=0.95,
                        payload={
                            "chunk_id": f"wrong-{index}",
                            "content": "wrong family",
                            "source_family": "fas",
                        },
                    )
                    for index in range(5)
                ]
                + [
                    SimpleNamespace(
                        id="right",
                        score=0.93,
                        payload={
                            "chunk_id": "right",
                            "content": "sharia evidence",
                            "source_family": "sharia_standard",
                        },
                    )
                ]
            )

    client = FakeClient()
    store = QdrantVectorStore.__new__(QdrantVectorStore)
    store.client = client
    store.collection_name = "aaoifi"
    monkeypatch.setenv("QDRANT_FILTER_OVERFETCH_MULTIPLIER", "6")

    chunks = store.similarity_search(
        [0.1, 0.2, 0.3],
        k=1,
        threshold=0.0,
        filters={"source_family": "sharia_standard"},
    )

    assert client.limit == 6
    assert [chunk["chunk_id"] for chunk in chunks] == ["right"]


def test_rag_pipeline_hybrid_mode_adds_rrf_trace_and_lifts_lexical_match():
    """Hybrid mode should let exact legal terms beat a slightly denser miss."""
    from src.rag.pipeline import RAGPipeline

    class FakeModel:
        def encode(self, query, normalize_embeddings=False):
            return Mock(tolist=lambda: [0.1, 0.2, 0.3])

    class FakeCollection:
        def query(self, query_embeddings, n_results, where=None):
            return {
                "documents": [[
                    "Unrelated leasing text with generic finance words.",
                    "Murabaha ownership before resale and risk transfer.",
                ]],
                "metadatas": [[
                    {"source_file": "fas-32.md", "standard_number": "FAS-32", "metadata_status": "cataloged"},
                    {"source_file": "fas-28.md", "standard_number": "FAS-28", "metadata_status": "cataloged"},
                ]],
                "distances": [[0.05, 0.12]],
                "ids": [["dense-wrong", "lexical-right"]],
            }

    pipeline = RAGPipeline.__new__(RAGPipeline)
    pipeline.vector_store = None
    pipeline.embedding_generator = None
    pipeline.model = FakeModel()
    pipeline.collection = FakeCollection()
    
    class FakeBM25Retriever:
        def retrieve(self, query, top_k):
            from src.rag.pipeline import ScoredDoc
            if "murabaha" in query.lower():
                return [ScoredDoc(doc_id="lexical-right", text="Murabaha ownership...", score=10.0, metadata={"source_file": "fas-28.md", "standard_number": "FAS-28", "metadata_status": "cataloged"})]
            return []
            
    pipeline.bm25_retriever = FakeBM25Retriever()

    chunks = pipeline.retrieve(
        "murabaha ownership before resale",
        k=1,
        threshold=0.0,
        mode="hybrid",
    )

    assert chunks[0].chunk_id == "lexical-right"
    assert chunks[0].metadata["retrieval_mode"] == "hybrid"
    assert chunks[0].metadata["score_components"]["lexical_score"] > 0
    assert chunks[0].metadata["score_components"]["rrf_score"] > 0


def test_bm25_retriever_and_rrf_merge_rank_lexical_matches():
    from src.rag.pipeline import BM25Retriever, ScoredDoc, rrf_merge

    sparse = BM25Retriever([
        ScoredDoc(doc_id="generic", text="Generic finance leasing text.", score=0.0, metadata={}),
        ScoredDoc(doc_id="dummy1", text="Another dummy document.", score=0.0, metadata={}),
        ScoredDoc(doc_id="dummy2", text="And another dummy.", score=0.0, metadata={}),
        ScoredDoc(
            doc_id="istisna",
            text="Istisna construction delay penalty actual damage contractor.",
            score=0.0,
            metadata={"standard_number": "SS-11"},
        ),
    ]).retrieve("construction delay penalty in istisna", top_k=2)
    fused = rrf_merge(
        dense_results=[
            SimpleNamespace(chunk_id="generic", score=0.0), 
            SimpleNamespace(chunk_id="istisna", score=0.0)
        ],
        sparse_results=sparse,
        k=60,
    )

    assert sparse[0].doc_id == "istisna"
    assert fused[0] == "istisna"
