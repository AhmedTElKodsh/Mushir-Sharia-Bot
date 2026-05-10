# L0 Implementation Review

**Date:** 2026-05-09

**Purpose:** Reconcile the planning files with the current repository state before starting L1-L4 work.

---

## Summary

The documented L0 RAG path exists and is still the stable baseline: CLI query, ChromaDB retrieval, Gemini generation, and simple citation display. However, the repository also contains partial L1/L2 prototype modules that are not reflected accurately in the planning summary and are not yet reliable enough to build on directly.

Treat L0 as complete only for the CLI RAG loop. Treat `src/chatbot/clarification_engine.py`, `src/chatbot/session_manager.py`, `src/chatbot/compliance_analyzer.py`, and `src/api/*` as prototype or draft code that must be stabilized during L1 before L2 starts.

---

## Verified Baseline

- `src/rag/pipeline.py` implements the active L0 retrieval path with `SentenceTransformer`, Chroma collection `aaoifi`, and `src.models.schema.SemanticChunk`.
- `src/chatbot/cli.py` implements the active CLI chatbot and calls Gemini 1.5 Pro directly through `google.generativeai`.
- `data/aaoifi_md/` contains sample markdown standards and `data/raw/aaoifi_standards/` contains downloaded raw PDFs.
- `chroma_db/` exists and contains a persisted Chroma database.
- `requirements.txt` matches the L0 stack: sentence-transformers, chromadb, langchain text splitters, google-generativeai, dotenv, pyyaml, pytest, numpy.

---

## Key Findings

1. **Planning docs overstate L0 cleanliness.**
   The docs say L0 has no API, no session management, no clarification, and no logging. The codebase does contain draft modules for these, but they are incomplete and should not be counted as delivered L1/L2 capability.

2. **The active RAG pipeline is not injectable yet.**
   `tests/test_rag_pipeline.py` expects `RAGPipeline(mock_vector_store, mock_embedding_gen)` and `augment_prompt()`, but `src/rag/pipeline.py` currently accepts `persist_dir` and `model_name`, loads the model immediately, and has no `augment_prompt()` method.

3. **Newer ruling model has a runtime annotation bug.**
   `src/models/ruling.py` references `AAOIFICiation` instead of `AAOIFICitation` and uses `Any` without importing it. Importing annotations for `ComplianceRuling` raises a `NameError`.

4. **API/session prototype loses state between requests.**
   `src/api/routes.py` creates a new `SessionManager()` inside each endpoint, so `/sessions/{id}/query` cannot retrieve sessions created by `/sessions`.

5. **L1/L2 dependencies are missing.**
   The environment and `requirements.txt` do not include `fastapi`, `openai`, `python-statemachine`, or `bleach`, while draft modules import them.

6. **L1 clarification currently conflicts with the planning intent.**
   The plan calls for LLM-driven clarification, preferably LangGraph. The current `ClarificationEngine` uses hardcoded operation types, hardcoded required variables, and `python-statemachine`.

7. **L2 scope drift exists.**
   The plan says SSE only and no WebSocket for L2, but `src/api/websocket.py` already introduces WebSocket handling. Park it until after SSE is complete and tested.

---

## Verification Notes

- `pytest -q` was unavailable from PATH.
- `.venv\Scripts\python.exe -m pytest -q` timed out after 120 seconds, likely due expensive collection or model/RAG initialization.
- `.venv\Scripts\python.exe -m compileall -q src tests` completed successfully, but this did not catch runtime annotation evaluation.
- Dependency probe showed `fastapi`, `openai`, `statemachine`, and `bleach` missing; `google.generativeai`, `chromadb`, and `sentence_transformers` present.
- Context7 was used for LangGraph documentation. Best match selected: `/websites/langchain_oss_python_langgraph`, high source reputation. Relevant current guidance: use `StateGraph`, checkpointers such as `MemorySaver`/`InMemorySaver`, `interrupt()`, `Command(resume=...)`, thread IDs, and streaming/resume patterns for human-in-the-loop flows.

---

## Planning Correction

Before implementing new product capabilities, L1 must include a stabilization slice:

- Unify the two model families (`src.models.schema` L0 models and newer `src.models.*` models).
- Make `RAGPipeline` testable through dependency injection while preserving the CLI behavior.
- Move prompt construction out of `cli.py` into a reusable prompt builder.
- Replace or quarantine hardcoded clarification logic with a LangGraph-based clarification flow.
- Decide that API/WebSocket files are draft code and keep L2 scope to FastAPI REST plus SSE.

