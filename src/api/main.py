import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import List

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

from src.api.error_handling import ErrorResponse
from src.api.rate_limit import InMemoryRateLimiter
from src.api.routes import router as api_router
from src.chatbot.application_service import ApplicationService
from src.chatbot.session_manager import SessionManager
from src.observability.metrics import MetricsRegistry


def parse_cors_origins(value: str) -> List[str]:
    """Parse CORS origins without evaluating environment-provided code."""
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return [origin.strip() for origin in value.split(",") if origin.strip()]
    if isinstance(parsed, list) and all(isinstance(origin, str) for origin in parsed):
        return parsed
    if isinstance(parsed, str):
        return [parsed]
    raise ValueError("CORS_ORIGINS must be a JSON string, JSON list, or comma-separated string")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.session_manager = _build_session_manager()
    app.state.rate_limiter = _build_rate_limiter()
    app.state.audit_store = _build_audit_store()
    app.state.application_service = ApplicationService(audit_store=app.state.audit_store)
    app.state.metrics = MetricsRegistry()
    app.state.infrastructure = _infrastructure_status(app)
    yield


def _build_session_manager():
    if os.getenv("SESSION_STORE_TYPE", "memory").lower() == "redis":
        try:
            from src.chatbot.redis_session_manager import RedisSessionManager

            return RedisSessionManager(expiry_minutes=int(os.getenv("SESSION_EXPIRY_MINUTES", "30")))
        except Exception as exc:
            print(f"Redis session store unavailable, falling back to memory: {exc}")
            return SessionManager(expiry_minutes=int(os.getenv("SESSION_EXPIRY_MINUTES", "30")))
    return SessionManager(expiry_minutes=int(os.getenv("SESSION_EXPIRY_MINUTES", "30")))


def _build_rate_limiter():
    limit = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    window_seconds = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "3600"))
    if os.getenv("RATE_LIMIT_STORE_TYPE", "memory").lower() == "redis":
        try:
            from src.api.redis_rate_limit import RedisRateLimiter

            return RedisRateLimiter(limit=limit, window_seconds=window_seconds)
        except Exception as exc:
            print(f"Redis rate limiter unavailable, falling back to memory: {exc}")
            return InMemoryRateLimiter(limit=limit, window_seconds=window_seconds)
    return InMemoryRateLimiter(limit=limit, window_seconds=window_seconds)


def _build_audit_store():
    if os.getenv("AUDIT_DATABASE_URL") or os.getenv("DATABASE_URL"):
        try:
            from src.storage.audit_store import PostgresAuditStore

            return PostgresAuditStore()
        except Exception as exc:
            print(f"PostgreSQL audit store unavailable, falling back to null audit store: {exc}")
            pass
    from src.storage.audit_store import NullAuditStore

    return NullAuditStore()


def _infrastructure_status(app: FastAPI):
    return {
        "vector_store": os.getenv("VECTOR_DB_TYPE", "chroma").lower(),
        "session_store": type(app.state.session_manager).__name__,
        "rate_limit_store": type(app.state.rate_limiter).__name__,
        "audit_store": type(app.state.audit_store).__name__,
    }


def create_app() -> FastAPI:
    app = FastAPI(
        title="Sharia Compliance Chatbot API",
        description="RAG-based Islamic finance compliance analysis using AAOIFI standards",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.metrics = MetricsRegistry()
    app.state.infrastructure = {
        "vector_store": os.getenv("VECTOR_DB_TYPE", "chroma").lower(),
        "session_store": "not_initialized",
        "rate_limit_store": "not_initialized",
        "audit_store": "not_initialized",
    }

    app.add_middleware(
        CORSMiddleware,
        allow_origins=parse_cors_origins(os.getenv("CORS_ORIGINS", '["*"]')),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context_and_errors(request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = MetricsRegistry.timer()
        try:
            response = await call_next(request)
        except Exception:
            response = JSONResponse(
                status_code=500,
                content=ErrorResponse.create(
                    "INTERNAL_ERROR",
                    "An internal error occurred",
                    request_id,
                ),
            )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        app.state.metrics.record(
            path=request.url.path,
            status_code=response.status_code,
            duration_seconds=MetricsRegistry.timer() - start,
        )
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        return JSONResponse(
            status_code=422,
            content=ErrorResponse.create(
                "VALIDATION_ERROR",
                "Request validation failed",
                request_id,
            ),
        )

    @app.get("/")
    async def root():
        return {
            "status": "ok",
            "name": "Sharia Compliance Chatbot API",
            "version": "1.0.0",
            "endpoints": {
                "health": "/health",
                "ready": "/ready",
                "query": "/api/v1/query",
                "query_stream": "/api/v1/query/stream",
                "sessions": "/api/v1/sessions",
                "docs": "/docs",
            },
        }

    @app.get("/chat", response_class=HTMLResponse)
    async def chat_page():
        return CHAT_HTML

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return Response(status_code=204)

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "timestamp": datetime.now(UTC).isoformat(), "version": "1.0.0"}

    @app.get("/ready")
    async def ready_check():
        return {
            "status": "ready",
            "timestamp": datetime.now(UTC).isoformat(),
            "infrastructure": app.state.infrastructure,
        }

    @app.get("/metrics", response_class=PlainTextResponse)
    async def metrics():
        return app.state.metrics.render()

    app.include_router(api_router, prefix="/api/v1")
    return app


CHAT_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mushir Sharia Chatbot</title>
  <style>
    :root {
      color-scheme: light;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f7f5ef;
      color: #1d2521;
    }
    body { margin: 0; min-height: 100vh; display: grid; grid-template-rows: auto 1fr; }
    header { padding: 22px 28px 14px; border-bottom: 1px solid #ddd6c7; background: #fbfaf6; }
    h1 { margin: 0; font-size: 24px; font-weight: 700; letter-spacing: 0; }
    main {
      display: grid;
      grid-template-rows: 1fr auto;
      gap: 16px;
      width: min(920px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 20px 0 24px;
    }
    #messages { display: flex; flex-direction: column; gap: 12px; overflow-y: auto; min-height: 360px; padding: 4px; }
    .message {
      max-width: 78%;
      padding: 12px 14px;
      border: 1px solid #d8d1c3;
      border-radius: 8px;
      background: #fff;
      line-height: 1.45;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .user { align-self: flex-end; background: #e8f1ed; border-color: #b7cec3; }
    .assistant { align-self: flex-start; }
    .event { align-self: flex-start; max-width: 78%; color: #5f6b65; font-size: 13px; padding: 2px 4px; }
    form { display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: end; padding-top: 12px; border-top: 1px solid #ddd6c7; }
    textarea {
      min-height: 72px;
      max-height: 180px;
      resize: vertical;
      border: 1px solid #bdb5a7;
      border-radius: 8px;
      padding: 12px;
      font: inherit;
      background: #fff;
      color: inherit;
    }
    button { height: 44px; border: 0; border-radius: 8px; padding: 0 18px; background: #214f44; color: white; font: inherit; font-weight: 650; cursor: pointer; }
    button:disabled { opacity: 0.55; cursor: wait; }
    @media (max-width: 640px) {
      header { padding-inline: 16px; }
      main { width: calc(100vw - 24px); }
      form { grid-template-columns: 1fr; }
      button { width: 100%; }
      .message, .event { max-width: 100%; }
    }
  </style>
</head>
<body>
  <header><h1>Mushir Sharia Chatbot</h1></header>
  <main>
    <section id="messages" aria-live="polite" aria-label="Chat messages">
      <div class="message assistant">Ask a compliance question to test the L2 stream.</div>
    </section>
    <form id="chat-form">
      <textarea id="prompt" name="prompt" placeholder="Ask Mushir about an Islamic finance transaction...">I want to invest in a company</textarea>
      <button id="send" type="submit">Ask Mushir</button>
    </form>
  </main>
  <script>
    const form = document.getElementById("chat-form");
    const promptInput = document.getElementById("prompt");
    const messages = document.getElementById("messages");
    const send = document.getElementById("send");
    let context = {};

    function addMessage(kind, text) {
      const node = document.createElement("div");
      node.className = kind === "event" ? "event" : `message ${kind}`;
      node.textContent = text;
      messages.appendChild(node);
      messages.scrollTop = messages.scrollHeight;
      return node;
    }

    function parseSse(text) {
      return text
        .trim()
        .split("\\n\\n")
        .map(block => {
          const event = {};
          for (const line of block.split("\\n")) {
            if (line.startsWith("event: ")) event.type = line.slice(7);
            if (line.startsWith("data: ")) event.data = JSON.parse(line.slice(6));
          }
          return event;
        })
        .filter(event => event.type);
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const query = promptInput.value.trim();
      if (!query) return;
      addMessage("user", query);
      send.disabled = true;
      send.textContent = "Streaming...";
      try {
        const response = await fetch("/api/v1/query/stream", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({query, context})
        });
        const events = parseSse(await response.text());
        for (const item of events) {
          const data = item.data || {};
          if (item.type === "started") addMessage("event", "Thinking...");
          if (item.type === "retrieval") addMessage("event", `Confidence ${Number(data.confidence || 0).toFixed(2)}`);
          if (item.type === "token") addMessage("assistant", data.text);
          if (item.type === "error") addMessage("assistant", data.message);
          if (item.type === "done") {
            if (data.clarification_question) addMessage("assistant", data.clarification_question);
            context = data.metadata || context;
            addMessage("event", `Complete - ${data.status}`);
          }
        }
      } catch (error) {
        addMessage("assistant", `Request failed: ${error.message}`);
      } finally {
        send.disabled = false;
        send.textContent = "Ask Mushir";
      }
    });
  </script>
</body>
</html>
"""


app = create_app()
