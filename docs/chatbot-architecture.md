# Chatbot Architecture

This document describes the architecture of the Mushir Sharia Compliance Chatbot's answer generation system.

## Overview

The chatbot uses a layered architecture that separates concerns between orchestration, prompt construction, LLM interaction, and validation. This design enables independent testing, flexible prompt versioning, and clean separation between business logic and LLM integration.

## Component Hierarchy

```
ApplicationService (Orchestrator)
    ↓
AnswerGenerator (Coordination Layer)
    ↓
PromptBuilder + LLMClient (Generation Layer)
    ↓
CitationValidator (Validation Layer)
```

## Core Components

### 1. AnswerGenerator

**Location:** `src/chatbot/answer_generator.py`

**Purpose:** Coordinates LLM generation with prompt building, acting as a bridge between the application service and the underlying LLM/prompt components.

**Responsibilities:**
- Accepts query, retrieved chunks, conversation history, and response language
- Delegates prompt construction to PromptBuilder
- Delegates LLM generation to LLMClient
- Handles both modern (system/user message separation) and legacy (single-string) prompt formats
- Returns generated answer text

**Key Methods:**

```python
def generate(
    query: str,
    chunks: List[Any],
    history: Optional[List[Dict[str, str]]] = None,
    response_language: str = "en",
) -> str:
    """Generate answer from query and retrieved chunks."""
```

**Design Pattern:**

The AnswerGenerator uses **adapter pattern** to support both:
- **Modern API:** `prompt_builder.build_messages()` returns `(system_prompt, user_prompt)` tuple for role-separated LLM calls
- **Legacy API:** `prompt_builder.build()` returns single concatenated string for backward compatibility

**Signature Inspection:**

The component uses Python's `inspect.signature()` to dynamically detect which parameters the prompt builder accepts, enabling graceful degradation when working with older prompt builder implementations.

### 2. ApplicationService

**Location:** `src/chatbot/application_service.py`

**Purpose:** Main orchestrator that coordinates the entire answer generation workflow.

**Responsibilities:**
- Query normalization (Arabic diacritics, transliteration variants)
- Language detection (Arabic vs English)
- Disclaimer enforcement
- Authority request detection (refuses binding fatwas)
- Cache lookup and storage
- RAG retrieval coordination
- Answer generation via AnswerGenerator
- Citation validation
- Compliance status determination
- Audit logging
- Session management

**Key Methods:**

```python
def answer(
    query: Optional[str],
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
    disclaimer_acknowledged: bool = True,
) -> AnswerContract:
    """Main entry point for compliance analysis."""
```

**Workflow:**

1. **Pre-processing:**
   - Validate query is not empty
   - Normalize query (diacritics, transliteration)
   - Detect response language
   - Check disclaimer acknowledgement
   - Check for authority requests (binding rulings)

2. **Cache Check:**
   - Generate cache key from query + prompt version + model + corpus version
   - Return cached answer if available (unless in eval mode)

3. **Clarification:**
   - Check if clarification is needed via ClarificationService
   - Return clarification question if facts are missing

4. **Retrieval:**
   - Retrieve top-k chunks from vector database
   - Return INSUFFICIENT_DATA if no chunks found

5. **Generation:**
   - Build prompt via PromptBuilder
   - Generate answer via AnswerGenerator → LLMClient
   - Validate citations via CitationValidator
   - Determine compliance status from answer text

6. **Post-processing:**
   - Audit log the query and answer
   - Cache the answer (unless clarification or eval mode)
   - Return AnswerContract

### 3. PromptBuilder

**Location:** `src/chatbot/prompt_builder.py`

**Purpose:** Constructs structured prompts for AAOIFI-grounded bilingual compliance analysis.

**Responsibilities:**
- Builds system prompt with AAOIFI grounding instructions
- Formats retrieved chunks with citations
- Includes conversation history (last N turns)
- Supports bilingual output (English/Arabic)
- Provides both modern (tuple) and legacy (string) APIs

**Key Methods:**

```python
def build_messages(
    query: str,
    chunks: List[Any],
    history: Optional[List[Dict[str, str]]] = None,
    response_language: str = "en",
) -> Tuple[str, str]:
    """Return (system_prompt, user_prompt) for role-separated LLM calls."""

def build(
    query: str,
    chunks: List[Any],
    history: Optional[List[Dict[str, str]]] = None,
    response_language: str = "en",
) -> str:
    """Backward-compatible single-string prompt."""
```

**Prompt Structure:**

**System Prompt:**
- AAOIFI grounding protocol (strict attribution, no hallucinations)
- Input normalization rules (misspellings, Arabic dialects)
- 3-phase chain-of-thought workflow
- Citation format requirements
- Prohibited behaviors
- Language-specific instructions
- Output format templates (English/Arabic)
- Incomplete query handling

**User Prompt:**
- Recent conversation history (last 3 turns, max 4000 chars)
- Retrieved AAOIFI excerpts with citations
- Current question
- Workflow execution instructions

### 4. LLMClient

**Location:** `src/chatbot/llm_client.py`

**Purpose:** Wrapper for LLM API calls with retry logic and error handling.

**Implementations:**

**OpenRouterClient:**
- OpenAI-compatible API for OpenRouter
- Supports multiple models (Gemini, GPT-4, Claude, etc.)
- Exponential backoff retry (3 attempts)
- Clear error messages for common failures
- Rate limit detection
- Empty response validation

**LLMClient (OpenAI):**
- Direct OpenAI API integration
- Similar retry logic
- Temperature 0.1 for deterministic outputs

**Key Methods:**

```python
def generate(
    prompt: str,
    system_prompt: Optional[str] = None
) -> str:
    """Generate response from LLM with retry logic."""
```

**Error Handling:**

- `LLMConfigurationError`: Missing API key or initialization failure
- `LLMResponseError`: Empty or invalid response
- `LLMRateLimitError`: Quota or rate limit exceeded

### 5. CitationValidator

**Location:** `src/chatbot/citation_validator.py`

**Purpose:** Extracts and validates AAOIFI citations from LLM-generated answers.

**Responsibilities:**
- Parses citation patterns from answer text
- Matches citations to retrieved chunks
- Calculates confidence scores
- Extracts quote boundaries
- Returns structured AAOIFICitation objects

**Citation Patterns:**

- `[AAOIFI FAS-X, Section Y.Z, page N]`
- `[FAS-X §Y.Z, p.N]`
- `[معيار أيوفي FAS-X، القسم Y.Z، صفحة N]`

## Data Flow

```
User Query
    ↓
ApplicationService.answer()
    ↓
[Query Normalization]
    ↓
[Cache Check] → Cache Hit? → Return Cached Answer
    ↓ No
[Clarification Check] → Needed? → Return Clarification Question
    ↓ No
[RAG Retrieval] → No Chunks? → Return INSUFFICIENT_DATA
    ↓ Chunks Found
AnswerGenerator.generate()
    ↓
PromptBuilder.build_messages()
    ↓
LLMClient.generate()
    ↓
CitationValidator.validate()
    ↓
[Status Determination]
    ↓
[Audit Logging]
    ↓
[Cache Storage]
    ↓
Return AnswerContract
```

## Design Patterns

### 1. Adapter Pattern (AnswerGenerator)

The AnswerGenerator adapts between different prompt builder APIs:
- Modern: `build_messages()` → `(system, user)` tuple
- Legacy: `build()` → single string

This enables gradual migration without breaking existing code.

### 2. Strategy Pattern (LLMClient)

Multiple LLM client implementations (OpenRouter, OpenAI) share the same interface, allowing runtime selection based on configuration.

### 3. Template Method (PromptBuilder)

The prompt construction follows a fixed template with customizable sections:
- System prompt (grounding rules)
- User prompt (history + chunks + query)
- Language-specific formatting

### 4. Chain of Responsibility (ApplicationService)

The answer workflow passes through multiple handlers:
1. Validation (empty query, disclaimer)
2. Cache lookup
3. Clarification check
4. Retrieval
5. Generation
6. Validation
7. Audit/cache

Each handler can short-circuit the chain by returning early.

## Configuration

### Environment Variables

```bash
# LLM Configuration
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=openrouter/free

# Caching
RESPONSE_CACHE_TTL_SECONDS=86400  # 24 hours

# Evaluation Mode (disables caching)
RAG_EVAL_MODE=false

# Disclaimer Enforcement
REQUIRE_DISCLAIMER_ACK=false

# Corpus Version (for cache invalidation)
AAOIFI_CORPUS_VERSION=v1.0
```

### Retrieval Parameters

```python
k = 5              # Top-k chunks to retrieve
threshold = 0.3    # Minimum similarity score
```

### Prompt Parameters

```python
max_history_turns = 3      # Recent conversation turns
max_history_chars = 4000   # Max history length
temperature = 0.1          # LLM temperature
max_retries = 3            # LLM retry attempts
timeout_seconds = 60       # LLM request timeout
```

## Testing Strategy

### Unit Tests

- **AnswerGenerator:** Mock LLMClient and PromptBuilder, verify correct delegation
- **PromptBuilder:** Test prompt construction with various inputs (chunks, history, languages)
- **LLMClient:** Test retry logic, error handling, rate limit detection
- **CitationValidator:** Test citation extraction and matching

### Integration Tests

- **ApplicationService:** Test full workflow with real RAG pipeline
- **End-to-End:** Test via API endpoints with real queries

### Evaluation Tests

- **Faithfulness:** RAGAS evaluation of answer grounding
- **Citation Accuracy:** Validate citations match retrieved chunks
- **Language Detection:** Test Arabic/English detection accuracy
- **Normalization:** Test query normalization (diacritics, transliteration)

## Future Enhancements

### L1 (Clarification Loop)

- LangGraph state machine for multi-turn clarification
- Session-based conversation history
- Structured logging with request IDs

### L2 (API + Streaming)

- FastAPI REST endpoints
- Server-Sent Events (SSE) streaming
- Token-by-token generation

### L3 (Production Ready)

- Redis session storage
- PostgreSQL audit logging
- Qdrant vector database
- Prometheus metrics
- Grafana dashboards

### L4 (Scale + Ops)

- API key authentication
- Tier-based rate limiting
- Docker deployment
- CI/CD pipelines
- Alerting and monitoring

## References

- **Design Document:** `.kiro/specs/sharia-compliance-chatbot/design.md`
- **Requirements:** `.kiro/specs/sharia-compliance-chatbot/requirements.md`
- **Tasks:** `.kiro/specs/sharia-compliance-chatbot/tasks.md`
- **Scripts Guide:** `docs/scripts-guide.md`
