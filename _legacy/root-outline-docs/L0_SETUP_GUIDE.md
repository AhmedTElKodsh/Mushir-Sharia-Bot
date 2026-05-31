# L0 Setup Guide - Step by Step

This guide walks you through setting up L0 from scratch.

---

## Quick Start (5 minutes)

```bash
# 1. Create virtual environment
python -m venv .venv

# 2. Activate (Windows CMD)
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
copy .env.example .env

# 5. Edit .env and add your API key
# OPENAI_API_KEY=sk-your-key-here

# 6. Verify setup
python scripts/setup_l0.py

# 7. Ingest corpus
python scripts/ingest.py

# 8. Run tests
pytest -v

# 9. Try a query
python -m src.chatbot.cli --query "What does AAOIFI require for murabaha cost disclosure?"
```

---

## Detailed Setup

### Step 1: Virtual Environment

**Why?** Isolates dependencies from your system Python.

```bash
python -m venv .venv
```

**Activate:**
- **Windows CMD**: `.venv\Scripts\activate`
- **Windows PowerShell**: `.venv\Scripts\Activate.ps1`
- **Linux/Mac**: `source .venv/bin/activate`

**Verify:** Your prompt should show `(.venv)` prefix.

---

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

**What gets installed:**
- `sentence-transformers` - Embedding model
- `chromadb` - Vector database
- `langchain-text-splitters` - Text chunking
- `openai` / `anthropic` - LLM APIs
- `pytest` - Testing framework

**Time:** ~2-3 minutes (downloads ~500MB of models on first run)

---

### Step 3: Configure Environment

```bash
copy .env.example .env
```

**Edit `.env` file:**

```env
# Add your API key (choose one)
OPENAI_API_KEY=sk-proj-...
# OR
ANTHROPIC_API_KEY=sk-ant-...

# These are already set correctly:
EMBED_MODEL=sentence-transformers/all-mpnet-base-v2
CHROMA_DIR=./chroma_db
CORPUS_DIR=./data/aaoifi_md
```

**Getting API Keys:**
- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/settings/keys

---

### Step 4: Verify Setup

```bash
python scripts/setup_l0.py
```

**Expected output:**
```
✓ Python 3.9+ (3.11+ recommended)
✓ Virtual environment active
✓ .env file exists
✓ API key configured
✓ Core dependencies installed
✓ Corpus ready (2 files)

✓ All checks passed! Ready to run L0
```

**If checks fail:** Follow the action items shown in the output.

---

### Step 5: Ingest Corpus

```bash
python scripts/ingest.py
```

**What happens:**
1. Reads markdown files from `data/aaoifi_md/`
2. Splits into 512-token chunks with 50-token overlap
3. Generates embeddings using `all-mpnet-base-v2`
4. Stores in ChromaDB at `./chroma_db/`

**Expected output:**
```
Loading embedding model: sentence-transformers/all-mpnet-base-v2
Initializing ChromaDB at: ./chroma_db
Found 2 markdown files to process

Processing: FAS-28-sample.md
  Generated 45 chunks
  ✓ Stored 45 chunks

Processing: FAS-1-sample.md
  Generated 67 chunks
  ✓ Stored 67 chunks

============================================================
Ingestion complete!
Total chunks stored: 112
ChromaDB location: ./chroma_db
============================================================
```

**Time:** ~30 seconds for sample files, ~5-10 minutes for full AAOIFI corpus

---

### Step 6: Run Tests

```bash
pytest -v
```

**Expected output:**
```
tests/test_rag_smoke.py::test_ingest_nonempty PASSED
tests/test_rag_smoke.py::test_retrieval_smoke PASSED
tests/test_rag_smoke.py::test_gold_evaluation SKIPPED (Gold evaluation set is empty)

======================== 2 passed, 1 skipped ========================
```

**What's tested:**
- ✅ ChromaDB is populated
- ✅ Retrieval returns relevant chunks
- ⊘ Gold evaluation (skipped until scholar adds test cases)

---

### Step 7: Query via CLI

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
Collection contains 112 chunks

Query: What does AAOIFI require for murabaha cost disclosure?

Retrieving top-5 relevant chunks...
✓ Retrieved 5 chunks

Generating compliance ruling...

================================================================================
COMPLIANCE RULING
================================================================================

According to AAOIFI FAS-28 §3.2, the Islamic financial institution MUST 
disclose the actual cost price of the goods to the purchaser. [FAS-28 §3.2]

This disclosure is a fundamental requirement for the validity of a Murabaha 
transaction under Sharia principles. The cost price includes:
- Purchase price of the goods
- Direct acquisition costs
- Transportation and handling costs
- Any other costs directly attributable to bringing the goods to their 
  present location and condition

--------------------------------------------------------------------------------
Retrieved 5 AAOIFI excerpts
Average relevance score: 0.87

Sources:
  • FAS-28-sample (score: 0.92)
  • FAS-28-sample (score: 0.89)
  • FAS-28-sample (score: 0.86)
  • FAS-28-sample (score: 0.83)
  • FAS-1-sample (score: 0.81)
================================================================================
```

**Success!** You now have a working L0 RAG loop with:
- ✅ Terminal input
- ✅ Semantic retrieval from AAOIFI corpus
- ✅ LLM-generated answer
- ✅ Citations to source standards

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'sentence_transformers'"

**Cause:** Dependencies not installed or wrong Python environment.

**Fix:**
```bash
# Ensure venv is activated (should see (.venv) in prompt)
.venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt
```

---

### "No valid API key found"

**Cause:** `.env` file missing or API key not set correctly.

**Fix:**
```bash
# Check .env exists
dir .env

# If not, create it
copy .env.example .env

# Edit .env and add:
OPENAI_API_KEY=<your-openai-api-key>
```

**Verify key format:**
- OpenAI: Must start with `sk-proj-` or `sk-`
- Anthropic: Must start with `sk-ant-`

---

### "ChromaDB collection is empty"

**Cause:** Ingestion script not run yet.

**Fix:**
```bash
python scripts/ingest.py
```

---

### "No markdown files found in data/aaoifi_md"

**Cause:** AAOIFI corpus not populated.

**For testing:** Two sample files are included (`FAS-1-sample.md`, `FAS-28-sample.md`)

**For production:** Run the AAOIFI converter script to generate full corpus.

---

### "No relevant AAOIFI standards found"

**Cause:** Query doesn't match corpus content or threshold too high.

**Fix:**
```bash
# Try retrieving more chunks
python -m src.chatbot.cli --query "your question" --k 10

# Or try a different query that matches sample content:
python -m src.chatbot.cli --query "What are the components of financial statements?"
```

---

## Next Steps After L0

Once L0 is working:

1. **Add Real AAOIFI Corpus**
   - Run AAOIFI converter on official standards
   - Re-run ingestion: `python scripts/ingest.py`

2. **Add Gold Evaluation Cases**
   - Work with Islamic finance scholar
   - Add test cases to `tests/fixtures/gold_eval.yaml`
   - Re-run tests: `pytest -v`

3. **Build L1: Clarification Loop**
   - Add variable extraction
   - Implement state machine for multi-turn clarification
   - Test with incomplete queries

4. **Build L2: FastAPI + SSE**
   - Add REST API endpoints
   - Implement Server-Sent Events for streaming
   - Add WebSocket support

5. **Build L3: Evaluation Harness**
   - Integrate Ragas for faithfulness metrics
   - Add DeepEval for CI/CD gates
   - Set up nightly evaluation runs

---

## File Structure Reference

```
.
├── src/
│   ├── models/
│   │   ├── __init__.py
│   │   └── schema.py              # Data models
│   ├── rag/
│   │   ├── __init__.py
│   │   └── pipeline.py            # RAG retrieval
│   └── chatbot/
│       ├── __init__.py
│       └── cli.py                 # CLI interface
├── scripts/
│   ├── ingest.py                  # Corpus ingestion
│   ├── check_corpus.py            # Corpus verification
│   └── setup_l0.py                # Setup verification
├── tests/
│   ├── __init__.py
│   ├── test_rag_smoke.py          # Smoke tests
│   └── fixtures/
│       └── gold_eval.yaml         # Gold test cases
├── data/
│   └── aaoifi_md/                 # AAOIFI markdown corpus
│       ├── FAS-1-sample.md
│       └── FAS-28-sample.md
├── chroma_db/                     # Vector database (gitignored)
├── .venv/                         # Virtual environment (gitignored)
├── .env                           # Environment config (gitignored)
├── .env.example                   # Environment template
├── requirements.txt               # Python dependencies
├── L0_README.md                   # L0 overview
└── L0_SETUP_GUIDE.md             # This file
```

---

## Support

**Issues?** Check:
1. Python version: `python --version` (need 3.9+)
2. Virtual environment active: Look for `(.venv)` in prompt
3. Dependencies installed: `pip list | grep sentence-transformers`
4. API key set: `python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('OK' if os.getenv('OPENAI_API_KEY') else 'Missing')"`
5. Corpus exists: `dir data\aaoifi_md\*.md`

**Still stuck?** Run the diagnostic:
```bash
python scripts/setup_l0.py
```

---

**L0 = Proof of concept. Keep it simple. Make it work. ✅**
