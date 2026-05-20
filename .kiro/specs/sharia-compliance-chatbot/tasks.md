# Implementation Task Plan: Source-Governed AAOIFI Assistant

**Created:** 2026-05-19
**Status:** Implemented and test-covered governance contracts
**Scope:** Convert the project-logic rethink and deep research report into implementation slices. Do not treat this as proof that runtime behavior already exists.

## Task Principles

- Work from current runtime capabilities; do not rebuild REST, SSE, `/chat`, or basic RAG unless a test proves a defect.
- Add source governance before expanding answer scope.
- Verify router and supersession seed data against cataloged AAOIFI sources before using it as authority.
- Keep tool/model choices behind measurement until they beat the current baseline on Mushir's gold set.
- Do not run bulk live generation against `openrouter/free`; use retrieval-only probes and fixtures for evaluation.

## Tasks

### 1. Source Catalog Planning Contract

- [x] Define `source_registry` fields for source family, standard number, titles, language, URL, acquisition date, extraction method, review status, source confidence, and currentness.
- [x] Define `document_versions` fields for version status, corpus/index version, extraction hash, effective/publication date when available, and source record linkage.
- [x] Define `source_relationships` edge types: `supersedes`, `amends`, `replaces`, `clarifies`, and `contextualizes`.
- [x] Seed candidate supersession records from the research report as unverified review items.
- [x] Add tests or fixtures that reject answer-supporting chunks without catalog provenance.

### 2. First-Release Accounting Router Seed

- [x] Add reviewable router seed records for Murabaha, Salam, Istisna, Ijarah, Mudaraba, Musharaka, Wakala bi al-Istithmar, Zakah, Takaful, Sukuk, shares, and similar instruments.
- [x] Store candidate standard routes separately from prompt text and code-level heuristics.
- [x] Mark each seed as `unverified`, `catalog_verified`, or `rejected`.
- [x] Add English, Arabic, mixed-language, synonym-heavy, and unclear phrasing cases for each first-release route.
- [x] Ensure a router match permits retrieval only; final answers still require evidence and citation gates.

### 3. Structured Ingestion And Parent/Child Chunking

- [x] Upgrade chunk metadata to include source ID, document version, section path, language, currentness, supersession status, operation tags, and citation anchors.
- [x] Define parent structural chunks for standard/section lineage.
- [x] Define child retrieval chunks for dense/hybrid retrieval.
- [x] Ensure child hits roll up to parent lineage before answer generation.
- [x] Quarantine chunks missing required metadata.

### 4. Governed Concept Map

- [x] Extract existing handwritten term expansions into a governed concept-map artifact.
- [x] Represent canonical terms, English labels, Arabic labels, transliterations, colloquial variants, synonyms, source-family routes, candidate standards, required facts, and ambiguity warnings.
- [x] Treat Arabizi/transliterated Arabic as input normalization that must map to reviewed canonical terms.
- [x] Evaluate external terminology seeds such as FIBO, Arabterm, and Arabic Ontology before adopting any term.
- [x] Add concept-map update tests.

### 5. Clarification And Uncertainty Policy

- [x] Encode clarification triggers for low term-routing confidence, cross-standard ties, weak evidence, legacy/superseded reference ambiguity, language mismatch, missing transaction facts, and unsupported permissibility scope.
- [x] Ensure the system asks one high-value user-visible question and never exposes hidden reasoning.
- [x] Add test cases where definition/informational questions bypass over-eager transaction clarification.
- [x] Track clarification precision and recall in evaluation reports.

### 6. Metadata-Aware Retrieval Evaluation

- [x] Record retrieval traces with original query, normalized query, candidate concepts, route, filters, scores, parent/child chunk IDs, and reranking rationale.
- [x] Add correct-standard and correct-source-family metrics separately from chunk similarity.
- [x] Add superseded-source and wrong-standard trap cases.
- [x] Spike hybrid retrieval variants only after the catalog and gold set exist.
- [x] Compare Qdrant, pgvector/PostgreSQL FTS, BGE-M3, multilingual-e5, rerankers, or other candidates against the same gold set before adoption.

### 7. Answer Admissibility And Citation Gates

- [x] Require source-family eligibility, currentness, retrieval confidence, citation support, ambiguity policy, language policy, and safety policy before final answer generation.
- [x] Keep FAS evidence limited to accounting, reporting, recognition, measurement, presentation, disclosure, and definitions.
- [x] Fail closed for halal/haram, permissibility, or contract-validity questions when Shariah-standard evidence is unavailable.
- [x] Keep `INSUFFICIENT_DATA` as a successful safety outcome.

### 8. Feedback And Admin Review

- [x] Define `feedback` records linked to answer ID, retrieval run ID, citation IDs, source IDs, language, status, and reviewer.
- [x] Add correction statuses: correct, partially correct, unsupported, wrong standard, stale source, translation issue, unsafe answer, and needs scholar review.
- [x] Require review before feedback updates source catalog, concept map, routing, rules, prompts, or eval cases.
- [x] Turn accepted corrections into gold-set cases.
- [x] Preserve audit trails and secret-safe logs.

### 9. Evaluation And Release Reporting

- [x] Maintain a project-specific AAOIFI gold set as the primary release gate.
- [x] Use external datasets such as ArBanking77, DarijaBanking, ArabicaQA, or SAHM only as supplementary robustness probes after license and relevance review.
- [x] Select at most one primary observability/evaluation spine after comparing Ragas, DeepEval, Promptfoo, Langfuse, Phoenix, or equivalent tools.
- [x] Report source-family accuracy, expected-standard hit rate, citation support, clarification precision/recall, Arabic robustness, refusal correctness, latency, and unresolved feedback.
- [x] Keep live LLM smoke tests small and separate from retrieval-only or fixture-backed matrices.

### 10. L6 Entry Gate

- [x] Confirm whether production scope includes accounting standards only or accounting plus Shariah standards.
- [x] Confirm whether non-binding permissibility assessment is allowed when Shariah-standard evidence exists.
- [x] Acquire and catalog Shariah-standard sources before any permissibility domain is implemented.
- [x] Create scenario schema, rule table, gold cases, red-line refusals, and human-review criteria for one domain at a time.
- [x] Do not call L6 complete until source, route, rule, evidence, citation, and human-review gates pass.

### 11. Egypt Financial Institutions Evidence Corpus

- [x] Treat `Egypt Financial Institutions Refresh for Sharia Screening.md`, `Egypt_Financial_Institutions_COMPLETE.xlsx`, and `Egyptian_Financial_Institutions_Complete_Presentation.pdf` as baseline inputs, not production authority.
- [x] Normalize the CBE banks, capital-market, insurance, and non-bank finance workbook sheets into a canonical institution registry with stable IDs, regulator category, source provenance, and refresh status.
- [x] Add registry validation that rejects institution rows missing regulator/source provenance.
- [x] Implement bounded official-site discovery with attempt counts, source evidence, confidence scoring, and stop reasons.
- [x] Define first-class gap statuses: `official_site_not_found`, `site_unreachable`, `blocked_by_security`, `requires_login`, `document_not_public`, `insufficient_public_data`, and `manual_review_required`.
- [x] Respect robots.txt, terms, rate limits, CAPTCHA, login walls, paywalls, and access controls; blocked content SHALL become a status, not an evasion target.
- [x] Capture public artifacts with URL, institution ID, document type, language, retrieval timestamp, HTTP status, content hash, raw path, extraction status, and citation-anchor strategy.
- [x] Prioritize contract-level and economic-substance documents: tariffs, fees, terms, contracts, model contracts, annual reports, prospectuses, sukuk documents, fund documents, policy wordings, and regulator rulebooks.
- [x] Build an operations catalog that preserves evidence spans for fees, payment terms, late-payment clauses, penalty beneficiaries, collateral, guarantees, insurance/takaful links, ownership or asset flow, and Sharia claims.
- [x] Generate engine AAOIFI mappings and initial compliance-risk labels only as `machine_proposed` review candidates.
- [x] Add scholar-review rows with reviewer decision, AAOIFI references, rationale, uncertainty flags, correction type, and accepted-gold-case flag.
- [x] Ensure future user-answer behavior lets user-supplied facts override stored institution assumptions and flags stale or conflicting public corpus details.
- [x] Run a pilot across mixed institution types and one no-details-found hard case before scaling to the full registry.
