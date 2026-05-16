# Mushir Project Context

This file is the working context for AI agents and developers making changes in this repository. Keep changes grounded in the current codebase, not in older roadmap language.

## Product Purpose

Mushir is a Sharia compliance assistant for Islamic finance questions. It answers only from retrieved AAOIFI Financial Accounting Standards excerpts and must not issue binding fatwas, legal opinions, or financial advice.

The product goal is a safe, citation-grounded chatbot that can:

- accept English, Arabic, and mixed-language questions;
- ask one focused follow-up question when facts are missing;
- retrieve relevant AAOIFI excerpts from a vector index;
- generate a concise answer with citations;
- refuse or return `INSUFFICIENT_DATA` when the source material is not enough;
- expose the same behavior through `/chat`, REST, and SSE APIs.

## Current Architecture

The main runtime flow is:

1. `src/api/main.py` creates the FastAPI app, middleware, health/readiness endpoints, metrics, static `/chat` UI, and `/api/v1` routes.
2. `src/api/routes.py` validates requests, applies rate limiting, maps errors to safe user-facing messages, and calls `ApplicationService`.
3. `src/chatbot/application_service.py` is the central answer orchestrator.
4. `src/chatbot/clarification_engine.py` asks a single targeted question when the user query is too vague.
5. `src/rag/pipeline.py` embeds and retrieves AAOIFI chunks from Chroma or Qdrant.
6. `src/chatbot/prompt_builder.py` builds strict AAOIFI-grounded prompts.
7. `src/chatbot/llm_client.py` calls OpenRouter through an OpenAI-compatible client.
8. `src/chatbot/citation_validator.py` accepts only citations backed by retrieved chunks.
9. `src/models/ruling.py` and `src/api/schemas.py` define the answer contract returned to API/UI callers.

## Safety Rules

- Never answer from general model knowledge when AAOIFI excerpts are missing.
- Never invent standard numbers, section numbers, pages, or citations.
- Never expose hidden reasoning, chain-of-thought, provider stack traces, API keys, or raw credentials.
- Never issue a binding Sharia ruling, fatwa, legal opinion, or financial advice.
- If the user asks for a binding ruling, refuse within Mushir's informational scope.
- If the question is unclear, ask exactly one focused follow-up question.
- If retrieval or citations are weak, fail closed with `INSUFFICIENT_DATA`.
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

## Documentation Map

- `README.md`: public project overview and setup.
- `docs/project-documentation.md`: current full technical documentation.
- `docs/client-plain-language-logic.md`: simple client-facing explanation.
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

