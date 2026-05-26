# AAOIFI Corpus Setup

## Good News! 🎉

You already have a **complete AAOIFI corpus** in:
```
gemini-gem-prototype/knowledge-base/
```

## What You Have

- **52 AAOIFI Standards** (both English and Arabic)
- **104 total markdown files** (52 × 2 languages)
- Mix of:
  - Financial Accounting Standards (FAS)
  - Sharia Standards
  - Conceptual Frameworks

## L0 Configuration

L0 is configured to use **English files only** because:
- Embedding model `all-mpnet-base-v2` is English-only
- Faster processing for initial testing
- Arabic support can be added in L1+ with multilingual models

### Files That Will Be Ingested

All files matching pattern: `*_en_*.md` or `*_en.*.md`

Examples:
- `AAOIFI_Standard_01_en_Financial_Accounting_Standard_No._(1)...md`
- `AAOIFI_Standard_28_en_Financial_Accounting_Standard_2_8.md`
- etc.

**Total: ~52 English standards**

### Files That Will Be Skipped (L0)

- Arabic files (`*_ar_*.md`) - ~52 files
- Index files (`INDEX.md`, `CONVERSION_SUMMARY.md`)

## Updated Configuration

Your `.env` should now have:

```env
CORPUS_DIR=./gemini-gem-prototype/knowledge-base
```

This replaces the previous:
```env
CORPUS_DIR=./data/aaoifi_md  # Old sample location
```

## Expected Ingestion Results

When you run `python scripts/ingest.py`:

```
Loading embedding model: sentence-transformers/all-mpnet-base-v2
Initializing ChromaDB at: ./chroma_db
Found 52 English AAOIFI standards to process
(Skipping 52 Arabic files - use multilingual model for Arabic support)

Processing: AAOIFI_Standard_01_en_...
  Generated 45 chunks
  ✓ Stored 45 chunks

Processing: AAOIFI_Standard_02_en_...
  Generated 38 chunks
  ✓ Stored 38 chunks

...

============================================================
Ingestion complete!
Total chunks stored: ~2,500-3,000 (estimated)
ChromaDB location: ./chroma_db
============================================================
```

**Time estimate:** 5-10 minutes for full corpus (vs 30 seconds for samples)

## Storage Requirements

- **ChromaDB size**: ~150-200 MB
- **RAM during ingestion**: ~3-4 GB
- **RAM during queries**: ~2 GB

## Python Version Update

Also updated to recommend **Python 3.11+** (you have 3.14.4):

**Benefits:**
- 25-30% faster than 3.9
- Better for embedding generation
- Improved error messages
- Better type hints

## Next Steps

1. **Update your .env file:**
   ```bash
   copy .env.example .env
   # Edit .env and set:
   # CORPUS_DIR=./gemini-gem-prototype/knowledge-base
   # OPENAI_API_KEY=sk-...
   ```

2. **Run ingestion (will take 5-10 min):**
   ```bash
   python scripts/ingest.py
   ```

3. **Run tests:**
   ```bash
   pytest -v
   ```

4. **Try queries on real AAOIFI standards:**
   ```bash
   python -m src.chatbot.cli --query "What does AAOIFI require for murabaha cost disclosure?"
   ```

## Adding Arabic Support (Future)

To enable Arabic in L1+:

1. **Change embedding model** in `.env`:
   ```env
   EMBED_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2
   ```

2. **Update ingestion script** to include Arabic files:
   ```python
   # Include both English and Arabic
   all_files = [f for f in md_files if "_en_" in f.name or "_ar_" in f.name]
   ```

3. **Re-run ingestion:**
   ```bash
   python scripts/ingest.py
   ```

**Note:** Multilingual model is:
- Slightly slower
- Slightly less accurate for English
- But supports 50+ languages including Arabic

## Corpus Quality

Your corpus appears to be well-structured:
- Consistent naming convention
- Both languages available
- Includes INDEX.md and CONVERSION_SUMMARY.md
- Ready for production use

## Comparison: Sample vs Real Corpus

| Metric | Sample (data/aaoifi_md) | Real (gemini-gem-prototype) |
|--------|-------------------------|------------------------------|
| Files | 2 | 52 (English) |
| Standards | FAS-1, FAS-28 | Full AAOIFI suite |
| Chunks | ~112 | ~2,500-3,000 |
| Coverage | Minimal | Comprehensive |
| Ingestion Time | 30 seconds | 5-10 minutes |
| Storage | ~5 MB | ~150-200 MB |

## Verification

After ingestion, verify corpus loaded correctly:

```bash
python -c "from chromadb import PersistentClient; c = PersistentClient(path='./chroma_db'); print(f'Chunks: {c.get_collection(\"aaoifi\").count()}')"
```

Expected output:
```
Chunks: 2500-3000
```

---

**You're ready to ingest the full AAOIFI corpus! 🚀**
