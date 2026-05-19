# Next-Level Planning Index

**Created:** 2026-05-09  
**Reviewed:** 2026-05-09 with BMAD party-mode perspectives from architecture, engineering, product, and test architecture.
**Reconciled:** 2026-05-11 after L1-L4 runtime implementation and L5 readiness review.
**Strategic research update:** 2026-05-18 after `docs/deep-research-report.md` and BMAD party-mode review.

This folder contains the refreshed implementation review and phase plans for the Sharia Compliance Chatbot after comparing the Kiro planning files with the current codebase.

The active implementation roadmap remains `L5-QUALITY-OPS-RELEASE-READINESS-PLAN.md`. L1-L4 are retained as historical phase plans and implementation references; they no longer represent the next unbuilt workstream.

The post-L5 strategic direction is `L6-RULES-FIRST-SHARIA-COMMERCIAL-EVALUATOR-PLAN.md`. L6 is not an immediate implementation task. It reframes Mushir from a FAS-heavy RAG chatbot into a structured, non-fatwa Sharia commercial-process assessment assistant that uses Shari'ah standards, transaction schemas, executable rules, evidence retrieval, and human-review escalation.

## Files

- `00-L0-IMPLEMENTATION-REVIEW.md` - Current-state review of L0 and draft L1/L2 code.
- `L1-CLARIFICATION-AND-STABILIZATION-PLAN.md` - Revised as core answer contract, stabilization, dependency injection, prompt/Gemini extraction, minimal clarification, and CLI preservation.
- `L2-API-AND-STREAMING-PLAN.md` - Revised as minimal FastAPI API first, optional SSE second, WebSocket deferred.
- `L3-PRODUCTION-INFRASTRUCTURE-PLAN.md` - Revised as persistence, evaluation, and observability with Qdrant gated by real need.
- `L4-COMPLIANCE-QUALITY-AND-OPS-PLAN.md` - Revised as trust, access, caching, and operations with citation validation before caching.
- `L5-QUALITY-OPS-RELEASE-READINESS-PLAN.md` - Active readiness plan for answer quality, citation trust, dependency-backed runtime behavior, and demo/release gates.
- `L6-RULES-FIRST-SHARIA-COMMERCIAL-EVALUATOR-PLAN.md` - Proposed post-L5 product/architecture pivot based on the deep research report: Shari'ah-standards-first routing, transaction ontology, executable rules, structured verdicts, and QA gates.
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
6. After L5 is green, verify official source acquisition for AAOIFI Shari'ah Standards, FAS, governance, ethics, auditing, and any scholar-reviewed fatwa sources before starting L6 implementation.
7. Before enabling any L6 domain, define its transaction schema, source route, executable rules, gold cases, red-line refusals, and human-review criteria.

## Research Critique Applied

The deep research report changes the roadmap assumptions in three ways:

- **FAS is not enough for permissibility.** FAS remains important for accounting, recognition, measurement, presentation, and disclosure. Halal/haram and contract-validity questions must route first to AAOIFI Shari'ah Standards or other reviewed Sharia sources.
- **RAG is an evidence layer, not the judge.** The target system must extract structured facts, select standards, evaluate rules, validate citations, and only then use the LLM to explain the result.
- **The product is assessment support, not fatwa issuance.** User-facing output must stay non-binding, fail closed when facts or evidence are missing, and escalate high-impact or disputed scenarios to qualified scholar/compliance review.
