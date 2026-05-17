# Mushir Project Context

This file is the working context for AI agents and developers making changes in this repository. Keep changes grounded in the current codebase, not in older roadmap language.

Last refreshed: 2026-05-17

## Product Purpose

Mushir is a Sharia compliance assistant for Islamic finance questions. It answers only from retrieved AAOIFI Financial Accounting Standards excerpts and must not issue binding fatwas, legal opinions, or financial advice.

The product goal is a safe, citation-grounded chatbot that can:

- accept English, Arabic, and mixed-language questions;
- ask one focused follow-up question when facts are missing;
- retrieve relevant AAOIFI excerpts from a vector index;
- generate a concise answer with citations;
- answer simple definition questions directly from citable retrieved excerpts when possible;
- refuse or return `INSUFFICIENT_DATA` when the source material is not enough;
- expose the same behavior through `/chat`, REST, and SSE APIs.

## Current Architecture

The main runtime flow is:

1. `src/api/main.py` creates the FastAPI app, middleware, health/readiness endpoints, metrics, static `/chat` UI, and `/api/v1` routes.
2. `src/api/routes.py` validates requests, applies rate limiting, maps errors to safe user-facing messages, and calls `ApplicationService`.
3. `src/chatbot/application_service.py` is the central answer orchestrator.
4. `src/chatbot/clarification_engine.py` asks a single targeted question when the user query is too vague.
5. `src/rag/pipeline.py` embeds and retrieves AAOIFI chunks from Chroma or Qdrant.
6. Definition-style questions are answered from retrieved, citable excerpts before the LLM is called when the retrieved text directly defines the requested term.
7. `src/chatbot/prompt_builder.py` builds strict AAOIFI-grounded prompts.
8. `src/chatbot/llm_client.py` calls OpenRouter through an OpenAI-compatible client.
9. `src/chatbot/citation_validator.py` accepts only citations backed by retrieved chunks.
10. `src/models/ruling.py` and `src/api/schemas.py` define the answer contract returned to API/UI callers.

## Safety Rules

- Never answer from general model knowledge when AAOIFI excerpts are missing.
- Never invent standard numbers, section numbers, pages, or citations.
- Never expose hidden reasoning, chain-of-thought, provider stack traces, API keys, or raw credentials.
- Never issue a binding Sharia ruling, fatwa, legal opinion, or financial advice.
- If the user asks for a binding ruling, refuse within Mushir's informational scope.
- If the question is unclear, ask exactly one focused follow-up question.
- If retrieval or citations are weak, fail closed with `INSUFFICIENT_DATA`.
- Definition questions may return `INSUFFICIENT_DATA` with citations because a definition is not a transaction-level compliance ruling.
- Arabic citation support must stay validator-backed. Keep `[FAS-X]`, `[FAS-X §Y]`, and Arabic citation formats covered by tests.
- Cache only validated non-clarification answers.
- Keep docs secret-safe: use placeholders, not real keys or key-shaped examples.

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
- `OPENROUTER_MODEL`: default model name used through OpenRouter.
- `OPENROUTER_MAX_TOKENS`: max output tokens.
- `CORPUS_DIR`: AAOIFI markdown corpus location.
- `EMBED_MODEL`: embedding model. Keep multilingual for Arabic support.
- `CHROMA_DIR`: local Chroma index path.
- `VECTOR_DB_TYPE`: `chroma` or `qdrant`.
- `REQUIRE_ARABIC_RETRIEVAL`: defaults to true; do not silently serve Arabic with an English-only index.
- `REQUIRE_DISCLAIMER_ACK`: when true, API callers must pass `context.disclaimer_acknowledged=true`.
- `RAG_EVAL_MODE`: bypasses response cache for retrieval evaluation.
- `CORS_ORIGINS`: wildcard is local-only; release should use explicit origins.

## Development Commands

Use the repo virtual environment on Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --timeout=90
```

Fast targeted gate:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "unit or service or api" -q --timeout=60
```

Rebuild multilingual Chroma index:

```powershell
.\.venv\Scripts\python.exe scripts\ingest.py --reset --languages en,ar
```

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

## Documentation Map

- `README.md`: public project overview and setup.
- `docs/project-documentation.md`: current full technical documentation.
- `docs/client-plain-language-logic.md`: simple client-facing report with visuals and graphs.
- `docs/chatbot-architecture.md`: detailed answer-generation architecture.
- `docs/l5-production-readiness.md`: release/readiness runbook.
- `docs/ops/deployment.md`: deployment operations.
- `docs/ops/huggingface-spaces.md`: Hugging Face Spaces deployment notes.
- `.kiro/specs/sharia-compliance-chatbot/next-level-plans/`: historical L1-L4 plans and active L5 roadmap.

## Editing Guidance

- Prefer small, behavior-focused changes.
- Preserve fail-closed behavior and citation validation.
- Keep tests updated with every behavior change.
- Do not rewrite historical planning docs unless explicitly asked; add current-state docs or clearly mark updates instead.
- Use `apply_patch` for manual file edits.
- Avoid broad refactors unless they directly reduce risk or remove duplicated logic already visible in the codebase.
