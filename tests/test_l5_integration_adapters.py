import os
import uuid

import pytest


@pytest.mark.integration
def test_redis_session_rate_limit_and_cache_adapters_with_configured_service():
    redis_url = os.getenv("MUSHIR_TEST_REDIS_URL")
    if not redis_url:
        pytest.skip("Set MUSHIR_TEST_REDIS_URL to run Redis adapter integration coverage.")

    from src.api.redis_rate_limit import RedisRateLimiter
    from src.chatbot.redis_session_manager import RedisSessionManager
    from src.storage.cache import RedisCacheStore

    namespace = f"l5-{uuid.uuid4().hex}"
    session_manager = RedisSessionManager(redis_url=redis_url, expiry_minutes=1)
    limiter = RedisRateLimiter(redis_url=redis_url, limit=1, window_seconds=60)
    cache = RedisCacheStore(redis_url=redis_url)
    try:
        session = session_manager.create_session(f"{namespace}-session")
        assert session_manager.get_session(session.session_id).session_id == f"{namespace}-session"

        first = limiter.check(f"{namespace}-client")
        second = limiter.check(f"{namespace}-client")
        assert first.allowed is True
        assert second.allowed is False

        cache.set_json(namespace, "key", {"ok": True}, 60)
        assert cache.get_json(namespace, "key") == {"ok": True}
    finally:
        session_manager.delete_session(f"{namespace}-session")
        cache.client.delete(f"mushir:cache:{namespace}:key")
        for key in cache.client.scan_iter(f"mushir:rate:{namespace}-client:*"):
            cache.client.delete(key)


@pytest.mark.integration
def test_postgres_audit_store_with_configured_database():
    database_url = os.getenv("MUSHIR_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set MUSHIR_TEST_DATABASE_URL to run PostgreSQL audit integration coverage.")

    from src.models.ruling import AnswerContract, ComplianceStatus
    from src.storage.audit_store import PostgresAuditStore

    store = PostgresAuditStore(database_url=database_url)
    request_id = f"l5-request-{uuid.uuid4().hex}"
    audit_id = None
    try:
        audit_id = store.log_answer(
            query="L5 audit smoke",
            answer=AnswerContract(
                answer="Not addressed in retrieved AAOIFI standards.",
                status=ComplianceStatus.INSUFFICIENT_DATA,
                citations=[],
                reasoning_summary="No retrieved excerpts.",
                metadata={"test_run": request_id},
            ),
            session_id=f"l5-session-{uuid.uuid4().hex}",
            request_id=request_id,
        )

        assert audit_id
    finally:
        if audit_id:
            with store.psycopg.connect(store.database_url) as conn:
                conn.execute("DELETE FROM audit_logs WHERE audit_id = %s", (audit_id,))


@pytest.mark.integration
def test_qdrant_runtime_adapter_with_configured_service():
    qdrant_url = os.getenv("MUSHIR_TEST_QDRANT_URL")
    if not qdrant_url:
        pytest.skip("Set MUSHIR_TEST_QDRANT_URL to run Qdrant service integration coverage.")

    from src.models.chunk import SemanticChunk
    from src.rag.qdrant_store import QdrantVectorStore

    vector = [1.0] + [0.0] * 767
    collection = f"mushir_l5_test_{uuid.uuid4().hex}"
    store = QdrantVectorStore(url=qdrant_url, collection_name=collection, vector_size=768)
    try:
        store.store_chunks(
            [
                SemanticChunk(
                    chunk_id="l5-qdrant-chunk",
                    document_id="l5-doc",
                    content="AAOIFI requires source-backed evidence for compliance claims.",
                    chunk_index=0,
                    token_count=10,
                    embedding=vector,
                    metadata={"standard_number": "FAS-L5", "section_number": "1"},
                )
            ]
        )

        results = store.similarity_search(vector, k=1, threshold=0.0)

        assert results[0]["chunk_id"] == "l5-qdrant-chunk"
        assert results[0]["metadata"]["standard_number"] == "FAS-L5"
    finally:
        store.client.delete_collection(collection)
