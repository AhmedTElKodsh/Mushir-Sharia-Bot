# P1-S5: Test Infrastructure Prep — MockLLM + StorageAdapter

**Phase:** 1 (Pre-Phase 2)
**Priority:** 0 (blocking Phase 2)
**Effort:** Medium
**Dependencies:** P1-S4

## Description

Build two foundational pieces that Phase 2's stateful features depend on: a `MockLLM` adapter for deterministic backend testing and a `StorageAdapter` interface for testable frontend persistence. Per Murat's architecture review.

## Acceptance Criteria

### MockLLM Adapter

- [ ] `MockLLM` class in `src/chatbot/llm_client.py` (or adjacent `test_helpers.py`)
- [ ] Accepts `(responses: list[str], delays: list[float])` — injectable via `app.dependency_overrides`
- [ ] Implements same interface as `OpenRouterClient.generate()`
- [ ] Supports configurable failure modes: `HTTPError(429)`, `HTTPError(502)`, `TimeoutError`
- [ ] Existing tests continue to pass (backward-compatible mock replacement)
- [ ] Pydantic SSE schema: discriminated union per event type (`StartedEvent`, `TokenEvent`, `CitationEvent`, `DoneEvent`, `ErrorEvent`)
- [ ] Schema test: "given this Pydantic model, does `_sse()` produce the right `data:` lines?"

### StorageAdapter Interface

- [ ] `StorageAdapter` class in `src/static/js/storage.js`
- [ ] Methods: `get(key)`, `set(key, value)`, `remove(key)`, `clear()`, `schemaVersion`
- [ ] `schemaVersion: int` field — enables migration from N to N+1
- [ ] `MockStorage` class for unit tests (implements same interface, uses `Map`)
- [ ] Current disclaimer banner (P1-S3) refactored to use `StorageAdapter` instead of raw `sessionStorage`
- [ ] No functional regression — disclaimer behavior unchanged

## Files Touched

- `src/chatbot/llm_client.py` — add `MockLLM` class
- `src/chatbot/llm_client.py` or new `src/chatbot/test_helpers.py` — Pydantic SSE schema
- `src/static/js/storage.js` — refactor to `StorageAdapter` class with `schemaVersion`
- `src/static/js/app.js` — update disclaimer handler to use `StorageAdapter`
- `tests/test_sse_schema.py` — new test file for SSE Pydantic schema
- `tests/test_storage_adapter.py` — new test file for StorageAdapter

## Verification

1. `python -m pytest tests/ -v --tb=short` — all 202+ existing + new tests pass
2. `MockLLM` injectable via `app.dependency_overrides` — test with a 429 scenario
3. `StorageAdapter` works in browser — disclaimer banner persists/clears as before
4. SSE schema test asserts correct `data:` lines per event type
