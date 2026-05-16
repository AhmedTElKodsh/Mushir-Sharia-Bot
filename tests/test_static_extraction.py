"""Regression guard for P1-S1 static extraction.

Verifies that / and /chat serve the extracted index.html correctly
via FastAPI StaticFiles mount, and that key structural elements
are present in both the HTML response and the static files.
"""
import pytest
from fastapi.testclient import TestClient


# Strings that must appear in the served HTML (not in external JS)
HTML_SURFACE_STRINGS = [
    "Mushir Sharia Chatbot",
    'id="prompt"',
    'id="messages"',
    'id="history-sidebar"',
    "Previous chats",
    'id="chat-form"',
    "Ask a Sharia compliance question",
    "Ask Mushir",
    'placeholder="Ask about an Islamic finance transaction..."',
    '/static/css/base.css',
    '/static/css/chat.css',
    '/static/css/components.css',
    '/static/css/dark.css',
    '/static/js/sse-client.js',
    '/static/js/renderer.js',
    '/static/js/app.js',
]


@pytest.mark.api
def test_root_returns_chat_html():
    from src.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    for s in HTML_SURFACE_STRINGS:
        assert s in response.text, f"Missing expected string in / response: {s!r}"
    assert 'id="disclaimer"' not in response.text
    assert "Informational guidance only" not in response.text


@pytest.mark.api
def test_chat_returns_chat_html():
    from src.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        response = client.get("/chat")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    for s in HTML_SURFACE_STRINGS:
        assert s in response.text, f"Missing expected string in /chat response: {s!r}"
    assert 'id="disclaimer"' not in response.text
    assert "Informational guidance only" not in response.text


@pytest.mark.api
def test_static_files_accessible():
    """Verify that extracted static files are served correctly."""
    from src.api.main import create_app

    app = create_app()
    static_files = [
        "/static/css/base.css",
        "/static/css/chat.css",
        "/static/css/components.css",
        "/static/css/dark.css",
        "/static/js/sse-client.js",
        "/static/js/renderer.js",
        "/static/js/app.js",
        "/static/js/storage.js",
        "/static/js/shortcuts.js",
        "/static/js/flyout.js",
    ]
    with TestClient(app) as client:
        for path in static_files:
            response = client.get(path)
            assert response.status_code == 200, f"Static file not accessible: {path}"


@pytest.mark.api
def test_static_files_contain_expected_content():
    """Verify extracted JS and CSS contain the expected code."""
    from src.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        # Verify sse-client.js has parseSse and processSseStream functions
        sse = client.get("/static/js/sse-client.js").text
        assert "function parseSse" in sse
        assert "function processSseStream" in sse
        assert "event: " in sse or "event:" in sse

        # Verify renderer.js has addMessage, addEvent, renderTypingIndicator,
        # renderErrorBubble, and retryHandler
        renderer = client.get("/static/js/renderer.js").text
        assert "function addMessage" in renderer
        assert "function addEvent" in renderer
        assert "function renderTypingIndicator" in renderer
        assert "function renderErrorBubble" in renderer
        assert "function retryHandler" in renderer

        # Verify app.js has form submit handler, submitQuery, and /api/v1/query/stream
        app_js = client.get("/static/js/app.js").text
        assert "addEventListener" in app_js
        assert "function submitQuery" in app_js
        assert "/api/v1/query/stream" in app_js
        assert "function loadConversation" in app_js
        assert "disclaimer_acknowledged: true" in app_js

        # Verify base.css has :root custom properties
        base = client.get("/static/css/base.css").text
        assert ":root {" in base
        assert "color-scheme" in base

        # Verify chat.css has message styles
        chat = client.get("/static/css/chat.css").text
        assert ".message" in chat
        assert "button" in chat

        # Verify dark.css has media query
        dark = client.get("/static/css/dark.css").text
        assert "@media (prefers-color-scheme: dark)" in dark

        # Verify components.css has typing indicator and error bubble styles
        components = client.get("/static/css/components.css").text
        assert "Components" in components
        assert ".typing-indicator" in components
        assert ".error-bubble" in components
        assert "@keyframes typingDot" in components
        assert "@media (prefers-reduced-motion: reduce)" in components
