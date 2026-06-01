# Implementation Task Plan: Source-Governed AAOIFI Assistant

**Created:** 2026-05-19
**Status:** Maintained implementation truth table, refreshed 2026-06-01; current app version V1.5 (`1.5.0`)
**Scope:** Convert the project-logic rethink, deep research reports, and crawler research into implementation slices. Do not treat planned or researched behavior as proof that runtime behavior already exists.

## Task Principles

- Work from current runtime capabilities; do not rebuild REST, SSE, `/chat`, or basic RAG unless a test proves a defect.
- Add source governance before expanding answer scope.
- Verify router and supersession seed data against cataloged AAOIFI sources before using it as authority.
- Keep tool/model choices behind measurement until they beat the current baseline on Mushir's gold set.
- Complete official-source registry identity before broad L6 product crawling.
- Treat third-party pages as discovery-only unless an official artifact confirms the fact.
- Do not run bulk live generation against `openrouter/free`; use retrieval-only probes and fixtures for evaluation.
- Keep the 2026-05-31 hard-case routing invariants green: GC-001 clarifies first, Istisna/Muqawala penalties route to `SS-05` + `SS-11`, `SS-10` stays reserved for Salam unless Salam is actually implicated, and organized banking tawarruq routes to `SS-30`.

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
- [x] Add launch-blocking hard-case routing matrix tests for construction penalty, debt late-payment, Salam, and tawarruq boundaries.

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
- [x] Preserve the production text boundary in evaluation: mock LLM fixture dicts are adapted to text before `ApplicationService`, and structured fields are merged back only for assertions.

### 10. L6 Entry Gate

- [x] Confirm whether production scope includes accounting standards only or accounting plus Shariah standards.
- [x] Confirm whether non-binding permissibility assessment is allowed when Shariah-standard evidence exists.
- [x] Acquire and catalog Shariah-standard sources before any permissibility domain is implemented.
- [x] Create scenario schema, rule table, gold cases, red-line refusals, and human-review criteria for one domain at a time.
- [x] Do not call L6 complete until source, route, rule, evidence, citation, and human-review gates pass.

### 11. Egypt Financial Institutions Evidence Corpus

**Current implementation state (V1.5, 2026-06-01):** governance/data-contract foundation, fixture-safe pipeline helpers, app versioning, registry completion, live regulator revalidation, and the guarded bank evidence scrape are implemented with focused tests. The crawl-first data layer now has 69 bank operation/mapping rows exported for scholar review. Human-scholar-review fields stay blank for now and are a later enhancement step, not a pre-scrape blocker.

- [x] Treat `Egypt Financial Institutions Refresh for Sharia Screening.md`, `Egypt_Financial_Institutions_COMPLETE.xlsx`, and `Egyptian_Financial_Institutions_Complete_Presentation.pdf` as baseline inputs, not production authority.
- [x] Normalize the CBE banks, capital-market, insurance, and non-bank finance workbook sheets into a canonical institution registry with stable IDs, regulator category, source provenance, and refresh status.
- [x] Add registry data contracts and validation that reject institution rows missing regulator/source provenance.
- [x] Add a registry loader that reads the workbook and emits validated `InstitutionRegistryRecord` rows.
- [x] Add bounded official-site discovery data contracts with attempt counts, source evidence, confidence scoring, and stop reasons.
- [x] Implement the official-site discovery runner with configured search budgets and no inferred URLs.
- [x] Define first-class gap statuses: `official_site_not_found`, `site_unreachable`, `blocked_by_security`, `requires_login`, `document_not_public`, `insufficient_public_data`, and `manual_review_required`.
- [x] Add access-control decision contracts for robots.txt, terms, rate limits, CAPTCHA, login walls, paywalls, and access controls.
- [x] Wire access-control checks into the crawler/fetcher so blocked content becomes a status, not an evasion target.
- [x] Add public-artifact metadata contracts for URL, institution ID, document type, language, retrieval timestamp, HTTP status, content hash, raw path, extraction status, and citation-anchor strategy.
- [x] Implement public artifact fetching and storage under `data/runtime/artifacts/l6_scrape/`.
- [x] Prioritize contract-level and economic-substance documents: tariffs, fees, terms, contracts, model contracts, annual reports, prospectuses, sukuk documents, fund documents, policy wordings, and regulator rulebooks.
- [x] Add operations-catalog contracts that preserve evidence spans for fees, payment terms, late-payment clauses, penalty beneficiaries, collateral, guarantees, insurance/takaful links, ownership or asset flow, and Sharia claims.
- [x] Implement extraction/classification from captured artifacts into operations-catalog records.
- [x] Add machine AAOIFI mapping contracts that keep initial compliance-risk labels as `machine_proposed` review candidates.
- [x] Implement the engine mapping generator from operations and evidence spans.
- [x] Add scholar-review record contracts with reviewer decision, AAOIFI references, rationale, uncertainty flags, correction type, and accepted-gold-case flag.
- [x] Implement scholar-review export/import and accepted-gold-case generation.
- [x] Export database-ready rows with institution name, operation/contract, Mushir engine review, AAOIFI references, and blank human-scholar-review fields.
- [x] Export bilingual scholar-facing review lists in Arabic and English with the same review item numbers and stable operation IDs for human scholar handoff.
- [x] Add a user-fact override contract so user-supplied facts can override stored institution assumptions.
- [x] Add a pilot-readiness gate that requires mixed institution coverage, at least one hard no-details/blocked case, captured artifacts, extracted operations, and accepted scholar-reviewed gold data.
- [ ] Wire institution pre-knowledge and user-fact override behavior into runtime answer flow after reviewed corpus data exists.
- [x] Run a guarded crawl-first bank evidence slice with bounded discovery, blocked-site classification, raw capture, extraction, gap marking, operations extraction, and Mushir engine assessment export.
- [ ] Run a crawl-first pilot across mixed non-bank institution types and one no-details-found hard case before scaling beyond the bank slice.
- [ ] Approve broader non-bank scraping after official website discovery proves crawl limits, blocked-site classification, raw capture, extraction, deduplication, gap marking, operations extraction, and Mushir engine assessment export. Scholar review remains blank until the later review/improvement layer.

### 12. Official-Source Crawler Research Integration

**Current planning state (2026-05-22):** the official crawler research moved the next L6 data slice earlier in the workflow. Finish regulator-backed institution registry completion and immutable provenance before product crawling.

- [x] Promote the curated crawler research and raw Tavily output into `docs/research/` with raw evidence under `docs/research/raw/2026-05-22/`.
- [x] Add CBE bank PDF handling that records raw PDF hash, source URL, retrieved timestamp, parse status, and rejection/security-page status.
- [x] Add FRA paginated register and detail-page parsers for capital-market, insurance, finance, fintech, and linked official PDFs.
- [x] Parse FRA detail pages by visible Arabic/English labels, not brittle CSS-only assumptions.
- [x] Export a normalized institution table with source metadata, duplicate scores, official website confidence, and `ready_for_product_crawl`.
- [x] Preserve every old workbook row in a ledger, including rows that become official-source gaps.
- [x] Add tests for CBE rejection pages, FRA pagination, detail-label parsing, workbook dedupe, and no fail-open product-crawl readiness.
- [x] Keep `scripts/run_l6_institution_pilot.py` as the bounded entrypoint unless it becomes too large for maintainability; evaluate Scrapy/Crawlee only after that point.

### 13. Research-Gated RAG And Model Intelligence Upgrades

**Current planning state (2026-05-22):** RAG/model libraries are candidate tools, not architecture decisions. Adopt only after baseline metrics prove improvement.

- [x] Create a retrieval-only and fixture-backed evaluation baseline before adopting Ragas, DeepEval, RAGChecker, or observability platforms.
- [x] Report expected-standard hit rate, source-family accuracy, citation support, unsupported-answer rate, refusal correctness, clarification precision, Arabic/mixed-language pass rate, and latency.
- [x] Spike `bm25s` plus current dense retrieval before Qdrant hybrid search.
- [x] Compare BGE-M3 and BGE reranker against the current multilingual MPNet baseline using a separate temporary index.
- [ ] Test Docling on a controlled AAOIFI source sample after the package installs cleanly in the active Python version.
- [x] Test pdfplumber on a controlled CBE/FRA registry PDF sample.
- [x] Keep PyMuPDF/PyMuPDF4LLM, Marker, and other GPL/AGPL candidates blocked until license review.
- [x] Add a lightweight trace schema before adopting Phoenix/OpenInference, TruLens, or Langfuse.
- [x] Use Instructor/Pydantic only for scenario extraction and schema enforcement; keep `CitationValidator` and source-family gates authoritative.
- [x] Defer OPA/Catala until one source-covered L6 domain has verified rules, evidence, and gold cases.

### 14. Gemini Roadmap Gap Implementation Alignment

**Current implementation state (2026-05-24):** the Gemini roadmap is now classified as a gap-filling backlog, not a replacement architecture. The FastAPI `/chat`, REST, SSE, `ApplicationService`, retrieval boundary, clarification engine, and citation validator remain the product spine.

- [x] Extend the retrieval contract to accept optional `filters` and `mode` while preserving older retriever callers.
- [x] Add runtime retrieval trace metadata for `retrieval_mode`, dense score, lexical score, RRF score, parent chunk ID, child chunk ID, section path, citation anchor, and source metadata when present.
- [x] Reject explicitly quarantined `metadata_status=quarantined_missing_catalog` chunks before answer support.
- [x] Add dense/hybrid retrieval mode support with a BM25-style lexical sidecar and RRF trace before considering Qdrant hybrid, BGE-M3, Milvus, or Vectara as production changes.
- [x] Add bounded Arabizi/code-switch normalization for first-wave finance terms such as `ta2seet`, `ta2kheer`, and related Murabaha/late-payment language.
- [x] Add first Murabaha late-payment rule metadata (`rule_id`, `rule_version`, evidence requirements, missing facts, and human-review flags) without allowing it to issue a verdict without Shari'ah-standard evidence.
- [x] Keep LangGraph, Chainlit, GLiNER/GLinker, full SAHM model adoption, and 10-route retrieval deferred as measured spikes.
- [x] Build catalog-backed ingestion fixtures where AAOIFI chunks are `cataloged` rather than quarantined.
- [x] Add a formal retrieval-only benchmark command covering expected-standard hit rate, source-family accuracy, citation support, refusal correctness, Arabic/mixed-language pass rate, and latency.
- [x] Add durable scholar-review persistence only after reviewed source/rule/evidence gates exist.
