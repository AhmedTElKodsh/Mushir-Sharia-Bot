from unittest.mock import Mock


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
