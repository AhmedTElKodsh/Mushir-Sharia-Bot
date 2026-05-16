---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-05-15'
inputDocuments:
  - "_bmad-output/planning-artifacts/ux-design-specification.md"
  - "_bmad-output/planning-artifacts/ux-design-directions.html"
  - "_bmad-output/planning-artifacts/stories/HANDOFF-TO-AMELIA.md"
  - "src/api/main.py"
  - "src/api/routes.py"
  - "src/chatbot/application_service.py"
  - "src/chatbot/llm_client.py"
workflowType: 'architecture'
project_name: 'Mushir-Sharia-Bot'
user_name: 'Ahmed'
date: '2026-05-15'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements (from UX spec + codebase):**
- Bilingual (Arabic/English) Sharia compliance Q&A with LLM-powered answers
- RAG pipeline retrieving AAOIFI FAS standards from ChromaDB
- SSE streaming with 6 event types (started, retrieval, token, citation, done, error)
- Multi-turn conversation with session management
- Clarification loop for incomplete queries
- Compliance status (COMPLIANT / NON_COMPLIANT / PARTIALLY_COMPLIANT / INSUFFICIENT_DATA)
- Citation validation and inline display
- Responsive web UI with dark mode and RTL support

**Non-Functional Requirements:**
- Mobile-first responsive web (WCAG AA)
- Zero frontend build tooling
- Bilingual with auto-language detection
- SSE first-token latency <3s
- HuggingFace Spaces single-container deployment

**Scale & Complexity:**
- Primary domain: Single-page chat application, API-driven monolith
- Complexity: Low-Medium
- Technical stack: Python FastAPI + vanilla HTML/CSS/JS + ChromaDB + OpenRouter

### Party Mode Analysis — Accepted

#### Winston (Architect)

**Architecture category:** "Server-orchestrated thin client" — not SPA, not traditional server-rendered.

**3 ADRs needed:**
1. Async streaming architecture — how `_answer_service()` refactors to yield tokens incrementally
2. Session/persistence model — database-backed vs. HuggingFace persistent storage
3. Citation data model — how retrieval results are structured, stored, and linked to response spans

**ADR-worthy vs. implementation:** SSE event types and CSS approach are implementation, not ADRs. SSE needs an API contract document (OpenAPI fragment), not an ADR.

**Session identity decision needed now:** Anonymous UUIDs in sessionStorage (reversible, unblocks persistence). Document as constraint.

**Biggest risk:** Synchronous `_answer_service()` — users with slow LLM providers see 30s+ pause before any token appears.

**Architectural debt from Phase 1:**
1. Layer coupling in monolithic `main.py` — Phase 2 streaming/citations need `services/` `models/` `routes/` refactoring
2. Session fragility — in-memory dict means Space restart destroys all conversations
3. Implicit SSE threading — adding multiple event sources requires event bus abstraction

#### Amelia (Senior Engineer)

**JS module architecture:** Clean — `sse-client.js` dispatches custom DOM events, `app.js` listens, `renderer.js` consumes. SSE reconnect logic isolated.

**Phase 2 gotchas:**
1. SSE schema lacks structured citation model — `application_service.py` returns flat strings. Needs `content + citations[]` dataclass
2. No message ID scheme — threading needs unique IDs. Add UUID in `start` event payload
3. Dark mode CSS cascade — citation flyout overlay may miss variable inheritance

**Recommendations:**
- Split `renderer.js` into `message.js` + `citation.js` before P2-S5
- Start modeling citation dataclass now (even if unused) so test patterns exist

**Test architecture gaps:**
1. Zero frontend tests — Vitest + jsdom needed
2. No SSE streaming integration test — test full `_sse()` generator event sequence
3. No CSS regression coverage — Playwright smoke test for dark mode
4. Fixture coupling — if `application_service` returns dataclass for Phase 2, all mocks need updating

#### Murat (Test Architect)

**Risk profile:**
- No auth: CRITICAL severity, LOW blast radius (OpenRouter credits only). Acceptable for v0.4.0
- Synchronous LLM: MEDIUM — 60-90s blocking call is the highest production risk. No timeout handling or heartbeat ping event
- No database: LOW risk — ChromaDB is file-backed, no concurrent writer contention

**Top 3 priorities before Phase 2:**
1. MockLLM adapter with configurable failure modes (429, 502, timeout)
2. Pydantic SSE event schema — discriminated union per event type
3. `StorageAdapter` interface with schema versioning (migration from N to N+1)

**Biggest Phase 2 risk:** localStorage + animation timing — three concurrent mutation sources (typewriter timer, citation click, SSE push). Encapsulate behind `StorageAdapter`.

**Test infrastructure decisions to document:**
| Decision | Recommendation |
|----------|---------------|
| Fixture scope | Module-scoped ChromaDB, function-scoped everything else |
| Mock LLM | `MockLLM` accepting `(responses[], delays[])` — injectable via `app.dependency_overrides` |
| SSE contract tests | Pydantic discriminated union + golden-file assertions on `data:` lines |
| Frontend testing | Playwright component tests (not e2e for Phase 1/2) |
| localStorage | `StorageAdapter` with `schema_version` — test with `MockStorage` |
| CI ordering | Fastest-first: Pydantic → fixtures → SSE → integration → resilience |

### Starter Template Evaluation

**Decision:** Skipped — brownfield project with all technology choices already committed:

| Dimension | Current Decision | Status |
|-----------|-----------------|--------|
| Backend | Python FastAPI in `src/api/main.py` | Shipped |
| Frontend | Vanilla HTML/CSS/JS in `src/static/` | Shipped (P1-S1) |
| Vector DB | ChromaDB (file-based) | Shipped |
| LLM | OpenRouter (synchronous) | Shipped |
| Build tooling | None (deliberate zero-tooling) | Shipped |
| Hosting | HuggingFace Spaces Docker | Shipped |
| Testing | Pytest (202 tests), Playwright | Shipped |

The 3 critical ADRs identified in Party Mode are the next focus.

#### Mary (Business Analyst)

**Missing stakeholder voices:**
1. **Mufti/Sharia scholar** — Who verifies the corpus? Who defines authoritative vs. fringe sources? No curation workflow exists.
2. **End-user** — They're asking about halal vs. haram with spiritual stakes. SessionStorage and anonymous UUIDs affect trust directly.
3. **Admin/deployer** — No audit trails, no escalation paths, no intervention mechanism when LLM contradicts scholarly consensus.

**Anonymous UUID risks:**
- No recall continuity — session gone tomorrow, user expects a coherent advisor
- No abuse attribution — fringe rulings published citing "Mushir AI" with zero traceability
- No personalization surface — bookmarking, scholar preferences, query history all blocked

**"Reference chatbot" framing is incomplete:** A Sharia compliance tool has baseline trust requirements. Every answer needs: clear disclaimers, source attribution, and a visible boundary between "retrieved source" and "LLM synthesis."

**Requirements not served:**
- **Authority ranking** — ChromaDB retrieval is flat semantic search. Hanafi user getting Hanbali ruling without context = theological error.
- **Query escalation** — No confidence threshold → human pathway. Should be: high-conf → synthesize, medium → direct quotes, low → "requires a scholar."

**#1 ADR priority: Citation data model.** The shape of evidence determines audit trails, quality metrics, RAG evaluation datasets, and the ability to prove every answer. The citation schema — with source ID, scholar, school of thought, publication, page/paragraph, retrieval score, and LLM confidence — future-proofs every downstream requirement. Get this right first.

## Core Architectural Decisions

### Decision Priority Analysis

**Already Decided (existing implementation):**

| Category | Decision | Location |
|----------|----------|----------|
| Data | ChromaDB file-based vector store | `src/rag/pipeline.py` |
| API | REST + SSE streaming via FastAPI | `src/api/routes.py` |
| Frontend | Vanilla HTML/CSS/JS, zero tooling | `src/static/` |
| State management | DOM-driven + sessionStorage | Phase 1 |
| Hosting | HuggingFace Spaces Docker | `Dockerfile` |
| Auth | None (Phase 1-2 scope) | Deliberate |
| Monitoring | NullAuditStore + MetricsRegistry | `src/observability/metrics.py` |

### ADR-1: Citation Data Model

**Status:** ⬜ Not yet implemented — must be designed before Phase 2 (P2-S5 flyout)

**Recommended schema (Pydantic dataclass):**
```python
@dataclass
class CitationEvidence:
    source_id: str              # ChromaDB chunk ID
    standard: str               # e.g. "FAS-21"
    section: str                # e.g. "§4/3"
    excerpt: str                # Raw text from retrieved chunk
    scholar: Optional[str]      # AAOIFI board (future)
    school_of_thought: Optional[str]  # Hanafi, Shafi, etc. (future)
    retrieval_score: float      # ChromaDB similarity
    llm_confidence: float       # LLM self-assessment
```

**Why this matters (Mary):** The citation schema determines audit trails, quality metrics, RAG evaluation, and the ability to prove "every answer came from Scholar X, page Y, paragraph Z." A poorly structured citation model means rebuilding later while users are relying on answers.

**Affects:** P2-S5 (Citation Flyout), ApplicationService return type, all 202 test fixtures

### ADR-2: Session/Persistence Model

**Status:** ✅ Decision made — anonymous UUIDs in sessionStorage

**Decision:** Anonymous UUID generated on first visit, stored in browser sessionStorage, passed as `session_id` to all API calls.

**Constraint documented:** Sessions do not survive cross-device or browser restart (sessionStorage is per-tab). No user identity — no abuse attribution, no recall continuity across days. Acceptable for v0.4.0.

**Future path:** Upgrade to `localStorage` (survives browser close) or server-side database when auth is added.

**Affects:** P2-S3 (Message Persistence), P2-S6 (Multi-Turn Threading)

### ADR-3: Async Streaming Architecture

**Status:** 🟡 Deferred to Phase 4

**Decision:** Phase 2 uses client-side typewriter simulation (receive full answer in one `token` event, render character-by-character via `requestAnimationFrame`). True LLM streaming (refactoring `_answer_service()` to yield incremental tokens via an async generator) is deferred until Phase 4, and only if latency data justifies it.

**Rationale:** Synchronous call is simpler, testable, and doesn't require refactoring the LLM client or the service layer. The user sees the same visual effect either way. True streaming only benefits long responses (>30s generation time), which data should confirm before investing.

**Risk documented:** Users with slow LLM providers may see a 30s+ pause before the first character appears. Mitigation: typing indicator (P2-S1) shows "Mushir is composing..." during this window.

**Affects:** P2-S4 (Typewriter Effect — client-side only), Future Phase 4 epic

## Implementation Patterns & Consistency Rules

### Naming Conventions

| Domain | Convention | Example |
|--------|-----------|---------|
| Python | `snake_case` | `_answer_service()`, `_query_events()` |
| CSS custom props | `kebab-case` | `--color-primary`, `--bubble-max-width` |
| Files (Python) | `snake_case.py` | `application_service.py`, `citation_validator.py` |
| Files (CSS/JS) | `kebab-case` | `sse-client.js`, `components.css` |
| SSE events | lowercase single-word | `started`, `retrieval`, `token`, `citation`, `done`, `error` |
| JSON fields | `snake_case` | `request_id`, `session_id`, `clarification_question` |
| HTML/CSS classes | `kebab-case` | `citation-anchor`, `compliance-badge` |

### Structural Patterns

- **Test mirroring:** `tests/test_api_l2.py` mirrors `src/api/` — one test file per module
- **Domain grouping:** `src/chatbot/` (orchestration), `src/rag/` (retrieval), `src/api/` (transport layer), `src/models/` (data contracts)
- **Static files by type:** `css/`, `js/` under `src/static/`
- **FastAPI convention:** routes in `routes.py`, app factory in `main.py`, Pydantic schemas in `schemas.py`

### API Patterns

- **SSE:** Single emission point via `_sse()` helper — `event: {type}\ndata: {json}\n\n`
- **REST responses:** Pydantic `QueryResponse` model with `answer`, `status`, `citations`, `metadata`
- **Error shape:** `ErrorResponse(code, message, request_id, timestamp)` — structured and consistent
- **Status codes:** 200=success, 422=validation, 429=rate limit, 500=internal, 501=not implemented

### Process Patterns

| Pattern | Mechanism | Location |
|---------|-----------|----------|
| Loading state | SSE `started` → typing indicator → cleared on first `token` | P2-S1 |
| Error recovery | SSE `error` → red bubble + retry button → re-sends last query | P2-S1 |
| State management | No global state — `app.js` orchestrates via custom DOM events | `app.js` |
| Persistence | `StorageAdapter` (sessionStorage) with schema version field | P2-S3 |
| Language detection | Arabic char ratio >30% → RTL + Arabic font | `application_service.py` + CSS |
| Typewriter | Client-side `requestAnimationFrame` loop (not backend streaming) | P2-S4 |

## Project Structure & Boundaries

### Current Structure (post Phase 1)

```
src/
├── api/                # FastAPI transport
│   ├── main.py         # App factory, middleware, StaticFiles mount
│   ├── routes.py       # REST + SSE endpoints, _sse() helper
│   ├── schemas.py      # Pydantic models (QueryRequest, QueryResponse, ErrorResponse)
│   ├── dependencies.py # DI wiring
│   └── rate_limit.py   # InMemoryRateLimiter
├── chatbot/            # Core domain logic
│   ├── application_service.py  # answer(), normalization, caching
│   ├── llm_client.py           # OpenRouter wrapper with retry
│   ├── prompt_builder.py       # AAOIFI prompt construction
│   ├── citation_validator.py   # Citation extraction from answer text
│   ├── clarification_engine.py # Multi-turn fact gathering
│   └── session_manager.py      # In-memory session store
├── static/             # Frontend (Phase 1)
│   ├── index.html
│   ├── css/ (base.css, chat.css, components.css, dark.css)
│   └── js/ (app.js, sse-client.js, renderer.js, storage.js, shortcuts.js, flyout.js)
├── rag/                # RAG pipeline
│   └── pipeline.py     # ChromaDB retrieval + embedding
├── models/             # Data contracts
│   ├── ruling.py       # AnswerContract, ComplianceStatus, AAOIFICitation
│   └── session.py      # SessionState, ClarificationState
├── storage/            # Persistence adapters
│   ├── cache.py        # InMemoryCacheStore, RedisCacheStore
│   └── audit_store.py  # PostgresAuditStore, NullAuditStore
├── config/             # Logging, environment
└── observability/      # MetricsRegistry
```

### Phase 2 File Additions (frontend only)

| File | Purpose | Story |
|------|---------|-------|
| `src/static/js/flyout.js` | Citation flyout panel + focus trap | P2-S5 |
| `src/static/js/storage.js` (populate) | `StorageAdapter` with schema versioning | P2-S3 |
| No new backend files | All Phase 2 changes are frontend-only | — |

### Boundary Rules

1. **`src/api/` never contains business logic** — only routing, DI, SSE formatting
2. **`src/chatbot/` never knows about SSE or HTTP** — returns `AnswerContract`, not SSE events
3. **`src/static/js/` modules communicate via custom DOM events** — not direct imports
4. **All SSE emission is single-sourced through `_sse()`** — never raw `yield "data: ..."`
5. **`sessionStorage` access is encapsulated behind `StorageAdapter`** — never direct `getItem` calls

## Architecture Validation

### Coherence: ✅

All technology choices are compatible and deployed:
- Python FastAPI + vanilla HTML/CSS/JS + ChromaDB + OpenRouter + HuggingFace Spaces Docker
- No version conflicts (all committed code passes 202/202 tests)
- SSE contract correct (all 6 event types via `_sse()`)

### Requirements Coverage: ✅

14 UX enhancement categories mapped to 10 stories across 4 phases. 3 ADRs cover critical gaps. All user stories are implementable with current architecture decisions.

### Gap Analysis

| Gap | Severity | Status |
|-----|----------|--------|
| Citation data model (structured Pydantic schema) | **Critical** — blocks P2-S5 | ADR-1 documented, needs implementation before Phase 2 |
| Zero frontend tests | **Critical** — blocks Phase 2 quality | Playwright + Vitest planned |
| No auth (anonymous UUID only) | Low — acceptable for v0.4.0 | ADR-2 documents constraint |
| No sync LLM streaming (full answer buffered) | Medium — UX risk, deferred to Phase 4 | ADR-3 documents decision |
| No admin/curation workflow | Low — not in scope | Deferred post-MVP |
| No authority ranking (madhab-aware) | Low — not in scope | Deferred post-MVP |
| No query escalation (conf → human) | Low — not in scope | Deferred post-MVP |
