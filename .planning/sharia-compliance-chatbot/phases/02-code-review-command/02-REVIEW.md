---
phase: 02-code-review
reviewed: 2026-05-15T12:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - src/api/main.py
  - src/chatbot/application_service.py
  - src/chatbot/citation_validator.py
  - src/chatbot/clarification_engine.py
  - src/chatbot/compliance_analyzer.py
  - src/rag/chunker.py
  - src/rag/embeddings.py
  - src/rag/pipeline.py
  - src/storage/cache.py
  - tests/test_api_l2.py
  - tests/test_api_readiness.py
  - tests/test_l5_readiness.py
  - tests/test_patch_coverage.py
  - tests/test_rag_hardening.py
  - tests/test_rag_pipeline.py
findings:
  critical: 2
  warning: 7
  info: 3
  total: 12
status: issues_found
---

# Phase 02: Adversarial Code Review Report

**Reviewed:** 2026-05-15T12:00:00Z
**Depth:** standard
**Status:** issues_found

## Summary

This review covers 15 files in a patch that (a) removes the disclaimer acknowledgment checkbox from the chat UI, (b) refactors the RAG pipeline and embedding logic toward new `EmbeddingService`/`QueryPreprocessor` abstractions, (c) rewrites `ComplianceAnalyzer` from a full LLM-driven pipeline into a thin keyword matcher, (d) moves authority-request blocking from the RAG pipeline into `ApplicationService`, (e) changes the language detection threshold, and (f) adds a cache eviction policy.

**Key findings.** Two critical issues: 1) the authority-detection regex is broken for the Arabic terms the system is designed to catch, and 2) the embedding query path silently drops the bi-directional query expansion that is the whole point of the multilingual RAG pipeline. Several warnings around swallowed exceptions, duplicated logic, and a gutted compliance analyzer that no longer actually analyzes compliance.

---

## Critical Issues

### CR-01: Authority detection regex uses `\w` — impossible to match Arabic word boundaries

**Files:**
- `src/chatbot/application_service.py:379`
- `src/chatbot/constants.py:2-8`

**Issue:**
`_is_authority_request` uses `re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', lowered)`.

Python's `re` module defines `\w` as `[a-zA-Z0-9_]` only — it does **not** match Arabic/Unicode letter characters (U+0600–U+06FF). The constants file (`src/chatbot/constants.py`) contains four Arabic authority terms:
```python
"فتوى ملزمة"     # binding fatwa
"حكم شرعي ملزم"  # binding ruling
"نصيحة قانونية"   # legal advice
"نصيحة مالية"     # financial advice
```

The `\w`-based word boundary assertions treat every adjacent Arabic character as a non-word boundary. This produces:

1. **False negatives**: Arabic queries containing these exact phrases with surrounding text are not detected. Example: `"أريد فتوى ملزمة حول المرابحة"` — the `\u0623` before `\u0641\u062a\u0648\u0649` is not a `\w` character, so the lookbehind fires at every position, making the match succeed accidentally by luck, not by design. Conversely, any prefix character that happens to belong to the wrong Unicode range breaks the assertion in an unpredictable direction.

2. **False positives / incorrect boundaries**: `\w` after an Arabic match doesn't extend through the rest of an Arabic compound, so `"احكمشرعي"` could accidentally match the substring boundary.

**Why it matters:**
The authority gate is the primary compliance-safety mechanism. A user asking in Arabic for a binding fatwa will not be reliably detected, and the system may generate a full RAG response with compliance analysis instead of returning the refusal contract. This is a regulatory/compliance failure in the core safety path.

**Fix:**
Replace the `\w`-based word boundary assertions with a Unicode-aware approach that recognizes Arabic letters as word constituents. Use the `regex` module (third-party, Unicode-aware) or craft boundaries using explicit Unicode categories:

```python
# Either switch to `regex` module which respects Unicode word boundaries
# pip install regex
import regex as re

# Or craft an explicit boundary pattern for the application_service check:
# Match only where the term is NOT preceded/followed by any letter (L category)
import unicodedata

def _is_authority_request(query: str) -> bool:
    if not query:
        return False
    lowered = query.lower()
    for term in AUTHORITY_REQUEST_TERMS:
        # Simple substring match — acceptable here since false positives
        # (refusing when not needed) are safer than false negatives.
        if term in lowered:
            return True
    return False
```

If false-positive rates from dropping the boundary check are a concern, use the `regex` module:
```python
import regex as re

for term in AUTHORITY_REQUEST_TERMS:
    pattern = r'\b' + re.escape(term) + r'\b'  # \b in regex is Unicode-aware
    if re.search(pattern, lowered):
        return True
```

---

### CR-02: RAG pipeline `embed_query()` silently drops query expansion on main code path

**Files:**
- `src/rag/pipeline.py:150-195`
- `src/rag/embedding_service.py:25-29`

**Issue:**
The refactored `RAGPipeline.embed_query()` has four fallback paths (A–D). Path A (the primary path for production) calls `embedding_service.embed_text(query)` directly. `EmbeddingService.embed_text()` (lines 25-29) does:

```python
def embed_text(self, text: str, normalize: bool = True) -> List[float]:
    if not text:
        return []
    return self.model.encode(text, normalize_embeddings=normalize).tolist()
```

This is a raw `model.encode()` call with **no query expansion**. The old code always called `_expand_for_embedding(query)` before encoding, which appended English synonyms to Arabic queries (and vice versa) — the entire reason the multilingual model was chosen.

Paths C and D still call `QueryPreprocessor.expand_for_embedding(query)`. So the expansion behavior depends on which internal attribute is set, which varies by constructor path and initialization order — creating a silent correctness regression.

**Why it matters:**
Cross-lingual retrieval for Arabic queries is fundamentally broken. An Arabic user asking `"ما هي المرابحة؟"` will have their query embedded as raw Arabic, then searched against a vector store built from English AAOIFI standard texts. Without the English synonym injection (`"murabaha deferred payment sale"`) that the expansion provides, the semantic gap is too large — the nearest neighbors will be noise. This is a silent regression: no error, no warning, just terrible retrieval quality.

**Fix:**
Remove the four-path fallback and always expand before embedding:

```python
def embed_query(self, query: str) -> List[float]:
    if not query:
        return []
    expanded = QueryPreprocessor.expand_for_embedding(query)
    return self.embedding_service.embed_text(expanded)
```

Delete the fallback paths B–D. They exist only to support stale object states that should never occur in a correctly constructed pipeline.

---

## Warnings

### WR-01: `ComplianceAnalyzer` rewrite removes LLM-driven compliance analysis

**Files:**
- `src/chatbot/compliance_analyzer.py` (entire file — 117 lines replaced with 57)

**Issue:**
The old `ComplianceAnalyzer` was a complete compliance pipeline:
1. Enhance the query with extracted variables
2. Retrieve relevant AAOIFI chunks from RAG
3. Call the LLM with `AAOIFI_ADHERENCE_SYSTEM_PROMPT` + augmented prompt
4. Parse structured ruling from LLM response (status, reasoning, citations, recommendations, warnings)
5. Validate citations against retrieved chunks

The new version is a thin wrapper that:
1. Calls `citation_validator.validate(answer, chunks)`
2. Keyword-matches the answer text to derive `ComplianceStatus`
3. Extracts the first line of the answer as "reasoning summary"

There is **no LLM call**, **no query enhancement with variables**, **no AAOIFI adherence analysis**, **no recommendations/warnings extraction**. If the caller was relying on `ComplianceAnalyzer.analyze()` to do the actual compliance work, the system no longer performs compliance analysis.

**Why it matters:**
The system may now return answers with `COMPLIANT` status without ever consulting the LLM for AAOIFI adherence checking. If compliance analysis is performed elsewhere (e.g., directly in the orchestrator), this class is dead code. If not, the compliance check is silently missing. The diff does not show the caller being updated.

**Fix:**
Either (a) restore the LLM call in `ComplianceAnalyzer.analyze()`, or (b) if compliance analysis has been moved to `ApplicationService`, delete this class entirely to prevent dead-code confusion and document where the analysis now lives.

---

### WR-02: `_build_retriever()` silently returns `None` on ALL failures — no alert, no metrics

**File:** `src/api/main.py:82-97`

**Issue:**
```python
def _build_retriever():
    try:
        from src.rag.pipeline import RAGPipeline
        return RAGPipeline()
    except Exception as exc:
        print(_safe_fallback_message(f"RAG retriever ({exc.__class__.__name__}: {exc})"))
        return None
```

`except Exception` catches everything: `ImportError` (missing deps), `OSError` (disk full on ChromaDB write), `MemoryError` (OOM loading SentenceTransformer), `chromadb.errors.ChromaDBException` (corrupt index), etc. All are reduced to a `print()` call and a silent `None` return.

This `None` propagates into `ApplicationService(retriever=None)`, forcing every single user request through the lazy-init fallback in `application_service.py:124-137`, which also catches all exceptions and returns an error contract. The system runs in permanent degraded mode with no metrics, no health-check effect, and no operator-visible signal beyond a single `print()` that most production log aggregators discard.

**Why it matters:**
A corrupted ChromaDB or a failed model download at startup is invisible to monitoring. Operators will only discover the problem when every user query returns "Retrieval backend is not available."

**Fix:**
1. Do NOT catch `Exception` broadly. Catch specific known failure modes.
2. Re-raise or set a health-check signal so `/health` and `/ready` endpoints report the degraded state.
3. Log through the structured logger, not `print()`.

```python
def _build_retriever():
    try:
        from src.rag.pipeline import RAGPipeline
        return RAGPipeline()
    except (ImportError, OSError, chromadb.errors.ChromaDBException) as exc:
        logger.error("RAG retriever failed to initialize", exc_info=exc)
        # Signal degraded health
        app.state.infrastructure["rag_pipeline"] = "unhealthy"
        return None
```

---

### WR-03: Cache eviction scans entire dictionary at capacity — O(n) per insert

**File:** `src/storage/cache.py:37-58`

**Issue:**
```python
def set_json(self, namespace, key, value, ttl_seconds):
    full_key = self._cache_key(namespace, key)
    if len(self._values) >= self.MAX_ENTRIES and full_key not in self._values:
        self._evict()
    self._values[full_key] = ...

def _evict(self):
    now = time.time()
    expired = [k for k, (exp, _) in self._values.items() if exp <= now]
    if expired:
        for k in expired[:self.EVICT_BATCH]:
            self._values.pop(k, None)
    else:
        sorted_keys = sorted(self._values.keys(), key=lambda k: self._values[k][0])
        for k in sorted_keys[:self.EVICT_BATCH]:
            self._values.pop(k, None)
```

When the cache reaches `MAX_ENTRIES` (10,000), every subsequent `set_json` call:
1. Iterates all 10,000 entries to find expired ones
2. If none expired, sorts all 10,000 entries by expiry time — O(n log n)
3. Pops 500 entries

For a system that may process many requests per second, this turns an O(1) insert into an O(n) operation on every cache miss at capacity. Under sustained load, the cache becomes a bottleneck.

**Why it matters:**
Worst-case: cache at steady-state max, high request throughput with unique keys (cache misses dominate). Every insert triggers a 10,000-entry scan + sort, introducing latency spikes.

**Fix:**
Use passive eviction: check/remove expired entries on read (`get_json` already does this) and only evict on insert when truly necessary. Use a simpler eviction: randomly pop 1 entry (amortized O(1)) instead of scanning all:

```python
def _evict(self):
    """Evict expired entries or, if none, a single random entry."""
    now = time.time()
    expired = [k for k, (exp, _) in self._values.items() if exp <= now]
    if expired:
        # Batch-evict expired
        for k in expired[:self.EVICT_BATCH]:
            self._values.pop(k, None)
    else:
        # Evict *one* random entry — O(1) amortized
        import random
        victim = random.choice(list(self._values.keys()))
        self._values.pop(victim, None)
```

---

### WR-04: `_collection_has_metadata` catches ALL exceptions silently

**File:** `src/rag/pipeline.py:26-37`

**Issue:**
```python
def _collection_has_metadata(collection, key, value):
    try:
        results = collection.get(where={key: value}, limit=1, include=["metadatas"])
        ...
    except Exception:
        pass
    return False
```

The bare `except Exception: pass` swallows `ValueError` from malformed `where` filters, `KeyError` from missing keys in the ChromaDB response, and `chromadb.errors.ChromaDBException` from database connection issues. Every failure silently returns `False`, which causes `validate_chroma_index_for_arabic_retrieval` to raise a misleading "Chroma collection must contain at least one Arabic document" error, sending operators down the wrong debugging path when the real problem is a broken database connection.

**Why it matters:**
Makes operational debugging of ChromaDB issues extremely difficult by hiding the real error and substituting a misleading one.

**Fix:**
Let the exception propagate and include context:

```python
def _collection_has_metadata(collection, key, value):
    try:
        results = collection.get(where={key: value}, limit=1, include=["metadatas"])
        ...
    except Exception as exc:
        logger.error(f"Failed to query ChromaDB metadata (key={key}, value={value!r}): {exc}")
        raise  # Or return False and let caller decide, but always log
```

---

### WR-05: `ask_if_needed()` creates `SessionState` with potentially incomplete initialization

**File:** `src/chatbot/clarification_engine.py:240-250`

**Issue:**
```python
def ask_if_needed(self, query: str, session_id: Optional[str] = None) -> Optional[str]:
    state = SessionState(session_id=session_id or "")
    result = self.process_query(state, query)
    ...
```

`SessionState(session_id="")` is created with only the session_id field. If `SessionState.__init__` has additional required fields, this line raises a `TypeError`. Even if it doesn't, `process_query` may access `state.conversation_history`, `state.clarification_state`, `state.extracted_variables`, etc. — fields that must have sensible defaults. A partially initialized `SessionState` will cause `AttributeError` or unexpected behavior.

**Why it matters:**
A crash in the "check if we need clarification" path means every query that misses the cache and hits this branch produces a 500 error instead of a fallback response.

**Fix:**
Either (a) use a factory method that provides complete defaults, or (b) catch exceptions at this call site and return `None` so the system degrades gracefully:

```python
def ask_if_needed(self, query, session_id=None):
    try:
        state = SessionState.create_transient(session_id or "")
        result = self.process_query(state, query)
        ...
    except Exception:
        logger.warning("Clarification check failed for query", exc_info=True)
        return None
```

---

### WR-06: Language detection threshold (30% → 50%) produces wrong-language responses for mixed queries

**Files:**
- `src/chatbot/application_service.py:327` (method `_detect_language`)
- `src/rag/query_preprocessor.py:101-112` (mirror method)

**Issue:**
The threshold for classifying a query as Arabic was lowered from `ratio > 0.30` to `ratio > 0.50`. A bilingual user writing `"ما هو murabaha"` (What is murabaha) has ~4 Arabic chars out of ~15 total = 27%. This is now classified as English.

The response language changes from Arabic to English, the RAG retrieval language filter shifts, and the refusal messages switch to English — all for queries that contain Arabic intent markers. The 30% threshold was deliberately chosen to capture code-mixed queries from Arabic-dominant bilingual users; raising it to 50% means the system now requires >50% Arabic content before treating a query as Arabic.

**Why it matters:**
Arabic-dominant users who naturally mix English financial terms into Arabic queries will receive English-only responses. This is a UX regression for the primary user demographic.

**Fix:**
Restore the 30% threshold, or make it configurable per deployment (e.g., `ARABIC_THRESHOLD=0.30` env var), or switch to a classifier that detects intent language independently of character ratio.

---

### WR-07: `_status_from_answer` and `ComplianceAnalyzer._determine_status` are identical logic duplicates

**Files:**
- `src/chatbot/application_service.py:437-457`
- `src/chatbot/compliance_analyzer.py:40-65`

**Issue:**
Both methods contain identical keyword-matching logic for deriving `ComplianceStatus` from answer text — checking for `INSUFFICIENT`, `PARTIALLY_COMPLIANT`, `CONDITIONALLY COMPLIANT`, `NON_COMPLIANT`, `COMPLIANT` — in the same order and with the same return values. This logic is now duplicated across two files.

**Why it matters:**
When the keyword set needs to change (e.g., adding a new status phrase), one copy will inevitably be missed, causing inconsistent compliance determination depending on which code path processes the answer.

**Fix:**
Extract to a shared utility function:

```python
# src/chatbot/compliance_analyzer.py or a new shared module
def derive_compliance_status(answer: str, citations) -> ComplianceStatus:
    """Shared compliance status derivation — single source of truth."""
    upper = answer.upper()
    if "INSUFFICIENT" in upper or not citations:
        return ComplianceStatus.INSUFFICIENT_DATA
    if "PARTIALLY_COMPLIANT" in upper or "CONDITIONALLY COMPLIANT" in upper:
        return ComplianceStatus.PARTIALLY_COMPLIANT
    if "NON_COMPLIANT" in upper or "NON-COMPLIANT" in upper:
        return ComplianceStatus.NON_COMPLIANT
    if "COMPLIANT" in upper:
        return ComplianceStatus.COMPLIANT
    return ComplianceStatus.INSUFFICIENT_DATA
```

Both `ApplicationService._status_from_answer` and `ComplianceAnalyzer._determine_status` should call this.

---

## Info

### IN-01: `EmbeddingGenerator.embed_batch` bypasses `EmbeddingService` abstraction

**File:** `src/rag/embeddings.py:26-28`

**Issue:**
```python
def embed_batch(self, texts, batch_size=BATCH_SIZE):
    return self._service.model.encode(
        texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=True
    ).tolist()
```

This calls `self._service.model.encode()` directly instead of `self._service.embed_batch()`. If `EmbeddingService.embed_batch` acquires preprocessing or error handling later, the batch path will diverge from the single-text path. Use `self._service.embed_batch()` instead.

---

### IN-02: `print()` instead of structured logging in production startup paths

**Files:**
- `src/api/main.py:82-97` (`_build_retriever`)
- `src/rag/pipeline.py:119` (`print(f"Loading embedding model: ...")`)
- `src/rag/embedding_service.py:21` (`print(f"Loading embedding model: ...")`)
- `src/chatbot/application_service.py:130` (`print(f"RAG retriever init failed: ...")`)

**Issue:**
Multiple production code paths use `print()` for reporting failures and initialization. `print()` output is not captured by structured logging systems (e.g., `loguru`, `structlog`, `logging` with JSON formatters), making these events invisible in production observability. Replace all `print()` calls with `logger.info()`/`logger.error()` using the existing `setup_logging()` logger.

---

### IN-03: Disclaimer checkbox removed from UI — no alternative acknowledgment path

**File:** `src/api/main.py:346-351`

**Issue:**
The checkbox that required users to explicitly acknowledge "informational guidance only, not a binding Sharia ruling, fatwa, legal advice, or financial advice" has been removed. The commit message says "remove disclaimer checkbox from chat interface" with no replacement mechanism. Users can now submit queries without any acknowledgment.

If the domain/regulatory requirements for this system include user acknowledgment of non-binding guidance (common for Islamic finance advisory tools), this removal introduces legal exposure. Either retain a streamlined acknowledgment (e.g., a one-time modal on first visit) or ensure the removal has explicit product/legal sign-off documented in the commit message.

---

_Reviewed: 2026-05-15T12:00:00Z_
_Reviewer: OpenCode (gsd-code-reviewer — Blind Hunter)_
_Depth: standard_
