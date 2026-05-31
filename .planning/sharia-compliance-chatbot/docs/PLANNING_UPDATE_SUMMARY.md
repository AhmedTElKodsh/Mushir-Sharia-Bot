# Planning Update Summary

**Date:** 2026-05-20
**Status:** Maintained planning docs reformulated and extended with Egypt institution evidence-corpus planning
**Trigger:** BMAD party-mode rethink of Mushir's app logic against the current implementation, official AAOIFI accounting standards page, `deep-research-report.md`, and the Egypt financial institutions refresh package.

## What Changed

The planning has been reframed from:

> A chatbot that downloads AAOIFI files, chunks them, and answers with RAG.

to:

> A bilingual, source-governed AAOIFI standards assistant that normalizes financial-operation language, routes to the correct source family, retrieves current and citable evidence, clarifies uncertainty, and answers only when evidence is admissible.

## Why The Change Was Needed

The implementation is already ahead of the older L0-L4 narrative. The codebase includes FastAPI, REST, SSE, browser chat, multilingual retrieval, OpenRouter generation, clarification, citation validation, source-family routing metadata, and fail-closed behavior.

The old planning language still over-emphasized generic RAG milestones and older model assumptions. It did not make source governance, source-family routing, Arabic/English concept normalization, supersession, and answer admissibility explicit enough.

## Evidence Reviewed

- Current code paths:
  - `src/chatbot/application_service.py`
  - `src/chatbot/clarification_engine.py`
  - `src/chatbot/commercial_assessment.py`
  - `src/rag/pipeline.py`
  - `src/rag/query_preprocessor.py`
  - `src/chatbot/citation_validator.py`
  - `scripts/ingest.py`
- Current planning docs:
  - `requirements.md`
  - `design.md`
  - `next-level-plans/README.md`
  - `next-level-plans/L6-RULES-FIRST-SHARIA-COMMERCIAL-EVALUATOR-PLAN.md`
- Official AAOIFI accounting standards page:
  - bilingual standards list;
  - supersession notes;
  - warning that standards are regularly updated on the official site.
- Deep research report:
  - first-release FAS router seed;
  - candidate supersession graph;
  - parent/child chunking recommendation;
  - source/retrieval/answer trace data model;
  - Arabic NLP, retrieval, evaluation, and observability candidates.
- Egypt financial institutions refresh package:
  - `Egypt Financial Institutions Refresh for Sharia Screening.md`;
  - `Egypt_Financial_Institutions_COMPLETE.xlsx`;
  - `Egyptian_Financial_Institutions_Complete_Presentation.pdf`;
  - baseline sectors for CBE banks, capital-market institutions, insurance, non-bank finance, payment services, funds, sukuk, and regulator model contracts.

## Core Planning Corrections

1. RAG is evidence retrieval, not the decision authority.
2. Downloaded text is derived content; official source records need cataloging.
3. Correct retrieval means correct source family, standard, language, currentness, and section, not just semantic similarity.
4. Arabic, English, mixed-language, transliterated, and colloquial queries require a governed concept-normalization layer.
5. Clarification is a product safety behavior and must be evaluated.
6. FAS can support accounting-treatment answers, but FAS alone cannot support halal/haram or contract-validity conclusions.
7. Final answers require an admissibility gate: source family, currentness, retrieval confidence, citation support, ambiguity handling, and safety policy.
8. Free OpenRouter routes must not be used for large evaluation matrices.
9. Research-proposed tool/model choices must stay as measured spikes until they pass Mushir-specific AAOIFI tests.
10. Feedback/admin review should become part of governance before corrections influence routing, source catalog data, rules, prompts, or evaluations.
11. Egypt institution scraping must be bounded, public-source, provenance-preserving, and scholar-reviewed before it can become supervised compliance truth.

## Files Updated

- `requirements.md` now defines the maintained product contract and requirements around source governance, ingestion metadata, concept normalization, routing, clarification, retrieval, answer admissibility, evaluation, and roadmap governance.
- `requirements.md` now also includes the first-release router seed, supersession seed, parent/child chunking requirement, and admin feedback requirement.
- `design.md` now maps the target architecture to the current codebase and defines the source-governed pipeline, data model, chunking model, router seed, retrieval trace, and feedback loop.
- `tasks.md` now translates the rethink and research report into implementation slices.
- `tasks.md` now includes an Egypt financial institutions evidence-corpus backlog for registry normalization, bounded discovery, public artifact capture, operations cataloging, and scholar-review data.
- `PROJECT-LOGIC-RETHINK-2026-05-19.md` captures the full rethink, implementation gap analysis, research addendum, and open stakeholder decisions.
- `AGENT_ROUNDTABLE_SUMMARY.md` now reflects the 2026-05-19 BMAD review and deep research follow-up.
- `next-level-plans/README.md` now routes future planning through L5 readiness plus source-governed semantic understanding and research-seed verification.
- `next-level-plans/L6-RULES-FIRST-SHARIA-COMMERCIAL-EVALUATOR-PLAN.md` now aligns L6 with source catalog, concept map, routing, rules, quality gates, and the accounting-support boundary for FAS routes.
- `next-level-plans/L6-EGYPT-FINANCIAL-INSTITUTIONS-EVIDENCE-CORPUS-PLAN.md` defines the public-source Egypt institution operations corpus, hard gap statuses, anti-bot/access-control policy, and scholar-review workflow.

## Open Decisions To Confirm Before New Implementation

- Should the first production-grade corpus include only AAOIFI accounting standards or both accounting and Shariah standards?
- May Mushir provide non-binding standards-based permissibility assessments when Shariah-standard evidence exists, or should all permissibility questions route to scholar review?
- May future versions include non-AAOIFI sources?
- What source refresh cadence is required?
- Which user persona should drive tone and default risk posture?
- Which Egypt institution sectors should be piloted first before the full registry crawl?
- What review format does the Sharia scholar prefer for operation evidence and engine-proposed AAOIFI mappings?

## Current Roadmap After Reformulation

1. Keep the current runtime foundation.
2. Complete L5 release readiness and query-path proof.
3. Build an official source catalog and source freshness workflow.
4. Verify first-release FAS router and supersession seed records against cataloged sources.
5. Move handwritten bilingual term mappings into a governed concept map.
6. Add parent/child chunking, source-family gates, and correct-standard retrieval evaluation.
7. Add feedback/admin review and accepted-correction evaluation flow.
8. Harden clarification and refusal policy with evaluation cases.
9. Only then expand into L6 rules-first non-binding commercial-process assessment.
10. Build the Egypt institutions evidence corpus through a pilot-first pipeline before any full-registry scrape.
