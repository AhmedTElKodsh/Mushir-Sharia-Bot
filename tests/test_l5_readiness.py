import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
def test_l5_stable_public_api_smoke_paths():
    from src.api.main import create_app

    app = create_app()

    with TestClient(app) as client:
        root = client.get("/")
        chat = client.get("/chat")
        health = client.get("/health")
        ready = client.get("/ready")
        metrics = client.get("/metrics")
        disclaimer = client.get("/api/v1/compliance/disclaimer")

    assert root.status_code == 200
    assert root.json()["endpoints"]["query"] == "/api/v1/query"
    assert root.json()["endpoints"]["query_stream"] == "/api/v1/query/stream"
    assert chat.status_code == 200
    assert 'id="prompt"' in chat.text
    assert "/api/v1/query/stream" in chat.text
    assert health.json()["status"] == "healthy"
    assert ready.json()["status"] == "ready"
    assert ready.json()["readiness_level"] == "dev"
    assert ready.json()["infrastructure"]["vector_store"] in {"chroma", "qdrant"}
    assert ready.json()["infrastructure"]["session_store"]
    assert ready.json()["infrastructure"]["rate_limit_store"]
    assert ready.json()["infrastructure"]["audit_store"]
    assert ready.json()["infrastructure"]["cache_store"]
    assert "mushir_request_count" in metrics.text
    assert disclaimer.json()["requires_acknowledgement"] is True
    assert disclaimer.json()["version"] == "l5-bilingual-disclaimer-v1"
    assert "ar" in disclaimer.json()["supported_languages"]
    assert "مشير" in disclaimer.json()["translations"]["ar"]

@pytest.mark.api
def test_l5_production_readiness_degrades_without_required_services(monkeypatch):
    from src.api.main import create_app

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("AUTH_TOKEN", raising=False)

    with TestClient(create_app()) as client:
        ready = client.get("/ready")

    payload = ready.json()
    assert ready.status_code == 503
    assert payload["status"] == "degraded"
    assert payload["readiness_level"] == "production"
    assert payload["checks"]["provider_configured"] is False
    assert payload["checks"]["auth_configured"] is False
    assert payload["checks"]["durable_audit_store"] is False


@pytest.mark.api
def test_l5_rest_and_sse_share_final_answer_contract():
    from src.api.dependencies import get_application_service
    from src.api.main import create_app
    from src.models.ruling import AAOIFICitation, AnswerContract, ComplianceStatus

    class Service:
        def answer(self, query, session_id=None, request_id=None, disclaimer_acknowledged=True):
            return AnswerContract(
                answer="COMPLIANT: Supported by [FAS-01 §1].",
                status=ComplianceStatus.COMPLIANT,
                citations=[
                    AAOIFICitation(
                        document_id="FAS-01.md",
                        standard_number="FAS-01",
                        section_number="1",
                        excerpt="AAOIFI requires ownership and risk transfer before resale.",
                        confidence_score=0.91,
                        quote_start=0,
                        quote_end=62,
                    )
                ],
                reasoning_summary="Grounded in FAS-01.",
                metadata={"confidence": 0.91},
            )

    app = create_app()
    app.dependency_overrides[get_application_service] = lambda: Service()

    with TestClient(app) as client:
        rest = client.post("/api/v1/query", json={"query": "Is this compliant?", "session_id": "s1"})
        stream = client.post("/api/v1/query/stream", json={"query": "Is this compliant?", "session_id": "s1"})

    assert rest.status_code == 200
    assert stream.status_code == 200
    assert rest.json()["answer"] in stream.text
    assert rest.json()["citations"][0]["excerpt"] in stream.text
    assert rest.json()["citations"][0]["confidence_score"] == 0.91


@pytest.mark.api
def test_l5_stream_error_state_is_user_safe():
    from src.api.dependencies import get_application_service
    from src.api.main import create_app

    class Service:
        def answer(self, query, session_id=None, request_id=None, disclaimer_acknowledged=True):
            raise RuntimeError("provider unavailable")

    app = create_app()
    app.dependency_overrides[get_application_service] = lambda: Service()

    with TestClient(app) as client:
        response = client.post("/api/v1/query/stream", json={"query": "bad state"})

    assert response.status_code == 200
    assert "event: started" in response.text
    assert "event: error" in response.text
    assert "The answer service is temporarily unavailable. Please try again later." in response.text
    assert "provider unavailable" not in response.text


@pytest.mark.api
def test_l5_infrastructure_fallback_logs_do_not_expose_exception_details(monkeypatch, capsys):
    from src.api import main

    class BrokenAuditStore:
        def __init__(self):
            raise RuntimeError("postgres://user:secret@example/db")

    monkeypatch.setenv("AUDIT_DATABASE_URL", "postgres://user:secret@example/db")
    monkeypatch.setattr("src.storage.audit_store.PostgresAuditStore", BrokenAuditStore)

    store = main._build_audit_store()
    captured = capsys.readouterr()

    assert type(store).__name__ == "NullAuditStore"
    assert "PostgreSQL audit store: configured backend unavailable" in captured.out
    assert "secret" not in captured.out
    assert "postgres://" not in captured.out
