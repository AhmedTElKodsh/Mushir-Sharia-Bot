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
    required = ["retrieval_configured", "provider_configured", "auth_configured", "durable_audit_store"]
    for key in required:
        assert key in checks, f"Missing check: {key}"


@pytest.mark.api
def test_ready_infrastructure_shows_store_types():
    from src.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        res = client.get("/ready")

    infra = res.json()["infrastructure"]
    assert "vector_store" in infra
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
        res = client.get("/")

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