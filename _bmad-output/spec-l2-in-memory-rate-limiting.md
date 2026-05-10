---
title: 'L2 In-Memory Rate Limiting'
type: 'feature'
created: '2026-05-10'
status: 'done'
baseline_commit: '7b7fe7700f9a789d8f64e3b5f73847e0c4481adb'
context:
  - '{project-root}/.kiro/specs/sharia-compliance-chatbot/next-level-plans/L2-API-AND-STREAMING-PLAN.md'
---

<frozen-after-approval reason="human-owned intent - do not modify unless human renegotiates">

## Intent

**Problem:** The L2 API exposes REST and SSE query endpoints without an endpoint-level guard against accidental or abusive repeated requests. This leaves the local API surface inconsistent with the L2 plan's in-memory rate limiting requirement.

**Approach:** Add a small in-memory rate limiter as API transport infrastructure, inject it through FastAPI dependencies, and apply it to `/api/v1/query` and `/api/v1/query/stream` while keeping billing tiers, auth, Redis, and database-backed limits out of scope.

## Boundaries & Constraints

**Always:** Keep rate limiting in memory for L2. Tests must be able to force a small limit and fake time. Controlled 429 responses must include `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset`. Existing request IDs and error payload shape must survive.

**Ask First:** Changing public endpoint paths, introducing authentication requirements, adding persistent infrastructure, or changing the L1 answer contract.

**Never:** Add Redis, PostgreSQL, API keys, billing tiers, WebSocket work, or real Gemini/vector-store calls in API tests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Within limit | Client sends query before hourly quota is exhausted | Endpoint runs normally and returns rate limit headers with remaining count | N/A |
| Limit exceeded | Same client exceeds configured request count within the same window | Endpoint returns HTTP 429 with controlled error payload and rate limit headers | Do not call `ApplicationService` |
| Window reset | Client was limited, then fake clock advances past reset time | Next request is accepted with refreshed remaining count | N/A |

</frozen-after-approval>

## Code Map

- `src/api/main.py` -- FastAPI app factory and lifespan state; should initialize one rate limiter per app.
- `src/api/dependencies.py` -- Dependency provider home for application-scoped services.
- `src/api/routes.py` -- REST and SSE query endpoints that need rate-limit enforcement.
- `src/api/schemas.py` -- Controlled error response shape reused for 429 payloads.
- `tests/test_api_query.py` / `tests/test_api_streaming.py` -- Existing API contract tests that must keep passing.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/rate_limit.py` -- Create in-memory fixed-window limiter with injectable clock and serializable limit decision.
- [x] `src/api/dependencies.py` -- Add dependency provider for the app-scoped limiter.
- [x] `src/api/main.py` -- Initialize the limiter in lifespan using environment defaults and keep root/docs behavior unchanged.
- [x] `src/api/routes.py` -- Apply limiter to `/query` and `/query/stream`, add headers on success and 429, and skip service calls when blocked.
- [x] `tests/test_rate_limit.py` -- Cover allowed requests, 429, reset behavior, and stream protection using fakes.

**Acceptance Criteria:**
- Given a configured limit of two requests, when the same client sends a third `/api/v1/query` request in the same window, then the response is HTTP 429 and the service is not called.
- Given a successful `/api/v1/query/stream` request, when it returns SSE events, then the HTTP response includes rate limit headers.
- Given the limiter clock advances beyond the reset timestamp, when the client sends another query, then the request is accepted and remaining quota is recalculated.

## Verification

**Commands:**
- `.\.venv\Scripts\python.exe -m pytest tests/test_rate_limit.py -m api -q` -- expected: new rate-limit tests pass.
- `.\.venv\Scripts\python.exe -m pytest tests/test_api_app.py tests/test_api_query.py tests/test_api_streaming.py tests/test_rate_limit.py -m "unit or api" -q` -- expected: existing L2 API behavior remains green.

## Suggested Review Order

**Limiter Core**

- Fixed-window decision object owns reusable quota headers.
  [`rate_limit.py:24`](../src/api/rate_limit.py#L24)

- Clock-injected bucket logic enables deterministic reset tests.
  [`rate_limit.py:42`](../src/api/rate_limit.py#L42)

**API Enforcement**

- REST query checks quota before touching application service.
  [`routes.py:55`](../src/api/routes.py#L55)

- SSE endpoint carries quota headers on streaming responses.
  [`routes.py:75`](../src/api/routes.py#L75)

- Controlled 429 payload preserves API error shape.
  [`routes.py:127`](../src/api/routes.py#L127)

**App Wiring**

- Lifespan creates one app-scoped limiter from environment defaults.
  [`main.py:36`](../src/api/main.py#L36)

- Dependency override hook keeps tests isolated from real services.
  [`dependencies.py:21`](../src/api/dependencies.py#L21)

**Tests**

- REST over-limit test proves service calls stop after quota exhaustion.
  [`test_rate_limit.py:33`](../tests/test_rate_limit.py#L33)

- Fake-clock reset test covers hourly window refresh behavior.
  [`test_rate_limit.py:61`](../tests/test_rate_limit.py#L61)

- Streaming test verifies headers and 429 protection.
  [`test_rate_limit.py:87`](../tests/test_rate_limit.py#L87)
