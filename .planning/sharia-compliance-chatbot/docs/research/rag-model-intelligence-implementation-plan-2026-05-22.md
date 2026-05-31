# Mushir RAG, Model Intelligence, and Official-Source Crawler Implementation Plan

Generated: 2026-05-22

## Summary

This plan merges two research streams:

1. OSS RAG/model intelligence research for evaluation, retrieval, ingestion, tracing, structured extraction, and future rules-first tooling.
2. Official-source crawler research for CBE/FRA registry completion, immutable source capture, product/contract discovery, and institution evidence gates.

The corrected implementation order is crawler and provenance first for L6 data, evaluation first for RAG/model changes, and no broad framework replacement.

## Decision Rules

- Keep `ApplicationService`, retrieval, prompt building, and `CitationValidator` as the answer boundary.
- Keep L5 focused on release readiness; do not turn L5 into an L6 crawler or model overhaul.
- For L6 data, complete regulator-backed institution identity before product crawling.
- Use search engines only to discover candidate official URLs, never to create compliance facts.
- Adopt OSS libraries only after they improve a named metric against Mushir fixtures or gold cases.
- Treat GPL/AGPL/commercial-license candidates as blocked until explicit license review.

## Ordered Implementation Slices

### Slice 0: Evidence Package Cleanup

Goal: make research and raw evidence findable.

Actions:

- Keep the RAG/model research synthesis at `docs/research/rag-model-intelligence-open-source-research-2026-05-22.md`.
- Keep the official crawler synthesis at `docs/research/deep_research_official_source_crawler_2026-05-22.md`.
- Keep raw Tavily/GitHub/crawl evidence in `docs/research/raw/2026-05-22/`.
- Link the research package from `docs/index.md` and the maintained planning docs.

Acceptance gate:

- `docs/research/README.md` explains canonical syntheses, raw evidence, and planning rules.

### Slice 1: Official Regulator Registry Completion

Goal: finish the institution denominator before product crawling.

Actions:

- Add or refine CBE bank PDF handling with raw PDF hash, extracted text/table output, parse status, and rejected/security-page status.
- Add FRA register and detail-page parsers for capital market, insurance, finance, fintech, and linked official PDFs.
- Export a normalized institution table with regulator source, duplicate score, official website confidence, source URL, raw artifact hash, and `ready_for_product_crawl`.
- Preserve every old workbook row in the ledger, including gaps.

Acceptance gate:

- No institution becomes `ready_for_product_crawl` without an official website or reviewed official-source candidate.
- Tests cover CBE rejection pages, FRA pagination, Arabic-label detail parsing, workbook dedupe, and fail-closed readiness.

### Slice 2: Official Evidence Artifact Capture

Goal: capture source material immutably before extraction or assessment.

Actions:

- Store raw HTTP response bytes and headers, original PDFs, extracted text, rendered DOM or screenshot only when browser fallback is necessary, content type, status code, source URL, retrieval timestamp, and SHA-256.
- Record robots.txt, terms, rate-limit, CAPTCHA, login, paywall, and access-control decisions as statuses.
- Use static fetch first; use Playwright/browser fallback only for JavaScript-heavy official pages or official downloads that static fetch cannot access.

Acceptance gate:

- Every artifact-linked row has raw path, hash, source URL, extraction status, and access-control decision.
- Blocked or gated content is recorded as a gap, not bypassed.

### Slice 3: Product and Contract Discovery

Goal: discover products and contracts only under reviewed institutions.

Actions:

- Use official-domain and regulator-scoped search expansion for title-only products.
- Treat third-party snippets as `DISCOVERY_ONLY`.
- Prioritize PDFs, tariff/KFS pages, terms, contracts, prospectuses, annual reports, sukuk documents, fund documents, policy wordings, and regulator rulebooks over marketing pages.
- Use Faisal Murabaha as the first fixture for splitting one evidence-rich page into multiple operation records.

Acceptance gate:

- Every extracted operation links to at least one official artifact.
- Title-only products are retained as `insufficient_contractual_evidence`.
- Search expansion has max query, result, depth, and source-class budgets.

### Slice 4: RAG Evaluation Baseline

Goal: measure current behavior before adopting any retrieval or model library.

Actions:

- Add a repeatable baseline command for retrieval-only and fixture-backed evaluation.
- Track expected-standard hit rate, source-family accuracy, citation support, unsupported-answer rate, refusal correctness, clarification precision, Arabic/mixed-language pass rate, and latency.
- Use custom pytest metrics first; evaluate Ragas, DeepEval, or RAGChecker only after baseline fields are stable.

Acceptance gate:

- Baseline report exists before any RAG/model candidate is adopted.

### Slice 5: Hybrid Retrieval and Reranking Spikes

Goal: improve retrieval without changing production behavior prematurely.

Actions:

- Spike `bm25s` plus current dense retrieval for exact AAOIFI terms, Arabic terms, transliterations, and standard numbers.
- Compare Qdrant hybrid only if the local BM25+dense experiment improves metrics.
- Compare BGE-M3 and BGE reranker against the current multilingual MPNet baseline using a separate temporary index.

Acceptance gate:

- Candidate improves expected-standard hit rate or Arabic robustness without reducing citation precision or refusal correctness.

### Slice 6: Extraction Quality and Trace Observability

Goal: improve source structure and debugging.

Actions:

- Test Docling on a controlled AAOIFI source sample.
- Use pdfplumber as the preferred CBE/FRA registry PDF/table extractor.
- Treat PyMuPDF/PyMuPDF4LLM as license-gated candidates.
- Add a lightweight retrieval/evidence trace schema before adopting Phoenix/OpenInference, TruLens, or Langfuse.

Acceptance gate:

- Extracted output preserves source file, page, heading/table context, citation anchors, and artifact hash.
- One local run can be inspected from query/discovery to citation/evidence gate without exposing secrets or chain-of-thought.

### Slice 7: Structured Extraction and One-Domain Rules

Goal: support future L6 without letting models become authority.

Actions:

- Use existing Pydantic schemas first; evaluate Instructor only for scenario extraction and answer-schema enforcement.
- Keep `CitationValidator` and source-family gates authoritative.
- Defer OPA/Catala until one source-covered domain has verified rules, evidence, and gold cases.

Acceptance gate:

- Extracted scenario facts never produce a verdict without source evidence.
- Rules output remains subordinate to source availability, citation validation, and scholar-review status.

## What Not To Do

- Do not replace the current answer orchestration with Haystack, LlamaIndex, LangGraph, or another framework.
- Do not put agentic web search in the user answer path.
- Do not treat third-party pages as compliance evidence.
- Do not infer institution products, contracts, or Sharia claims from names alone.
- Do not adopt GPL/AGPL libraries before license review.
- Do not run bulk live evaluation against `openrouter/free`.

## Verification

Before staging this planning update:

- Run `git diff --check` on touched docs.
- Scan docs and research files for key-shaped secrets.
- Verify moved raw evidence paths with `Test-Path`.
- Stage only docs/research and maintained planning files.
- Leave pre-existing L6 pilot script/test changes unstaged unless explicitly requested.
