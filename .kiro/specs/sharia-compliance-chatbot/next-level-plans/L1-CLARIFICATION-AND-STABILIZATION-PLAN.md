# L1 Core Answer Contract and Stabilization Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Every implementation step starts with a failing or updated test.

**Goal:** Make the existing CLI RAG app reliable, testable, and grounded before adding API or production infrastructure.

**Architecture:** Preserve the working L0 CLI behavior while extracting a shared application service: `CLI -> ApplicationService -> RAGPipeline`. Keep ChromaDB, sentence-transformers, and Gemini 1.5 Pro as the default local stack. Add simple interfaces for retrieval, prompt building, Gemini calls, citation validation, and clarification so later CLI/API/SSE paths reuse the same core.

**Tech Stack:** Python, ChromaDB, sentence-transformers, google-generativeai, pytest, pytest-mock, pydantic or dataclasses, standard `logging`. Add LangGraph only behind the clarification interface if the clarification flow needs resumable branching; do not let LangGraph leak into CLI or API code.

---

## Product Contract

L1 must define the answer shape before any new transport work:

- `answer`: concise grounded answer.
- `status`: `COMPLIANT`, `NON_COMPLIANT`, `PARTIALLY_COMPLIANT`, `INSUFFICIENT_DATA`, or `CLARIFICATION_NEEDED`.
- `citations`: retrieved AAOIFI sources used by the answer.
- `reasoning_summary`: short explanation tied to citations.
- `limitations`: concise disclaimer that this is informational guidance, not a binding Sharia ruling.
- `clarification_question`: present only when missing facts materially block a grounded answer.
- `metadata`: model name, prompt version, corpus version if available, retrieved chunk IDs, and confidence.

Clarification is not the default user experience. Ask only when missing facts affect the ruling, such as contract type, parties, payment structure, penalty terms, ownership transfer, risk transfer, or asset description.

---

## Test Rules

- Use `python -m pytest`, never bare `pytest`, in all docs and scripts.
- Default tests must not load embedding models, call Gemini, access the network, or require containers.
- External services are mocked or faked in unit and service tests.
- Real ChromaDB/Gemini/Qdrant/Redis/Postgres checks are explicitly marked.
- Add `pytest.ini` or equivalent:

```ini
[pytest]
markers =
    unit: fast isolated tests with no network/model/container dependencies
    service: tests using fakes/mocks across app services
    api: FastAPI endpoint and SSE tests
    integration: requires external services such as ChromaDB, Qdrant, Redis, PostgreSQL
    eval: Ragas/DeepEval quality checks
    slow: long-running tests excluded from default development runs
    smoke: minimal confidence checks for CI and deployment
```

Default developer command:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "unit or service"
```

---

## Task 1: Repair Baseline

**Files:**
- Modify: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `pytest.ini`
- Modify: `src/models/ruling.py`
- Modify: `src/models/__init__.py`
- Test: `tests/test_models.py`

- [ ] Add dev dependencies: `pytest`, `pytest-mock`, and `pytest-timeout`.
- [ ] Add runtime dependencies only if used in L1. Do not add `fastapi`, `openai`, `python-statemachine`, `bleach`, Redis, Qdrant, or Postgres dependencies in L1.
- [ ] Fix `src/models/ruling.py`: import `Any`; rename `AAOIFICiation` to `AAOIFICitation`; keep empty citations valid only for `INSUFFICIENT_DATA` or `CLARIFICATION_NEEDED`.
- [ ] Add a regression test that evaluates `ComplianceRuling.__annotations__`.
- [ ] Export canonical L1 models from `src/models/__init__.py` while keeping `src.models.schema` available for L0 callers.
- [ ] Quarantine incomplete API/WebSocket modules so they do not break L1 imports.
- [ ] Run: `.\.venv\Scripts\python.exe -m compileall -q src tests`
- [ ] Run: `.\.venv\Scripts\python.exe -m pytest tests/test_models.py -m unit -q`

Acceptance:
- Project imports without runtime annotation errors.
- L0 CLI imports still work.
- No L1 test imports instantiate sentence-transformers, ChromaDB, or Gemini at import time.

---

## Task 2: Define Core Contracts

**Files:**
- Create: `src/chatbot/application_service.py`
- Create: `src/chatbot/contracts.py`
- Modify: `src/rag/pipeline.py`
- Test: `tests/test_application_service.py`

- [ ] Define small protocols or interfaces for:
  - `Retriever`
  - `Embedder`
  - `LLMClient`
  - `PromptBuilder`
  - `ClarificationService`
  - `CitationValidator`
  - `SessionStore`
- [ ] Add `ApplicationService.answer(query, session_id=None)` that returns the L1 answer contract.
- [ ] Keep concrete Chroma, sentence-transformers, and Gemini factories outside the pure business flow.
- [ ] Add fake implementations in tests.
- [ ] Run: `.\.venv\Scripts\python.exe -m pytest tests/test_application_service.py -m service -q`

Acceptance:
- CLI, future API, and future SSE can all call the same `ApplicationService`.
- Tests can drive the application service with fake retriever and fake LLM.

---

## Task 3: Make RAGPipeline Injectable

**Files:**
- Modify: `src/rag/pipeline.py`
- Test: `tests/test_rag_pipeline.py`

- [ ] Update `RAGPipeline.__init__` to accept optional injected `vector_store` and `embedding_generator`.
- [ ] Preserve current zero-argument CLI behavior with Chroma collection `aaoifi`.
- [ ] Add `augment_prompt(query, chunks)` or move prompt assembly fully to `PromptBuilder`; choose one path and make tests match it.
- [ ] Normalize retrieval output into one canonical chunk/citation shape at the boundary.
- [ ] Mark real Chroma retrieval tests as `integration` or `smoke`.
- [ ] Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_pipeline.py -m "unit or service" -q`

Acceptance:
- Mocked RAG tests run under 5 seconds.
- Heavy model/database tests do not run by default.

---

## Task 4: Extract Prompt Builder and Gemini Client

**Files:**
- Create: `src/chatbot/prompt_builder.py`
- Modify: `src/chatbot/llm_client.py`
- Modify: `src/chatbot/cli.py`
- Test: `tests/test_prompt_builder.py`
- Test: `tests/test_llm_client.py`

- [ ] Move the AAOIFI grounding prompt and chunk formatting into `PromptBuilder`.
- [ ] Create `GeminiClient` using `google-generativeai`; keep model `gemini-1.5-pro` and temperature `0.1` as defaults.
- [ ] Add retries, timeout handling, missing API key errors, quota/rate-limit errors, and empty-response handling.
- [ ] Tests must mock the Gemini transport and must not require `GEMINI_API_KEY`.
- [ ] Add one skipped/marked `llm` smoke test for real Gemini only when a key is present.
- [ ] Run: `.\.venv\Scripts\python.exe -m pytest tests/test_prompt_builder.py tests/test_llm_client.py -m unit -q`

Acceptance:
- Prompt rendering is deterministic.
- CLI calls Gemini only through `GeminiClient`.

---

## Task 5: Add Minimal Clarification Service

**Files:**
- Modify: `src/chatbot/clarification_engine.py`
- Modify: `src/models/session.py`
- Test: `tests/test_clarification_engine.py`

- [ ] Replace hardcoded operation templates with `ClarificationService`.
- [ ] Use an injected classifier that can be Gemini-backed in production and fake-backed in tests.
- [ ] Keep max clarification turns at 2.
- [ ] Merge user follow-up facts into current session context.
- [ ] Return `CLARIFICATION_NEEDED` only when missing facts block a grounded answer.
- [ ] Keep LangGraph optional behind the service boundary. If used, follow current LangGraph patterns for graph state, thread ID config, and in-memory checkpointer.
- [ ] Run: `.\.venv\Scripts\python.exe -m pytest tests/test_clarification_engine.py tests/test_session.py -m "unit or service" -q`

Acceptance:
- Clear query proceeds to retrieval.
- Ambiguous query asks one relevant clarification.
- Follow-up can make the session ready.
- Repeated vague answers exit within two turns.

---

## Task 6: Wire CLI Through ApplicationService

**Files:**
- Modify: `src/chatbot/cli.py`
- Modify: `src/chatbot/session_manager.py`
- Test: `tests/test_cli_flow.py`

- [ ] Preserve: `python -m src.chatbot.cli --query "..."`
- [ ] Add optional: `python -m src.chatbot.cli --interactive`
- [ ] Make CLI depend on `ApplicationService`, not ChromaDB, Gemini, prompt templates, or clarification internals.
- [ ] Add friendly user errors for missing corpus, missing Chroma collection, missing API key, retrieval failure, and LLM failure.
- [ ] Test CLI with mocked app service and captured stdin/stdout.
- [ ] Run: `.\.venv\Scripts\python.exe -m pytest tests/test_cli_flow.py -m service -q`

Acceptance:
- Single-query L0 command still works.
- Interactive mode supports clarification and best-effort insufficient-data responses.

---

## L1 Verification Gate

- [ ] `.\.venv\Scripts\python.exe -m compileall -q src tests`
- [ ] `.\.venv\Scripts\python.exe -m pytest -m "unit or service" --timeout=60`
- [ ] `.\.venv\Scripts\python.exe -m pytest -m smoke tests/test_rag_smoke.py::test_retrieval_smoke -q` only after Chroma is populated.
- [ ] Manual CLI smoke query with existing `.env`.

L1 is done when:
- Core answer contract exists and is tested.
- Every default test uses fakes or mocks.
- Gemini is behind a client abstraction.
- Prompt construction is centralized.
- Clarification is service-level and limited.
- L0 CLI behavior is preserved.

