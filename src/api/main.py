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
from fastapi.staticfiles import StaticFiles
from pathlib import Path

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
    # Eagerly build the retriever once at startup so all requests share one
    # pre-warmed SentenceTransformer model — eliminates the per-request
    # lazy-init race condition and prevents concurrent OOM on free-tier hosts.
    retriever = _build_retriever()
    app.state.application_service = ApplicationService(
        retriever=retriever,
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


def _build_retriever():
    """Eagerly construct the RAGPipeline at startup to prevent lazy-init races.

    If ChromaDB / SentenceTransformer are unavailable (e.g., in CI or test
    environments), returns None so ApplicationService falls back to its
    existing per-request lazy-init path without crashing startup.
    """
    from src.config.logging_config import setup_logging as _setup_logging

    _logger = _setup_logging()
    try:
        from src.rag.pipeline import RAGPipeline

        return RAGPipeline()
    except Exception as exc:
        _logger.error("RAG retriever failed to initialize: %s", exc, exc_info=True)
        return None


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
            "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'self' https://huggingface.co https://*.hf.space"
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

    STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    index_html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    @app.get("/", response_class=HTMLResponse)
    async def root():
        return index_html

    @app.get("/chat", response_class=HTMLResponse)
    async def chat_page():
        return index_html

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
