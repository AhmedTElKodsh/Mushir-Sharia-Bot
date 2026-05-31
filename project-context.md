# Mushir Project Context

This file is the working context for AI agents and developers making changes in this repository. Keep changes grounded in the current codebase, not in older roadmap language.

Last refreshed: 2026-05-31

## Product Purpose

Mushir is a source-governed AAOIFI standards assistant for Islamic finance questions. The current runtime answers only from retrieved AAOIFI corpus excerpts and must not issue binding fatwas, legal opinions, or financial advice.

The product goal is a safe, citation-grounded chatbot that can:

- accept English, Arabic, and mixed-language questions;
- ask one focused follow-up question when facts are missing;
- retrieve relevant AAOIFI excerpts from a vector index;
- generate a concise answer with citations;
- answer simple definition questions directly from citable retrieved excerpts when possible;
- refuse or return `INSUFFICIENT_DATA` when the source material is not enough;
- expose the same behavior through `/chat`, REST, and SSE APIs.

The post-L5 planning goal is broader but still non-binding: a rules-first Sharia commercial-process assessment assistant. The first runtime scaffold is present in `src/chatbot/commercial_assessment.py` and `src/models/commercial.py`: deterministic scenario extraction, source-family routing, targeted standard resolution, placeholder rule traces, source-family detection, and a fail-closed guard for late-payment/default permissibility questions when Shari'ah-standard evidence is absent. Do not present this as the full L6 evaluator until source acquisition, executable rules, and QA gates are complete.

As of 2026-05-31, the active hard-case routing fix treats the Arabic construction delay-penalty question (GC-001) as clarification-required until the delaying party is known. Construction / muqawala / istisna penalty routes must target `SS-05` plus `SS-11`; `SS-10` is Salam and is forbidden for this case unless Salam is actually implicated. The runtime also guards against an Arabic false-positive where `sarf` / currency routing matched inside `banking` wording such as organized banking tawarruq; organized tawarruq must still route to `SS-30`.

As of 2026-05-25, the hard-Sharia evidence target is source-tracked as at least 60 AAOIFI Shari'ah Standards: AAOIFI's complimentary-access announcement still states 59 Shari'ah standards, while a later AAOIFI announcement identifies Shari'ah Standard No. 60 on Waqf. Keep this mismatch visible in coverage reports and do not downgrade the target back to 59 without a fresh official-source review. The local governed catalog currently covers SS-01 through SS-54 from the official public English compendium plus SS-60 from AAOIFI's official Waqf PDF, and it retains Arabic source files for SS-02, SS-04, SS-09, SS-11, and SS-15. SS-55 through SS-59 remain missing until full official/licensed source text is acquired, and `hard_sharia_ready` must remain false until all target standards have governed source records plus retrieval, answerability, Arabic/English parity, and scholar-review gates.

The 2026-05-19 planning rethink reframes Mushir as a controlled standards workflow rather than a generic RAG bot. The intended architecture is source catalog -> structured ingestion -> bilingual concept normalization -> intent classification -> clarification -> source-family routing -> metadata-aware retrieval -> citation-gated answer -> evaluation. Downloaded markdown is derived content; source currentness, supersession, source family, and citation traceability must become answer-admissibility gates.

The spec-level `deep-research-report.md` was reviewed on 2026-05-19 and promoted into planning only where it creates useful contracts: first-release FAS router seed, supersession seed graph, parent/child chunking, source/retrieval/answer trace records, uncertainty classes, and feedback/admin review. Treat specific library/model/tool names from the report as spike candidates until they are measured against Mushir's AAOIFI gold set.

The 2026-05-20 Egypt financial institutions workstream is a public-source evidence-corpus plan for post-L5/L6 evaluation. It covers CBE banks, CBE payment-service sources, capital-market institutions, insurance and takaful entities, mortgage finance, leasing, consumer finance, microfinance/SME finance, fintech licensees, Islamic funds, sukuk sources, and FRA model contracts. Treat the refresh markdown, workbook, and presentation as baseline inputs only. Before broad scraping, revalidate entities against current regulator sources, use bounded discovery, respect access controls, record missing details explicitly, and keep machine-proposed AAOIFI labels separate from scholar-reviewed ground truth.

## Current Architecture

The main runtime flow is:

1. `src/api/main.py` creates the FastAPI app, middleware, health/readiness endpoints, metrics, static `/chat` UI, and `/api/v1` routes.
2. `src/api/routes.py` validates requests, applies rate limiting, maps errors to safe user-facing messages, and calls `ApplicationService`.
3. `src/chatbot/application_service.py` is the central answer orchestrator.
4. `src/chatbot/commercial_assessment.py` extracts transaction scenarios, missing facts, source-family routes, and first-wave rule-review metadata.
5. `src/chatbot/contract_family_router.py` maps user queries to specific financial contract families before retrieval.
6. `src/chatbot/clarification_engine.py` asks a single targeted question when the route or transaction facts are not safe enough for retrieval or answer generation.
7. `src/rag/standard_resolver.py` provides targeted standard resolution such as istisna penalty routing to `SS-05` and `SS-11`.
8. `src/rag/pipeline.py` embeds and retrieves AAOIFI chunks from Chroma or Qdrant; explicit BM25/RRF APIs now formalize sparse/dense merge behavior without replacing the existing hybrid stack.
9. Definition-style questions are answered from retrieved, citable excerpts before the LLM is called when the retrieved text directly defines the requested term.
10. `src/ontology/concept_router.py` and `ruling_evaluator.py` apply structured logic to map retrieved definitions into commercial rules.
11. `src/chatbot/prompt_builder.py` builds strict AAOIFI-grounded prompts.
12. `src/chatbot/llm_client.py` calls OpenRouter through an OpenAI-compatible client.
13. `src/chatbot/citation_validator.py` accepts only citations backed by retrieved chunks; evaluation mocks must return text into this boundary, not dicts.
14. `src/models/ruling.py` and `src/api/schemas.py` define the answer contract returned to API/UI callers.
15. `src/acquisition/egypt_financial/` contains the Data Acquisition layer (crawlers and extractors) for processing local regulatory data.
16. `tests/evaluation/` provides the Sharia Compliance Evaluation Framework using Gold Sets (GC-*), bilingual parity, scholar-review queue checks, and ECE metrics.
17. `tests/fixtures/hard_case_routing_matrix.yaml` and `tests/routing_matrix.py` are the canonical runtime-test support for launch-blocking hard-case routes such as istisna penalties and Salam/debt boundary cases.

## Safety Rules

- Never answer from general model knowledge when AAOIFI excerpts are missing.
- Never invent standard numbers, section numbers, pages, or citations.
- Never expose hidden reasoning, chain-of-thought, provider stack traces, API keys, or raw credentials.
- Never issue a binding Sharia ruling, fatwa, legal opinion, or financial advice.
- If the user asks for a binding ruling, refuse within Mushir's informational scope.
- If the question is unclear, ask exactly one focused follow-up question.
- If a construction penalty / muqawala / istisna question does not state whether the contractor or customer delayed, ask the focused party/cause clarification before retrieval or verdict.
- If retrieval or citations are weak, fail closed with `INSUFFICIENT_DATA`.
- Definition questions may return `INSUFFICIENT_DATA` with citations because a definition is not a transaction-level compliance ruling.
- Arabic citation support must stay validator-backed. Keep `[FAS-X]`, `[FAS-X Â§Y]`, and Arabic citation formats covered by tests.
- Cache only validated non-clarification answers.
- Keep docs secret-safe: use placeholders, not real keys or key-shaped examples.
- Keep research-derived router and supersession seeds reviewable and catalog-verified before treating them as authority.
- For Egypt institution scraping, do not infer official websites, contracts, or compliance status when public evidence is missing; record the bounded-search gap.
- Respect robots.txt, rate limits, login walls, CAPTCHA, paywalls, and access controls. Do not bypass security barriers to collect contracts or terms.
- Institution pre-knowledge is subordinate to user-supplied facts in future answers and must be flagged when stale, conflicting, or incomplete.

## Runtime Modes

Default local/demo mode:

- Vector store: Chroma, `CHROMA_DIR=./chroma_db_multilingual`
- Embeddings: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
- Sessions: in-memory `SessionManager`
- Rate limiting: in-memory `InMemoryRateLimiter`
- Audit: `NullAuditStore`
- Cache: in-memory cache
- LLM: OpenRouter model from `OPENROUTER_MODEL`

Production target mode:

- Explicit CORS origins
- `APP_ENV=production`
- durable audit database through `AUDIT_DATABASE_URL` or `DATABASE_URL`
- optional Redis for sessions, rate limiting, and cache
- optional Qdrant for vector storage
- configured `AUTH_TOKEN`
- configured `OPENROUTER_API_KEY`

## Hosting And Retrieval Payload Direction

- Keep Hugging Face Spaces as the public demo host for now. It is the intended lightweight demo/beta surface for `/chat`, `/health`, `/ready`, and live smoke checks.
- Do not treat a large Chroma upload failure as an automatic reason to leave Hugging Face. Treat it first as a deployment-shape problem: app/UI changes and retrieval-index changes should not be bundled together by default.
- Stop re-uploading `chroma_db_multilingual` unless the retrieval index actually changes. For UI-only changes, use `scripts/deploy_huggingface_space.py --ui-only`. For app/runtime changes that do not touch retrieval data, use `--skip-index`.
- Use the full deploy path only after rebuilding or changing the Chroma index, and verify the index through `/ready` plus a live query smoke before calling the bot ready.
- Long-term upgrade direction: move the retrieval payload out of routine Space commits into external artifact or vector storage. Good candidates are a versioned object/artifact store for index downloads, a managed vector database, or a deliberate Postgres/pgvector design. Do not use Supabase merely as a raw Chroma folder dump unless there is a clear operational reason.

## Important Environment Variables

- `OPENROUTER_API_KEY`: required for live answer generation.
- `OPENROUTER_MODEL`: default model name used through OpenRouter. Keep `openrouter/free` for the demo path unless there is a deliberate provider upgrade.
- `OPENROUTER_MAX_TOKENS`: max output tokens.
- `CORPUS_DIR`: AAOIFI markdown corpus location.
- `EMBED_MODEL`: embedding model. Keep multilingual for Arabic support.
- `CHROMA_DIR`: local Chroma index path.
- `VECTOR_DB_TYPE`: `chroma` or `qdrant`.
- `REQUIRE_ARABIC_RETRIEVAL`: defaults to true; do not silently serve Arabic with an English-only index.
- `REQUIRE_DISCLAIMER_ACK`: when true, API callers must pass `context.disclaimer_acknowledged=true`.
- `RAG_EVAL_MODE`: bypasses response cache for retrieval evaluation.
- `CORS_ORIGINS`: wildcard is local-only; release should use explicit origins.

Provider-use rule: OpenRouter free routing is a constrained shared API path. Do
not run bulk live generation matrices against it. Use fake LLM fixtures,
retrieval-only probes, and `RAG_EVAL_MODE=true` for evaluation loops; keep live
query smoke checks small, spaced out, and only after retrieval/clarification
behavior has been verified locally.

## Development Commands

Use the repo virtual environment on Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --timeout=90
```

Fast targeted gate:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "unit or service or api" -q --timeout=60
```

High-risk source-governance slice:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.tmp\pytest tests\test_l1_contracts.py tests\test_commercial_assessment.py tests\test_source_governance.py tests\test_ingest_bilingual.py tests\test_rag_pipeline.py tests\test_institution_pipeline.py tests\test_l6_institution_pilot_script.py tests\test_scholar_review.py tests\test_repo_layout.py
```

Rebuild multilingual Chroma index:

```powershell
.\.venv\Scripts\python.exe scripts\ingest.py --reset --languages en,ar --source-catalog path\to\aaoifi-source-catalog.yaml
```

Fresh source-governed ingests require `--source-catalog`. Use `--allow-uncataloged` only for explicit diagnostic indexes because those chunks are quarantined and cannot support answers.

Run API locally:

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Smoke endpoints:

```powershell
curl.exe http://127.0.0.1:8000/health
curl.exe http://127.0.0.1:8000/ready
```

Smoke bilingual answer behavior:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_l1_contracts.py::test_application_service_answers_arabic_definition_with_validator_backed_citation tests\test_l1_contracts.py::test_application_service_expands_definition_retrieval_before_llm tests\test_clarification_engine.py::test_arabic_definition_question_skips_transaction_clarification -q
```

Critical Sharia goldset and evaluation gate:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\evaluation\test_critical_goldset.py -q --timeout=90
.\.venv\Scripts\python.exe -m pytest tests\evaluation -q --timeout=90
```

Current broad verification snapshot from 2026-05-31:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --timeout=90
# 619 passed, 48 skipped, 2 warnings
```

Fixture-backed retrieval-only baseline:

```powershell
.\.venv\Scripts\python.exe scripts\run_retrieval_baseline.py
```

This command must not touch the live vector index or LLM provider. Use it before adopting retrieval/model candidates.

Shari'ah evidence coverage matrix:

```powershell
.\.venv\Scripts\python.exe scripts\report_sharia_corpus_coverage.py --catalog data\source_registry\aaoifi-source-catalog.yaml --output _bmad-output\implementation-artifacts\sharia-corpus-coverage-2026-05-25.json --matrix-output _bmad-output\implementation-artifacts\sharia-standards-coverage-matrix-2026-05-25.json
```

This command is the current hard-Sharia release gate: it reports `hard_sharia_ready=false` while any target standard is missing, lacks Arabic/English parity, lacks retrieval smoke evidence, lacks seeded representative questions, or lacks scholar-review evidence.

Accessible Shari'ah source extraction:

```powershell
.\.venv\Scripts\python.exe scripts\extract_aaoifi_sharia_compendium.py
.\.venv\Scripts\python.exe scripts\generate_aaoifi_source_catalog.py --corpus-dir gemini-gem-prototype\knowledge-base --output data\source_registry\aaoifi-source-catalog.yaml
```

The acquisition status and blockers for SS-55 through SS-59 are tracked in `data/source_registry/aaoifi-sharia-acquisition-manifest.yaml`.

Scholar-review persistence:

- Use `src.governance.ScholarReviewStore` for append-only JSONL review records tied to source IDs, citation IDs, reviewer identity, and optional rule metadata.
- Runtime queue plumbing supports Q1 auto-flagged, Q2 random-sample, and Q3 user-reported review items.
- `scripts/export_scholar_review.py` exports CSV by default and XLSX when `openpyxl` is available; `scripts/import_scholar_corrections.py` imports corrections, marks queue items reviewed, extends gold cases, and records pending ontology patches.
- Review records can seed gold-case work, but they do not automatically update runtime governance, source catalog, prompts, or rule policy.

## Documentation Map

- `README.md`: public project overview and setup.
- `.planning/STATE.md`: canonical planning router for the consolidated `.planning/sharia-compliance-chatbot/` tree.
- `.planning/sharia-compliance-chatbot/docs/index.md`: planning documentation index and best starting point while the public `docs/` tree is being cleaned.
- `.planning/sharia-compliance-chatbot/docs/project-documentation.md`: current full technical documentation.
- `.planning/sharia-compliance-chatbot/docs/ai-project-brief.md`: detailed AI-agent handoff with runtime contracts, data authority ladder, L5/L6 status, commands, and safe edit rules.
- `.planning/sharia-compliance-chatbot/docs/client-plain-language-logic.md`: client-facing report covering planning, implementation, current limits, L5 readiness, and L6 future direction.
- `.planning/sharia-compliance-chatbot/docs/client-source-governed-aaoifi-roadmap.md`: visual client-facing roadmap for the updated source-governed AAOIFI assistant logic.
- `.planning/sharia-compliance-chatbot/docs/chatbot-architecture.md`: detailed answer-generation architecture.
- `.planning/sharia-compliance-chatbot/docs/l5-production-readiness.md`: release/readiness runbook.
- `.planning/sharia-compliance-chatbot/docs/deep-research-report.md`: research input for the L6 rules-first evaluator direction.
- `.planning/sharia-compliance-chatbot/docs/requirements.md`: maintained source-governed requirements.
- `.planning/sharia-compliance-chatbot/docs/design.md`: maintained source-governed design.
- `.planning/sharia-compliance-chatbot/docs/tasks.md`: maintained implementation backlog for source-governed planning slices.
- `.planning/sharia-compliance-chatbot/next-level-plans/`: historical L1-L4 plans, active L5 roadmap, and proposed L6 direction.
- `.planning/sharia-compliance-chatbot/next-level-plans/L6-EGYPT-FINANCIAL-INSTITUTIONS-EVIDENCE-CORPUS-PLAN.md`: post-L5/L6 data-acquisition plan for public Egyptian institution operations, contracts, bounded discovery, ethical crawling, gap marking, and scholar-reviewed evaluation rows.
- `.planning/sharia-compliance-chatbot/docs/l6-egypt-institution-scrape/README.md`: project-facing guide to the planned Egypt institutions scrape workstream and folder boundaries.
- `data/source_registry/`: tracked source-category and regulator-source planning seeds for the Egypt institution corpus.
- `tests/fixtures/hard_case_routing_matrix.yaml`: canonical launch-blocking routing cases for runtime regression tests.
- `.planning/sharia-compliance-chatbot/docs/ops/deployment.md`: deployment operations.
- `.planning/sharia-compliance-chatbot/docs/ops/huggingface-spaces.md`: Hugging Face Spaces deployment notes.
- `.planning/sharia-compliance-chatbot/docs/PROJECT-LOGIC-RETHINK-2026-05-19.md`: current planning rethink and gap analysis.
- `_legacy/root-outline-docs/`: archived historical root markdown files from the L0, setup, deployment-status, and old report era.
- `_legacy/root-smoke-screenshots/`: archived historical root screenshots.
- `_legacy/browser-smoke/`: archived browser smoke screenshots and local smoke process evidence.
- `_legacy/runtime-logs/`: archived root `logs/` output from before runtime logs moved under `data/runtime/logs/`.
- `scripts/legacy/`: archived Windows batch wrappers moved out of the project root.

## Root Folder Policy

Keep these root folders because tools or runtime paths expect them:

- `src/`, `tests/`, `scripts/`, `config/`, `data/`, `e2e/`: active project source, tests, configuration, data seeds, and end-to-end checks.
- `.agents`, `.bob`, `.cline`, `.trae`, `.claude`, `.kiro`: agent/tool workspaces intentionally kept for compatibility.
- `_bmad/` and `_bmad-output/`: BMAD configuration and generated BMAD artifacts; current BMAD config writes to `_bmad-output/`.
- `gemini-gem-prototype/`: legacy name, active role. It contains the tracked AAOIFI markdown corpus used by `CORPUS_DIR=./gemini-gem-prototype/knowledge-base`.
- `chroma_db_multilingual/`: ignored local multilingual Chroma index used by the demo runtime.
- `chroma_db/`: ignored older/local Chroma index; keep until the active retrieval index history is fully reconciled.
- `.venv/` and `node_modules/`: local dependency installs, ignored by git.
- `superpowers/`, `.agent`, `.codex`, `.gsd`, `.planning`: local agent/planning/tooling context.

Do not keep generated smoke screenshots, historical reports, runtime logs, or ad hoc temp folders in the project root. Archive them under `_legacy/` or write new runtime output under `data/runtime/`.

## Editing Guidance

- Prefer small, behavior-focused changes.
- Preserve fail-closed behavior and citation validation.
- Keep tests updated with every behavior change.
- Do not rewrite historical planning docs unless explicitly asked; add current-state docs or clearly mark updates instead.
- Keep `.agents`, `.bob`, `.cline`, `.trae`, `.claude`, and `.kiro` in place; do not collapse those agent folders during cleanup.
- Keep new planning work inside `.planning/sharia-compliance-chatbot/` and use `.planning/STATE.md` as the routing file.
- Keep the project root limited to essential entry/config files. Archive historical reports, screenshots, and legacy wrappers under `_legacy/` or `scripts/legacy/`.
- Use `apply_patch` for manual file edits.
- Avoid broad refactors unless they directly reduce risk or remove duplicated logic already visible in the codebase.
