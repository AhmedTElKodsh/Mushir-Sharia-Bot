# BMAD Roundtable Summary: Project Logic Rethink

**Date:** 2026-05-20
**Mode:** `bmad-party-mode` planning review
**Participants:** Winston, Amelia, Mary, Murat
**Scope:** Rethink Mushir's project logic, compare the desired product with the implemented code, and integrate useful planning inputs from `deep-research-report.md`. Planning documents only.

## Consensus

Mushir should no longer be described as a generic RAG chatbot over AAOIFI files.

The better framing is:

> Mushir is a bilingual, source-governed AAOIFI standards assistant that interprets financial-operation intent, routes to the right source family, retrieves current and citable evidence, clarifies uncertainty, and answers only when the evidence is admissible.

## Main Architecture Correction

The target path should be:

1. Authoritative source catalog.
2. Structured bilingual ingestion.
3. Financial concept normalization.
4. Intent and operation classification.
5. Clarification when uncertainty is high.
6. Source-family and standard routing.
7. Metadata-aware retrieval.
8. Evidence-only LLM explanation.
9. Citation and answer-admissibility validation.
10. Non-binding answer, clarification, refusal, or scholar-review path.

## Winston: Architecture View

Winston emphasized that Mushir needs boring, enforceable architecture:

- Downloaded markdown is derived content, not the source of authority.
- The source catalog must track standard family, language, version, official URL, currentness, and supersession.
- Query expansion is useful, but it should be grounded in a concept-normalization layer.
- Clarification should occur before unsafe retrieval or answer generation, not only after failure.
- FAS and Shariah permissibility must be separated at routing time.
- The LLM should explain validated evidence; it should not invent verdict authority.

## Amelia: Engineering View

Amelia found that the implementation is already ahead of the old plan:

- `ApplicationService` is the right orchestration boundary.
- Multilingual retrieval, query expansion, clarification, citation validation, source-family routing, REST, SSE, and UI are already present.
- The gap is not missing RAG; the gap is missing a durable semantic contract.
- Handwritten Python dictionaries should evolve into a governed concept map.
- Source catalog and metadata-aware tests should come before broad runtime redesign.

Concrete engineering targets:

- Source catalog schema.
- Chunk metadata requirements.
- Concept map artifact.
- Correct-standard retrieval tests.
- Clarification policy tests.
- Citation support gates.

## Mary: Product And Analysis View

Mary reframed the product risk:

- A correct-looking answer from the wrong source family is a product failure.
- A correct-looking answer from a superseded source is a product failure.
- Accounting standards should not be treated as enough for all Islamic-finance permissibility questions.
- Arabic, English, mixed-language, colloquial, and institutional shorthand questions need explicit planning support.

Mary's planning structure:

1. Product logic and scope.
2. Source governance.
3. Query understanding.
4. Retrieval and routing.
5. Safety and answer policy.
6. Evaluation plan.
7. Implementation roadmap.

## Murat: Quality View

Murat recommended planning around answer admissibility:

- Source family must be eligible.
- Source currentness must pass.
- Retrieval must return the right standard, not only related text.
- Citations must support material claims.
- Ambiguity must be resolved or clarified.
- `INSUFFICIENT_DATA` is a valid safety outcome.

Highest risks:

1. Authoritative mismatch: plausible answer from wrong, stale, or weakly related standard.
2. Ambiguity collapse: answering as if the transaction structure is known.
3. Bilingual drift: mixed or colloquial Arabic retrieves nearby but doctrinally wrong material.

## Implementation Versus Desired Logic

Already aligned:

- Multilingual retrieval foundation.
- Query normalization and term expansion.
- Clarification flow.
- Source-family fail-closed scaffold.
- Citation validation.
- Shared answer contract across API/UI.

Not yet planned strongly enough:

- Official source catalog.
- First-release FAS router seed verification.
- Supersession and currentness gate.
- Governed financial concept map.
- Parent/child chunking with citation roll-up.
- Metadata-aware retrieval filters.
- Correct-source evaluation.
- Feedback/admin correction workflow.
- Clarification precision/recall gates.
- FAS-versus-Shariah answer boundary as a core product rule.

## Deep Research Follow-Up

The roundtable treated the deep research report as useful, but not as automatic architecture. Consensus:

- Promote the concrete router map, supersession seeds, parent/child chunking, trace data model, uncertainty classes, and feedback loop into current planning.
- Keep Qdrant named vectors, pgvector, BGE-M3, multilingual-e5, PyArabic, CAMeL Tools, Farasa, Ragas, DeepEval, Promptfoo, Langfuse, Phoenix, and benchmark datasets as spike candidates until verified against Mushir's own AAOIFI gold set.
- Separate source authority, product routing, and retrieval/evaluation infrastructure in every future implementation ticket.

## Planning Changes Made

- Rewrote `requirements.md` around source governance, concept normalization, routing, clarification, retrieval, answer admissibility, evaluation, and roadmap governance.
- Rewrote `requirements.md` further with the first-release router seed, supersession seed, parent/child chunking, and admin feedback requirement.
- Rewrote `design.md` around the target source-governed pipeline, current runtime component map, data model, chunking model, router seed, retrieval trace, and feedback loop.
- Added `tasks.md` as the planning backlog for the source-governed implementation slices.
- Added `PROJECT-LOGIC-RETHINK-2026-05-19.md`.
- Rewrote this roundtable summary.
- Updated the next-level planning index and L6 plan.

## 2026-05-20 Egypt Institution Corpus Addendum

The same BMAD voices reviewed the proposed Egypt financial institutions scrape and agreed it should be framed as a public-source evidence corpus, not a broad "crawl everything" feature.

Consensus:

- Mary: the business value is proving what was found, what was not found, and what a Sharia scholar accepted or corrected. The plan should require source trails and explicit `Not publicly available` outcomes instead of guessed details.
- Winston: the architecture should split institution registry, bounded discovery, public document acquisition, raw evidence storage, normalized operations catalog, and supervised scholar-review dataset.
- Amelia: implementation should start with repo preparation and tests: registry validation, no-invented-URL discovery, bounded retry policy, blocked-page classification, evidence-span preservation, and scholar-review dataset rows.
- Murat: the biggest risk is silently turning incomplete public data into confident Sharia status. Missing details, access blocks, and insufficient evidence must be first-class outcomes.

Planning updates from this round:

- Added `next-level-plans/L6-EGYPT-FINANCIAL-INSTITUTIONS-EVIDENCE-CORPUS-PLAN.md`.
- Added Requirement 17 for the Egypt financial institutions evidence corpus.
- Added Track G to `design.md`.
- Added Task 11 to `tasks.md`.
- Added tracked source-registry seed files under `data/source_registry/`.
- Added `docs/l6-egypt-institution-scrape/README.md` and runtime artifact boundaries.

## Open Questions

These should be confirmed before implementation expands:

- Accounting standards only, or accounting plus Shariah standards as production source scope?
- Can Mushir ever give non-binding permissibility assessments when Shariah-standard evidence exists?
- Are non-AAOIFI sources allowed later?
- What is the source refresh cadence?
- Who is the primary user persona?
- Which Egypt institution sector should be the first pilot slice?
- What review packet format should the Sharia scholar use for extracted operations and engine-proposed AAOIFI mappings?
