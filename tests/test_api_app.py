import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
def test_create_app_lifespan_initializes_service_once():
    from src.api.main import create_app

    app = create_app()

    assert not hasattr(app.state, "application_service")
    with TestClient(app) as client:
        first = client.app.state.application_service
        second = client.app.state.application_service
        assert first is second
        response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


@pytest.mark.api
def test_dependency_override_replaces_application_service():
    from src.api.dependencies import get_application_service
    from src.api.main import create_app
    from src.models.ruling import AnswerContract, ComplianceStatus

    class FakeService:
        def answer(self, query, session_id=None):
            return AnswerContract(
                answer=f"fake answer for {query}",
                status=ComplianceStatus.INSUFFICIENT_DATA,
                citations=[],
                reasoning_summary="fake",
            )

    app = create_app()
    app.dependency_overrides[get_application_service] = lambda: FakeService()
    with TestClient(app) as client:
        response = client.post("/api/v1/query", json={"query": "test question"})

    assert response.status_code == 200
    assert response.json()["answer"] == "fake answer for test question"
    assert response.headers["X-Request-ID"]
