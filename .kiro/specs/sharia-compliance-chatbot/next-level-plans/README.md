# Next-Level Planning Index

**Created:** 2026-05-09  
**Reviewed:** 2026-05-09 with BMAD party-mode perspectives from architecture, engineering, product, and test architecture.
**Reconciled:** 2026-05-11 after L1-L4 runtime implementation and L5 readiness review.

This folder contains the refreshed implementation review and phase plans for the Sharia Compliance Chatbot after comparing the Kiro planning files with the current codebase.

The active roadmap is now `L5-QUALITY-OPS-RELEASE-READINESS-PLAN.md`. L1-L4 are retained as historical phase plans and implementation references; they no longer represent the next unbuilt workstream.

## Files

- `00-L0-IMPLEMENTATION-REVIEW.md` - Current-state review of L0 and draft L1/L2 code.
- `L1-CLARIFICATION-AND-STABILIZATION-PLAN.md` - Revised as core answer contract, stabilization, dependency injection, prompt/Gemini extraction, minimal clarification, and CLI preservation.
- `L2-API-AND-STREAMING-PLAN.md` - Revised as minimal FastAPI API first, optional SSE second, WebSocket deferred.
- `L3-PRODUCTION-INFRASTRUCTURE-PLAN.md` - Revised as persistence, evaluation, and observability with Qdrant gated by real need.
- `L4-COMPLIANCE-QUALITY-AND-OPS-PLAN.md` - Revised as trust, access, caching, and operations with citation validation before caching.
- `L5-QUALITY-OPS-RELEASE-READINESS-PLAN.md` - Active readiness plan for answer quality, citation trust, dependency-backed runtime behavior, and demo/release gates.
- `PARTY-MODE-REVIEW-SUMMARY.md` - Consensus review notes and plan changes from BMAD party mode.

## Current Implementation State

- **Implemented:** Shared answer service, prompt builder, Gemini client, citation validator, REST query, SSE stream, `/chat`, rate limiting, validation envelopes, readiness, metrics, Redis/Postgres/cache adapters, disclaimer handling, Qdrant ingest, and retrieval eval seed.
- **Validated:** Fast unit/service/API gate currently covers the core app boundary, API schema behavior, streaming event order, rate limiting, cache behavior, citation metadata, and in-memory Qdrant adapter checks.
- **Not yet production-ready:** The project still needs stronger gold-set coverage, explicit retrieval thresholds, real dependency integration runs, browser-visible demo gates, and documented runtime modes.

## Active Execution Order

1. Reconcile stale roadmap language with the implemented L1-L4 runtime.
2. Complete L5 RAG quality and citation trust gates.
3. Add separately marked integration gates for Redis, PostgreSQL, and Qdrant runtime modes.
4. Browser-test `/chat` and smoke-test stable public APIs under the demo configuration.
5. Freeze feature expansion until the L5 trust and runtime gates are green.
