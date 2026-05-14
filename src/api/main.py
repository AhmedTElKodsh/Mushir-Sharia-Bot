import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Dict, List

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

from src.api.error_handling import ErrorResponse
from src.api.rate_limit import InMemoryRateLimiter
from src.api.routes import router as api_router
from src.chatbot.application_service import ApplicationService
from src.chatbot.clarification_engine import ClarificationEngine
from src.chatbot.session_manager import SessionManager
from src.observability.metrics import MetricsRegistry


INFRA_FALLBACK_MESSAGE = "configured backend unavailable; falling back to local runtime"


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
    app.state.cache_store = _build_cache_store()
    app.state.application_service = ApplicationService(
        clarification_service=ClarificationEngine(),
        audit_store=app.state.audit_store,
        cache_store=app.state.cache_store,
    )
    app.state.metrics = MetricsRegistry()
    app.state.infrastructure = _infrastructure_status(app)
    yield


def _build_session_manager():
    if os.getenv("SESSION_STORE_TYPE", "memory").lower() == "redis":
        try:
            from src.chatbot.redis_session_manager import RedisSessionManager

            return RedisSessionManager(expiry_minutes=int(os.getenv("SESSION_EXPIRY_MINUTES", "30")))
        except Exception as exc:
            print(_safe_fallback_message("Redis session store"))
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
            print(_safe_fallback_message("Redis rate limiter"))
            return InMemoryRateLimiter(limit=limit, window_seconds=window_seconds)
    return InMemoryRateLimiter(limit=limit, window_seconds=window_seconds)


def _build_audit_store():
    if os.getenv("AUDIT_DATABASE_URL") or os.getenv("DATABASE_URL"):
        try:
            from src.storage.audit_store import PostgresAuditStore

            return PostgresAuditStore()
        except Exception as exc:
            print(_safe_fallback_message("PostgreSQL audit store"))
            pass
    from src.storage.audit_store import NullAuditStore

    return NullAuditStore()


def _build_cache_store():
    if os.getenv("CACHE_STORE_TYPE", "memory").lower() == "redis":
        try:
            from src.storage.cache import RedisCacheStore

            return RedisCacheStore()
        except Exception as exc:
            print(_safe_fallback_message("Redis cache"))
    from src.storage.cache import InMemoryCacheStore

    return InMemoryCacheStore()


def _infrastructure_status(app: FastAPI):
    return {
        "vector_store": os.getenv("VECTOR_DB_TYPE", "chroma").lower(),
        "session_store": type(app.state.session_manager).__name__,
        "rate_limit_store": type(app.state.rate_limiter).__name__,
        "audit_store": type(app.state.audit_store).__name__,
        "cache_store": type(app.state.cache_store).__name__,
    }


def _safe_fallback_message(component: str) -> str:
    return f"{component}: {INFRA_FALLBACK_MESSAGE}"


def _readiness_status(app: FastAPI) -> Dict[str, Any]:
    level = os.getenv("APP_ENV", "dev").strip().lower() or "dev"
    infrastructure = app.state.infrastructure
    checks = {
        "retrieval_configured": infrastructure.get("vector_store") in {"chroma", "qdrant"},
        "provider_configured": bool(os.getenv("OPENROUTER_API_KEY")),
        "auth_configured": bool(os.getenv("AUTH_TOKEN")),
        "durable_session_store": infrastructure.get("session_store") != "SessionManager",
        "durable_rate_limit_store": infrastructure.get("rate_limit_store") != "InMemoryRateLimiter",
        "durable_audit_store": infrastructure.get("audit_store") != "NullAuditStore",
        "durable_cache_store": infrastructure.get("cache_store") != "InMemoryCacheStore",
    }
    production_requirements = [
        "retrieval_configured",
        "provider_configured",
        "auth_configured",
        "durable_audit_store",
    ]
    degraded = level == "production" and not all(checks[name] for name in production_requirements)
    return {
        "status": "degraded" if degraded else "ready",
        "readiness_level": level,
        "checks": checks,
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
        "cache_store": "not_initialized",
    }

    _cors_origins = parse_cors_origins(os.getenv("CORS_ORIGINS", '["*"]'))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        # credentials=True + wildcard origin is rejected by all browsers (CORS spec);
        # only enable when a specific origin list is configured.
        allow_credentials="*" not in _cors_origins,
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
        # Allow HuggingFace to embed via iframe; omit X-Frame-Options so the
        # CSP frame-ancestors directive below takes precedence (RFC 7034 §2).
        response.headers["Content-Security-Policy"] = (
            "frame-ancestors 'self' https://huggingface.co https://*.hf.space"
        )
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

    @app.get("/", response_class=HTMLResponse)
    async def root():
        return CHAT_HTML

    @app.get("/chat", response_class=HTMLResponse)
    async def chat_page():
        return CHAT_HTML

    @app.get("/api", tags=["info"])
    async def api_info():
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
                "disclaimer": "/api/v1/compliance/disclaimer",
                "docs": "/docs",
            },
        }

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return Response(status_code=204)

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "timestamp": datetime.now(UTC).isoformat(), "version": "1.0.0"}

    @app.get("/ready")
    async def ready_check():
        readiness = _readiness_status(app)
        return JSONResponse(
            status_code=503 if readiness["status"] == "degraded" else 200,
            content={
                "status": readiness["status"],
                "readiness_level": readiness["readiness_level"],
                "timestamp": datetime.now(UTC).isoformat(),
                "infrastructure": app.state.infrastructure,
                "checks": readiness["checks"],
            },
        )

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
    .controls { display: grid; gap: 8px; }
    label { display: flex; gap: 8px; align-items: flex-start; font-size: 13px; color: #3f4a45; line-height: 1.35; }
    input[type="checkbox"] { margin-top: 2px; accent-color: #214f44; }
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
      <div class="message assistant">Ask a Sharia compliance question — in English or Arabic. / اسأل سؤالاً عن الامتثال الشرعي باللغة الإنجليزية أو العربية.</div>
    </section>
    <form id="chat-form">
      <div class="controls">
        <textarea id="prompt" name="prompt" placeholder="Ask Mushir about an Islamic finance transaction... / اسأل مشير عن معاملة مالية إسلامية...">I want to invest in a company</textarea>
      </div>
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
      // Auto-detect Arabic text and apply RTL direction
      if (kind !== "event") {
        const arabicChars = (text.match(/[\u0600-\u06ff]/g) || []).length;
        const ratio = arabicChars / Math.max(text.length, 1);
        if (ratio > 0.3) {
          node.setAttribute("dir", "rtl");
          node.style.textAlign = "right";
          node.style.fontFamily = "'Noto Sans Arabic', 'Segoe UI', sans-serif";
        }
      }
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
      let thinkingMessage = null;
      try {
        const response = await fetch("/api/v1/query/stream", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({query, context})
        });
        const events = parseSse(await response.text());
        for (const item of events) {
          const data = item.data || {};
          if (item.type === "started") {
            thinkingMessage = addMessage("event", "Thinking...");
          }
          if (item.type === "retrieval") {
            if (thinkingMessage) thinkingMessage.remove();
            thinkingMessage = null;
            addMessage("event", `Confidence ${Number(data.confidence || 0).toFixed(2)}`);
          }
          if (item.type === "token") addMessage("assistant", data.text);
          if (item.type === "citation") {
            const standard = data.standard_number || data.document_id || "AAOIFI source";
            const section = data.section_number ? ` §${data.section_number}` : "";
            const page = data.quote_start > 0 ? `` : "";  // quote_start used as offset proxy
            const sourceFile = data.document_id && data.document_id !== standard
              ? ` — ${data.document_id}` : "";
            const pageNum = (data.section_title && /\\bp\\.?\\s*\\d+/i.test(data.section_title))
              ? ` (${data.section_title})` : "";
            addMessage("event", `📖 ${standard}${section}${pageNum}${sourceFile}`);
          }
          if (item.type === "error") {
            if (thinkingMessage) thinkingMessage.remove();
            thinkingMessage = null;
            addMessage("assistant", data.message);
          }
          if (item.type === "done") {
            if (thinkingMessage) thinkingMessage.remove();
            thinkingMessage = null;
            if (data.clarification_question) addMessage("assistant", data.clarification_question);
            context = data.metadata || context;
            addMessage("event", `Complete - ${data.status}`);
          }
        }
      } catch (error) {
        if (thinkingMessage) thinkingMessage.remove();
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
