"""Regression guard for P1-S1 static extraction.

Captures baseline HTML output from / and /chat before extraction,
then verifies the extracted static files produce equivalent output.
"""
import pytest
from fastapi.testclient import TestClient


BASELINE_STRINGS = [
    "Mushir Sharia Chatbot",
    'id="prompt"',
    'id="messages"',
    'id="chat-form"',
    "Ask a Sharia compliance question",
    "/api/v1/query/stream",
    "Ask Mushir",
    "I want to invest in a company",
]


@pytest.mark.api
def test_root_returns_chat_html():
    from src.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    for s in BASELINE_STRINGS:
        assert s in response.text, f"Missing expected string in / response: {s!r}"


@pytest.mark.api
def test_chat_returns_chat_html():
    from src.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        response = client.get("/chat")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    for s in BASELINE_STRINGS:
        assert s in response.text, f"Missing expected string in /chat response: {s!r}"


@pytest.mark.api
def test_chat_html_contains_css_js_structure():
    """Verify structural elements present in the current inline CHAT_HTML."""
    from src.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        html = client.get("/chat").text

    # CSS block
    assert "<style>" in html
    assert "</style>" in html
    assert ":root {" in html

    # JS block
    assert "<script>" in html
    assert "</script>" in html
    assert "function addMessage" in html
    assert "function parseSse" in html
    assert "addEventListener(\"submit\"" in html or "addEventListener('submit'" in html

    # HTML structure
    assert "messages" in html
    assert "chat-form" in html
    assert "prompt" in html
    assert "send" in html
