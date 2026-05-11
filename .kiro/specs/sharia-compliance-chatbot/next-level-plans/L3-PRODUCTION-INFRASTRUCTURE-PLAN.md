# L3 Persistence, Evaluation, and Observability Plan

> **Historical status:** This plan is retained as the original L3 execution plan. The implemented runtime now includes Redis-backed session/rate-limit/cache adapters, PostgreSQL audit storage, metrics, readiness infrastructure reporting, Qdrant adapter/ingest support, and a retrieval evaluation harness. Remaining unchecked boxes in this document are historical work items unless they are re-promoted in the active L5 readiness plan.

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Do not start L3 until the L2 verification gate passes.

**Goal:** Add restart-safe infrastructure and measurable quality gates without changing the L2 API contract.

**Architecture:** Keep the working L2 application stable. Add adapters behind existing contracts so local development can still use in-memory/Chroma defaults while deployed environments can use Redis, PostgreSQL or SQLite, and eventually Qdrant.

**Tech Stack:** Redis, ChromaDB, optional Qdrant, SQLite or PostgreSQL, Docker Compose, pytest integration markers, Ragas or DeepEval after baseline evals exist, standard JSON logging, optional Prometheus instrumentation.

---

## Scope

In scope:
- Storage adapter interfaces if not completed in L1.
- Redis session and rate-limit backends once multiple workers or restarts matter.
- Lightweight audit persistence.
- Golden evaluation suite.
- Structured logging and minimal metrics.
- Docker Compose for local production-like testing.

Out of scope:
- Kubernetes.
- Enterprise dashboards.
- Multi-tenancy.
- OAuth/SSO.
- Mandatory Qdrant migration before there is a scaling or deployment reason.

---

## Test Rules

- Integration tests are marked `integration` and excluded from default developer tests.
- Eval tests are marked `eval` and run on small PR subsets, larger nightly/release sets.
- Docker-backed tests must have health checks and clear skip behavior when services are unavailable.

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not integration and not eval and not slow"
.\.venv\Scripts\python.exe -m pytest -m integration
.\.venv\Scripts\python.exe -m pytest -m eval
```

---

## Track A: Persistence and Deployment

### Task 1: Storage Adapter Finalization

**Files:**
- Create: `src/storage/vector_store.py`
- Create: `src/storage/session_store.py`
- Create: `src/storage/audit_store.py`
- Modify: `src/rag/pipeline.py`
- Modify: `src/chatbot/session_manager.py`
- Test: `tests/test_storage_interfaces.py`

- [ ] Ensure vector, session, and audit interfaces are small and already used by application code.
- [ ] Keep in-memory session store and Chroma vector store as default local implementations.
- [ ] Add tests proving stores can be swapped without changing `ApplicationService`.
- [ ] Run: `.\.venv\Scripts\python.exe -m pytest tests/test_storage_interfaces.py -m service -q`

Acceptance:
- Business logic imports interfaces, not concrete infra clients.

### Task 2: Redis Sessions and Rate Limits

**Files:**
- Create: `src/storage/redis_session_store.py`
- Modify: `src/api/rate_limit.py`
- Test: `tests/integration/test_redis_sessions.py`

- [ ] Add `redis` dependency.
- [ ] Store session state as JSON with 30-minute TTL.
- [ ] Store rate-limit counters with hourly TTL.
- [ ] Keep memory store for local tests.
- [ ] Return controlled service-unavailable errors if Redis is required but unavailable.
- [ ] Run with Redis available: `.\.venv\Scripts\python.exe -m pytest tests/integration/test_redis_sessions.py -m integration -q`

Acceptance:
- Two API worker instances can share the same session store when pointed at Redis.

### Task 3: Lightweight Audit Store

**Files:**
- Create: `src/storage/sqlite_audit_store.py`
- Optional: `src/storage/postgres_audit_store.py`
- Create: `src/storage/audit_schema.py`
- Test: `tests/test_audit_store.py`
- Optional integration: `tests/integration/test_postgres_audit_store.py`

- [ ] Start with SQLite or JSONL if local audit review is enough.
- [ ] Add PostgreSQL only when deployment, reporting, or retention requirements justify it.
- [ ] Persist query, normalized query, retrieved chunk IDs, citations, final status, model, prompt version, corpus version, latency, request ID, and errors.
- [ ] Do not store secrets or API keys.
- [ ] Audit failures should not block the query path unless compliance policy explicitly requires blocking.
- [ ] Run: `.\.venv\Scripts\python.exe -m pytest tests/test_audit_store.py -m service -q`

Acceptance:
- Completed rulings have reproducible provenance.

### Task 4: Docker Compose Health Checks

**Files:**
- Modify: `docker-compose.yml`
- Create: `docs/ops/L3-local-stack.md`
- Test: `tests/integration/test_docker_stack.py`

- [ ] Add services only as needed: API, Redis, optional Postgres, optional Qdrant.
- [ ] Add health checks for each containerized service.
- [ ] Document startup and teardown commands.
- [ ] Run integration smoke tests only when Docker services are running.

Acceptance:
- A developer can start the L3 local stack with one documented command.

---

## Track B: Evaluation and Observability

### Task 5: Golden Evaluation Baseline

**Files:**
- Create: `tests/eval/gold_cases.yaml`
- Create: `tests/eval/test_rag_quality.py`
- Create: `scripts/run_eval.py`

- [ ] Start with 20 representative AAOIFI questions before using Ragas or DeepEval.
- [ ] Track expected standards, expected refusal/clarification behavior, citation presence, and false-compliance risk.
- [ ] Add retrieval metrics: precision@5, recall@5, MRR, and citation coverage.
- [ ] Add known-bad cases that must fail if the system overclaims compliance.
- [ ] Run: `.\.venv\Scripts\python.exe -m pytest tests/eval -m eval -q`

Acceptance:
- Eval suite can run locally and in CI with deterministic thresholds.

### Task 6: Ragas or DeepEval Integration

**Files:**
- Modify: `scripts/run_eval.py`
- Optional: `tests/eval/test_ragas_quality.py`
- Optional: `tests/eval/test_deepeval_quality.py`

- [ ] Add only one framework first: choose Ragas for RAG faithfulness or DeepEval for pytest-style gates.
- [ ] Keep eval offline; never call eval frameworks in the request path.
- [ ] Suggested starting thresholds:
  - faithfulness >= 0.80
  - answer relevance >= 0.80
  - citation coverage >= 0.90
  - hallucination regression no worse than baseline

Acceptance:
- Eval failures produce a readable report with failing query, retrieved sources, answer, and reason.

### Task 7: Structured Logs and Minimal Metrics

**Files:**
- Modify: `src/config/logging_config.py`
- Create: `src/observability/metrics.py`
- Modify: `src/api/main.py`
- Test: `tests/test_observability.py`

- [ ] Add JSON logs with request ID, latency, status, model, retrieval count, clarification flag, and error type.
- [ ] Add metrics for request count, latency, error count, active sessions, retrieval count, clarification rate, and LLM failure rate.
- [ ] Use Prometheus instrumentation only after the API is stable.
- [ ] Test metric counters without depending on a real metrics backend.

Acceptance:
- Logs are useful for debugging and avoid sensitive raw content unless explicitly configured.

---

## Qdrant Decision Gate

Do not migrate to Qdrant by default in L3 unless one of these is true:

- Chroma deployment or concurrency is blocking.
- Vector count or latency exceeds agreed limits.
- Multi-instance deployment requires an external vector service.

If Qdrant is justified:

- [ ] Add `qdrant-client`.
- [ ] Implement `QdrantVectorStore` behind the same vector interface.
- [ ] Compare Chroma and Qdrant on the gold query set.
- [ ] Require at least 95 percent overlap@5 before production cutover.

---

## L3 Verification Gate

- [ ] `.\.venv\Scripts\python.exe -m pytest -m "not integration and not eval and not slow" --timeout=60`
- [ ] `.\.venv\Scripts\python.exe -m pytest -m integration` with Docker services running.
- [ ] `.\.venv\Scripts\python.exe -m pytest -m eval` on the small eval set.
- [ ] Local stack health check passes.

L3 is done when:
- L2 API contract is unchanged.
- Restart-safe storage is available where needed.
- Eval baseline exists and catches known bad cases.
- Logs/metrics expose real quality and service risks.
- Qdrant is either justified with parity results or explicitly deferred.
