# L0 Architecture Diagram

## High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         L0 RAG LOOP                             │
└─────────────────────────────────────────────────────────────────┘

User Query (Terminal)
        │
        ▼
┌───────────────────┐
│   CLI Chatbot     │  python -m src.chatbot.cli --query "..."
│  (cli.py)         │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│   RAG Pipeline    │  1. Embed query
│  (pipeline.py)    │  2. Search ChromaDB
└─────────┬─────────┘  3. Return top-k chunks
          │
          ▼
┌───────────────────┐
│   ChromaDB        │  Similarity search
│  (chroma_db/)     │  Returns: chunks + scores + metadata
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Prompt Builder   │  System prompt + retrieved chunks + query
│  (cli.py)         │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│   LLM API         │  OpenAI GPT-4 or Anthropic Claude
│  (OpenAI/Anthropic)│  Temperature: 0.1
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Compliance Ruling │  Answer + Citations
│  (schema.py)      │  Format: [FAS-XX §Y]
└─────────┬─────────┘
          │
          ▼
    Terminal Output
```

---

## Data Flow

### 1. Ingestion Phase (One-time)

```
AAOIFI Markdown Files (data/aaoifi_md/*.md)
        │
        ▼
┌───────────────────┐
│  Ingest Script    │  scripts/ingest.py
│                   │
│  1. Read .md      │
│  2. Chunk text    │  RecursiveCharacterTextSplitter
│     (512 tokens)  │  chunk_size=512, overlap=50
│  3. Generate      │  sentence-transformers
│     embeddings    │  all-mpnet-base-v2 (768-dim)
│  4. Store         │
└─────────┬─────────┘
          │
          ▼
┌───────────────────────────────────────┐
│         ChromaDB Storage              │
│                                       │
│  Collection: "aaoifi"                 │
│                                       │
│  For each chunk:                      │
│  ├─ ID: hash(filename:index)         │
│  ├─ Embedding: [768 floats]          │
│  ├─ Document: chunk text             │
│  └─ Metadata:                         │
│      ├─ source_file: "FAS-28.md"     │
│      ├─ chunk_idx: 5                  │
│      └─ total_chunks: 45              │
└───────────────────────────────────────┘
```

### 2. Query Phase (Every request)

```
User Query: "What does AAOIFI require for murabaha cost disclosure?"
        │
        ▼
┌───────────────────┐
│  Query Embedding  │  sentence-transformers
│                   │  all-mpnet-base-v2
│  Input: string    │
│  Output: [768]    │
└─────────┬─────────┘
          │
          ▼
┌───────────────────────────────────────┐
│      ChromaDB Similarity Search       │
│                                       │
│  Query: embedding vector              │
│  Method: cosine similarity            │
│  Parameters:                          │
│  ├─ n_results: 5 (top-k)             │
│  └─ threshold: 0.3 (min score)       │
│                                       │
│  Returns:                             │
│  ├─ documents: [chunk texts]          │
│  ├─ metadatas: [source info]          │
│  ├─ distances: [similarity scores]    │
│  └─ ids: [chunk IDs]                  │
└─────────┬─────────────────────────────┘
          │
          ▼
┌───────────────────────────────────────┐
│      Convert to SemanticChunks        │
│                                       │
│  For each result:                     │
│  ├─ chunk_id: from results.ids       │
│  ├─ text: from results.documents     │
│  ├─ citation:                         │
│  │   ├─ standard_id: from filename   │
│  │   ├─ section: None (L0)           │
│  │   └─ source_file: from metadata   │
│  └─ score: 1 - distance              │
└─────────┬─────────────────────────────┘
          │
          ▼
┌───────────────────────────────────────┐
│       Build Augmented Prompt          │
│                                       │
│  System Prompt:                       │
│  "You are a Sharia compliance         │
│   assistant. Answer ONLY from         │
│   provided AAOIFI excerpts..."        │
│                                       │
│  User Prompt:                         │
│  "Excerpts from AAOIFI Standards:     │
│                                       │
│   [FAS-28] (Score: 0.92)              │
│   {chunk 1 text}                      │
│   ---                                 │
│   [FAS-28] (Score: 0.89)              │
│   {chunk 2 text}                      │
│   ...                                 │
│                                       │
│   Question: {user query}              │
│                                       │
│   Answer with citations [FAS-XX §Y]:" │
└─────────┬─────────────────────────────┘
          │
          ▼
┌───────────────────┐
│    LLM API Call   │  OpenAI or Anthropic
│                   │
│  Model: GPT-4 or  │
│         Claude 3.5│
│  Temperature: 0.1 │
│  Max tokens: 2000 │
└─────────┬─────────┘
          │
          ▼
┌───────────────────────────────────────┐
│         LLM Response                  │
│                                       │
│  "According to AAOIFI FAS-28 §3.2,    │
│   the Islamic financial institution   │
│   MUST disclose the actual cost       │
│   price of the goods to the           │
│   purchaser. [FAS-28 §3.2]            │
│                                       │
│   This disclosure is a fundamental    │
│   requirement for the validity of a   │
│   Murabaha transaction under Sharia   │
│   principles..."                      │
└─────────┬─────────────────────────────┘
          │
          ▼
┌───────────────────────────────────────┐
│      Create ComplianceRuling          │
│                                       │
│  question: {user query}               │
│  answer: {LLM response}               │
│  chunks: [SemanticChunk objects]      │
│  confidence: avg(chunk scores)        │
└─────────┬─────────────────────────────┘
          │
          ▼
┌───────────────────────────────────────┐
│        Format Terminal Output         │
│                                       │
│  ════════════════════════════════════ │
│  COMPLIANCE RULING                    │
│  ════════════════════════════════════ │
│                                       │
│  {answer with citations}              │
│                                       │
│  ──────────────────────────────────── │
│  Retrieved 5 AAOIFI excerpts          │
│  Average relevance score: 0.87        │
│                                       │
│  Sources:                             │
│    • FAS-28 (score: 0.92)             │
│    • FAS-28 (score: 0.89)             │
│    ...                                │
│  ════════════════════════════════════ │
└───────────────────────────────────────┘
```

---

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        L0 COMPONENTS                            │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│   Data Models    │  src/models/schema.py
│                  │
│  • AAOIFICitation│  - standard_id, section, page, source_file
│  • SemanticChunk │  - chunk_id, text, citation, score
│  • ComplianceRuling│ - question, answer, chunks, confidence
└──────────────────┘

┌──────────────────┐
│   RAG Pipeline   │  src/rag/pipeline.py
│                  │
│  RAGPipeline     │
│  ├─ __init__()   │  Load model + connect ChromaDB
│  ├─ embed_query()│ Generate query embedding
│  └─ retrieve()   │  Similarity search + filter + convert
└──────────────────┘

┌──────────────────┐
│   CLI Chatbot    │  src/chatbot/cli.py
│                  │
│  • AAOIFI_ADHERENCE_SYSTEM_PROMPT
│  • TEMPLATE      │  Prompt template
│  • format_chunks()│ Format for LLM
│  • call_llm()    │  OpenAI/Anthropic API
│  • main()        │  CLI entry point
└──────────────────┘

┌──────────────────┐
│ Ingestion Script │  scripts/ingest.py
│                  │
│  1. Load model   │  SentenceTransformer
│  2. Init ChromaDB│  PersistentClient
│  3. Load splitter│  RecursiveCharacterTextSplitter
│  4. Process files│  For each .md file:
│     ├─ Read text │    - Read content
│     ├─ Chunk     │    - Split into chunks
│     ├─ Embed     │    - Generate embeddings
│     └─ Store     │    - Upsert to ChromaDB
└──────────────────┘

┌──────────────────┐
│   Setup Tools    │  scripts/
│                  │
│  • setup_l0.py   │  Environment verification
│  • check_corpus.py│ Corpus validation
└──────────────────┘

┌──────────────────┐
│   Tests          │  tests/test_rag_smoke.py
│                  │
│  • test_ingest_nonempty()
│  • test_retrieval_smoke()
│  • test_gold_evaluation()
└──────────────────┘
```

---

## File Structure

```
mushir-sharia-bot/
│
├── src/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── schema.py              ← Data models
│   ├── rag/
│   │   ├── __init__.py
│   │   └── pipeline.py            ← RAG retrieval logic
│   └── chatbot/
│       ├── __init__.py
│       └── cli.py                 ← Terminal interface
│
├── scripts/
│   ├── ingest.py                  ← Corpus ingestion
│   ├── check_corpus.py            ← Corpus validation
│   └── setup_l0.py                ← Setup verification
│
├── tests/
│   ├── __init__.py
│   ├── test_rag_smoke.py          ← Smoke tests
│   └── fixtures/
│       └── gold_eval.yaml         ← Gold test cases
│
├── data/
│   └── aaoifi_md/                 ← AAOIFI markdown corpus
│       ├── .gitkeep
│       ├── FAS-1-sample.md        ← Sample standard
│       └── FAS-28-sample.md       ← Sample standard
│
├── chroma_db/                     ← Vector database (gitignored)
│   ├── chroma.sqlite3
│   └── [parquet files]
│
├── .venv/                         ← Virtual environment (gitignored)
│
├── .env                           ← Environment config (gitignored)
├── .env.example                   ← Environment template
├── .gitignore
├── requirements.txt               ← Python dependencies
│
├── L0_README.md                   ← Quick reference
├── L0_SETUP_GUIDE.md              ← Detailed setup
├── L0_COMPLETE.md                 ← Implementation summary
├── L0_ARCHITECTURE.md             ← This file
├── IMPLEMENTATION_SUMMARY.md      ← Delivery summary
│
└── quick_start_l0.bat             ← Windows quick start
```

---

## Sequence Diagram

```
User          CLI           RAG           ChromaDB      LLM
 │             │             │              │            │
 │─query──────>│             │              │            │
 │             │             │              │            │
 │             │─embed_query>│              │            │
 │             │             │              │            │
 │             │             │─similarity──>│            │
 │             │             │   search     │            │
 │             │             │              │            │
 │             │             │<─top-k chunks│            │
 │             │             │  + scores    │            │
 │             │             │              │            │
 │             │<─SemanticChunk[]           │            │
 │             │             │              │            │
 │             │─format_chunks              │            │
 │             │─build_prompt               │            │
 │             │                            │            │
 │             │─system_prompt + user_prompt────────────>│
 │             │                            │            │
 │             │<─answer with citations─────────────────│
 │             │                            │            │
 │             │─create_ruling              │            │
 │             │                            │            │
 │<─formatted──│                            │            │
 │  output     │                            │            │
```

---

## Data Models

### AAOIFICitation

```python
@dataclass
class AAOIFICitation:
    standard_id: str          # "FAS-28"
    section: Optional[str]    # "3.2" (None in L0)
    page: Optional[int]       # 15 (None in L0)
    source_file: str          # "FAS-28-sample.md"
```

### SemanticChunk

```python
@dataclass
class SemanticChunk:
    chunk_id: str             # "a3f5b2c1..."
    text: str                 # "According to AAOIFI..."
    citation: AAOIFICitation  # Citation object
    score: float              # 0.92 (similarity score)
```

### ComplianceRuling

```python
@dataclass
class ComplianceRuling:
    question: str                    # User query
    answer: str                      # LLM response
    chunks: List[SemanticChunk]      # Retrieved chunks
    confidence: float                # Average score
```

---

## Configuration

### Environment Variables (.env)

```env
# LLM API (choose one)
OPENAI_API_KEY=sk-proj-...
# OR
ANTHROPIC_API_KEY=sk-ant-...

# Embedding model
EMBED_MODEL=sentence-transformers/all-mpnet-base-v2

# Storage paths
CHROMA_DIR=./chroma_db
CORPUS_DIR=./data/aaoifi_md
```

### Chunking Parameters

```python
RecursiveCharacterTextSplitter(
    chunk_size=512,        # Max tokens per chunk
    chunk_overlap=50,      # Overlap between chunks
    separators=[           # Split priority
        "\n\n",            # 1. Paragraphs
        "\n",              # 2. Lines
        ". ",              # 3. Sentences
        " ",               # 4. Words
        ""                 # 5. Characters
    ]
)
```

### Retrieval Parameters

```python
retrieve(
    query="...",
    k=5,                   # Top-k chunks to retrieve
    threshold=0.3          # Min similarity score (0-1)
)
```

### LLM Parameters

```python
# OpenAI
client.chat.completions.create(
    model="gpt-4",
    temperature=0.1,       # Low for consistency
    messages=[...]
)

# Anthropic
client.messages.create(
    model="claude-3-5-sonnet-20241022",
    temperature=0.1,
    max_tokens=2000,
    messages=[...]
)
```

---

## Performance Characteristics

### Ingestion (One-time)

| Corpus Size | Chunks | Time | Storage |
|-------------|--------|------|---------|
| 2 samples | ~112 | 30s | ~5MB |
| 10 standards | ~500 | 2min | ~20MB |
| 50 standards | ~2,500 | 10min | ~100MB |
| Full AAOIFI | ~10,000 | 30min | ~400MB |

### Query (Per request)

| Operation | Time | Notes |
|-----------|------|-------|
| Embed query | 50ms | Local model |
| ChromaDB search | 100ms | k=5 |
| LLM call | 2-5s | Network + generation |
| **Total** | **2-6s** | End-to-end |

### Resource Usage

| Resource | L0 | Production |
|----------|-----|-----------|
| RAM | ~2GB | ~8GB |
| Disk | ~500MB | ~5GB |
| CPU | 2 cores | 4+ cores |
| GPU | Optional | Recommended |

---

## Limitations (L0)

### By Design

- ❌ No clarification loop (single-turn only)
- ❌ No conversation history
- ❌ No streaming (waits for full response)
- ❌ No API (terminal only)
- ❌ No authentication
- ❌ No rate limiting
- ❌ No monitoring

### Technical

- Section extraction not implemented (citations show file only)
- No cross-reference resolution
- No multi-hop reasoning
- No query expansion
- No re-ranking

### Data

- Sample corpus only (2 files)
- English-only embeddings
- No Arabic support

**These are intentional.** L0 proves the core loop. Later layers add features.

---

## Next Layer Preview

### L1: Clarification Loop

```
User: "I want to invest in a company"
  ↓
Clarification Engine: "What type of company?"
  ↓
User: "Tech company with some haram revenue"
  ↓
Clarification Engine: "What % is haram revenue?"
  ↓
User: "About 3%"
  ↓
RAG Pipeline: [retrieve relevant standards]
  ↓
LLM: "According to FAS-21..."
```

### L2: FastAPI + SSE

```
POST /api/v1/query
  ↓
SSE Stream:
  data: {"type": "thinking"}
  data: {"type": "retrieving", "chunks": 5}
  data: {"type": "generating"}
  data: {"type": "chunk", "text": "According to..."}
  data: {"type": "chunk", "text": "AAOIFI FAS-28..."}
  data: {"type": "complete", "ruling": {...}}
```

---

**L0 Architecture: Simple, focused, proven. ✅**
