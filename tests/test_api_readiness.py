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
    assert body["version"] == "1.0.0"


@pytest.mark.api
def test_root_returns_api_info():
    from src.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        res = client.get("/api")

    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Sharia Compliance Chatbot API"
    assert body["version"] == "1.0.0"
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
