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
from src.governance.scholar_review import ScholarReviewQueueStore
from src.observability.metrics import MetricsRegistry
from scripts.report_sharia_corpus_coverage import (
    DEFAULT_ACQUISITION_MANIFEST,
    load_acquisition_manifest,
    load_catalog,
    sharia_coverage_report,
)


INFRA_FALLBACK_MESSAGE = "configured backend unavailable; falling back to local runtime"
DEFAULT_SOURCE_CATALOG_FILE = "data/source_registry/aaoifi-source-catalog.yaml"
APP_VERSION = "1.5.0"
APP_VERSION_LABEL = "V1.5"


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
    app.state.scholar_review_queue_store = _build_scholar_review_queue_store()
    # Eagerly build the retriever once at startup so all requests share one
    # pre-warmed SentenceTransformer model — eliminates the per-request
    # lazy-init race condition and prevents concurrent OOM on free-tier hosts.
    retriever = _build_retriever()
    app.state.retriever_ready = retriever is not None
    app.state.application_service = ApplicationService(
        retriever=retriever,
        llm_client=_build_llm_client(),
        clarification_service=ClarificationEngine(),
        session_store=app.state.session_manager,
        audit_store=app.state.audit_store,
        cache_store=app.state.cache_store,
        scholar_review_queue_store=app.state.scholar_review_queue_store,
        scholar_sampling_rate=float(os.getenv("SCHOLAR_REVIEW_SAMPLE_RATE", "0.05")),
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


def _mock_llm_enabled() -> bool:
    return os.getenv("MUSHIR_MOCK_LLM", "").strip().lower() in {"1", "true", "yes", "on"}


def _build_llm_client():
    if not _mock_llm_enabled():
        return None

    class StaticEvidenceLLM:
        model_name = "static-e2e-mock"

        def generate(self, prompt: str, system_prompt: str | None = None) -> str:
            return (
                "SUPPORTED_BY_RETRIEVED_EVIDENCE: This response is grounded in the "
                "retrieved AAOIFI evidence for this local smoke test. [SS-08 §1]"
            )

    return StaticEvidenceLLM()


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
        _logger.error("RAG retriever failed to initialize: %s", type(exc).__name__)
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


def _build_scholar_review_queue_store():
    return ScholarReviewQueueStore(os.getenv("SCHOLAR_REVIEW_QUEUE_PATH", "data/scholar_review_queue.jsonl"))


def _infrastructure_status(app: FastAPI):
    status = {
        "vector_store": os.getenv("VECTOR_DB_TYPE", "chroma").lower(),
        "retriever_ready": bool(getattr(app.state, "retriever_ready", False)),
        "session_store": type(app.state.session_manager).__name__,
        "rate_limit_store": type(app.state.rate_limiter).__name__,
        "audit_store": type(app.state.audit_store).__name__,
        "cache_store": type(app.state.cache_store).__name__,
    }
    retriever = getattr(app.state, "application_service", None)
    retriever = getattr(retriever, "retriever", None)
    vector_store = getattr(retriever, "vector_store", None)
    if status["vector_store"] == "qdrant":
        qdrant_status = _qdrant_readiness_status(vector_store)
        status["qdrant"] = qdrant_status
    return status


def _qdrant_readiness_status(vector_store: Any) -> Dict[str, Any]:
    if vector_store is None or not hasattr(vector_store, "readiness_status"):
        return {
            "collection_populated": False,
            "governed_metadata_ready": False,
            "bilingual_coverage_ready": False,
            "retrieval_smoke_ready": False,
            "error": "Qdrant vector store readiness is unavailable.",
        }
    try:
        return vector_store.readiness_status()
    except Exception:
        return {
            "collection_populated": False,
            "governed_metadata_ready": False,
            "bilingual_coverage_ready": False,
            "retrieval_smoke_ready": False,
            "error": "Qdrant vector store readiness check failed.",
        }


def _safe_fallback_message(component: str) -> str:
    return f"{component}: {INFRA_FALLBACK_MESSAGE}"


def _readiness_status(app: FastAPI) -> Dict[str, Any]:
    level = os.getenv("APP_ENV", "dev").strip().lower() or "dev"
    release_tier = (
        os.getenv("RELEASE_TIER", "")
        .strip()
        .lower()
        .replace("_", "-")
        .replace(" ", "-")
    )
    tier_order = {
        "local-dev": 0,
        "dev": 0,
        "development": 0,
        "public-demo": 1,
        "controlled-beta": 2,
        "production-pilot": 3,
        "production": 3,
        "hard-sharia-ready": 4,
    }
    effective_tier = release_tier or ("production-pilot" if level == "production" else "local-dev")
    if effective_tier not in tier_order:
        effective_tier = "production-pilot" if level == "production" else "public-demo"
    if level == "production" and tier_order[effective_tier] < tier_order["production-pilot"]:
        effective_tier = "production-pilot"
    infrastructure = app.state.infrastructure
    sharia_corpus = _sharia_corpus_coverage_status()
    auth_token = os.getenv("AUTH_TOKEN", "").strip()
    checks = {
        "retrieval_configured": infrastructure.get("vector_store") in {"chroma", "qdrant"},
        "retriever_ready": bool(infrastructure.get("retriever_ready")),
        "sharia_corpus_complete": sharia_corpus.get("status") == "complete",
        "hard_sharia_ready": sharia_corpus.get("hard_sharia_ready") is True,
        "provider_configured": bool(os.getenv("OPENROUTER_API_KEY")) or _mock_llm_enabled(),
        "auth_configured": bool(auth_token),
        "auth_enforced": tier_order[effective_tier] < tier_order["controlled-beta"] or bool(auth_token),
        "durable_session_store": infrastructure.get("session_store") != "SessionManager",
        "durable_rate_limit_store": infrastructure.get("rate_limit_store") != "InMemoryRateLimiter",
        "durable_audit_store": infrastructure.get("audit_store") != "NullAuditStore",
        "durable_cache_store": infrastructure.get("cache_store") != "InMemoryCacheStore",
    }
    if infrastructure.get("vector_store") == "qdrant":
        qdrant = infrastructure.get("qdrant") or {}
        checks.update(
            {
                "qdrant_collection_populated": qdrant.get("collection_populated") is True,
                "qdrant_governed_metadata_ready": qdrant.get("governed_metadata_ready") is True,
                "qdrant_bilingual_coverage_ready": qdrant.get("bilingual_coverage_ready") is True,
                "qdrant_retrieval_smoke_ready": qdrant.get("retrieval_smoke_ready") is True,
            }
        )
    runtime_requirements = [
        "retrieval_configured",
        "retriever_ready",
        "provider_configured",
    ]
    if infrastructure.get("vector_store") == "qdrant":
        runtime_requirements.extend(
            [
                "qdrant_collection_populated",
                "qdrant_governed_metadata_ready",
                "qdrant_bilingual_coverage_ready",
                "qdrant_retrieval_smoke_ready",
            ]
        )
    tier_requirements = {
        "local-dev": ["retrieval_configured"],
        "dev": ["retrieval_configured"],
        "development": ["retrieval_configured"],
        "public-demo": runtime_requirements,
        "controlled-beta": runtime_requirements + ["auth_enforced", "durable_audit_store"],
        "production-pilot": runtime_requirements
        + [
            "auth_enforced",
            "durable_session_store",
            "durable_rate_limit_store",
            "durable_audit_store",
            "durable_cache_store",
        ],
        "production": runtime_requirements
        + [
            "auth_enforced",
            "durable_session_store",
            "durable_rate_limit_store",
            "durable_audit_store",
            "durable_cache_store",
        ],
        "hard-sharia-ready": runtime_requirements
        + [
            "auth_enforced",
            "durable_session_store",
            "durable_rate_limit_store",
            "durable_audit_store",
            "durable_cache_store",
            "hard_sharia_ready",
        ],
    }
    required_checks = tier_requirements[effective_tier]
    degraded = not all(checks[name] for name in required_checks)
    return {
        "status": "degraded" if degraded else "ready",
        "readiness_level": level,
        "release_tier": release_tier or None,
        "effective_release_tier": effective_tier,
        "required_checks": required_checks,
        "checks": checks,
        "evidence_coverage": {"sharia_corpus": sharia_corpus},
    }


def _sharia_corpus_coverage_status() -> Dict[str, Any]:
    catalog_path = Path(os.getenv("SOURCE_CATALOG_FILE", DEFAULT_SOURCE_CATALOG_FILE))
    acquisition_manifest_path = Path(os.getenv("SHARIA_ACQUISITION_MANIFEST_FILE", DEFAULT_ACQUISITION_MANIFEST))
    try:
        report = sharia_coverage_report(
            load_catalog(catalog_path),
            acquisition_manifest=load_acquisition_manifest(acquisition_manifest_path),
        )
        return {
            "status": report["status"],
            "hard_sharia_ready": report["hard_sharia_ready"],
            "release_gate": report["release_gate"],
            "release_gate_fail_count": report["release_gate_fail_count"],
            "target_sharia_standard_count": report["target_sharia_standard_count"],
            "covered_sharia_standard_count": report["covered_sharia_standard_count"],
            "missing_sharia_standard_count": report["missing_sharia_standard_count"],
            "blocked_source_count": report["blocked_source_count"],
            "blocked_source_standards": report["blocked_source_standards"],
            "blocked_source_details": report["blocked_source_details"],
            "coverage_ratio": report["coverage_ratio"],
            "covered_sharia_standards": report["covered_sharia_standards"],
            "missing_sharia_standards": report["missing_sharia_standards"],
            "bilingual_sharia_standard_count": report["bilingual_sharia_standard_count"],
            "language_counts": report["language_counts"],
            "no_go_reasons": report["no_go_reasons"],
            "catalog_path": catalog_path.as_posix(),
            "acquisition_manifest_path": acquisition_manifest_path.as_posix(),
        }
    except Exception:
        return {
            "status": "unknown",
            "hard_sharia_ready": False,
            "release_gate": "fail",
            "release_gate_fail_count": 60,
            "target_sharia_standard_count": 60,
            "covered_sharia_standard_count": 0,
            "missing_sharia_standard_count": 60,
            "blocked_source_count": 0,
            "blocked_source_standards": [],
            "blocked_source_details": [],
            "coverage_ratio": 0.0,
            "covered_sharia_standards": [],
            "missing_sharia_standards": [],
            "bilingual_sharia_standard_count": 0,
            "language_counts": {},
            "no_go_reasons": ["Sharia corpus coverage could not be inspected."],
            "catalog_path": catalog_path.as_posix(),
            "acquisition_manifest_path": acquisition_manifest_path.as_posix(),
        }


def create_app() -> FastAPI:
    app = FastAPI(
        title="Sharia Compliance Chatbot API",
        description="RAG-based Islamic finance compliance analysis using AAOIFI standards",
        version=APP_VERSION,
        lifespan=lifespan,
    )
    app.state.metrics = MetricsRegistry()
    app.state.infrastructure = {
        "vector_store": os.getenv("VECTOR_DB_TYPE", "chroma").lower(),
        "retriever_ready": False,
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
            auth_error = _production_auth_error(request, request_id)
            if auth_error is not None:
                response = auth_error
            else:
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
                _validation_error_message(exc),
                request_id,
            ),
        )

    @app.get("/api", tags=["info"])
    async def api_info():
        return {
            "status": "ok",
            "name": "Sharia Compliance Chatbot API",
            "version": APP_VERSION,
            "version_label": APP_VERSION_LABEL,
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
        return {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "version": APP_VERSION,
            "version_label": APP_VERSION_LABEL,
        }

    @app.get("/ready")
    async def ready_check():
        readiness = _readiness_status(app)
        return JSONResponse(
            status_code=503 if readiness["status"] == "degraded" else 200,
            content={
                "status": readiness["status"],
                "readiness_level": readiness["readiness_level"],
                "release_tier": readiness["release_tier"],
                "effective_release_tier": readiness["effective_release_tier"],
                "required_checks": readiness["required_checks"],
                "timestamp": datetime.now(UTC).isoformat(),
                "version": APP_VERSION,
                "version_label": APP_VERSION_LABEL,
                "infrastructure": app.state.infrastructure,
                "checks": readiness["checks"],
                "evidence_coverage": readiness["evidence_coverage"],
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


def _production_auth_error(request: Request, request_id: str) -> JSONResponse | None:
    if os.getenv("APP_ENV", "dev").strip().lower() != "production":
        return None
    auth_token = os.getenv("AUTH_TOKEN", "").strip()
    if not request.url.path.startswith("/api/v1"):
        return None
    if request.url.path == "/api/v1/compliance/disclaimer":
        return None
    if not auth_token:
        return JSONResponse(
            status_code=503,
            content=ErrorResponse.create(
                "AUTH_MISCONFIGURED",
                "Production API authentication is not configured",
                request_id,
            ),
        )
    if request.headers.get("authorization", "") == f"Bearer {auth_token}":
        return None
    return JSONResponse(
        status_code=401,
        content=ErrorResponse.create("UNAUTHORIZED", "Authentication required", request_id),
    )


def _validation_error_message(exc: RequestValidationError) -> str:
    """Return a concise user-facing validation error without exposing internals."""
    for error in exc.errors():
        loc = tuple(error.get("loc", ()))
        message = str(error.get("msg", "Invalid value")).strip()
        field = str(loc[-1]) if loc else "request"
        if field == "query":
            if "cannot be empty" in message.lower() or "at least 1 character" in message.lower():
                return "Invalid request: query cannot be empty. Please enter a Sharia compliance question."
            if error.get("type") == "missing":
                return "Invalid request: query is required. Please include a non-empty query field."
        if field == "conversation_history":
            return "Invalid request: conversation_history is too long. Send at most 20 messages."
        if field != "body":
            return f"Invalid request: {field} {message}."
    return "Invalid request: check the request body and try again."


app = create_app()
