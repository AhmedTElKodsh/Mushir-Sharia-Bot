# Next-Level Planning Index

**Created:** 2026-05-09
**Reconciled:** 2026-05-11 after L1-L4 runtime implementation and L5 readiness review
**Strategic update:** 2026-05-18 after L6 research
**Project-logic rethink:** 2026-05-19 after BMAD party-mode review
**Deep research integration:** 2026-05-19 after reviewing `../docs/deep-research-report.md`
**Egypt institutions corpus update:** 2026-05-20 after reviewing the Egyptian financial institutions refresh package
**Research cleanup and crawler update:** 2026-05-22 after reviewing OSS RAG/model intelligence and official-source crawler research

This folder contains historical phase plans and current next-level planning for Mushir. The maintained top-level planning source is now:

- `../docs/requirements.md`
- `../docs/design.md`
- `../docs/tasks.md`
- `../docs/PROJECT-LOGIC-RETHINK-2026-05-19.md`
- `../docs/AGENT_ROUNDTABLE_SUMMARY.md`

## Current Planning Position

Mushir is a bilingual, source-governed AAOIFI standards assistant. It should not be described as a generic RAG bot.

The core architecture is:

source catalog -> structured ingestion -> concept normalization -> intent classification -> clarification -> source-family routing -> metadata-aware retrieval -> citation-gated answer -> evaluation.

## Active Workstream

The active near-term workstream remains L5 release readiness for the implemented runtime:

- answer quality;
- retrieval quality;
- citation trust;
- source-family fail-closed behavior;
- dependency-backed runtime checks;
- browser and API query-path smoke checks;
- deployment hygiene;
- documentation hygiene.

Do not reopen solved REST/SSE/UI work unless a current test or runtime check proves a defect.

## Post-L5 Direction

After L5 is green, the next product-risk reductions are:

1. Official source catalog and source freshness workflow.
2. Verification of the first-release FAS router seed and supersession seed graph.
3. Structured chunk metadata and parent/child chunking tied to catalog records.
4. Governed bilingual financial concept map.
5. Source-family and correct-standard retrieval gates.
6. Clarification and refusal policy evaluation.
7. Feedback/admin review loop and accepted-correction-to-gold-case workflow.
8. Official-source crawler registry completion for CBE/FRA institution identity and provenance.
9. Metadata-aware retrieval and hybrid search spikes measured against the gold set.
10. L6 rules-first non-binding commercial-process assessment.
11. Egypt financial institutions public-operations evidence corpus for supervised scholar-reviewed evaluation.

## Files

- `00-L0-IMPLEMENTATION-REVIEW.md` - Historical review of early implementation state.
- `L1-CLARIFICATION-AND-STABILIZATION-PLAN.md` - Historical L1 plan; much of this runtime is now implemented.
- `L2-API-AND-STREAMING-PLAN.md` - Historical L2 plan; REST, SSE, and `/chat` are now implemented.
- `L3-PRODUCTION-INFRASTRUCTURE-PLAN.md` - Historical infrastructure plan; selected adapters exist, but production dependency gates remain.
- `L4-COMPLIANCE-QUALITY-AND-OPS-PLAN.md` - Historical trust/ops plan; useful for citation, cache, and operations context.
- `L5-QUALITY-OPS-RELEASE-READINESS-PLAN.md` - Active readiness plan.
- `L6-RULES-FIRST-SHARIA-COMMERCIAL-EVALUATOR-PLAN.md` - Future rules-first assessment direction, now aligned to source catalog, concept map, source-family routing, and QA gates.
- `L6-EGYPT-FINANCIAL-INSTITUTIONS-EVIDENCE-CORPUS-PLAN.md` - Future L6 data-acquisition workstream for public Egyptian institution operations, contracts, bounded discovery, ethical crawling, gap marking, and scholar-reviewed evaluation rows.
- `PARTY-MODE-REVIEW-SUMMARY.md` - Earlier party-mode refinement of L1-L4, retained as history.
- `../docs/tasks.md` - Current implementation task backlog for source catalog, router seeds, parent/child chunking, concept map, retrieval evaluation, feedback, and L6 entry gates.
- `../docs/deep-research-report.md` - Research input reviewed on 2026-05-19; useful seed data must be catalog-verified before it becomes answer authority.
- `../docs/Egypt Financial Institutions Refresh for Sharia Screening.md` - Baseline Egypt institution refresh input; useful for source-universe planning but not final production authority without live regulator revalidation.
- `../docs/research/README.md` - Research evidence index for canonical syntheses and raw evidence.
- `../docs/research/deep_research_official_source_crawler_2026-05-22.md` - Official-source crawler research for CBE/FRA registry completion, provenance, and product/contract evidence gates.
- `../docs/research/rag-model-intelligence-implementation-plan-2026-05-22.md` - Ordered implementation plan merging crawler evidence gates with RAG/model intelligence upgrades.

## Current Implementation State

Implemented:

- shared answer service;
- prompt builder;
- OpenRouter-compatible LLM client;
- citation validator;
- REST query;
- SSE stream;
- browser `/chat`;
- rate limiting;
- validation envelopes;
- readiness and metrics;
- Redis/Postgres/cache adapters;
- disclaimer handling;
- Qdrant ingest support;
- multilingual Chroma retrieval;
- query preprocessing and domain reranking;
- first commercial scenario/source-family scaffold.
- tracked source-registry seed area for the Egypt institutions evidence-corpus workstream.

Still not complete:

- official source catalog;
- verified first-release FAS router seed;
- source freshness and supersession gate;
- governed bilingual concept map;
- parent/child chunking with citation roll-up;
- feedback/admin review loop;
- metadata-aware retrieval filtering;
- correct-standard/source-family evaluation matrix;
- full L6 source acquisition and executable rules.
- full Egypt institution regulator completion, official-site discovery, public artifact capture, operations catalog, and scholar-review dataset implementation.
- research-gated RAG/model intelligence experiments with measured baseline comparisons.

## Execution Order

1. Finish L5 release-readiness evidence.
2. Build the source catalog design and seed records for the active corpus.
3. Verify the first-release FAS router seed and supersession graph against cataloged sources.
4. Upgrade ingestion metadata, parent/child chunking, and index versioning.
5. Extract term mappings into a governed concept map with tests.
6. Add bilingual, mixed-language, colloquial, ambiguous, wrong-standard, and superseded-source eval cases.
7. Add metadata-aware retrieval and source-family routing gates.
8. Add feedback/admin review capture and accepted-correction evaluation flow.
9. Complete official-source crawler registry work before broad product crawling: CBE bank PDF, FRA registers/details, raw artifact hashes, dedupe, and `ready_for_product_crawl`.
10. Run product/contract discovery only under reviewed institutions, keeping third-party leads as `DISCOVERY_ONLY`.
11. Run RAG/model intelligence experiments only after the baseline metrics exist.
12. Implement L6 only one domain at a time, starting with the best-source-covered domain.
13. Build the Egypt institutions evidence corpus as a data-acquisition and review program: registry, bounded discovery, ethical crawl, extraction, operations catalog, scholar-review dataset, then accepted gold cases.

## Safety Rules For Future Planning

- Do not answer permissibility from FAS-only evidence.
- Do not treat retrieved text as official unless it has catalog provenance.
- Do not silently use superseded sources for current answers.
- Do not expose chain-of-thought.
- Do not run large live eval batches against `openrouter/free`.
- Do not treat tool/model suggestions from research as architecture until measured against Mushir's AAOIFI gold set.
- Do not let official-source crawler search results become evidence; search creates leads only.
- Do not mark an institution ready for product crawling without an official website or reviewed official-source candidate.
- Do not mark title-only products as assessment-ready.
- Do not call L6 complete until source, route, rule, evidence, citation, and human-review gates exist.
- Do not treat missing public institution details as compliance, non-compliance, or a reason to guess; record the bounded-search gap.
- Do not bypass anti-bot controls, login walls, paywalls, CAPTCHA, or access restrictions.
