# L5 Production Readiness Runbook

This runbook defines the demo/release checks for the implemented Mushir runtime.

Last refreshed: 2026-06-01. Current app version: V1.5 (`1.5.0`). Current local verification baseline: full pytest suite `619 passed, 48 skipped, 2 warnings`; critical goldset `19 passed, 19 skipped`; evaluation suite `96 passed, 44 skipped`. V1.5 targeted verification covered the versioning/static/API and L6 institution evidence slices.

## Runtime Modes

| Concern | Local/default mode | Production target | Fallback behavior |
| --- | --- | --- | --- |
| Vector store | `VECTOR_DB_TYPE=chroma`, `CHROMA_DIR=./chroma_db_multilingual` | `VECTOR_DB_TYPE=qdrant`, `QDRANT_URL`, `QDRANT_COLLECTION` | Chroma remains valid for local/demo fallback when Qdrant is not selected, but it must be built with the configured multilingual embedding model. |
| Sessions | `SESSION_STORE_TYPE=memory` | `SESSION_STORE_TYPE=redis`, `REDIS_URL` | App falls back to in-memory sessions if Redis setup fails. |
| Rate limiting | `RATE_LIMIT_STORE_TYPE=memory` | `RATE_LIMIT_STORE_TYPE=redis`, `REDIS_URL` | App falls back to in-memory rate limiting if Redis setup fails. |
| Audit | `NullAuditStore` | `AUDIT_DATABASE_URL` or `DATABASE_URL` | App falls back to null audit logging if PostgreSQL setup fails. |
| Cache | `CACHE_STORE_TYPE=memory` | `CACHE_STORE_TYPE=redis`, `REDIS_URL` | App falls back to in-memory cache if Redis setup fails. |
| LLM | `OPENROUTER_API_KEY`, `OPENROUTER_MODEL=openrouter/free`, `OPENROUTER_MAX_TOKENS=1024` | Explicit OpenRouter model with known quota/latency | Missing OpenRouter key fails when generation is first needed. Free routes must be used conservatively. |
| Arabic answers and retrieval | Automatic Arabic query detection, `l1-aaoifi-grounded-bilingual-v1` prompt, `./chroma_db_multilingual` | Same model/index contract, or equivalent Qdrant collection | Arabic user questions receive Arabic safety/disclaimer language and are evaluated against Arabic retrieval rows. |
| App version | `APP_VERSION=1.5.0`, label `V1.5` | Same version must appear in API metadata, `/health`, `/ready`, package metadata, and visible UI | Release smoke should fail if visible/API version surfaces diverge. |

## Required Environment Variables

For a live answer-generating demo:

- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`
- `OPENROUTER_MAX_TOKENS`
- `CORPUS_DIR`
- `EMBED_MODEL`
- `CORS_ORIGINS` with explicit demo/release origins, not `["*"]`

For OpenRouter free-model use:

- Keep `OPENROUTER_MODEL=openrouter/free` only for demos, smoke tests, and constrained experiments.
- Do not run bulk live generation matrices against free routes.
- Prefer fake LLM fixtures, retrieval-only probes, and `RAG_EVAL_MODE=true` for evaluation loops.
- Use low concurrency, backoff, and small spaced-out smoke calls to avoid overloading shared free API nodes.

For Arabic support:

- `EMBED_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2`.
- `CHROMA_DIR=./chroma_db_multilingual`.
- The answer layer detects Arabic queries and sets `metadata.response_language=ar`.
- The prompt version is `l1-aaoifi-grounded-bilingual-v1`.
- The disclaimer endpoint exposes `l5-bilingual-disclaimer-v1` with Arabic text.
- `REQUIRE_ARABIC_RETRIEVAL=true` by default. A legacy English-only, model-mismatched, or non-normalized Chroma index must fail startup instead of silently serving Arabic queries with the wrong embedding space.
- The current multilingual Chroma index was built from both English and Arabic corpus files with normalized embeddings and cosine distance.
- Arabic retrieval quality is claimed only when the Arabic answerable eval rows pass the retrieval gate below.

For Qdrant-backed retrieval:

- `VECTOR_DB_TYPE=qdrant`
- `QDRANT_URL` or `QDRANT_LOCATION`
- `QDRANT_COLLECTION`
- `QDRANT_VECTOR_SIZE`

For Redis-backed runtime behavior:

- `REDIS_URL`
- `SESSION_STORE_TYPE=redis`
- `RATE_LIMIT_STORE_TYPE=redis`
- `CACHE_STORE_TYPE=redis`

For PostgreSQL audit logging:

- `AUDIT_DATABASE_URL` or `DATABASE_URL`

For integration tests:

- `MUSHIR_TEST_REDIS_URL`
- `MUSHIR_TEST_DATABASE_URL`
- `MUSHIR_TEST_QDRANT_URL`

## Verification Commands

Fast development gate:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "unit or service or api" --timeout=60 -q
```

Retrieval quality gate:

```powershell
.\.venv\Scripts\python.exe scripts\ingest.py --reset --languages en,ar
$env:CHROMA_DIR=".\chroma_db_multilingual"; $env:EMBED_MODEL="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"; .\.venv\Scripts\python.exe scripts\evaluate_rag.py --gold tests\fixtures\gold_eval.yaml --min-hit-at-k 0.70 --min-recall-at-k 0.70 --min-mrr 0.30 --min-answerable-cases 3 --max-unanswerable-retrieval-rate 1.00
```

External adapter gate:

```powershell
.\.venv\Scripts\python.exe -m pytest -m integration -q
```

Critical Sharia evaluation gate:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\evaluation\test_critical_goldset.py -q --timeout=90
.\.venv\Scripts\python.exe -m pytest tests\evaluation -q --timeout=90
```

Full local regression gate:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --timeout=90
```

API smoke gate:

```powershell
curl.exe http://127.0.0.1:8000/health
curl.exe http://127.0.0.1:8000/ready
curl.exe -X POST http://127.0.0.1:8000/api/v1/query -H "Content-Type: application/json" -d "{\"query\":\"Can Mushir give a binding fatwa?\"}"
curl.exe -X POST http://127.0.0.1:8000/api/v1/query/stream -H "Content-Type: application/json" -d "{\"query\":\"Can Mushir give a binding fatwa?\"}"
```

Browser gate:

- Open `http://127.0.0.1:8000/chat`.
- Verify first-turn response, second-turn context, bad query handling, stream completion, citation display, and error state.

## Operational Expectations

- `/ready` must report selected infrastructure modes.
- `/metrics` must expose request counts and latency buckets without secrets.
- Audit records must include request/session IDs, status, citations, and metadata, but never API keys or raw credentials.
- Response caching must only cache validated non-clarification answers.
- `RAG_EVAL_MODE=true` must bypass response cache for quality evaluation.
- Provider, retrieval, and integration failures must return controlled API/SSE error envelopes.
- Arabic support must remain visible in fast tests and gold eval rows, not only in manual UI testing.
- GC-001 and the hard-case routing matrix must remain green before demo/release: construction delay penalties clarify the delaying party, use `SS-05`/`SS-11`, and do not reintroduce `SS-10` unless Salam is implicated.
- Evaluation mocks must preserve the production boundary by returning text into `ApplicationService`; structured fixture dicts are for assertions only.
