import json

from fastapi.testclient import TestClient

from src.api.dependencies import get_application_service
from src.api.main import app, parse_cors_origins
from src.models.ruling import AAOIFICitation, AnswerContract, ComplianceStatus


def _named_sse_events(response_text):
    events = []
    for block in response_text.strip().split("\n\n"):
        event = {}
        for line in block.splitlines():
            if line.startswith("event: "):
                event["type"] = line.removeprefix("event: ")
            if line.startswith("data: "):
                event["data"] = json.loads(line.removeprefix("data: "))
        if event:
            events.append(event)
    return events


def test_root_returns_api_entrypoint():
    client = TestClient(app)

    response = client.get("/api")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["endpoints"]["health"] == "/health"
    assert response.json()["endpoints"]["query"] == "/api/v1/query"
    assert response.json()["endpoints"]["query_stream"] == "/api/v1/query/stream"


def test_chat_page_contains_input_and_output_surface():
    client = TestClient(app)

    response = client.get("/chat")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'id="prompt"' in response.text
    assert 'id="messages"' in response.text
    assert "Ask Mushir" in response.text
    # CSS/JS externalised to static files in Phase 1 refactor
    assert '/static/css/chat.css' in response.text
    assert '/static/js/app.js' in response.text


def test_session_query_endpoint_is_disabled():
    client = TestClient(app)

    created = client.post("/api/v1/sessions")
    assert created.status_code == 200
    session_id = created.json()["session_id"]

    queried = client.post(
        f"/api/v1/sessions/{session_id}/query",
        json={"content": "I want to invest in a company"},
    )

    assert queried.status_code == 501


def test_query_stream_returns_l2_sse_events_for_clarification():
    class FakeService:
        def answer(self, query, session_id=None):
            return AnswerContract(
                answer="What type of company or business activity is involved?",
                status=ComplianceStatus.CLARIFICATION_NEEDED,
                citations=[],
                reasoning_summary="Missing material facts.",
                clarification_question="What type of company or business activity is involved?",
            )

    app.dependency_overrides[get_application_service] = lambda: FakeService()
    client = TestClient(app)

    response = client.post("/api/v1/query/stream", json={"content": "I want to invest in a company"})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _named_sse_events(response.text)
    assert [event["type"] for event in events] == ["started", "retrieval", "token", "done"]
    assert events[-1]["data"]["status"] == "CLARIFICATION_NEEDED"
    assert events[-1]["data"]["clarification_question"] == "What type of company or business activity is involved?"


def test_query_requires_disclaimer_acknowledgement_by_default():
    class FakeService:
        def answer(self, query, session_id=None, request_id=None, disclaimer_acknowledged=True):
            assert disclaimer_acknowledged is False
            return AnswerContract(
                answer="Please acknowledge the Sharia guidance disclaimer before continuing.",
                status=ComplianceStatus.CLARIFICATION_NEEDED,
                citations=[],
                reasoning_summary="Disclaimer acknowledgement is required.",
                clarification_question=(
                    "Do you acknowledge that Mushir provides informational guidance only "
                    "and not a binding Sharia ruling?"
                ),
                metadata={"disclaimer_required": True},
            )

    client = TestClient(app)
    app.dependency_overrides[get_application_service] = lambda: FakeService()

    response = client.post("/api/v1/query", json={"query": "Is this compliant?"})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "CLARIFICATION_NEEDED"
    assert response.json()["metadata"]["disclaimer_required"] is True


def test_query_stream_retrieves_generates_and_completes_when_ready():
    class FakeService:
        def answer(self, query, session_id=None):
            assert query == "About 3%"
            return AnswerContract(
                answer="According to AAOIFI [FAS-01 §1].",
                status=ComplianceStatus.COMPLIANT,
                citations=[
                    AAOIFICitation(
                        document_id="fas01.md",
                        standard_number="FAS-01",
                        section_number="1",
                        excerpt="AAOIFI excerpt",
                    )
                ],
                reasoning_summary="Grounded in FAS-01.",
                metadata={"confidence": 0.91},
            )

    client = TestClient(app)
    app.dependency_overrides[get_application_service] = lambda: FakeService()

    response = client.post(
        "/api/v1/query/stream",
        json={
            "query": "About 3%",
            "context": {"session_id": "ready-session"},
        },
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    events = _named_sse_events(response.text)
    assert [event["type"] for event in events] == [
        "started",
        "retrieval",
        "token",
        "citation",
        "done",
    ]
    assert events[1]["data"]["confidence"] == 0.91
    assert events[2]["data"]["text"] == "According to AAOIFI [FAS-01 §1]."
    assert events[4]["data"]["answer"] == "According to AAOIFI [FAS-01 §1]."


def test_query_stream_returns_error_event_when_llm_fails():
    class FailingService:
        def answer(self, query, session_id=None):
            raise RuntimeError("model unavailable")

    client = TestClient(app)
    app.dependency_overrides[get_application_service] = lambda: FailingService()

    response = client.post("/api/v1/query/stream", json={"query": "About 3%"})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    events = _named_sse_events(response.text)
    assert [event["type"] for event in events] == ["started", "error"]
    assert events[-1]["data"]["message"] == "The answer service is temporarily unavailable. Please try again later."
    assert "model unavailable" not in response.text


def test_parse_cors_origins_uses_json_not_eval():
    assert parse_cors_origins('["https://example.com", "http://localhost:8000"]') == [
        "https://example.com",
        "http://localhost:8000",
    ]
    assert parse_cors_origins("https://example.com,http://localhost:8000") == [
        "https://example.com",
        "http://localhost:8000",
    ]
    assert parse_cors_origins("__import__('os').system('echo unsafe')") == [
        "__import__('os').system('echo unsafe')"
    ]


def test_login_does_not_issue_dummy_tokens():
    client = TestClient(app)

    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "secret"})

    assert response.status_code == 501
    assert "dummy-token" not in response.text
