# BMAD Party-Mode Review Summary

**Date:** 2026-05-09

**Review voices:** Winston (Architecture), Amelia (Engineering), John (Product), Murat (Test Architecture)

---

## Consensus

The original plans were directionally right but too eager to add infrastructure before the answer contract is trustworthy. The leanest path is:

1. Make the local AAOIFI-grounded answer excellent.
2. Wrap the same application service in a minimal API.
3. Add persistence and evaluation only after API behavior is stable.
4. Harden trust, access, caching, and operations after real deployment needs are clear.

---

## Required Plan Changes Applied

- L1 now centers on the core answer contract, dependency injection, fake-first tests, prompt/Gemini extraction, minimal clarification, and CLI preservation.
- L2 now makes REST `/query` the primary milestone; SSE is optional after REST stability; WebSocket is explicitly deferred.
- L3 now separates persistence/deployment from evaluation/observability and gates Qdrant migration behind real scaling or deployment need.
- L4 now orders trust work before operational acceleration: citation validation, disclaimer/versioning, API keys, caching, CI/CD, alerts.
- Every phase now has explicit test rules, commands, markers, and acceptance gates.

---

## Open-Source Library Guidance

Use libraries only when they reduce complexity in the current phase:

- L1: `pytest`, `pytest-mock`, `pytest-timeout`, `google-generativeai`, optional `pydantic`, optional LangGraph behind a clarification interface.
- L2: `fastapi`, `uvicorn`, `httpx`, native FastAPI `StreamingResponse`; optional `sse-starlette` only if native SSE formatting becomes noisy.
- L3: `redis`, optional `sqlalchemy`, optional `qdrant-client`, one eval framework first (`ragas` or `deepeval`), optional Prometheus instrumentation after API stability.
- L4: Redis cache support, CI provider workflows, alerting tied to the actual deployment target.

Avoid adding `openai` unless the project actually adds OpenAI as a supported provider.

---

## Quality Rule

No default test may call live Gemini, load heavy embedding models, require Docker services, or use the network. Those checks must be explicitly marked as `integration`, `llm`, `eval`, or `slow`.

