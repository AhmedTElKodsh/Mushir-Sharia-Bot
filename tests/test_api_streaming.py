import json

import pytest
from fastapi.testclient import TestClient


def _events(text):
    parsed = []
    for block in text.strip().split("\n\n"):
        event = {}
        for line in block.splitlines():
            if line.startswith("event: "):
                event["event"] = line.removeprefix("event: ")
            if line.startswith("data: "):
                event["data"] = json.loads(line.removeprefix("data: "))
        if event:
            parsed.append(event)
    return parsed


@pytest.mark.api
def test_query_stream_emits_l2_event_order():
    from src.api.dependencies import get_application_service
    from src.api.main import create_app
    from src.models.ruling import AnswerContract, ComplianceStatus

    class FakeService:
        def answer(self, query, session_id=None):
            return AnswerContract(
                answer="Not addressed in retrieved AAOIFI standards.",
                status=ComplianceStatus.INSUFFICIENT_DATA,
                citations=[],
                reasoning_summary="No chunks.",
                metadata={"confidence": 0.0},
            )

    app = create_app()
    app.dependency_overrides[get_application_service] = lambda: FakeService()

    with TestClient(app) as client:
        response = client.post("/api/v1/query/stream", json={"query": "test"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _events(response.text)
    assert [event["event"] for event in events] == ["started", "retrieval", "token", "done"]
    assert events[-1]["data"]["status"] == "INSUFFICIENT_DATA"


@pytest.mark.api
def test_query_stream_returns_error_event_for_service_failure():
    from src.api.dependencies import get_application_service
    from src.api.main import create_app

    class FailingService:
        def answer(self, query, session_id=None):
            raise RuntimeError("provider down")

    app = create_app()
    app.dependency_overrides[get_application_service] = lambda: FailingService()

    with TestClient(app) as client:
        response = client.post("/api/v1/query/stream", json={"query": "test"})

    events = _events(response.text)
    assert [event["event"] for event in events] == ["started", "error"]
    assert events[-1]["data"]["code"] == "SERVICE_ERROR"
