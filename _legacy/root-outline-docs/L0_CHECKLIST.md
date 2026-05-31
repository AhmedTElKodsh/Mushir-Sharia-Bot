# L0 Setup Checklist

Use this checklist to verify your L0 setup is complete and working.

---

## Pre-Setup Checklist

- [ ] Python 3.9+ installed (3.11+ recommended) (`python --version`)
- [ ] Git installed (optional, for version control)
- [ ] OpenAI API key OR Anthropic API key obtained
- [ ] Terminal/command prompt access

---

## Setup Checklist

### 1. Virtual Environment

- [ ] Created virtual environment: `python -m venv .venv`
- [ ] Activated environment: `.venv\Scripts\activate` (Windows)
- [ ] Prompt shows `(.venv)` prefix

### 2. Dependencies

- [ ] Installed requirements: `pip install -r requirements.txt`
- [ ] No error messages during installation
- [ ] Can import key packages:
  ```python
  python -c "import sentence_transformers, chromadb, langchain_text_splitters"
  ```

### 3. Environment Configuration

- [ ] Created `.env` file: `copy .env.example .env`
- [ ] Added API key to `.env`:
  - [ ] `OPENAI_API_KEY=sk-...` OR
  - [ ] `ANTHROPIC_API_KEY=sk-ant-...`
- [ ] Verified other variables are set:
  - [ ] `EMBED_MODEL=sentence-transformers/all-mpnet-base-v2`
  - [ ] `CHROMA_DIR=./chroma_db`
  - [ ] `CORPUS_DIR=./data/aaoifi_md`

### 4. Corpus Verification

- [ ] Directory exists: `data/aaoifi_md/`
- [ ] Sample files present:
  - [ ] `FAS-1-sample.md`
  - [ ] `FAS-28-sample.md`
- [ ] (Optional) Added real AAOIFI markdown files

### 5. Setup Verification

- [ ] Ran: `python scripts/setup_l0.py`
- [ ] All checks passed:
  - [ ] ✓ Python Version
  - [ ] ✓ Virtual Environment
  - [ ] ✓ Environment File
  - [ ] ✓ API Key
  - [ ] ✓ Core Dependencies
  - [ ] ✓ AAOIFI Corpus

---

## Ingestion Checklist

- [ ] Ran: `python scripts/ingest.py`
- [ ] No error messages
- [ ] Output shows:
  - [ ] "Loading embedding model: sentence-transformers/all-mpnet-base-v2"
  - [ ] "Initializing ChromaDB at: ./chroma_db"
  - [ ] "Found X markdown files to process"
  - [ ] "Ingestion complete! Total chunks stored: X"
- [ ] Directory created: `chroma_db/`
- [ ] Files exist in `chroma_db/`:
  - [ ] `chroma.sqlite3`
  - [ ] Parquet files

---

## Testing Checklist

- [ ] Ran: `pytest -v`
- [ ] Test results:
  - [ ] `test_ingest_nonempty` PASSED
  - [ ] `test_retrieval_smoke` PASSED
  - [ ] `test_gold_evaluation` SKIPPED (expected)
- [ ] Summary shows: "2 passed, 1 skipped"

---

## Query Checklist

- [ ] Ran sample query:
  ```bash
  python -m src.chatbot.cli --query "What does AAOIFI require for murabaha cost disclosure?"
  ```
- [ ] Output shows:
  - [ ] "L0 AAOIFI Compliance Chatbot" header
  - [ ] "Initializing RAG pipeline..."
  - [ ] "Collection contains X chunks"
  - [ ] "Retrieving top-5 relevant chunks..."
  - [ ] "✓ Retrieved X chunks"
  - [ ] "Generating compliance ruling..."
  - [ ] "COMPLIANCE RULING" section
  - [ ] Answer text with citations (e.g., `[FAS-28 §3.2]`)
  - [ ] "Sources:" list with scores
- [ ] No error messages

---

## Verification Checklist

### File Structure

- [ ] `src/models/schema.py` exists
- [ ] `src/rag/pipeline.py` exists
- [ ] `src/chatbot/cli.py` exists
- [ ] `scripts/ingest.py` exists
- [ ] `tests/test_rag_smoke.py` exists
- [ ] All `__init__.py` files exist

### Git Status (Optional)

- [ ] `.env` is gitignored (not tracked)
- [ ] `chroma_db/` is gitignored (not tracked)
- [ ] `.venv/` is gitignored (not tracked)
- [ ] Source files are tracked

---

## Definition of Done

L0 is complete when ALL of these are true:

- [ ] **1. ChromaDB populated**: `chroma_db/` directory exists with data
- [ ] **2. Tests pass**: `pytest -v` shows 2 passed, 1 skipped
- [ ] **3. CLI works**: Query returns answer with `[FAS-XX §Y]` citation
- [ ] **4. No broken imports**: All Python files import successfully
- [ ] **5. Gitignore correct**: Sensitive files not tracked

---

## Troubleshooting Checklist

If something doesn't work, check:

### Virtual Environment Issues

- [ ] Virtual environment is activated (see `(.venv)` in prompt)
- [ ] Using correct Python: `which python` or `where python`
- [ ] Python version is 3.9+: `python --version`

### Dependency Issues

- [ ] Ran `pip install -r requirements.txt` in activated venv
- [ ] No error messages during installation
- [ ] Can import packages: `python -c "import sentence_transformers"`

### API Key Issues

- [ ] `.env` file exists (not `.env.example`)
- [ ] API key is set in `.env`
- [ ] Key format is correct:
  - OpenAI: starts with `sk-proj-` or `sk-`
  - Anthropic: starts with `sk-ant-`
- [ ] No spaces around `=` in `.env`

### Corpus Issues

- [ ] `data/aaoifi_md/` directory exists
- [ ] At least 2 sample files present
- [ ] Files are `.md` format
- [ ] Files contain text (not empty)

### ChromaDB Issues

- [ ] Ran `python scripts/ingest.py` successfully
- [ ] `chroma_db/` directory created
- [ ] `chroma.sqlite3` file exists
- [ ] No permission errors

### LLM Issues

- [ ] API key is valid (not expired)
- [ ] Have internet connection
- [ ] API service is not down
- [ ] Have API credits/quota

---

## Quick Diagnostic

Run this to check everything at once:

```bash
python scripts/setup_l0.py
```

Expected output:
```
============================================================
L0 Setup Verification
============================================================

Python Version:
✓ Python 3.X.X

Virtual Environment:
✓ Virtual environment active

Environment File:
✓ .env file exists

API Key:
✓ OpenAI API key configured
  (or Anthropic API key configured)

Dependencies:
✓ Core dependencies installed

AAOIFI Corpus:
✓ Corpus ready (X files)

============================================================
✓ All checks passed! Ready to run L0
============================================================
```

---

## Success Criteria

You know L0 is working when:

✅ Setup verification passes all checks  
✅ Ingestion completes without errors  
✅ Tests pass (2 passed, 1 skipped)  
✅ CLI query returns cited answer  
✅ No error messages anywhere  

---

## Next Steps After L0

Once all checkboxes are ticked:

1. **Test with different queries**
   ```bash
   python -m src.chatbot.cli --query "What are the components of financial statements?"
   python -m src.chatbot.cli --query "What is required for Ijarah accounting?"
   ```

2. **Add real AAOIFI corpus** (if available)
   - Place markdown files in `data/aaoifi_md/`
   - Re-run: `python scripts/ingest.py`
   - Re-test: `pytest -v`

3. **Work with scholar on gold evaluation**
   - Add test cases to `tests/fixtures/gold_eval.yaml`
   - Re-run: `pytest -v`
   - Verify `test_gold_evaluation` passes

4. **Ready for L1**
   - Say: "L0 works, let's build L1"
   - Next: Clarification loop implementation

---

## Support

**Still stuck?**

1. Run diagnostic: `python scripts/setup_l0.py`
2. Check error messages carefully
3. Verify each checklist item above
4. Review troubleshooting section
5. Check documentation:
   - [L0_README.md](./L0_README.md)
   - [L0_SETUP_GUIDE.md](./L0_SETUP_GUIDE.md)
   - [L0_ARCHITECTURE.md](./L0_ARCHITECTURE.md)

---

**Print this checklist and tick off items as you go! ✅**
