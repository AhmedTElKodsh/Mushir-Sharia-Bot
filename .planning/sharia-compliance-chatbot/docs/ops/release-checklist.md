# Mushir Release Checklist

Use this checklist before exposing Mushir outside local development.

## Pre-Launch Gates

- Fast gate passes:
  `.\.venv\Scripts\python.exe -m pytest -m "unit or service or api" --timeout=60 -q`
- Integration gate passes with only expected external-service skips:
  `.\.venv\Scripts\python.exe -m pytest -m integration -q`
- Multilingual RAG gate passes:
  `$env:CHROMA_DIR=".\chroma_db_multilingual"; $env:EMBED_MODEL="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"; .\.venv\Scripts\python.exe scripts\evaluate_rag.py --gold tests\fixtures\gold_eval.yaml --min-hit-at-k 0.70 --min-recall-at-k 0.70 --min-mrr 0.30 --min-answerable-cases 3 --max-unanswerable-retrieval-rate 1.00`
- Browser smoke passes at `/chat` for English, Arabic, and refusal/error states.
- Docker image builds and serves `/health` and `/ready`.

## Required Runtime Configuration

- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL=openrouter/free` for demo or an explicit paid model for production
- `OPENROUTER_MAX_TOKENS=1024`
- `VECTOR_DB_TYPE=chroma`
- `CHROMA_DIR=/app/chroma_db_multilingual`
- `EMBED_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
- `REQUIRE_ARABIC_RETRIEVAL=true`
- `CORS_ORIGINS` set to the real public origin before production.

Do not run large live generation batches against `openrouter/free`. Use fake LLM fixtures, retrieval-only checks, and `RAG_EVAL_MODE=true` for matrix evaluation; reserve live OpenRouter calls for small smoke checks with backoff.

## Post-Deploy Smoke

- `GET /health` returns `healthy`.
- `GET /ready` returns `ready`.
- `GET /api/v1/compliance/disclaimer` returns `l5-bilingual-disclaimer-v1`.
- `/chat` loads in a browser.
- English and Arabic questions render without mojibake.
- Unanswerable or provider-failure paths show safe controlled messages.

## Rollback

- Keep the previous working image or commit available.
- Revert DNS/reverse-proxy traffic to the previous image if `/health`, `/ready`, or `/chat` fails.
- Do not disable citation validation or Arabic retrieval validation to force a deploy through.
