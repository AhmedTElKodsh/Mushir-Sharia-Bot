"""Integration tests for /sessions endpoints."""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
def test_create_session_returns_new_session_id():
    from src.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        res = client.post("/api/v1/sessions")

    assert res.status_code == 200
    body = res.json()
    assert "session_id" in body
    assert body["status"] == "created"


@pytest.mark.api
def test_create_session_id_is_uuid():
    from src.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        res = client.post("/api/v1/sessions")

    import uuid

    session_id = res.json()["session_id"]
    uuid.UUID(session_id)


@pytest.mark.api
def test_get_session_history_returns_404_for_nonexistent():
    from src.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        res = client.get("/api/v1/sessions/nonexistent-session/history")

    assert res.status_code == 404


@pytest.mark.api
def test_session_query_endpoint_is_disabled_instead_of_bypassing_query_gates():
    from src.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        create_res = client.post("/api/v1/sessions")
        session_id = create_res.json()["session_id"]

        query_res = client.post(
            f"/api/v1/sessions/{session_id}/query",
            json={"query": "I want to invest in a tech company"},
        )
        assert query_res.status_code == 501

        history_res = client.get(f"/api/v1/sessions/{session_id}/history")
        assert history_res.status_code == 200
        body = history_res.json()
        assert body["session_id"] == session_id


@pytest.mark.api
def test_get_session_history_returns_404_for_unknown_session():
    from src.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        res = client.get("/api/v1/sessions/unknown-session/history")
        assert res.status_code == 404
