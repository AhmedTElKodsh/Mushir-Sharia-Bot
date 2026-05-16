import pytest
from fastapi.testclient import TestClient


class FakeService:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def answer(self, query, session_id=None):
        self.calls.append((query, session_id))
        if self.error:
            raise self.error
        return self.result


@pytest.mark.api
def test_rest_query_returns_l1_contract():
    from src.api.dependencies import get_application_service
    from src.api.main import create_app
    from src.models.ruling import AAOIFICitation, AnswerContract, ComplianceStatus

    service = FakeService(
        AnswerContract(
            answer="Compliant [FAS-01 §1].",
            status=ComplianceStatus.COMPLIANT,
            citations=[
                AAOIFICitation(
                    document_id="fas01.md",
                    standard_number="FAS-01",
                    section_number="1",
                    excerpt="excerpt",
                )
            ],
            reasoning_summary="Grounded in FAS-01.",
            metadata={"confidence": 0.88},
        )
    )
    app = create_app()
    app.dependency_overrides[get_application_service] = lambda: service

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/query",
            json={"query": "Is it compliant?", "session_id": "session-1"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "COMPLIANT"
    assert response.json()["citations"][0]["section_number"] == "1"
    assert response.headers["X-Request-ID"]
    assert service.calls == [("Is it compliant?", "session-1")]


@pytest.mark.api
def test_rest_query_maps_service_errors_to_controlled_payload():
    from src.api.dependencies import get_application_service
    from src.api.main import create_app

    app = create_app()
    app.dependency_overrides[get_application_service] = lambda: FakeService(error=RuntimeError("provider down"))

    with TestClient(app) as client:
        response = client.post("/api/v1/query", json={"query": "Is it compliant?"})

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "SERVICE_ERROR"
    assert response.json()["error"]["message"] == "The answer service is temporarily unavailable. Please try again later."
    assert "provider down" not in response.text
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.api
def test_rest_query_maps_validation_errors_to_controlled_payload():
    from src.api.main import create_app

    app = create_app()

    with TestClient(app) as client:
        response = client.post("/api/v1/query", json={"query": "   "})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.api
def test_rest_query_does_not_retry_internal_type_errors():
    from src.api.dependencies import get_application_service
    from src.api.main import create_app

    class BrokenService:
        def __init__(self):
            self.calls = 0

        def answer(self, query, session_id=None, request_id=None, disclaimer_acknowledged=True):
            self.calls += 1
            raise TypeError("request_id caused an internal failure")

    service = BrokenService()
    app = create_app()
    app.dependency_overrides[get_application_service] = lambda: service

    with TestClient(app) as client:
        response = client.post("/api/v1/query", json={"query": "Is it compliant?"})

    assert response.status_code == 500
    assert service.calls == 1
    assert "request_id caused" not in response.text


@pytest.mark.api
def test_rest_query_forwards_conversation_history_when_supported():
    from src.api.dependencies import get_application_service
    from src.api.main import create_app
    from src.models.ruling import AnswerContract, ComplianceStatus

    class HistoryAwareService:
        def __init__(self):
            self.history = None

        def answer(
            self,
            query,
            session_id=None,
            request_id=None,
            disclaimer_acknowledged=True,
            conversation_history=None,
        ):
            self.history = conversation_history
            return AnswerContract(
                answer="Not addressed in retrieved AAOIFI standards.",
                status=ComplianceStatus.INSUFFICIENT_DATA,
                citations=[],
                reasoning_summary="No chunks.",
                metadata={"confidence": 0.0},
            )

    service = HistoryAwareService()
    app = create_app()
    app.dependency_overrides[get_application_service] = lambda: service

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/query",
            json={
                "query": "Can you clarify?",
                "conversation_history": [
                    {"role": "user", "content": "I want to invest in a company"},
                    {"role": "assistant", "content": "Please provide sector and debt details."},
                ],
            },
        )

    assert response.status_code == 200
    assert service.history == [
        {"role": "user", "content": "I want to invest in a company"},
        {"role": "assistant", "content": "Please provide sector and debt details."},
    ]
