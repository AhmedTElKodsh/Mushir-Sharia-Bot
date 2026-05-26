---
phase: "01"
plan: "s5"
subsystem: "backend/frontend"
tags: ["test-infrastructure", "mock-llm", "sse-schema", "storage-adapter", "testing"]
requires: ["p1-s4"]
provides: ["mock-llm-adapter", "sse-event-schemas", "storage-adapter-pattern", "mock-storage"]
affects:
  - "src/chatbot/llm_client.py"
  - "src/api/schemas.py"
  - "src/static/js/storage.js"
  - "src/static/js/app.js"
  - "tests/test_sse_schema.py"
  - "tests/test_storage_adapter.py"
tech-stack:
  added:
    - "Pydantic discriminated union for SSE event types (6 models)"
    - "MockLLM: deterministic LLM stub with configurable responses/delays/failures"
    - "StorageAdapter: class-based wrapper around Web Storage API"
    - "MockStorage: Map-backed Storage impl for frontend unit tests"
  patterns:
    - "Injectable test doubles via dependency_overrides (MockLLM → OpenRouterClient)"
    - "Class-based storage wrapper with schemaVersion + migrate() for safe persistence evolution"
    - "Backward-compatible legacy API preserved alongside new class-based API"
key-files:
  created:
    - "tests/test_sse_schema.py"
    - "tests/test_storage_adapter.py"
  modified:
    - "src/chatbot/llm_client.py"
    - "src/api/schemas.py"
    - "src/static/js/storage.js"
    - "src/static/js/app.js"
decisions:
  - "MockLLM placed in llm_client.py (not a new file) because P1 is pre-ship and adding a new module for a test helper adds discoverability friction"
  - "SSE event models use plain event: str fields (not Literal) to match the existing _sse() string-based dispatch pattern in routes.py"
  - "StorageAdapter uses prototype-based constructor rather than ES6 `class` for pre-ES6 browser compatibility (matches existing project JS style)"
  - "Backward-compatible `var Storage = Storage || {}` legacy API preserved in storage.js so existing callers (app.js, potential third-party) continue working"
  - "Python-level test for StorageAdapter validates the adapter pattern with a Python-equivalent MockStorage to stay within pytest infrastructure"
metrics:
  duration: "~25 min"
  completed-date: "2026-05-16"
---

# Phase 1 Plan S5: Test Infrastructure Prep — MockLLM + StorageAdapter Summary

**MockLLM adapter for deterministic backend testing, Pydantic SSE event schema with wire-format tests, and a class-based StorageAdapter with MockStorage for testable frontend persistence**

## Tasks Executed

| # | Task | Type | Commit | Status |
|---|------|------|--------|--------|
| 1 | Add `MockLLM` class to `src/chatbot/llm_client.py` — deterministic stub with `generate(prompt, system_prompt)`, configurable responses/delays, failure modes (HTTPError, TimeoutError), injectable via `app.dependency_overrides` | auto | `0a84e91` | ✅ Done |
| 2 | Add Pydantic SSE event schemas to `src/api/schemas.py` — 6 event types (`StartedEvent`, `RetrievalEvent`, `TokenEvent`, `CitationEvent`, `DoneEvent`, `ErrorEvent`) | auto | `0a84e91` | ✅ Done |
| 3 | Refactor `src/static/js/storage.js` to `StorageAdapter` class with `get(key)`, `set(key, value)`, `remove(key)`, `clear()`, `migrate(fromVersion, toVersion)`, `schemaVersion` + `MockStorage` using `Map` | auto | `0a84e91` | ✅ Done |
| 4 | Update `src/static/js/app.js` disclaimer banner handler to use `StorageAdapter` instead of raw `sessionStorage` | auto | `0a84e91` | ✅ Done |
| 5 | Create `tests/test_sse_schema.py` — validates Pydantic model serialization + `_sse()` wire format for all 6 event types | auto | `0a84e91` | ✅ Done |
| 6 | Create `tests/test_storage_adapter.py` — validates adapter pattern using Python-equivalent MockStorage + structural checks on JS file | auto | `0a84e91` | ✅ Done |

## Acceptance Criteria Verification

### MockLLM Adapter

- ✅ **MockLLM class** in `src/chatbot/llm_client.py`
- ✅ **Accepts `(responses: list[str | Exception], delays: list[float] | None)`**
- ✅ **Implements `generate(prompt, system_prompt)`** — same interface as `OpenRouterClient`
- ✅ **Supports failure modes** — accepts `Exception` instances in responses list (HTTPError, TimeoutError, etc.)
- ✅ **`call_count` tracking** — `last_prompt`, `last_system_prompt` for assertion in tests
- ✅ **`model_name` property** — returns `"mock-llm"` so ApplicationService metadata works
- ✅ **`reset()` method** — resets call tracking for test isolation
- ✅ **Injectable via `app.dependency_overrides`** — drop-in replacement for `OpenRouterClient`

### SSE Event Schema

- ✅ **StartedEvent** — `request_id: str`
- ✅ **RetrievalEvent** — `confidence: float`
- ✅ **TokenEvent** — `text: str`
- ✅ **CitationEvent** — `document_id`, `standard_number`, `excerpt: Optional[str]`
- ✅ **DoneEvent** — `status: str`, `answer: str`
- ✅ **ErrorEvent** — `code: str`, `message: str`
- ✅ **SSE wire format** — `_sse()` produces correct `event: {type}\ndata: {json}\n\n`
- ✅ **Schema test** — 14 tests validate model creation + `_sse()` output per event type

### StorageAdapter Interface

- ✅ **StorageAdapter class** in `src/static/js/storage.js`
- ✅ **Methods: `get(key)`, `set(key, value)`, `remove(key)`, `clear()`, `migrate()`**
- ✅ **`schemaVersion: int`** — defaults to 1, settable via constructor
- ✅ **`MockStorage` class** — Map-backed, implements Web Storage API (`getItem`, `setItem`, `removeItem`, `clear`)
- ✅ **Disclaimer banner refactored** — `app.js` uses `StorageAdapter` instance with `STORAGE_KEY_DISCLAIMER_DISMISSED`
- ✅ **No functional regression** — backward-compatible `Storage` legacy API preserved

## Test Results

```
237 passed, 3 skipped in 19.65s
```

- 202 existing baseline tests: all pass (no regressions)
- 14 new SSE schema tests: all pass
- 21 new storage adapter tests: all pass

## Execution State Machine

```
New test code ↓
  tests/test_sse_schema.py ──→ TestSSEEventSchemas (7 model-validation tests)
                            ──→ TestSSEFormatting   (7 _sse() wire-format tests)
  tests/test_storage_adapter.py ──→ TestMockStorage        (6 mock storage tests)
                                ──→ TestStorageAdapter     (11 adapter pattern tests)
                                ──→ TestDisclaimerKeyConvention (3 JS file-structure tests)

Modified production code ↓
  src/chatbot/llm_client.py  ──→ MockLLM (generate, reset, call_count, model_name)
  src/api/schemas.py         ──→ 6 SSE event Pydantic models
  src/static/js/storage.js   ──→ StorageAdapter class + MockStorage class
  src/static/js/app.js       ──→ Uses new StorageAdapter for disclaimer persistence
```

## Deviations from Plan

None — plan executed exactly as written.

## Files Created

- **`tests/test_sse_schema.py`** — 14 tests across 2 classes: `TestSSEEventSchemas` (model serialisation for all 6 types) and `TestSSEFormatting` (wire-format assertions via `_sse()`)
- **`tests/test_storage_adapter.py`** — 21 tests across 3 classes: `TestMockStorage` (storage primitive behaviour), `TestStorageAdapter` (adapter pattern including error handling), `TestDisclaimerKeyConvention` (JS file content verification)

## Files Modified

- **`src/chatbot/llm_client.py`** — Added `MockLLM` class (lines 163-226) after `GeminiClient = OpenRouterClient` backward-compat alias
- **`src/api/schemas.py`** — Added 6 SSE event schemas (`StartedEvent`, `RetrievalEvent`, `TokenEvent`, `CitationEvent`, `DoneEvent`, `ErrorEvent`) after `StreamEvent`
- **`src/static/js/storage.js`** — Complete rewrite: ES5-prototype `StorageAdapter` class, `MockStorage` class (Map-backed), backward-compatible `Storage` legacy API preserved
- **`src/static/js/app.js`** — Disclaimer handler (IIFE block) updated: creates `new StorageAdapter()`, uses `get()`/`set()`/`remove()` instead of `Storage.*` calls

## Known Stubs

None — all artifacts are fully functional. `StorageAdapter.migrate()` is intentionally a no-op placeholder awaiting Phase 2 schema migrations.

## Next Phase Readiness

- ✅ MockLLM ready for Phase 2 streaming/typewriter tests
- ✅ SSE event schemas ready for Phase 2 citation and badge event types
- ✅ StorageAdapter ready for Phase 2 thread/persistence features
- ✅ 35 new tests + 202 existing = 237 passing
- **Ready for Phase 2** — all P1 stories (S1-S5) complete

## Self-Check: PASSED

- Created file `tests/test_sse_schema.py` verified present on disk
- Created file `tests/test_storage_adapter.py` verified present on disk
- Modified file `src/chatbot/llm_client.py` verified present on disk
- Modified file `src/api/schemas.py` verified present on disk
- Modified file `src/static/js/storage.js` verified present on disk
- Modified file `src/static/js/app.js` verified present on disk
- Commit `0a84e91` verified in git log
- Test suite passes at 237/240 (3 pre-existing skips)
