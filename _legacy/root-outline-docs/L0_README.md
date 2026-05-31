# L0 - Minimal RAG Loop

**Goal**: Smallest thing that proves the RAG loop works end-to-end on real AAOIFI text.

**No API, no streaming, no frontend.** Terminal in → cited answer out.

Once L0 is green, every later layer (SSE, FastAPI, eval harness) just plugs onto it.

---

## Prerequisites

- Python 3.9+ (minimum) / Python 3.11+ (recommended for better performance)
- AAOIFI markdown corpus in `data/aaoifi_md/*.md`
- OpenAI API key OR Anthropic API key

---

## Setup

### 1. Create Virtual Environment

```bash
python -m venv .venv
```

**Activate:**
- Windows CMD: `.venv\Scripts\activate`
- Windows PowerShell: `.venv\Scripts\Activate.ps1`
- Linux/Mac: `source .venv/bin/activate`

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and add your API key:

```bash
cp .env.example .env
```

Edit `.env`:
```
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...

EMBED_MODEL=sentence-transformers/all-mpnet-base-v2
CHROMA_DIR=./chroma_db
CORPUS_DIR=./data/aaoifi_md
```

### 4. Verify Corpus

Ensure AAOIFI markdown files exist:

```bash
ls data/aaoifi_md
```

If empty, you need to run the AAOIFI converter first to populate this directory.

---

## Run Order

### Step 1: Ingest Corpus

Chunk and embed AAOIFI standards into ChromaDB:

```bash
python scripts/ingest.py
```

**Expected output:**
- `chroma_db/` directory created
- Console shows: "Ingestion complete! Total chunks stored: X"

### Step 2: Run Tests

Verify the RAG pipeline works:

```bash
pytest -v
```

**Expected:**
- `test_ingest_nonempty` ✓ (ChromaDB populated)
- `test_retrieval_smoke` ✓ (Retrieval returns chunks)
- `test_gold_evaluation` ⊘ (Skipped - gold set empty)

### Step 3: Query via CLI

Ask a compliance question:

```bash
python -m src.chatbot.cli --query "What does AAOIFI require for murabaha cost disclosure?"
```

**Expected output:**
```
================================================================================
L0 AAOIFI Compliance Chatbot
================================================================================

Initializing RAG pipeline...
Loading embedding model: sentence-transformers/all-mpnet-base-v2
Connecting to ChromaDB: ./chroma_db
Collection contains 1234 chunks

Query: What does AAOIFI require for murabaha cost disclosure?

Retrieving top-5 relevant chunks...
✓ Retrieved 5 chunks

Generating compliance ruling...

================================================================================
COMPLIANCE RULING
================================================================================

According to AAOIFI FAS-28 §3.2, murabaha transactions require full disclosure
of the cost price to the purchaser. [FAS-28 §3.2] The standard mandates that...

--------------------------------------------------------------------------------
Retrieved 5 AAOIFI excerpts
Average relevance score: 0.82

Sources:
  • FAS-28 (score: 0.89)
  • FAS-28 (score: 0.85)
  • FAS-2 (score: 0.78)
  • FAS-1 (score: 0.76)
  • FAS-28 (score: 0.74)
================================================================================
```

---

## Definition of Done (L0)

✅ **Five Success Criteria:**

1. ✅ `chroma_db/` populated from full converted AAOIFI corpus
2. ✅ `pytest -v` passes (2 active + N skipped)
3. ✅ CLI returns answer with at least one `[FAS-XX §Y]` citation
4. ✅ No imports broken across `src/{models,rag,chatbot}/`
5. ✅ `.env`, `chroma_db/`, `data/` gitignored

**Hit those five, L0 is done.** Then we layer SSE on top.

---

## Troubleshooting

### "No markdown files found"
- Ensure `data/aaoifi_md/*.md` exists
- Run AAOIFI converter script first

### "No valid API key found"
- Check `.env` file exists (not `.env.example`)
- Verify `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` is set
- Key must start with `sk-` (OpenAI) or `sk-ant-` (Anthropic)

### "ChromaDB collection is empty"
- Run `python scripts/ingest.py` first
- Check console output for errors during ingestion

### "No relevant AAOIFI standards found"
- Try a different query
- Check if corpus covers the topic
- Lower threshold: `--k 10` to retrieve more chunks

---

## Next Steps (Post-L0)

Once L0 is green:

1. **L1**: Add clarification loop (identify missing variables)
2. **L2**: FastAPI + SSE streaming
3. **L3**: Eval harness (Ragas + DeepEval)
4. **L4**: Production deployment (Redis, PostgreSQL, monitoring)

---

## File Structure

```
.
├── src/
│   ├── models/
│   │   └── schema.py          # Data models (AAOIFICitation, SemanticChunk, ComplianceRuling)
│   ├── rag/
│   │   └── pipeline.py        # RAG retrieval logic
│   └── chatbot/
│       └── cli.py             # Terminal chatbot
├── scripts/
│   └── ingest.py              # Corpus ingestion
├── tests/
│   ├── test_rag_smoke.py      # Smoke tests
│   └── fixtures/
│       └── gold_eval.yaml     # Gold evaluation set (scholar fills)
├── data/
│   └── aaoifi_md/             # AAOIFI markdown corpus
├── chroma_db/                 # ChromaDB storage (gitignored)
├── .env                       # Environment config (gitignored)
├── requirements.txt           # Python dependencies
└── L0_README.md              # This file
```

---

## Key Design Decisions

- **Embedding Model**: `all-mpnet-base-v2` (768-dim, English-only, good for semantic search)
- **Vector DB**: ChromaDB embedded (simple, no server needed for L0)
- **Chunking**: 512 tokens, 50 overlap (preserves context across boundaries)
- **LLM**: OpenAI GPT-4 or Anthropic Claude 3.5 Sonnet (temperature=0.1 for consistency)
- **System Prompt**: Strict AAOIFI adherence - refuse without retrieved context

---

## References

Inspired by:
- **sougaaat/RAG-based-Legal-Assistant** - Legal domain RAG patterns
- **lawglance/lawglance** - Production legal RAG architecture
- **NirDiamant/Controllable-RAG-Agent** - Grounded RAG with verification

---

**L0 = Proof of concept. Keep it simple. Make it work.**
