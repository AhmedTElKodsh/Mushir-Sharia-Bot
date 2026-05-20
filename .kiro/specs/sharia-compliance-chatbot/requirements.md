# Requirements Document: Mushir AAOIFI Standards Assistant

**Last reformulated:** 2026-05-19
**Status:** Maintained planning source of truth
**Scope:** Planning only. This document describes the required product logic; it does not imply runtime code changes have already been made.

## Product Position

Mushir is a bilingual AAOIFI standards assistant for Islamic finance questions. It is not a general halal/haram oracle and it must not issue binding fatwas, legal opinions, or financial advice.

The product promise is:

> Given an English, Arabic, or mixed-language financial question, Mushir normalizes the user's wording into financial-operation concepts, routes the question to the right AAOIFI source family, retrieves current and citable standard text, asks a focused clarification question when uncertainty is high, and answers only when retrieved evidence supports the result.

The core planning correction is that RAG is an evidence mechanism, not the product brain. The product brain is the controlled path around source governance, concept normalization, routing, uncertainty handling, citation validation, and fail-closed answer policy.

## Current Implementation Baseline

The current codebase already includes more than the older L0-L4 planning language describes:

- FastAPI application, REST query endpoint, SSE streaming, and browser `/chat`.
- `ApplicationService` as the central orchestration boundary.
- Multilingual Chroma retrieval with optional Qdrant support.
- Multilingual sentence-transformer embeddings and Arabic/English index validation.
- Query normalization, transliteration handling, domain-term expansion, and domain reranking.
- Deterministic clarification flow with session state.
- Prompt building, OpenRouter-compatible LLM generation, citation validation, cache, and audit hooks.
- Source-family and commercial-assessment scaffold that can fail closed when permissibility questions lack Shariah-standard evidence.
- Local AAOIFI markdown corpus with English and Arabic files and a multilingual Chroma index.

The main planning gap is not "add RAG." The main planning gap is to make the semantic and source-governance contract durable, testable, and not trapped in handwritten code heuristics.

## Official Source Constraint

The official AAOIFI accounting standards page reviewed on 2026-05-19 shows these planning constraints:

- Accounting standards are listed in English and Arabic.
- Standards include supersession notes, for example older FAS entries replaced by later FAS entries.
- AAOIFI warns that standards are regularly updated on the official website and does not take responsibility for other copies in industry circulation.

Therefore downloaded markdown files are derived artifacts, not the authority itself. Planning must require a source catalog, source freshness checks, supersession handling, and citation traceability back to official URLs or accepted source records.

Reference: https://aaoifi.com/accounting-standards-2/?lang=en

## Product Boundaries

Mushir may answer:

- Accounting, recognition, measurement, presentation, reporting, disclosure, and definition questions when current retrieved AAOIFI evidence is sufficient.
- Standards-routing questions such as "which AAOIFI standard covers this topic" when source-family and standard metadata support the answer.
- Non-binding explanatory questions about retrieved AAOIFI terms when citations directly support the explanation.

Mushir must clarify or refuse:

- Ambiguous financial-operation descriptions.
- Questions where the operation could map to multiple standards or source families.
- Halal/haram, permissibility, contract-validity, or fatwa-adjacent questions when Shariah-standard evidence is missing.
- Questions where the retrieved evidence is weak, stale, superseded, conflicting, or not directly related.
- Requests for binding rulings, legal advice, investment advice, or hidden reasoning.

Clarifying questions are a visible user dialogue, not chain-of-thought. The system may keep a concise internal reasoning summary for audit, but it must not expose hidden reasoning.

## Planning Assumptions

These assumptions are safe unless the user or stakeholder changes them:

- Correctness and traceability are more important than conversational smoothness.
- Arabic and English are both first-class user languages.
- Accounting-standard answers are in current scope; broad permissibility assessment remains fail-closed unless Shariah-standard sources, rules, and QA gates exist.
- AAOIFI is the primary authority. Any future non-AAOIFI source must be explicitly approved and cataloged.
- Free OpenRouter routes are for small demos and smoke checks, not bulk evaluation.

## Open Stakeholder Decisions

These do not block the planning rewrite, but they should be confirmed before implementation expands:

- Whether the first production corpus must include only AAOIFI accounting standards or both accounting and Shariah standards.
- Whether permissibility questions may ever receive a non-binding "standards-based assessment" when Shariah-standard evidence exists, or should always be routed to scholar review.
- Whether future sources may include scholar-reviewed fatwa repositories, regulator guidance, or internal Shariah-board policies.
- Required refresh cadence for checking the official AAOIFI site.
- Primary user persona: accountant, auditor, bank employee, Shariah reviewer, Islamic finance student, or general public.

## Deep Research Inputs To Promote

The 2026-05-19 deep research report adds concrete planning inputs that should be promoted into requirements, with one important constraint: these are routing and schema seeds until the official source catalog verifies the underlying AAOIFI records.

First-release accounting router seed:

| User operation or product family | Candidate AAOIFI accounting route |
|---|---|
| Murabaha / deferred payment sale | FAS 28 |
| Salam | FAS 7, FAS 52 |
| Istisna | FAS 10, FAS 52 |
| Ijarah / leasing | FAS 32 |
| Mudaraba | FAS 3 |
| Musharaka | FAS 4, FAS 51 |
| Wakala bi al-Istithmar / investment agency | FAS 31 |
| Zakah | FAS 9, FAS 39 |
| Takaful | FAS 42, FAS 43 |
| Sukuk, shares, and similar instruments | FAS 33, FAS 34 |

Supersession seed records:

| Earlier standard | Candidate current route or replacement note |
|---|---|
| FAS 2 and FAS 20 | FAS 28 |
| FAS 11 | FAS 30 and FAS 35 |
| FAS 5 and FAS 6 | FAS 27 |
| FAS 17 | FAS 25, FAS 26, and later FAS 33 context |

These seed maps SHALL NOT be treated as final authority until catalog records confirm source URLs, titles, language coverage, version status, and supersession notes.

## Requirements

### Requirement 1: Authoritative Source Governance

**User story:** As a product owner, I want each AAOIFI source to be cataloged before ingestion, so that Mushir does not rely on stale or unidentified text.

Acceptance criteria:

1. The system SHALL maintain a source catalog for every ingested standard.
2. Each source catalog record SHALL include source family, standard number, English title, Arabic title when available, official URL, language, acquisition date, extraction method, review status, currentness status, and supersession fields.
3. Source families SHALL include at least `fas`, `sharia_standard`, `governance`, `ethics`, `auditing`, `fatwa`, and `local_overlay`.
4. The catalog SHALL distinguish official source pages from derived markdown, converted PDFs, or manually supplied text.
5. Superseded standards SHALL be flagged and SHALL NOT dominate retrieval unless the user explicitly asks historical questions.
6. If currentness cannot be verified, the source SHALL be marked as unverified and answer policy SHALL treat it as lower-confidence evidence.
7. Source-catalog changes SHALL be auditable.
8. The source model SHOULD include explicit records for `source_registry`, `document_versions`, `sections`, `chunks`, `term_variants`, `retrieval_runs`, `answers`, `citations`, `feedback`, and `eval_goldset`.
9. Supersession and relationship edges SHALL distinguish at least `supersedes`, `amends`, `replaces`, `clarifies`, and `contextualizes` when the source record supports the distinction.
10. The first-release router and supersession seeds in this document SHALL be loaded only as reviewable seed data, not as hard-coded prompt assumptions.

### Requirement 2: Structured Bilingual Ingestion

**User story:** As a developer, I want AAOIFI text converted into structured chunks with strong metadata, so that retrieval can return the right file, section, and language.

Acceptance criteria:

1. The ingestion pipeline SHALL ingest only files linked to a source catalog record.
2. Each chunk SHALL preserve document ID, source family, standard number, language, section or clause marker, source file path, chunk index, embedding model, extraction date, and source currentness.
3. Where available, each chunk SHOULD include section title, page number, citation anchor, topic tags, operation tags, and related standard references.
4. Chunking SHOULD preserve standards structure before token limits; token size is a fallback constraint, not the only split rule.
5. Arabic and English versions of the same standard SHOULD be linked through catalog metadata when official alignment is known.
6. Ingestion SHALL fail or quarantine chunks missing minimum metadata.
7. The multilingual vector index SHALL reject configurations that claim Arabic retrieval support without Arabic corpus content and a multilingual embedding model.
8. The ingestion design SHOULD support parent structural units and child retrieval units: parent chunks preserve standard/section context, while child chunks optimize retrieval and cite back to parent lineage.
9. Vector payload metadata SHOULD include standard number, version status, language, title in available languages, heading path, canonical terms, finance operation, page or section anchors, source URL, and aligned Arabic/English chunk IDs where known.

### Requirement 3: Financial Concept Normalization

**User story:** As a user, I want to ask in natural wording, colloquial Arabic, English, transliteration, or mixed language, so that Mushir can understand the financial operation instead of only matching exact standard titles.

Acceptance criteria:

1. The system SHALL normalize spelling, Arabic diacritics, Arabic letter variants, common transliteration variants, and common Islamic-finance spelling variants.
2. The system SHALL maintain a governed concept map outside ad hoc prompt text.
3. The concept map SHALL include canonical concepts, English labels, Arabic labels, transliterations, colloquial variants, synonyms, related source families, and ambiguity warnings.
4. Normalization SHALL distinguish lexical expansion from financial-operation classification.
5. Synonyms SHALL improve retrieval and routing but SHALL NOT force an answer when the underlying transaction remains unclear.
6. The concept map SHALL cover at least murabaha, deferred sale, ijarah, qard, riba, tawarruq, salam, istisna, wakala, mudaraba, musharaka, sukuk, zakat, takaful, investment accounts, late-payment penalties, impairment, disclosure, recognition, measurement, and presentation.
7. Updates to the concept map SHALL include test cases.
8. Arabizi/transliterated Arabic handling SHALL be treated as query normalization input, not as authoritative terminology unless mapped to a governed canonical term.
9. External terminology resources such as FIBO, Arabterm, and Arabic Ontology MAY be evaluated as seed sources, but all production terms SHALL be reviewed and governed locally.

### Requirement 4: Intent And Operation Classification

**User story:** As a compliance user, I want Mushir to identify what kind of question I am asking, so that it searches the right standards and does not answer accounting questions as Shariah rulings or vice versa.

Acceptance criteria:

1. The system SHALL classify question type before final answer generation.
2. Minimum question types SHALL include `accounting`, `permissibility`, `governance`, `definition`, `standards_routing`, `comparison`, and `unknown`.
3. The system SHALL extract or infer candidate contract families when possible.
4. Minimum contract families SHALL include `murabaha`, `ijarah`, `tawarruq`, `qard`, `wakala`, `sukuk`, `musharaka`, `mudaraba`, `salam`, `istisna`, and `unknown`.
5. The system SHALL track uncertainty when user wording can map to more than one operation.
6. The classification output SHALL be available in metadata for evaluation and audit.
7. Low-confidence classification SHALL route to clarification, not a final answer.
8. Accounting operation classification SHOULD use the first-release router seed table as a testable candidate map after catalog verification.

### Requirement 5: Clarification And Uncertainty Policy

**User story:** As a user, I want Mushir to ask one useful question when my scenario is unclear, so that I can reach an accurate answer without receiving guesses.

Acceptance criteria:

1. The system SHALL ask a focused clarification question when operation type, source family, required facts, or standard candidate is ambiguous.
2. Clarification triggers SHALL include multiple plausible operations, missing contract structure, missing parties, missing asset or service, missing payment terms, low retrieval confidence, split retrieval across standards, source-family mismatch, and unsupported permissibility scope.
3. Clarification SHALL use the user's preferred language where reasonably detected.
4. The system SHALL ask only the highest-value missing question per turn.
5. Clarification SHALL not expose hidden reasoning or chain-of-thought.
6. The system SHALL allow fail-closed `INSUFFICIENT_DATA` when clarification cannot resolve source or fact gaps.
7. Clarification behavior SHALL be measured for precision and recall.
8. Clarification policy SHALL explicitly cover low term-routing confidence, cross-standard ties, weak evidence, legacy/superseded reference ambiguity, and material language mismatch.

### Requirement 6: Source-Family Routing

**User story:** As a Shariah or accounting reviewer, I want Mushir to route questions to the correct source family, so that answers do not misuse FAS evidence for permissibility conclusions.

Acceptance criteria:

1. Accounting, recognition, measurement, presentation, reporting, and disclosure questions SHALL route primarily to FAS.
2. Halal/haram, permissibility, contract-validity, and fatwa-adjacent questions SHALL route primarily to Shariah Standards or approved Shariah sources.
3. Governance or institutional-control questions SHALL include governance standards when available.
4. Mixed questions SHALL separate accounting-treatment evidence from Shariah-permissibility evidence.
5. The router SHALL report primary and secondary source families in answer metadata.
6. If the required source family is unavailable or unverified, the answer SHALL clarify or fail closed.
7. The router SHALL prefer current sources over superseded sources.
8. The router SHALL separate product-family routing from final answer admissibility; a matched FAS route only permits retrieval, not automatic answer generation.
9. First-release FAS routes SHALL be regression-tested against representative English, Arabic, mixed-language, synonym-heavy, and unclear user phrasings.

### Requirement 7: Metadata-Aware Retrieval

**User story:** As a developer, I want retrieval to use both semantic similarity and standards metadata, so that correct source selection is evaluated separately from text similarity.

Acceptance criteria:

1. Retrieval SHALL combine dense multilingual search with metadata-aware filtering or reranking.
2. Retrieval SHOULD include lexical or hybrid search for standard numbers, Arabic terms, English terms, titles, and clause markers.
3. Retrieval SHALL support filters for source family, standard number, language, currentness, and concept tags when catalog data exists.
4. Retrieval evaluation SHALL report both relevant-chunk recall and correct-standard/source-family recall.
5. Retrieval SHALL prefer directly relevant current sections over semantically similar but wrong-family passages.
6. Low-confidence or conflicted retrieval SHALL trigger clarification or insufficient evidence.
7. Retrieval cache keys SHALL include corpus/index version, embedding model, query normalization version, and retrieval parameters.
8. Retrieval SHALL record enough trace data to inspect query normalization, routing candidates, filters, retrieved hits, reranking decisions, and cited chunks.
9. Qdrant named vectors, pgvector, PostgreSQL full-text search, BGE-M3, multilingual-e5, and other embedding/reranking options MAY be evaluated, but the requirement is hybrid-capable retrieval quality, not commitment to a specific backend before measurement.

### Requirement 8: Answer Admissibility

**User story:** As a risk owner, I want Mushir to answer only when all evidence gates are satisfied, so that fluent but unsupported answers are blocked.

Acceptance criteria:

1. A final answer SHALL be admissible only when source family, currentness, retrieval confidence, citation support, and ambiguity policy all pass.
2. Every material claim SHALL be traceable to retrieved evidence or SHALL be omitted.
3. The answer SHALL cite specific AAOIFI standards and section or chunk evidence when available.
4. The citation validator SHALL reject invented standard IDs, section IDs, page numbers, and unsupported references.
5. The system SHALL not answer from general model knowledge when AAOIFI evidence is missing.
6. The system SHALL distinguish definitions from transaction-level assessments.
7. `INSUFFICIENT_DATA` is a successful safety outcome when evidence is not enough.

### Requirement 9: Accounting Versus Shariah Boundary

**User story:** As a stakeholder, I want Mushir to separate accounting treatment from Shariah permissibility, so that users are not misled by accounting evidence alone.

Acceptance criteria:

1. FAS evidence MAY support accounting, reporting, recognition, measurement, presentation, disclosure, and definition answers.
2. FAS evidence alone SHALL NOT support halal/haram, permissibility, or contract-validity conclusions.
3. If a question combines accounting treatment and permissibility, Mushir SHALL answer the accounting portion if supported and explicitly mark the permissibility portion as requiring Shariah-standard evidence or qualified review.
4. Prompt wording SHALL avoid claiming that Mushir is a formal Shariah authority.
5. User-facing answers SHALL remain non-binding.

### Requirement 10: Multilingual Answer Behavior

**User story:** As an Arabic or bilingual user, I want Mushir to understand my language and respond clearly, so that I can use the tool naturally.

Acceptance criteria:

1. The system SHALL support English, Arabic, transliterated English, and mixed Arabic-English input.
2. Arabic input SHOULD receive Arabic output unless the user requests English.
3. Mixed-language input SHOULD preserve the user's likely preferred answer language.
4. Citations and standard identifiers SHALL remain stable across output languages.
5. Arabic output SHALL use clear formal Arabic for user-facing answers.
6. Colloquial Arabic SHALL be accepted as input but not treated as a reliable source term without normalization and uncertainty checks.

### Requirement 11: Runtime Surfaces

**User story:** As a developer or user, I want the same answer logic through UI and APIs, so that transport changes do not change the compliance behavior.

Acceptance criteria:

1. CLI, REST, SSE, and browser chat SHALL use the same answer service contract.
2. Transport layers SHALL not bypass clarification, retrieval, citation validation, disclaimer, rate limiting, or safety gates.
3. REST and SSE schemas SHALL expose status, answer, citations, limitations, clarification question, and metadata consistently.
4. Readiness checks SHALL not be treated as proof of answer-path quality.
5. Live smoke checks SHALL include at least one query-path proof after deployment or index changes.

### Requirement 12: Evaluation And Release Gates

**User story:** As a test architect, I want release gates that measure source correctness, not just answer style, so that regression tests catch authoritative mismatches.

Acceptance criteria:

1. The evaluation matrix SHALL include English, Arabic, mixed-language, colloquial Arabic, transliteration, synonym-heavy, ambiguous, unsupported, wrong-standard-trap, and superseded-source cases.
2. Each case SHALL define expected behavior: answer, clarify, refuse, or insufficient evidence.
3. Each answerable case SHALL include expected source family and expected standard or file candidates.
4. Each case SHALL check citation validity and source support.
5. Retrieval-only evaluation SHALL run separately from live LLM generation.
6. Bulk evaluation SHALL use fake LLM fixtures, retrieval-only probes, and `RAG_EVAL_MODE=true`; it SHALL NOT run large live matrices against `openrouter/free`.
7. A release SHALL be blocked by failure in source-family routing, citation support, Arabic retrieval support, or fail-closed safety behavior.
8. External datasets such as ArBanking77, DarijaBanking, ArabicaQA, or SAHM MAY be used as supplementary robustness probes only after license and relevance review; the primary gold set SHALL remain project-specific AAOIFI cases.
9. Evaluation SHALL track expert-correction rate and feedback closure status once reviewer feedback capture exists.

### Requirement 13: Source Refresh And Change Control

**User story:** As an operator, I want source updates to be deliberate and testable, so that the public demo does not silently drift.

Acceptance criteria:

1. Source refresh SHALL compare current catalog records against official AAOIFI pages or accepted source records.
2. New or changed standards SHALL create a new corpus/index version.
3. Supersession changes SHALL trigger retrieval and answer-policy regression tests.
4. App/UI deploys SHALL be separable from retrieval-index deploys.
5. Index deploys SHALL run readiness checks plus query-path smoke tests.
6. Documentation SHALL record the active corpus version and source refresh date.

### Requirement 14: Security, Privacy, And Secret Safety

**User story:** As a maintainer, I want secret-safe operations and privacy-aware logs, so that compliance work does not leak credentials or sensitive user scenarios.

Acceptance criteria:

1. Prompts, logs, docs, and summaries SHALL not expose real API keys or key-shaped examples.
2. User scenarios stored for audit SHALL avoid unnecessary personal data.
3. Provider errors SHALL be mapped to safe user-facing messages.
4. Hidden reasoning and model chain-of-thought SHALL not be logged or returned.
5. API access controls and rate limits SHALL be enabled for production-like deployments.

### Requirement 15: Roadmap Governance

**User story:** As a project manager, I want planning milestones to match the actual implementation state, so that the team does not rebuild solved layers or skip safety gates.

Acceptance criteria:

1. Historical L0-L4 files SHALL be treated as implementation history unless directly updated.
2. The active near-term gate SHALL remain L5 release readiness: quality, citation trust, runtime dependency checks, deployment smoke, and documentation hygiene.
3. The post-L5 direction SHALL be source-governed semantic understanding and rules-first assessment, not generic "more AI."
4. L6 SHALL not be called complete until source acquisition, catalog, concept map, routing, rules, gold cases, red-line refusals, and human-review criteria are implemented and tested.
5. Planning docs SHALL be updated when the implementation reality changes.

### Requirement 16: Admin Curation And Feedback Loop

**User story:** As a reviewer or maintainer, I want expert feedback and source corrections to be captured in a governed workflow, so that Mushir improves without silently changing authority rules.

Acceptance criteria:

1. The system SHALL capture user or reviewer feedback separately from hidden reasoning or provider traces.
2. Feedback records SHALL link to answer ID, citation IDs, retrieval run ID, source records, language, and reviewer status where available.
3. Admin review SHALL support marking a response as correct, partially correct, unsupported, wrong standard, stale source, translation issue, unsafe answer, or needs scholar review.
4. Corrections SHALL NOT automatically alter source catalog records, concept maps, or answer policy without review.
5. Accepted corrections SHOULD generate or update evaluation cases.
6. Feedback and admin activity SHALL be auditable.
7. Any future fine-tuning, retrieval tuning, or rule update based on feedback SHALL preserve source provenance and release gates.

### Requirement 17: Egypt Financial Institutions Evidence Corpus

**User story:** As a Sharia reviewer and product maintainer, I want a public-source corpus of Egyptian financial institutions, operations, and contracts, so that Mushir can be evaluated against real market documents without guessing or issuing binding rulings.

Acceptance criteria:

1. The system SHALL treat the Egyptian financial institutions refresh document, workbook, and presentation as baseline inputs that require live regulator revalidation before production use.
2. The institution registry SHALL include CBE banks, CBE payment-service sources, capital-market institutions, insurance and takaful entities, mortgage finance, leasing, consumer finance, microfinance/SME finance, fintech licensees, Islamic funds, sukuk sources, and FRA model-contract sources.
3. Every institution row SHALL preserve regulator category, registry source, discovery status, official website confidence, attempt count, last checked timestamp, and explicit gap reason when details are missing.
4. Official-source discovery SHALL be bounded by configured attempt budgets and SHALL mark gaps rather than continuing until an inferred or hallucinated source appears.
5. Third-party search results MAY support discovery but SHALL NOT become compliance evidence unless confirmed by official regulator, institution, exchange, depository, prospectus, annual-report, or other official public material.
6. The crawler SHALL respect robots.txt, site terms, rate limits, login walls, CAPTCHA, paywalls, and access controls; blocked or gated material SHALL be recorded as a status, not bypassed.
7. Public artifacts SHALL preserve URL, institution ID, source authority rank, document type, language, retrieval timestamp, HTTP status, content hash, raw path, text extraction status, and citation-anchor strategy.
8. Contract-level and economic-substance documents SHALL be prioritized over marketing pages, including tariffs, fees, terms, contracts, model contracts, prospectuses, annual reports, sukuk documents, fund documents, policy wordings, and regulator rulebooks.
9. Operation records SHALL capture evidence spans for fees, payment terms, late-payment clauses, penalty beneficiaries, collateral, guarantees, insurance/takaful linkage, ownership or asset flow, and Sharia claims where public evidence exists.
10. Missing contracts or unavailable terms SHALL be represented as `not_publicly_available`, `document_not_public`, or `insufficient_public_data`; they SHALL NOT be inferred from unrelated pages.
11. Engine-produced AAOIFI mappings and compliance-risk labels SHALL be stored as `machine_proposed` review candidates until a qualified Sharia scholar reviews them.
12. Scholar-review records SHALL capture reviewer decision, cited AAOIFI references, rationale, uncertainty flags, correction type, and whether the item becomes an accepted gold case.
13. Future answers using institution pre-knowledge SHALL treat user-supplied details as higher priority than stored public corpus assumptions and SHALL flag stale, conflicting, or incomplete institutional evidence.

## Success Criteria

Mushir is ready to expand beyond the current demo only when all of these are true:

- The source catalog can identify the official origin, language, family, currentness, and supersession status of every answer-supporting chunk.
- The first-release FAS router and supersession seeds have been verified against cataloged AAOIFI source records.
- Bilingual and mixed-language retrieval returns the correct source family and expected standard candidates for the gold set.
- Ambiguous scenarios ask one useful clarification question instead of guessing.
- Accounting and Shariah-permissibility boundaries are enforced.
- Citation validation blocks unsupported claims.
- Feedback and reviewer corrections can be captured without bypassing governance.
- Live deployment checks prove `/health`, `/ready`, and query-path behavior.
- Bulk evaluation avoids overloading constrained provider routes.
