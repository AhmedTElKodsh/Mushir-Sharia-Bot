# Next-Level Planning Index

**Created:** 2026-05-09  
**Reviewed:** 2026-05-09 with BMAD party-mode perspectives from architecture, engineering, product, and test architecture.

This folder contains the refreshed implementation review and phase plans for the Sharia Compliance Chatbot after comparing the Kiro planning files with the current codebase.

## Files

- `00-L0-IMPLEMENTATION-REVIEW.md` - Current-state review of L0 and draft L1/L2 code.
- `L1-CLARIFICATION-AND-STABILIZATION-PLAN.md` - Revised as core answer contract, stabilization, dependency injection, prompt/Gemini extraction, minimal clarification, and CLI preservation.
- `L2-API-AND-STREAMING-PLAN.md` - Revised as minimal FastAPI API first, optional SSE second, WebSocket deferred.
- `L3-PRODUCTION-INFRASTRUCTURE-PLAN.md` - Revised as persistence, evaluation, and observability with Qdrant gated by real need.
- `L4-COMPLIANCE-QUALITY-AND-OPS-PLAN.md` - Revised as trust, access, caching, and operations with citation validation before caching.
- `PARTY-MODE-REVIEW-SUMMARY.md` - Consensus review notes and plan changes from BMAD party mode.

## Recommended Execution Order

1. Complete L1 core stabilization and answer contract before adding public API behavior.
2. Complete L2 REST query before implementing SSE.
3. Complete L3 eval and persistence adapters before migrating vector infrastructure.
4. Complete L4 citation/disclaimer trust work before caching or access monetization.

The key correction is that current API, session, and clarification files are prototypes. They should be treated as inputs to L1/L2 implementation, not as finished phase deliverables.

