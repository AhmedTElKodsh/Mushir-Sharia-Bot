# L5 Quality, Operations, and Release Readiness Plan

**Status:** Active  
**Created:** 2026-05-11  
**Purpose:** Prove the implemented Mushir runtime is trustworthy enough for demo or release.

## Summary

L1-L4 are now the baseline runtime, not future work. The application has a shared answer service, REST/SSE API, browser chat surface, operational adapters, citation validation, disclaimer handling, Qdrant ingestion, and a seed retrieval evaluation harness.

L5 does not add major product features. It turns the current implementation into a measurable, demo-safe, dependency-aware system.

## Stable Public Interfaces

Treat these interfaces as stable during L5:

- `POST /api/v1/query`
- `POST /api/v1/query/stream`
- `GET /chat`
- `GET /health`
- `GET /ready`
- `GET /metrics`
- `GET /api/v1/compliance/disclaimer`

Changes to these interfaces must be backward compatible unless a test or documented contract is updated in the same change.

## Readiness Tracks

### 1. Plan Reconciliation

- Mark L1-L4 items as implemented, validated, or production-ready instead of leaving them as future work.
- Keep old phase plans as historical references.
- Use this L5 document as the active roadmap until demo/release gates are complete.

### 2. RAG Quality Gate

- Expand `tests/fixtures/gold_eval.yaml` beyond happy paths.
- Cover answerable, unanswerable, weak-citation, ambiguous, and Arabic/English queries.
- Make `scripts/evaluate_rag.py` enforce explicit thresholds for `hit_at_k`, `recall_at_k`, `mrr`, minimum answerable cases, and unanswerable retrieval rate.
- Emit threshold results in the JSON report so quality drift is visible.

### 2A. Arabic Support Version

- Detect Arabic user queries and carry `response_language=ar` in answer metadata.
- Use prompt version `l1-aaoifi-grounded-bilingual-v1` so Arabic responses are requested without changing AAOIFI citation tokens.
- Serve bilingual disclaimer version `l5-bilingual-disclaimer-v1`.
- Use `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` plus `./chroma_db_multilingual` for the default demo gate.
- Keep `REQUIRE_ARABIC_RETRIEVAL=true` so a legacy English-only, model-mismatched, or non-normalized Chroma index fails startup instead of silently serving Arabic queries from the wrong embedding space.
- Require the Arabic answerable eval row to pass retrieval thresholds before claiming Arabic retrieval quality.

### 3. Citation Trust Gate

- Grounded answers must cite retrieved chunks only.
- Unsupported citations must degrade to `INSUFFICIENT_DATA`.
- Citation excerpts and quote offsets must come from source chunk text.
- Cached answers must preserve validated citation metadata and must not bypass validation for new answers.

### 4. Runtime Integration Gate

- Keep the fast default gate free of network, Docker, model, and external service requirements.
- Add separately marked `integration` tests for Redis session/rate-limit/cache, PostgreSQL audit logging, and Qdrant ingest/query behavior.
- Integration tests may skip when required service URLs are absent, but their required environment variables must be documented.

### 5. End-to-End Demo Gate

- Browser-test `/chat` for first turn, second turn, bad query, stream completion, citation display, and error state.
- Smoke-test `/health`, `/ready`, `/api/v1/query`, and `/api/v1/query/stream`.
- Verify rate-limit and provider-error responses are understandable and stable.

### 6. Production Readiness

- Document required and optional environment variables.
- Define fallback behavior for Chroma/Qdrant, memory/Redis, null/PostgreSQL audit, and memory/Redis cache modes.
- Document setup, smoke, retrieval eval, integration, and browser verification commands.
- Ensure logs, metrics, cache, and audit records do not expose secrets or raw credentials.

## Verification Commands

Fast gate:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "unit or service or api" --timeout=60 -q
```

Retrieval gate:

```powershell
.\.venv\Scripts\python.exe scripts\ingest.py --reset --languages en,ar
$env:CHROMA_DIR=".\chroma_db_multilingual"; $env:EMBED_MODEL="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"; .\.venv\Scripts\python.exe scripts\evaluate_rag.py --gold tests\fixtures\gold_eval.yaml --min-hit-at-k 0.70 --min-recall-at-k 0.70 --min-mrr 0.30 --min-answerable-cases 3 --max-unanswerable-retrieval-rate 1.00
```

Integration gate:

```powershell
.\.venv\Scripts\python.exe -m pytest -m integration -q
```

## Completion Criteria

L5 is complete when:

- Planning docs no longer describe completed L1-L4 runtime work as missing.
- Retrieval eval has explicit thresholds and reports pass/fail status.
- Arabic answer support has prompt/disclaimer versions and fast-test coverage.
- Arabic semantic retrieval uses the multilingual index and passes the Arabic answerable eval row.
- Citation, cache, and weak-grounding behaviors are covered by fast tests.
- Redis/PostgreSQL/Qdrant runtime modes have separately marked integration coverage.
- `/chat` and stable public APIs pass documented smoke checks under the demo configuration.
- Production readiness commands and environment variables are documented.
