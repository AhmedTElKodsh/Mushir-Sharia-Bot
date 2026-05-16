# Mushir Project Documentation

Mushir is a FastAPI-based Sharia compliance chatbot for Islamic finance questions. It uses retrieval-augmented generation (RAG) over AAOIFI Financial Accounting Standards excerpts, then validates that generated answers are grounded in retrieved citations.

This document describes the current project as implemented in the repository.

## Goals

Mushir is built to:

- answer Islamic finance compliance questions using AAOIFI FAS excerpts;
- support English, Arabic, and mixed-language questions;
- ask one focused clarification question when important facts are missing;
- cite retrieved AAOIFI standards in grounded answers;
- refuse binding rulings, fatwas, legal opinions, and financial advice;
- fail closed when retrieval, citations, or provider responses are not reliable;
- expose the behavior through a browser chat UI, REST API, and SSE streaming API.

## Non-Goals

Mushir must not:

- replace a qualified Sharia scholar;
- issue binding religious rulings;
- answer from the model's general training data;
- invent AAOIFI standard numbers, pages, sections, or citations;
- expose hidden reasoning or provider stack traces;
- leak API keys or credentials in docs, logs, errors, or responses.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `src/api/` | FastAPI app, routes, schemas, rate limiting, API error handling |
| `src/chatbot/` | Main answer service, prompt builder, LLM client, citation validator, clarification engine |
| `src/rag/` | Embeddings, query preprocessing, Chroma/Qdrant retrieval, chunking |
| `src/models/` | Shared data models and answer contracts |
| `src/storage/` | Cache and audit-store implementations |
| `src/static/` | Browser chat UI |
| `scripts/` | Corpus conversion, ingestion, evaluation, deployment, smoke checks |
| `tests/` | Unit, service, API, integration, smoke, and readiness tests |
| `docs/` | Current technical, operations, and stakeholder documentation |
| `.kiro/specs/` | Historical planning files and active readiness plans |
| `gemini-gem-prototype/knowledge-base/` | AAOIFI markdown corpus used for ingestion |

## Main Runtime Flow

The current answer path is:

```text
User or API client
  -> FastAPI route validation and rate limiting
  -> ApplicationService
  -> disclaimer and authority checks
  -> clarification check
  -> RAG retrieval
  -> prompt construction
  -> OpenRouter LLM call
  -> citation validation
  -> status classification
  -> audit/cache handling
  -> API or chat UI response
```

## API Layer

The FastAPI app is created in `src/api/main.py`.

It provides:

- `GET /`: browser chat page;
- `GET /chat`: browser chat page;
- `GET /api`: API metadata;
- `GET /health`: basic liveness check;
- `GET /ready`: runtime readiness check;
- `GET /metrics`: plain-text app metrics;
- `POST /api/v1/query`: normal JSON answer endpoint;
- `POST /api/v1/query/stream`: Server-Sent Events stream endpoint;
- `POST /api/v1/sessions`: create a session;
- `GET /api/v1/sessions/{session_id}/history`: retrieve session history;
- `GET /api/v1/compliance/disclaimer`: disclaimer text and translations.

The app also adds:

- request IDs through `X-Request-ID`;
- safe validation errors;
- content security headers;
- CORS configuration from `CORS_ORIGINS`;
- a shared startup-built retriever when available.

## Request Validation And Error Handling

`src/api/routes.py` handles:

- rate limiting before expensive validation or generation;
- query validation through `InputValidator`;
- safe provider error messages for configuration, rate limits, and unusable model responses;
- SSE event envelopes for `started`, `retrieval`, `token`, `citation`, `done`, and `error`.

User-facing errors should explain the cause enough to be useful without exposing internals.

## Answer Contract

The response contract is defined by:

- `src/models/ruling.py`
- `src/api/schemas.py`

Each answer includes:

- `answer`;
- `status`;
- `citations`;
- `reasoning_summary`;
- `limitations`;
- `clarification_question`;
- `metadata`.

Grounded answers require citations. Clarification responses require exactly one concise question. This prevents the bot from giving unsupported answers or overwhelming users with long question lists.

## Application Service

`src/chatbot/application_service.py` is the main orchestrator.

It performs:

1. Empty-query handling.
2. English/Arabic query normalization.
3. Language detection.
4. Optional disclaimer acknowledgement enforcement.
5. Authority-request refusal for binding fatwa/legal/financial advice.
6. Response cache lookup.
7. Clarification check.
8. Retriever initialization fallback.
9. RAG retrieval.
10. Prompt building.
11. LLM generation.
12. Citation validation.
13. LLM uncertainty conversion into one follow-up question.
14. Compliance status derivation.
15. Audit logging.
16. Safe response caching.

The service returns `INSUFFICIENT_DATA` when the evidence path is not strong enough.

## Clarification Logic

`src/chatbot/clarification_engine.py` collects the minimum facts needed before retrieval.

It detects broad transaction categories such as:

- loan;
- investment;
- purchase;
- contract.

When important facts are missing, it asks one question at a time. For example, an unclear investment question first asks for the company or business activity. It avoids asking multiple questions in one response.

The app also checks LLM output after generation. If the model itself says more information is needed, the service converts that output into the same clean `CLARIFICATION_NEEDED` contract.

## Retrieval

`src/rag/pipeline.py` implements RAG retrieval.

Key behavior:

- uses a multilingual sentence-transformer embedding model by default;
- expands query terms for cross-language Arabic/English retrieval;
- validates that Chroma contains matching embedding metadata, normalized embeddings, and both Arabic and English rows when Arabic retrieval is required;
- supports Chroma locally and Qdrant as an optional production vector store;
- reranks candidates using similarity, lexical hits, and language preference;
- returns `SemanticChunk` objects with citation metadata.

Default retrieval settings:

- model: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`;
- Chroma directory: `./chroma_db_multilingual`;
- collection: `aaoifi`.

## Prompting

`src/chatbot/prompt_builder.py` builds strict prompts.

The prompt tells the model to:

- use only retrieved AAOIFI excerpts;
- avoid external knowledge;
- cite every compliance claim;
- ask exactly one follow-up question when facts are unclear;
- return `INSUFFICIENT_DATA` when excerpts are not enough;
- avoid hidden reasoning and chain-of-thought exposure;
- answer in English or Arabic depending on the detected language.

## LLM Provider

`src/chatbot/llm_client.py` uses an OpenAI-compatible client for OpenRouter.

Important settings:

- `OPENROUTER_API_KEY`;
- `OPENROUTER_MODEL`;
- `OPENROUTER_MAX_TOKENS`.

The client raises typed errors for missing configuration, rate limits, and unusable model responses. API routes map these to safe messages.

## Citation Validation

`src/chatbot/citation_validator.py` parses citations in generated answers and keeps only citations that match retrieved chunks.

Accepted answer statuses include:

- `COMPLIANT`;
- `NON_COMPLIANT`;
- `CONDITIONALLY_COMPLIANT`;
- `INSUFFICIENT_DATA`;
- `CLARIFICATION_NEEDED`.

If no valid citation supports a compliance answer, the system falls back to insufficient data.

## Browser Chat UI

The browser interface lives in `src/static/`.

It supports:

- chat input;
- disclaimer acknowledgement;
- request/session context;
- REST and streaming query paths;
- citation rendering;
- compliance labels;
- clarification display;
- helpful validation and provider error messages.

## Runtime Storage

Default local storage is intentionally simple:

- in-memory sessions;
- in-memory rate limiter;
- in-memory response cache;
- null audit store;
- local Chroma vector index.

Production-like modes can use:

- Redis for sessions, rate limiting, and cache;
- PostgreSQL for audit logging;
- Qdrant for vector retrieval.

The app falls back to local runtime components when optional infrastructure is unavailable, but `/ready` reports the selected mode and degraded production readiness when required components are missing.

## Environment Configuration

Minimum live-answer configuration:

```env
OPENROUTER_API_KEY=your-openrouter-api-key-here
OPENROUTER_MODEL=openrouter/free
OPENROUTER_MAX_TOKENS=1024
EMBED_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2
VECTOR_DB_TYPE=chroma
CHROMA_DIR=./chroma_db_multilingual
CORPUS_DIR=./gemini-gem-prototype/knowledge-base
```

Important release settings:

```env
APP_ENV=production
CORS_ORIGINS=["https://your-approved-origin.example"]
AUTH_TOKEN=your-auth-token
AUDIT_DATABASE_URL=your-postgres-url
REQUIRE_ARABIC_RETRIEVAL=true
```

Do not commit real credentials.

## Setup

Create and activate the virtual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Create `.env` from `.env.example` and set provider credentials locally.

Build or refresh the vector index:

```powershell
.\.venv\Scripts\python.exe scripts\ingest.py --reset --languages en,ar
```

Run the app:

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/chat
```

## Testing

Full test suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --timeout=90
```

Fast gate:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "unit or service or api" -q --timeout=60
```

Retrieval quality gate:

```powershell
$env:CHROMA_DIR=".\chroma_db_multilingual"
$env:EMBED_MODEL="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
.\.venv\Scripts\python.exe scripts\evaluate_rag.py --gold tests\fixtures\gold_eval.yaml --min-hit-at-k 0.70 --min-recall-at-k 0.70 --min-mrr 0.30 --min-answerable-cases 3 --max-unanswerable-retrieval-rate 1.00
```

API smoke:

```powershell
curl.exe http://127.0.0.1:8000/health
curl.exe http://127.0.0.1:8000/ready
curl.exe -X POST http://127.0.0.1:8000/api/v1/query -H "Content-Type: application/json" -d "{\"query\":\"Can Mushir give a binding fatwa?\"}"
```

## Deployment

The Docker image runs:

```text
uvicorn src.api.main:app --host 0.0.0.0 --port 7860
```

The Dockerfile sets local defaults for:

- Chroma retrieval;
- multilingual embedding model;
- Arabic retrieval requirement;
- OpenRouter model;
- API port `7860`.

Hugging Face Spaces deployment uses Docker frontmatter in `README.md` and the deployment helper scripts under `scripts/`.

Before treating any deployment as live, verify:

- `/health`;
- `/ready`;
- `/chat`;
- one English answerable question;
- one Arabic answerable question;
- one unanswerable or out-of-scope question;
- no secrets in logs or responses.

## Operational Checks

Use `/ready` to confirm:

- vector store mode;
- retriever readiness;
- provider configuration;
- auth configuration;
- durable audit/session/cache/rate-limit mode.

Use `/metrics` to inspect request counts and latency buckets.

Production should be considered degraded if required production checks fail.

## Known Constraints

- Mushir covers AAOIFI FAS excerpts in the configured corpus. It does not automatically cover every AAOIFI standard family unless those documents are ingested.
- Strong answer quality depends on the corpus, embeddings, and retrieval threshold.
- Free-tier hosting can be memory constrained because sentence-transformer models are loaded at runtime.
- Binding Sharia decisions still require qualified human review.

## Maintenance Rules

- Keep `project-context.md` updated when architecture or safety rules change.
- Keep this document current when endpoints, runtime modes, or answer flow change.
- Add tests for every safety behavior change.
- Run the focused gate before the full suite during active development.
- Use placeholders in docs and examples.
- Re-run secret scans after handling real credentials or deployment incidents.
