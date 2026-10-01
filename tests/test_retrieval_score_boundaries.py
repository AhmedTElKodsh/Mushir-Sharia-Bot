"""Provider and pipeline boundaries, including malformed evidence and diagnostic fallback."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.rag.pipeline import RAGPipeline, ScoredDoc
from src.rag.qdrant_store import QdrantVectorStore
from src.rag.vector_store import VectorStore

pytestmark = pytest.mark.unit
BAD = [None, float('nan'), float('inf'), -float('inf'), True, '0.9', 'invalid']


def pipeline():
    result = RAGPipeline.__new__(RAGPipeline)
    result.embed_query = Mock(return_value=[0.1, 0.2])
    result.vector_store = None
    result.bm25_retriever = None
    return result


@pytest.mark.parametrize('query', ['definition', 'تعريف'])
def test_pipeline_does_not_trust_provider_threshold(query):
    rag = pipeline()
    rag.vector_store = Mock()
    rag.vector_store.similarity_search.return_value = [
        {'chunk_id': str(i), 'content': 'source', 'metadata': {}, **({'similarity': score} if score is not None else {})}
        for i, score in enumerate([.49, .5, .51] + BAD)
    ]
    assert [c['chunk_id'] for c in rag.retrieve(query, threshold=.5)] == ['1', '2']


@pytest.mark.parametrize('bad', BAD)
def test_diagnostic_fallback_never_promotes_invalid_provider_score(bad):
    rag = pipeline()
    rag.vector_store = Mock()
    rag.vector_store.similarity_search.return_value = [dict(content='source', metadata={}, similarity=bad)]
    assert rag.retrieve('definition', threshold=.5, allow_low_confidence_fallback=True) == []


def test_chroma_pipeline_dense_cutoff_and_missing_distance(monkeypatch):
    rag = pipeline()
    rag.collection = Mock()
    scores = [.49, .5, .51] + BAD
    rag.collection.query.return_value = {
        'ids': [[str(i) for i in range(len(scores) + 1)]],
        'documents': [['definition'] * (len(scores) + 1)],
        'metadatas': [[{}] * (len(scores) + 1)],
        'distances': [[1 - s if isinstance(s, float) else s for s in scores]],
    }
    monkeypatch.setattr('src.rag.pipeline._domain_rerank_score', lambda q, d, m, s, t: s)
    assert [c.chunk_id for c in rag.retrieve('definition', threshold=.5)] == ['2', '1']


def test_hybrid_final_rank_cutoff_excludes_below_boundary():
    rag = pipeline()
    rag.collection = Mock()
    rag.collection.query.return_value = {'documents': [[]]}
    rag.bm25_retriever = Mock()
    rag.bm25_retriever.retrieve.return_value = [
        ScoredDoc(str(i), 'definition', score, {}) for i, score in enumerate([3., 2., 1., float('inf')])
    ]
    assert [c.chunk_id for c in rag.retrieve('definition', threshold=.5, mode='hybrid')] == ['0', '1']


@pytest.mark.parametrize('adapter', [VectorStore, QdrantVectorStore])
def test_adapters_inclusive_cutoff_reject_nonfinite_and_missing(adapter):
    store = adapter.__new__(adapter)
    scores = [.49, .5, .51] + BAD
    if adapter is QdrantVectorStore:
        store.collection_name = 'test'
        store.client = Mock()
        store.client.query_points.return_value = SimpleNamespace(points=[
            SimpleNamespace(id=str(i), score=s, payload={'content': 'definition'}) for i, s in enumerate(scores)
        ])
    else:
        store.collection = Mock()
        store.collection.query.return_value = {
            'ids': [[str(i) for i in range(len(scores))]], 'documents': [['definition'] * len(scores)],
            'metadatas': [[{}] * len(scores)],
            'distances': [[1 - s if isinstance(s, float) else s for s in scores]],
        }
    assert [c['chunk_id'] for c in store.similarity_search([.1], threshold=.5)] == ['1', '2']


@pytest.mark.parametrize('bad', BAD + [-.1, 1.1])
def test_invalid_threshold_fails_before_embedding_or_provider(bad):
    rag = pipeline()
    with pytest.raises(ValueError):
        rag.retrieve('definition', threshold=bad)
    rag.embed_query.assert_not_called()


def test_application_custom_retriever_cannot_bypass_cutoff_or_missing_score():
    from src.chatbot.application_service import ApplicationService
    from tests.test_l1_contracts import FakeRetriever
    chunks = [dict(content='source', metadata={}, score=s) for s in [.49, .5, .51] + BAD]
    service = ApplicationService(retriever=FakeRetriever(chunks))
    assert [c['score'] for c in service._retrieve('definition', k=5, threshold=.5)] == [.5, .51]
