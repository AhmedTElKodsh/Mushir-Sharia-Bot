import pytest
from fastapi.testclient import TestClient


class CountingService:
    def answer(self, query, session_id=None):
        from src.models.ruling import AnswerContract, ComplianceStatus

        return AnswerContract(
            answer=f"answer for {query}",
            status=ComplianceStatus.INSUFFICIENT_DATA,
            citations=[],
            reasoning_summary="fake",
        )


@pytest.mark.api
def test_metrics_endpoint_exposes_prometheus_text():
    from src.api.dependencies import get_application_service
    from src.api.main import create_app

    app = create_app()
    app.dependency_overrides[get_application_service] = lambda: CountingService()

    with TestClient(app) as client:
        client.post("/api/v1/query", json={"query": "screen this investment"})
        metrics = client.get("/metrics")

    assert metrics.status_code == 200
    assert "mushir_request_count" in metrics.text
    assert 'path="/api/v1/query"' in metrics.text


@pytest.mark.api
def test_ready_endpoint_reports_l3_infrastructure_status():
    from src.api.main import create_app

    app = create_app()

    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["infrastructure"]["vector_store"] in {"chroma", "qdrant"}
    assert data["infrastructure"]["session_store"]
    assert data["infrastructure"]["rate_limit_store"]
    assert data["infrastructure"]["audit_store"]


@pytest.mark.service
def test_application_service_writes_audit_entry():
    from src.chatbot.application_service import ApplicationService
    from src.models.ruling import AnswerContract, ComplianceStatus

    class Retriever:
        def retrieve(self, query, k=5, threshold=0.3):
            return []

    class AuditStore:
        def __init__(self):
            self.calls = []

        def log_answer(self, query, answer, session_id=None, request_id=None):
            self.calls.append((query, answer.status, session_id, request_id))

    audit_store = AuditStore()
    service = ApplicationService(retriever=Retriever(), audit_store=audit_store)

    answer = service.answer("unknown structure", session_id="s1", request_id="r1")

    assert isinstance(answer, AnswerContract)
    assert answer.status == ComplianceStatus.INSUFFICIENT_DATA
    assert audit_store.calls == [("unknown structure", ComplianceStatus.INSUFFICIENT_DATA, "s1", "r1")]
