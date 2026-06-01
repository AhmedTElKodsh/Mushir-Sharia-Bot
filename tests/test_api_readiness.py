"""Unit tests for readiness check and infrastructure status."""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
def test_ready_returns_correct_structure():
    from src.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        res = client.get("/ready")

    body = res.json()
    assert "status" in body
    assert "readiness_level" in body
    assert "effective_release_tier" in body
    assert "required_checks" in body
    assert "checks" in body
    assert "infrastructure" in body


@pytest.mark.api
def test_ready_status_degraded_when_production_and_missing_components(monkeypatch):
    import os

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_TOKEN", "")

    from src.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        res = client.get("/ready")

    body = res.json()
    if body["status"] == "degraded":
        assert res.status_code == 503
    assert body["readiness_level"] == "production"


@pytest.mark.api
def test_ready_checks_all_required_infrastructure_components():
    from src.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        res = client.get("/ready")

    checks = res.json()["checks"]
    required = [
        "retrieval_configured",
        "retriever_ready",
        "sharia_corpus_complete",
        "hard_sharia_ready",
        "provider_configured",
        "auth_configured",
        "auth_enforced",
        "durable_audit_store",
    ]
    for key in required:
        assert key in checks, f"Missing check: {key}"


@pytest.mark.api
def test_ready_reports_partial_sharia_corpus_coverage():
    from src.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        res = client.get("/ready")

    body = res.json()
    coverage = body["evidence_coverage"]["sharia_corpus"]
    assert coverage["status"] == "partial"
    assert coverage["hard_sharia_ready"] is False
    assert coverage["release_gate"] == "fail"
    assert coverage["release_gate_fail_count"] == 60
    assert coverage["covered_sharia_standard_count"] == 55
    assert coverage["target_sharia_standard_count"] == 60
    assert coverage["missing_sharia_standard_count"] == 5
    assert coverage["missing_sharia_standards"] == ["SS-55", "SS-56", "SS-57", "SS-58", "SS-59"]
    assert coverage["blocked_source_count"] == 5
    assert coverage["blocked_source_standards"] == ["SS-55", "SS-56", "SS-57", "SS-58", "SS-59"]
    assert coverage["blocked_source_details"][0]["status"] == "missing_full_official_or_licensed_text"
    assert coverage["covered_sharia_standards"][:5] == ["SS-01", "SS-02", "SS-03", "SS-04", "SS-05"]
    assert coverage["covered_sharia_standards"][-1] == "SS-60"
    assert body["checks"]["sharia_corpus_complete"] is False
    assert body["checks"]["hard_sharia_ready"] is False
    assert coverage["no_go_reasons"]


@pytest.mark.api
def test_ready_infrastructure_shows_store_types():
    from src.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        res = client.get("/ready")

    infra = res.json()["infrastructure"]
    assert "vector_store" in infra
    assert "retriever_ready" in infra
    assert "session_store" in infra
    assert "rate_limit_store" in infra
    assert "audit_store" in infra
    assert "cache_store" in infra


@pytest.mark.api
def test_lifespan_wires_session_store_into_application_service():
    from src.api.main import create_app

    app = create_app()
    with TestClient(app):
        service = app.state.application_service

    assert service.session_store is app.state.session_manager


@pytest.mark.api
def test_health_returns_ok_and_timestamp():
    from src.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        res = client.get("/health")

    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "healthy"
    assert "timestamp" in body
    assert "version" in body
    assert body["version"] == "1.5.0"
    assert body["version_label"] == "V1.5"


@pytest.mark.api
def test_root_returns_api_info():
    from src.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        res = client.get("/api")

    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Sharia Compliance Chatbot API"
    assert body["version"] == "1.5.0"
    assert body["version_label"] == "V1.5"
    assert "endpoints" in body
    assert "/api/v1/query" in body["endpoints"].values()


@pytest.mark.api
def test_favicon_returns_204():
    from src.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        res = client.get("/favicon.ico")

    assert res.status_code == 204


@pytest.mark.api
def test_production_ready_degrades_when_retriever_startup_fails(monkeypatch):
    from src.api import main as api_main

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-provider-key")
    monkeypatch.setenv("AUTH_TOKEN", "test-auth-token")
    monkeypatch.setattr(api_main, "_build_retriever", lambda: None)

    app = api_main.create_app()
    with TestClient(app) as client:
        res = client.get("/ready")

    body = res.json()
    assert res.status_code == 503
    assert body["status"] == "degraded"
    assert body["checks"]["retriever_ready"] is False
    assert body["infrastructure"]["retriever_ready"] is False


@pytest.mark.api
def test_public_demo_ready_degrades_when_runtime_provider_missing(monkeypatch):
    from src.api import main as api_main

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("RELEASE_TIER", "public-demo")
    monkeypatch.setattr(api_main, "_build_retriever", lambda: object())

    app = api_main.create_app()
    with TestClient(app) as client:
        res = client.get("/ready")

    body = res.json()
    assert res.status_code == 503
    assert body["status"] == "degraded"
    assert body["checks"]["provider_configured"] is False


@pytest.mark.api
def test_public_demo_ready_accepts_explicit_mock_provider(monkeypatch):
    from src.api import main as api_main

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("RELEASE_TIER", "public-demo")
    monkeypatch.setenv("MUSHIR_MOCK_LLM", "true")
    monkeypatch.setattr(api_main, "_build_retriever", lambda: object())

    app = api_main.create_app()
    with TestClient(app) as client:
        res = client.get("/ready")

    body = res.json()
    assert body["checks"]["provider_configured"] is True


@pytest.mark.api
def test_production_pilot_ready_does_not_require_hard_sharia_ready(monkeypatch):
    from src.api import main as api_main

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("RELEASE_TIER", "production-pilot")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-provider-key")
    monkeypatch.setenv("AUTH_TOKEN", "test-auth-token")
    monkeypatch.setattr(api_main, "_build_retriever", lambda: object())

    app = api_main.create_app()
    with TestClient(app) as client:
        app.state.infrastructure.update(
            {
                "session_store": "RedisSessionStore",
                "rate_limit_store": "RedisRateLimiter",
                "audit_store": "PostgresAuditStore",
                "cache_store": "RedisCacheStore",
                "retriever_ready": True,
                "vector_store": "chroma",
            }
        )
        res = client.get("/ready")

    body = res.json()
    assert body["effective_release_tier"] == "production-pilot"
    assert "hard_sharia_ready" not in body["required_checks"]


@pytest.mark.api
def test_production_api_requires_bearer_auth(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_TOKEN", "test-token")

    from src.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        res = client.post(
            "/api/v1/query",
            json={"query": "What is Murabaha?", "context": {"disclaimer_acknowledged": True}},
        )

    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.api
def test_production_api_fails_closed_when_auth_token_missing(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("AUTH_TOKEN", raising=False)

    from src.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        res = client.post(
            "/api/v1/query",
            json={"query": "What is Murabaha?", "context": {"disclaimer_acknowledged": True}},
        )

    assert res.status_code == 503
    assert res.json()["error"]["code"] == "AUTH_MISCONFIGURED"


@pytest.mark.api
def test_production_api_accepts_matching_bearer_auth(monkeypatch):
    from src.api.dependencies import get_application_service
    from src.models.ruling import AnswerContract, ComplianceStatus

    class FastService:
        def answer(self, query, **kwargs):
            return AnswerContract(
                answer="ok",
                status=ComplianceStatus.INSUFFICIENT_DATA,
                citations=[],
                reasoning_summary="test",
                limitations="test",
                metadata={"confidence": 0.0},
            )

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_TOKEN", "test-token")

    from src.api.main import create_app

    app = create_app()
    app.dependency_overrides[get_application_service] = lambda: FastService()

    with TestClient(app) as client:
        res = client.post(
            "/api/v1/query",
            json={"query": "What is Murabaha?", "context": {"disclaimer_acknowledged": True}},
            headers={"Authorization": "Bearer test-token"},
        )

    assert res.status_code == 200


@pytest.mark.api
def test_qdrant_readiness_checks_are_reported_and_gate_runtime(monkeypatch):
    from src.api import main as api_main

    class FakeQdrantStore:
        def readiness_status(self):
            return {
                "collection_populated": True,
                "governed_metadata_ready": True,
                "bilingual_coverage_ready": False,
                "retrieval_smoke_ready": True,
                "chunk_count": 10,
            }

    class FakeRetriever:
        vector_store = FakeQdrantStore()

    monkeypatch.setenv("VECTOR_DB_TYPE", "qdrant")
    monkeypatch.setenv("RELEASE_TIER", "public-demo")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-provider-key")
    monkeypatch.setattr(api_main, "_build_retriever", lambda: FakeRetriever())

    app = api_main.create_app()
    with TestClient(app) as client:
        res = client.get("/ready")

    body = res.json()
    assert res.status_code == 503
    assert body["checks"]["qdrant_collection_populated"] is True
    assert body["checks"]["qdrant_governed_metadata_ready"] is True
    assert body["checks"]["qdrant_bilingual_coverage_ready"] is False
    assert body["checks"]["qdrant_retrieval_smoke_ready"] is True
    assert body["infrastructure"]["qdrant"]["chunk_count"] == 10


@pytest.mark.api
def test_retrieval_error_log_does_not_include_raw_secret(capsys):
    from src.chatbot.application_service import ApplicationService
    from src.models.ruling import ComplianceStatus

    class SecretFailingRetriever:
        def retrieve(self, query, k=5, threshold=0.3):
            raise RuntimeError("OPENROUTER_API_KEY=sk-test-secret")

    service = ApplicationService(retriever=SecretFailingRetriever())
    answer = service.answer("What is murabahah?")

    captured = capsys.readouterr()
    assert answer.status == ComplianceStatus.INSUFFICIENT_DATA
    assert "could not reach the AAOIFI evidence index" in answer.answer
    assert "retriever/index readiness" in answer.answer
    assert "sk-test-secret" not in captured.out
    assert "OPENROUTER_API_KEY" not in captured.out
    assert "sk-test-secret" not in answer.answer
    assert "OPENROUTER_API_KEY" not in answer.answer
