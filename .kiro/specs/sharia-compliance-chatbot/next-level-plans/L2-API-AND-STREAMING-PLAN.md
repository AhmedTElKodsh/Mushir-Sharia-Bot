# L2 Minimal API and Optional SSE Plan

> **Historical status:** This plan is retained as the original L2 execution plan. The implemented runtime now includes FastAPI app-factory/lifespan setup, `/api/v1/query`, `/api/v1/query/stream`, `/chat`, request IDs, validation envelopes, rate limiting, and API/SSE tests. Remaining unchecked boxes in this document are historical work items unless they are re-promoted in the active L5 readiness plan.

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Do not start L2 until the L1 verification gate passes.

**Goal:** Expose the L1 application service through a minimal FastAPI API. Add SSE only after the normal REST query path is stable.

**Architecture:** FastAPI is a transport layer, not business logic. Use `API -> ApplicationService -> RAGPipeline`. Initialize services once through an app factory/lifespan and inject them with `Depends`. Keep sessions and rate limits in memory for L2.

**Tech Stack:** FastAPI, Pydantic, uvicorn, httpx, pytest. Use native `StreamingResponse` for SSE first; use `sse-starlette` only if native formatting becomes cumbersome.

**Context7 note:** Current FastAPI docs support `StreamingResponse` with async generators, `Depends()` for dependency injection, `httpx`/TestClient for tests, and `lifespan` with `asynccontextmanager` for startup/cleanup.

---

## Scope

In scope:
- `GET /health`
- `GET /ready`
- `POST /query`
- Optional `POST /query/stream` after `/query` is stable
- Typed request/response schemas
- Request IDs and controlled error responses
- In-memory sessions and rate limits only if needed by the endpoint contract

Out of scope:
- WebSocket
- JWT, API keys, user portal, billing tiers
- Redis, PostgreSQL, Qdrant
- Multiple API versions
- Admin dashboards

---

## Test Rules

- API tests use FastAPI dependency overrides and fake application services.
- No API test calls real Gemini or loads real embedding models by default.
- Use `python -m pytest`, never bare `pytest`.
- Mark API tests with `api`.

Default L2 command:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "unit or service or api" --timeout=60
```

---

## Task 1: FastAPI App Factory and Lifespan

**Files:**
- Modify: `src/api/main.py`
- Create: `src/api/dependencies.py`
- Test: `tests/test_api_app.py`

- [ ] Add L2 dependencies: `fastapi`, `uvicorn`, `httpx`. Add `sse-starlette` only if chosen.
- [ ] Implement `create_app()` and keep module-level `app = create_app()`.
- [ ] Use FastAPI lifespan to initialize application-scoped services once.
- [ ] Provide dependency functions for `ApplicationService`, session store, and rate limiter.
- [ ] Replace unsafe `eval(os.getenv("CORS_ORIGINS"...))` with JSON parsing and safe defaults.
- [ ] Register global error middleware.
- [ ] Run: `.\.venv\Scripts\python.exe -m pytest tests/test_api_app.py -m api -q`

Acceptance:
- API startup does not create a new session manager per request.
- Test overrides can replace every external service.

---

## Task 2: Schemas First

**Files:**
- Create: `src/api/schemas.py`
- Test: `tests/test_api_schemas.py`

- [ ] Define `QueryRequest`.
- [ ] Define `QueryResponse` using the L1 answer contract.
- [ ] Define `Citation`.
- [ ] Define `ClarificationResponse` if kept separate from `QueryResponse`.
- [ ] Define `ErrorResponse`.
- [ ] Define `StreamEvent`.
- [ ] Add schema tests for required fields, empty query rejection, and serialization.
- [ ] Run: `.\.venv\Scripts\python.exe -m pytest tests/test_api_schemas.py -m unit -q`

Acceptance:
- CLI and API expose the same answer fields.
- Response schemas are stable before endpoints are implemented.

---

## Task 3: REST Query Endpoint

**Files:**
- Modify: `src/api/routes.py`
- Test: `tests/test_api_query.py`

- [ ] Implement `POST /query`.
- [ ] Call only `ApplicationService`; do not import ChromaDB, Gemini, or prompt internals in route code.
- [ ] Return full answer, insufficient-data response, or clarification-needed response.
- [ ] Add request ID to response headers and error payloads.
- [ ] Handle malformed input, empty corpus, retrieval failure, LLM failure, timeout, and service error.
- [ ] Run: `.\.venv\Scripts\python.exe -m pytest tests/test_api_query.py -m api -q`

Acceptance:
- `/query` returns the same contract as CLI.
- No citation appears unless grounded in retrieved context.
- Session continuity is tested if sessions remain part of the API.

---

## Task 4: SSE Streaming Endpoint

**Files:**
- Create: `src/api/streaming.py`
- Modify: `src/api/routes.py`
- Test: `tests/test_api_streaming.py`

- [ ] Start this task only after `/query` tests pass.
- [ ] Implement `POST /query/stream` with `StreamingResponse` and media type `text/event-stream`.
- [ ] Emit explicit events: `started`, `retrieval`, `token`, `citation`, `done`, `error`.
- [ ] Ensure the endpoint yields before final completion; do not buffer the full answer before first event.
- [ ] Handle upstream errors as `error` events.
- [ ] Run: `.\.venv\Scripts\python.exe -m pytest tests/test_api_streaming.py -m api -q`

Acceptance:
- Stream event order is tested.
- Stream closes cleanly.
- WebSocket remains out of scope.

---

## Task 5: In-Memory Rate Limiting

**Files:**
- Create: `src/api/rate_limit.py`
- Modify: `src/api/main.py`
- Test: `tests/test_rate_limit.py`

- [ ] Add only if the API is intended for more than local trusted use.
- [ ] Implement per-IP or per-session hourly counters.
- [ ] Use a fake clock in tests.
- [ ] Return HTTP 429 with `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset`.
- [ ] Keep billing tiers out of L2.
- [ ] Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rate_limit.py -m api -q`

Acceptance:
- Tests can force a small limit and receive 429 after exceeding it.

---

## Task 6: Park WebSocket Prototype

**Files:**
- Modify: `src/api/websocket.py`
- Modify: `src/api/main.py`

- [ ] Remove WebSocket router inclusion from the L2 app.
- [ ] Add a module docstring marking WebSocket as deferred until SSE fails to satisfy a real client need.
- [ ] Do not add WebSocket dependencies or tests in L2.

Acceptance:
- API docs expose REST and optional SSE only.

---

## L2 Verification Gate

- [ ] `.\.venv\Scripts\python.exe -m compileall -q src tests`
- [ ] `.\.venv\Scripts\python.exe -m pytest -m "unit or service or api" --timeout=60`
- [ ] `.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000`
- [ ] Manually verify `/health`, `/ready`, `/query`, and `/query/stream` if SSE was implemented.

L2 is done when:
- FastAPI is only a transport wrapper around L1.
- `/query` is stable and tested.
- SSE is implemented only if needed and tested.
- WebSocket, Redis, Qdrant, Postgres, and auth are deferred.
