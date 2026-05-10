import json

from fastapi.testclient import TestClient

from src.api.main import app, parse_cors_origins


def _sse_events(response_text):
    events = []
    for block in response_text.strip().split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line.removeprefix("data: ")))
    return events


def test_root_returns_api_entrypoint():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["endpoints"]["health"] == "/health"
    assert response.json()["endpoints"]["query"] == "/api/v1/query"


def test_chat_page_contains_input_and_output_surface():
    client = TestClient(app)

    response = client.get("/chat")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'id="prompt"' in response.text
    assert 'id="messages"' in response.text
    assert "Ask Mushir" in response.text


def test_session_created_session_can_be_queried():
    client = TestClient(app)

    created = client.post("/api/v1/sessions")
    assert created.status_code == 200
    session_id = created.json()["session_id"]

    queried = client.post(
        f"/api/v1/sessions/{session_id}/query",
        json={"content": "I want to invest in a company"},
    )

    assert queried.status_code == 200
    assert queried.json()["status"] == "clarifying"


def test_query_stream_returns_l2_sse_events_for_clarification():
    client = TestClient(app)

    response = client.post("/api/v1/query", json={"content": "I want to invest in a company"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _sse_events(response.text)
    assert [event["type"] for event in events] == ["thinking", "clarifying"]
    assert events[-1]["questions"] == ["What type of company or business activity is involved?"]
    assert events[-1]["context"]["session_id"]
    assert events[-1]["context"]["extracted_variables"]["operation_type"] == "investment"
    assert events[-1]["context"]["awaiting_variable"] == "company_activity"


def test_query_stream_retrieves_generates_and_completes_when_ready(monkeypatch):
    client = TestClient(app)

    class FakeChunk:
        text = "AAOIFI excerpt"
        score = 0.91

        class citation:
            standard_id = "FAS-01"
            section = "1"
            source_file = "fas01.md"

    class FakeRAGPipeline:
        def retrieve(self, query, k=5):
            assert "non_compliant_revenue_percent: 3.0" in query
            return [FakeChunk()]

    monkeypatch.setattr("src.api.routes.RAGPipeline", lambda: FakeRAGPipeline())
    monkeypatch.setattr("src.api.routes.call_llm", lambda system, prompt: "According to AAOIFI [FAS-01 §1].")

    response = client.post(
        "/api/v1/query",
        json={
            "content": "About 3%",
            "context": {
                "session_id": "ready-session",
                "extracted_variables": {
                    "operation_type": "investment",
                    "company_activity": "Tech company with some haram revenue",
                },
                "awaiting_variable": "non_compliant_revenue_percent",
            },
        },
    )

    assert response.status_code == 200
    events = _sse_events(response.text)
    assert [event["type"] for event in events] == [
        "thinking",
        "retrieving",
        "generating",
        "chunk",
        "complete",
    ]
    assert events[1]["chunks"] == 1
    assert events[3]["text"] == "According to AAOIFI [FAS-01 §1]."
    assert events[4]["ruling"]["answer"] == "According to AAOIFI [FAS-01 §1]."

def test_query_stream_returns_error_event_when_llm_fails(monkeypatch):
    client = TestClient(app)

    class FakeChunk:
        text = "AAOIFI excerpt"
        score = 0.91

        class citation:
            standard_id = "FAS-01"
            section = "1"
            source_file = "fas01.md"

    class FakeRAGPipeline:
        def retrieve(self, query, k=5):
            return [FakeChunk()]

    def fail_llm(system, prompt):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr("src.api.routes.RAGPipeline", lambda: FakeRAGPipeline())
    monkeypatch.setattr("src.api.routes.call_llm", fail_llm)

    response = client.post(
        "/api/v1/query",
        json={
            "content": "About 3%",
            "context": {
                "session_id": "llm-failure-session",
                "extracted_variables": {
                    "operation_type": "investment",
                    "company_activity": "Tech company",
                },
                "awaiting_variable": "non_compliant_revenue_percent",
            },
        },
    )

    assert response.status_code == 200
    events = _sse_events(response.text)
    assert [event["type"] for event in events] == ["thinking", "retrieving", "generating", "error"]
    assert events[-1]["message"] == "The model provider failed while generating this answer."
    assert events[-1]["retryable"] is True


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
