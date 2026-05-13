# Scripts Guide

This document provides detailed information about the utility scripts available in the `scripts/` directory.

## Overview

The scripts directory contains utilities for acquiring, downloading, and converting AAOIFI standards documents. These scripts support the data acquisition phase of the Sharia Compliance Chatbot system.

## Scripts

### 1. check_corpus.py

**Purpose:** Verify that the AAOIFI markdown corpus exists and is ready for ingestion into the vector database.

**Requirements:**
```bash
pip install python-dotenv
```

**Usage:**

```bash
python scripts/check_corpus.py
```

**Features:**

- **Directory Verification:** Checks if corpus directory exists
- **File Detection:** Scans for markdown files in corpus directory
- **Sample Display:** Shows first 5 files with sizes
- **Actionable Guidance:** Provides clear next steps if corpus is missing or empty
- **Environment Configuration:** Respects `CORPUS_DIR` environment variable

**Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `CORPUS_DIR` | `./data/aaoifi_md` | Path to AAOIFI markdown corpus directory |

**Output Format:**

```
============================================================
L0 Corpus Check
============================================================

✓ Corpus directory exists: ./data/aaoifi_md
✓ Found 15 markdown files

Sample files:
  • AAOIFI_Standard_01_en_Murabaha.md (45.2 KB)
  • AAOIFI_Standard_02_en_Ijarah.md (38.7 KB)
  • AAOIFI_Standard_03_en_Musharaka.md (52.1 KB)
  • AAOIFI_Standard_04_en_Mudaraba.md (41.8 KB)
  • AAOIFI_Standard_05_en_Disclosure.md (36.5 KB)
  ... and 10 more

============================================================
✓ Corpus is ready for ingestion!
============================================================

Next step: python scripts/ingest.py
```

**Error Scenarios:**

**Scenario 1: Directory Not Found**
```
============================================================
L0 Corpus Check
============================================================

❌ Corpus directory not found: ./data/aaoifi_md

Action required:
  1. Create directory: mkdir -p ./data/aaoifi_md
  2. Run AAOIFI converter to populate with .md files
```

**Scenario 2: No Markdown Files**
```
============================================================
L0 Corpus Check
============================================================

✓ Corpus directory exists: ./data/aaoifi_md
❌ No markdown files found in ./data/aaoifi_md

Action required:
  Run AAOIFI converter script to generate markdown files
  Expected: data/aaoifi_md/*.md
```

**Integration with Workflow:**

This script is designed to be run **before** `ingest.py` to ensure the corpus is ready:

```bash
# Step 1: Check corpus
python scripts/check_corpus.py

# Step 2: If corpus is ready, proceed with ingestion
python scripts/ingest.py
```

**Return Codes:**

- `0` (implicit): Corpus is ready
- No explicit error codes (script continues regardless)

**Use Cases:**

1. **Pre-Ingestion Validation:** Verify corpus before running expensive embedding operations
2. **CI/CD Pipelines:** Automated checks in deployment workflows
3. **Debugging:** Quick diagnostic when ingestion fails
4. **Documentation:** Show users what files will be processed

---

### 2. ingest.py

**Purpose:** Chunk AAOIFI markdown files and embed them into ChromaDB vector database.

**Requirements:**
```bash
pip install python-dotenv langchain-text-splitters sentence-transformers chromadb
```

**Usage:**

```bash
python scripts/ingest.py
```

**Features:**

- **Semantic Chunking:** Uses LangChain RecursiveCharacterTextSplitter
- **Embedding Generation:** sentence-transformers/paraphrase-multilingual-mpnet-base-v2 (768-dim)
- **Vector Storage:** ChromaDB persistent storage using cosine space
- **Metadata Tracking:** Stores source file, filename language, detected text language, embedding model, chunk index, and total chunks
- **Progress Reporting:** Real-time processing status per file
- **Error Handling:** Continues processing if individual files fail

**Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `CORPUS_DIR` | `./gemini-gem-prototype/knowledge-base` | Path to AAOIFI markdown corpus |
| `CHROMA_DIR` | `./chroma_db_multilingual` | ChromaDB storage location |
| `EMBED_MODEL` | `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` | Embedding model |
| `INGEST_LANGUAGES` | `en,ar` | Comma-separated language codes to ingest |

**Chunking Configuration:**

- **Chunk Size:** 512 tokens
- **Chunk Overlap:** 50 tokens
- **Separators:** `["\n\n", "\n", ". ", " ", ""]` (paragraph → sentence → word)

**Output Format:**

```
Loading embedding model: sentence-transformers/paraphrase-multilingual-mpnet-base-v2
Initializing ChromaDB at: ./chroma_db_multilingual
Found 104 AAOIFI standards to process for languages: en, ar

Processing: AAOIFI_Standard_01_en_Murabaha.md
  Generated 87 chunks
  ✓ Stored 87 chunks

Processing: AAOIFI_Standard_02_en_Ijarah.md
  Generated 72 chunks
  ✓ Stored 72 chunks

...

============================================================
Ingestion complete!
Total chunks stored: 1245
ChromaDB location: ./chroma_db_multilingual
============================================================
```

**Error Handling:**

```
Processing: AAOIFI_Standard_10_en_Example.md
  ✗ Error processing AAOIFI_Standard_10_en_Example.md: [Errno 2] No such file or directory
```

**ChromaDB Collection Schema:**

```python
{
    "ids": ["md5_hash_of_filename:chunk_idx"],
    "embeddings": [[768-dim vector]],
    "documents": ["chunk text content"],
    "metadatas": [{
        "source_file": "AAOIFI_Standard_01_en_Murabaha.md",
        "standard_number": "AAOIFI_Standard_01_en_Murabaha",
        "language": "en",
        "source_language": "en",
        "embedding_model": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        "embedding_normalized": true,
        "chunk_idx": 0,
        "total_chunks": 87
    }]
}
```

**Performance:**

- **Embedding Speed:** ~100 chunks/second on CPU, ~500 chunks/second on GPU
- **Storage:** ~1KB per chunk (text + embedding + metadata)
- **Typical Corpus:** 15 standards × 80 chunks = 1200 chunks ≈ 1.2MB

**Integration with RAG Pipeline:**

After ingestion, the ChromaDB collection is ready for:
1. Similarity search queries
2. Top-k retrieval for RAG
3. Compliance analysis with AAOIFI citations

---

### 3. convert_pdf_to_markdown.py

**Purpose:** Convert AAOIFI PDF standards to clean Markdown format optimized for knowledge bases and RAG systems.

**Requirements:**
```bash
pip install pymupdf
```

**Usage:**

```bash
# Convert single PDF file
python scripts/convert_pdf_to_markdown.py --input "path/to/FAS01.pdf" --output "output/"

# Convert all PDFs in a directory
python scripts/convert_pdf_to_markdown.py --input-dir "pdfs/" --output-dir "output/"

# Convert with custom output filename
python scripts/convert_pdf_to_markdown.py --input "FAS01.pdf" --output "output/" --name "AAOIFI_FAS01_General-Presentation"
```

**Features:**

- **Text Extraction:** Uses PyMuPDF (fitz) to extract text with layout preservation
- **Structure Detection:** Automatically detects document structure including:
  - Document title
  - Section headers (e.g., "1. Introduction")
  - Subsection headers (e.g., "1.1 Background")
  - Sub-subsection headers (e.g., "1.1.1 Purpose")
- **Text Cleaning:**
  - Removes page numbers
  - Removes common headers/footers (AAOIFI, Financial Accounting Standard)
  - Fixes broken hyphenation (word-\nword → word)
  - Removes excessive whitespace
  - Fixes common OCR errors (ﬁ → fi, ﬂ → fl)
- **Markdown Conversion:**
  - Converts section headers to proper Markdown headers (##, ###, ####)
  - Preserves paragraph structure
  - Maintains readability
- **Metadata Header:**
  - Adds standard number (FAS-XX)
  - Includes title and source URL
  - Adds conversion date
  - Generates table of contents with anchor links
- **Naming Convention:**
  - Follows pattern: `AAOIFI_FASXX_Title.md`
  - Supports custom naming via `--name` parameter

**Output Format:**

```markdown
# AAOIFI FAS-01: General Presentation and Disclosure in the Financial Statements

**Standard Number:** FAS-01  
**Title:** General Presentation and Disclosure in the Financial Statements  
**Source:** https://aaoifi.com/accounting-standards-2/?lang=en  
**Converted:** 2024-01-15  
**Format:** Markdown (converted from PDF)

---

## Table of Contents

1. [Introduction](#introduction)
2. [Objective](#objective)
3. [Scope](#scope)
...

---

## 1. Introduction

[Content here...]
```

**Command-Line Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `--input` | Conditional | Input PDF file path (required if not using `--input-dir`) |
| `--output` | Conditional | Output directory for single file conversion |
| `--input-dir` | Conditional | Input directory containing PDF files (required if not using `--input`) |
| `--output-dir` | Conditional | Output directory for batch conversion |
| `--name` | Optional | Custom output filename (without .md extension) |

**Error Handling:**

- Validates input file/directory exists
- Handles PDF extraction failures gracefully
- Continues batch processing if individual files fail
- Provides detailed progress reporting
- Returns exit code 0 on success, 1 on failure

**Batch Processing:**

When using `--input-dir`, the script:
1. Finds all PDF files in the directory
2. Processes each file sequentially
3. Reports progress for each file
4. Provides summary statistics (successful/failed/total)

**Example Output:**

```
============================================================
Converting: FAS01.pdf
============================================================

Step 1: Extracting text from PDF...
Processing 45 pages...
  Processed 10/45 pages...
  Processed 20/45 pages...
  Processed 30/45 pages...
  Processed 40/45 pages...
✓ Extracted 125430 characters from PDF

Step 2: Cleaning text...
✓ Cleaned text (124856 characters)

Step 3: Detecting document structure...
✓ Detected 12 sections
  Title: GENERAL PRESENTATION AND DISCLOSURE IN THE FINANCIAL STATEMENTS

Step 4: Converting to Markdown...
✓ Converted to Markdown

Step 5: Adding metadata header...
✓ Added metadata header

Step 6: Saving to file...
  Output: output/AAOIFI_FAS01.md
✓ Saved successfully

============================================================
✓ Conversion complete: AAOIFI_FAS01.md
============================================================
```

**Integration with RAG Pipeline:**

The converted Markdown files are optimized for:
- Semantic chunking (clear section boundaries)
- Vector embedding (clean, structured text)
- Citation extraction (preserved section numbers)
- Human readability (proper formatting)

**Limitations:**

- Requires well-structured PDF input
- May not handle heavily formatted tables perfectly
- OCR quality depends on source PDF quality
- Section detection relies on common numbering patterns

**Future Enhancements:**

See `scripts/CONVERTER_IMPROVEMENTS.md` for planned improvements including:
- Table extraction and Markdown table formatting
- Image extraction and embedding
- Multi-language support (Arabic)
- Advanced OCR error correction
- Parallel processing for large batches

---

### 6. test_bot.py

**Purpose:** Quick end-to-end test script to verify the API server is working correctly with all components integrated.

**Requirements:**
```bash
pip install requests
```

**Usage:**

```bash
# Ensure the server is running first (python -m src.api.main or similar)
python test_bot.py
```

**Features:**

- **Health Check:** Tests `/health` endpoint for basic server availability
- **Readiness Check:** Tests `/ready` endpoint to verify all infrastructure components
- **Real Query Test:** Sends actual compliance query to `/api/v1/query` endpoint
- **Response Validation:** Validates answer, citations, and metadata structure
- **Error Handling:** 30-second timeout with graceful error messages
- **Formatted Output:** Clean, emoji-enhanced console output for easy reading
- **Next Steps Guidance:** Provides actionable next steps after testing

**Tested Endpoints:**

1. **GET /health** - Basic health check
2. **GET /ready** - Infrastructure readiness check
3. **POST /api/v1/query** - Compliance query endpoint

**Environment Variables:**

No environment variables required. The script assumes the server is running on:
```python
BASE_URL = "http://127.0.0.1:8000"
```

**Output Format:**

```
============================================================
🧪 Mushir Sharia Bot - End-to-End Test
============================================================

✅ Health check: {'status': 'healthy'}

📊 Readiness check:
  Status: ready
  Level: L2
  Infrastructure:
    - vector_db: ready
    - llm: ready
    - embedding_model: ready

🔍 Testing query: I want to invest in a company that produces halal food...

✅ Query successful!

📝 Answer:
  Based on AAOIFI standards...

📚 Citations: 3
  Status: complete

  First citation:
    - Document: FAS-21
    - Standard: FAS-21
    - Score: 0.856

============================================================
✅ Testing complete!
============================================================

💡 Next steps:
  1. Open browser: http://127.0.0.1:8000/chat
  2. Try the interactive chat interface
  3. Check server logs for any errors
```

**Test Query:**

The script uses a sample compliance query:
```
"I want to invest in a company that produces halal food. 
Is this permissible according to AAOIFI standards?"
```

This query tests:
- RAG retrieval from vector database
- LLM compliance analysis
- Citation extraction and formatting
- Response structure validation

**Response Structure Validation:**

The script validates the following response fields:

```python
{
    "answer": str,           # Main compliance ruling
    "status": str,           # "complete" or "incomplete"
    "citations": [           # List of AAOIFI citations
        {
            "document_id": str,
            "standard_number": str,
            "score": float,
            "text": str
        }
    ]
}
```

**Error Scenarios:**

**Scenario 1: Server Not Running**
```
❌ Health check failed. Server may not be running.

💡 Start the server first:
   python -m src.api.main
```

**Scenario 2: Readiness Check Failed**
```
⚠️  Readiness check failed. Some components may not be configured.

📊 Readiness check:
  Status: degraded
  Level: L1
  Infrastructure:
    - vector_db: not_ready
    - llm: ready
    - embedding_model: ready

💡 Check:
   - Vector database populated (run: python scripts/ingest.py)
   - Environment variables configured in .env
```

**Scenario 3: Query Timeout**
```
⏱️  Query timed out after 30 seconds

💡 This might indicate:
   - LLM processing taking too long
   - Vector database query slow
   - Network issues
```

**Scenario 4: Query Failed**
```
❌ Query failed with status 500
  Response: {"detail": "LLM client initialization failed"}

💡 Check:
   - GEMINI_API_KEY in .env
   - Server logs for detailed error
```

**Prerequisites:**

1. **Server Running:** API server must be running on port 8000
2. **Vector Database:** ChromaDB must be populated with AAOIFI standards
3. **Environment:** `.env` file configured with API keys
4. **Dependencies:** `requests` library installed

**Integration with Development Workflow:**

```bash
# 1. Start the server
python -m src.api.main

# 2. In another terminal, run the test
python test_bot.py

# 3. Review results and check server logs
```

**Integration with CI/CD:**

This script can be used in automated testing:

```bash
# In CI/CD pipeline
python -m src.api.main &
SERVER_PID=$!
sleep 5  # Wait for server to start

python test_bot.py
TEST_RESULT=$?

kill $SERVER_PID

if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ End-to-end tests passed"
else
    echo "❌ End-to-end tests failed"
    exit 1
fi
```

**Use Cases:**

1. **Development Testing:** Quick verification during development
2. **Pre-Deployment Checks:** Ensure everything works before deploying
3. **Smoke Testing:** Basic functionality test after changes
4. **Debugging:** Identify which component is failing
5. **Documentation:** Show users how to verify their setup

**Timeout Configuration:**

- **Default Timeout:** 30 seconds
- **Rationale:** Allows for LLM processing and vector search
- **Customization:** Modify `timeout=30` parameter in `requests.post()` call

**Comparison with test_space_query.py:**

| Feature | test_bot.py | test_space_query.py |
|---------|-------------|---------------------|
| **Target** | Local server | Deployed Hugging Face Space |
| **URL** | http://127.0.0.1:8000 | https://AElKodsh-mushir-sharia-bot.hf.space |
| **Use Case** | Development testing | Production verification |
| **Endpoints** | /health, /ready, /api/v1/query | /api/v1/query, /api/v1/query/stream |
| **Streaming** | No | Yes (SSE) |
| **Readiness** | Yes | No |

**Limitations:**

- No streaming endpoint testing (use test_space_query.py for that)
- Single query only (no batch testing)
- No authentication testing
- Hardcoded base URL (update if server port changes)

**Future Enhancements:**

- Add command-line arguments for custom queries and base URL
- Support multiple test queries for comprehensive testing
- Add performance benchmarking
- Implement retry logic with exponential backoff
- Add JSON output mode for CI/CD integration
- Test streaming endpoint when available locally
- Add authentication token testing

---

### 7. test_space_query.py

**Purpose:** Test the deployed Hugging Face Space API endpoints to verify functionality and diagnose issues.

**Requirements:**
```bash
pip install requests
```

**Usage:**

```bash
python scripts/test_space_query.py
```

**Features:**

- **Dual Endpoint Testing:** Tests both regular query and streaming endpoints
- **Real Query Simulation:** Sends actual compliance queries to the deployed Space
- **Response Validation:** Checks status codes, response structure, and data integrity
- **Performance Metrics:** Measures and displays response times
- **Error Diagnostics:** Provides actionable troubleshooting information for common errors
- **Formatted Output:** Clean, emoji-enhanced console output for easy reading
- **Citation Display:** Shows retrieved AAOIFI citations with truncated previews

**Tested Endpoints:**

1. **POST /api/v1/query** - Regular query endpoint
2. **POST /api/v1/query/stream** - Server-Sent Events (SSE) streaming endpoint

**Environment Variables:**

No environment variables required. The Space URL is hardcoded:
```python
SPACE_URL = "https://AElKodsh-mushir-sharia-bot.hf.space"
```

**Output Format:**

```
============================================================
🚀 Mushir Sharia Bot - Space Testing
============================================================

🧪 Testing /api/v1/query endpoint
   URL: https://AElKodsh-mushir-sharia-bot.hf.space/api/v1/query

📤 Sending query: I want to invest in a company that produces halal food. Is this permissible?

⏱️  Response time: 3.45s
📊 Status code: 200

✅ Query successful!

📝 Response:
   Answer: Based on AAOIFI standards...
   Status: complete
   Citations: 3 found

📚 Citations:
   1. AAOIFI_Standard_21_en - Investment in companies that produce halal products is generally...
   2. AAOIFI_Standard_05_en - Disclosure requirements for investment portfolios include...
   3. AAOIFI_Standard_01_en - General presentation standards require transparency in...

🎯 Full response:
{
  "answer": "Based on AAOIFI standards...",
  "status": "complete",
  "citations": [...]
}

============================================================
🧪 Testing /api/v1/query/stream endpoint
   URL: https://AElKodsh-mushir-sharia-bot.hf.space/api/v1/query/stream

📤 Sending query: What are the requirements for Murabaha transactions?

✅ Stream started

📡 Events:
   • thinking
   • retrieved
     Text: Based on AAOIFI FAS-28 (Murabaha and Other Deferred Payment Sales)...
   • token
     Text: The requirements for Murabaha transactions according to AAOIFI standards...
   • done
     Confidence: 0.92

✅ Stream completed successfully

============================================================
✅ Testing complete
============================================================
```

**Error Scenarios:**

**Scenario 1: Internal Server Error (500)**
```
❌ Internal server error
   Response: {"detail": "LLM client initialization failed"}

💡 This might indicate:
   - Missing or invalid GEMINI_API_KEY
   - Vector database not accessible
   - LLM client initialization failure
```

**Scenario 2: Connection Timeout**
```
❌ Request timeout (>60s)
   The Space might be cold-starting or overloaded
```

**Scenario 3: Connection Error**
```
❌ Connection error: [Errno 111] Connection refused
   The Space might be down or restarting
```

**Test Queries:**

The script uses two sample queries:

1. **Regular Query:** "I want to invest in a company that produces halal food. Is this permissible?"
   - Tests basic compliance analysis
   - Validates citation retrieval
   - Checks response structure

2. **Streaming Query:** "What are the requirements for Murabaha transactions?"
   - Tests SSE streaming functionality
   - Validates event types (thinking, retrieved, token, done)
   - Checks streaming data format

**Response Structure Validation:**

The script validates the following response fields:

```python
{
    "answer": str,           # Main compliance ruling
    "status": str,           # "complete" or "incomplete"
    "citations": [           # List of AAOIFI citations
        {
            "document_id": str,
            "text": str,
            "score": float
        }
    ]
}
```

**Integration with CI/CD:**

This script can be integrated into deployment pipelines:

```bash
# In CI/CD pipeline
python scripts/test_space_query.py
if [ $? -eq 0 ]; then
    echo "✅ Space deployment verified"
else
    echo "❌ Space deployment failed"
    exit 1
fi
```

**Use Cases:**

1. **Post-Deployment Verification:** Confirm Space is working after deployment
2. **Health Checks:** Periodic testing to ensure Space remains operational
3. **Debugging:** Diagnose issues with API endpoints or LLM integration
4. **Performance Monitoring:** Track response times over time
5. **Development Testing:** Validate changes before merging to production

**Timeout Configuration:**

- **Default Timeout:** 60 seconds
- **Rationale:** Allows for cold starts and LLM processing time
- **Customization:** Modify `timeout=60` parameter in `requests.post()` calls

**Limitations:**

- Hardcoded Space URL (update if Space name changes)
- No authentication testing (add when auth is implemented)
- Limited error recovery (no automatic retries)
- Single-threaded (no concurrent request testing)

**Future Enhancements:**

- Add command-line arguments for custom queries
- Support multiple Space URLs for testing different deployments
- Add performance benchmarking with multiple queries
- Implement retry logic with exponential backoff
- Add JSON output mode for CI/CD integration
- Support authentication token testing

---

### 8. deploy_to_hf_space.py

**Purpose:** Automated deployment script to upload the application to Hugging Face Space using the Hub API.

**Requirements:**
```bash
pip install huggingface_hub python-dotenv
```

**Usage:**

```bash
python scripts/deploy_to_hf_space.py
```

**Features:**

- **Hub API Integration:** Uses Hugging Face Hub API for programmatic deployment
- **Authentication:** Automatic login using HF_TOKEN from `.env` file
- **Selective Upload:** Uploads only necessary files and folders
- **Ignore Patterns:** Excludes development files, secrets, and build artifacts
- **Progress Reporting:** Real-time feedback on upload status
- **Error Diagnostics:** Provides troubleshooting guidance for common issues
- **Commit Messages:** Automatic commit message generation
- **Post-Deployment Info:** Displays Space URL and build logs link

**Environment Variables:**

| Variable | Required | Description |
|----------|----------|-------------|
| `HF_TOKEN` | Yes | Hugging Face API token with write access |

**Get Your Token:**
Visit https://huggingface.co/settings/tokens and create a token with write access.

**Files and Folders Uploaded:**

```python
paths_to_upload = [
    "src/",                      # Application source code
    "scripts/",                  # Utility scripts
    "requirements.txt",          # Python dependencies
    "Dockerfile",                # Container configuration
    "README.md",                 # Documentation
    ".dockerignore",             # Docker ignore patterns
    "chroma_db_multilingual/",   # Vector database
]
```

**Files Excluded (Ignore Patterns):**

```python
ignore_patterns = [
    "*.pyc",           # Python bytecode
    "__pycache__",     # Python cache directories
    ".env",            # Environment variables (secrets)
    ".git",            # Git repository
    ".venv",           # Virtual environment
    "*.log",           # Log files
    ".pytest_cache",   # Pytest cache
    "*.egg-info",      # Python package metadata
]
```

**Output Format:**

```
============================================================
🚀 Deploying Mushir Sharia Bot to Hugging Face Space
============================================================

Step 1: Authenticating with Hugging Face...
✅ Authenticated successfully

Step 2: Uploading files to AElKodsh/mushir-sharia-bot...
  Uploading from: d:\AI Projects\Freelance\Sabry\Mushir-Sharia-Bot
  To Space: AElKodsh/mushir-sharia-bot

✅ Upload successful!

============================================================
✅ Deployment Complete!
============================================================

Your Space is updating at:
  https://huggingface.co/spaces/AElKodsh/mushir-sharia-bot

Check build logs:
  https://huggingface.co/spaces/AElKodsh/mushir-sharia-bot?logs=container

Note: It may take 2-5 minutes for the Space to rebuild.
============================================================
```

**Error Scenarios:**

**Scenario 1: Missing HF_TOKEN**
```
❌ HF_TOKEN not found in .env file

Please add your Hugging Face token to .env:
  HF_TOKEN=your_token_here

Get your token from: https://huggingface.co/settings/tokens
```

**Scenario 2: Authentication Failed**
```
❌ Authentication failed: Invalid token

💡 Check:
   - Token is correct in .env file
   - Token has not expired
   - Token has write access
```

**Scenario 3: Upload Failed**
```
❌ Upload failed: Repository not found

Troubleshooting:
1. Verify your HF_TOKEN has write access
2. Check the Space exists: https://huggingface.co/spaces/AElKodsh/mushir-sharia-bot
3. Try manually: git push huggingface main
```

**Deployment Configuration:**

```python
repo_id = "AElKodsh/mushir-sharia-bot"
repo_type = "space"
commit_message = "feat: update Space with latest code and improvements"
```

**Integration with Development Workflow:**

```bash
# 1. Make changes to code
git add .
git commit -m "feat: add new feature"

# 2. Test locally
python test_bot.py

# 3. Deploy to Hugging Face Space
python scripts/deploy_to_hf_space.py

# 4. Verify deployment
python scripts/test_space_query.py
```

**Integration with CI/CD:**

```yaml
# Example GitHub Actions workflow
name: Deploy to Hugging Face Space

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install huggingface_hub python-dotenv
      
      - name: Deploy to Space
        env:
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
        run: |
          echo "HF_TOKEN=$HF_TOKEN" > .env
          python scripts/deploy_to_hf_space.py
      
      - name: Test deployment
        run: |
          sleep 120  # Wait for Space to rebuild
          python scripts/test_space_query.py
```

**Comparison with Manual Deployment:**

| Method | deploy_to_hf_space.py | Manual Git Push |
|--------|----------------------|-----------------|
| **Speed** | Fast (API upload) | Slower (Git operations) |
| **Selective Upload** | Yes (ignore patterns) | Requires .gitignore |
| **Authentication** | HF_TOKEN from .env | Git credentials |
| **Automation** | Easy to script | Requires Git commands |
| **Error Handling** | Built-in diagnostics | Manual troubleshooting |
| **Commit Messages** | Auto-generated | Manual |

**Use Cases:**

1. **Rapid Iteration:** Quick deployments during development
2. **CI/CD Pipelines:** Automated deployments on push/merge
3. **Selective Deployment:** Upload only specific files/folders
4. **Testing:** Deploy to staging Space before production
5. **Rollback:** Quick redeployment of previous version

**Prerequisites:**

1. **Hugging Face Account:** Create account at https://huggingface.co
2. **Space Created:** Create Space at https://huggingface.co/new-space
3. **Write Token:** Generate token with write access
4. **Environment Setup:** Add HF_TOKEN to `.env` file
5. **Dependencies Installed:** `pip install huggingface_hub python-dotenv`

**Security Considerations:**

- **Never commit .env file:** Ensure `.env` is in `.gitignore`
- **Token Permissions:** Use tokens with minimal required permissions
- **Token Rotation:** Rotate tokens periodically
- **CI/CD Secrets:** Store HF_TOKEN as encrypted secret in CI/CD platform
- **Audit Logs:** Review Hugging Face audit logs for unauthorized access

**Performance:**

- **Upload Speed:** Depends on file sizes and network speed
- **Typical Upload Time:** 30-60 seconds for ~50MB
- **Space Rebuild Time:** 2-5 minutes after upload
- **Total Deployment Time:** 3-6 minutes from script start to Space ready

**Limitations:**

- **Large Files:** Files >5GB may fail (use Git LFS for large files)
- **Rate Limits:** Hugging Face API has rate limits (typically 1000 requests/hour)
- **Network Dependency:** Requires stable internet connection
- **Space Downtime:** Space is unavailable during rebuild

**Future Enhancements:**

- Add command-line arguments for custom repo_id and commit message
- Support deployment to multiple Spaces (staging, production)
- Add dry-run mode to preview changes before upload
- Implement incremental uploads (only changed files)
- Add rollback functionality to previous deployment
- Support deployment from specific Git branches/tags
- Add deployment verification with automatic rollback on failure
- Implement blue-green deployment strategy

**Troubleshooting:**

**Issue:** "Upload takes too long"
- **Cause:** Large vector database or slow network
- **Solution:** Compress vector database or use Git LFS

**Issue:** "Space fails to build after deployment"
- **Cause:** Missing dependencies or configuration errors
- **Solution:** Check build logs at Space URL + `?logs=container`

**Issue:** "Token permission denied"
- **Cause:** Token lacks write access
- **Solution:** Regenerate token with write permissions

**Issue:** "Repository not found"
- **Cause:** Space doesn't exist or incorrect repo_id
- **Solution:** Create Space first or verify repo_id

---

### 9. download_*.py Scripts

**Purpose:** Various utilities for downloading AAOIFI standards with different strategies.

**Available Scripts:**
- `download_aaoifi_standards.py` - Basic download script
- `download_all_aaoifi.py` - Batch download all standards
- `download_all_aaoifi_v2.py` - Improved version with retry logic
- `download_corrected_aaoifi.py` - Download with corrections
- `retry_failed_aaoifi.py` - Retry previously failed downloads

---

### 10. acquire_aaoifi_standards.py

**Purpose:** Main script for acquiring AAOIFI standards from the official website.

**Usage:**
```bash
python scripts/acquire_aaoifi_standards.py
```

**Features:**
- Web scraping using Playwright
- PDF download and parsing
- HTML content extraction
- Document metadata storage

---

## Typical Data Acquisition and Ingestion Workflow

1. **Download PDFs:**
   ```bash
   python scripts/download_all_aaoifi_v2.py
   ```

2. **Convert to Markdown:**
   ```bash
   python scripts/convert_pdf_to_markdown.py --input-dir data/pdfs/ --output-dir data/aaoifi_md/
   ```

3. **Verify Corpus:**
   ```bash
   python scripts/check_corpus.py
   ```
   - Ensures markdown files exist in `data/aaoifi_md/`
   - Displays sample files and sizes
   - Confirms corpus is ready for ingestion

4. **Ingest into Vector Database:**
   ```bash
   python scripts/ingest.py
   ```
   - Chunks markdown files semantically
   - Generates embeddings
   - Stores in ChromaDB

5. **Verify Ingestion:**
   - Check ChromaDB directory exists: `ls chroma_db/`
   - Review ingestion logs for total chunks stored
   - Test retrieval with sample queries

6. **Integrate with RAG Pipeline:**
   - Use ChromaDB collection for similarity search
   - Retrieve relevant chunks for compliance queries
   - Generate compliance rulings with AAOIFI citations

## Typical Data Acquisition and Ingestion Workflow

1. **Download PDFs:**
   ```bash
   python scripts/download_all_aaoifi_v2.py
   ```

2. **Convert to Markdown:**
   ```bash
   python scripts/convert_pdf_to_markdown.py --input-dir data/pdfs/ --output-dir data/aaoifi_md/
   ```

3. **Verify Corpus:**
   ```bash
   python scripts/check_corpus.py
   ```
   - Ensures markdown files exist in `data/aaoifi_md/`
   - Displays sample files and sizes
   - Confirms corpus is ready for ingestion

4. **Ingest into Vector Database:**
   ```bash
   python scripts/ingest.py
   ```
   - Chunks markdown files semantically
   - Generates embeddings
   - Stores in ChromaDB

5. **Verify Ingestion:**
   - Check ChromaDB directory exists: `ls chroma_db/`
   - Review ingestion logs for total chunks stored
   - Test retrieval with sample queries

6. **Integrate with RAG Pipeline:**
   - Use ChromaDB collection for similarity search
   - Retrieve relevant chunks for compliance queries
   - Generate compliance rulings with AAOIFI citations

## Deployment Workflow

After developing and testing locally:

1. **Deploy to Hugging Face Space:**
   ```bash
   python scripts/deploy_to_hf_space.py
   ```
   - Authenticates with Hugging Face Hub API
   - Uploads source code, scripts, and vector database
   - Excludes development files and secrets
   - Provides Space URL and build logs link

2. **Wait for Space Rebuild:**
   - Space rebuilds automatically after upload (2-5 minutes)
   - Monitor build logs at Space URL + `?logs=container`
   - Check for build errors or missing dependencies

3. **Test Deployed Space:**
   ```bash
   python scripts/test_space_query.py
   ```
   - Verifies both query and streaming endpoints
   - Validates response structure and citations
   - Measures response times
   - Provides diagnostic information for errors

4. **Monitor Results:**
   - Check response times (target: <5s)
   - Verify citations are returned correctly
   - Ensure streaming events are properly formatted
   - Validate error handling for edge cases

5. **Troubleshoot Issues:**
   - Review error messages from test script
   - Check Space logs in Hugging Face dashboard
   - Verify environment variables (GEMINI_API_KEY, etc.)
   - Confirm vector database is accessible

### Deployment Testing Workflow

After deploying to Hugging Face Spaces (see Deployment Workflow above):

1. **Test Deployed Space:**
   ```bash
   python scripts/test_space_query.py
   ```
   - Verifies both query and streaming endpoints
   - Validates response structure and citations
   - Measures response times
   - Provides diagnostic information for errors

2. **Monitor Results:**
   - Check response times (target: <5s)
   - Verify citations are returned correctly
   - Ensure streaming events are properly formatted
   - Validate error handling for edge cases

3. **Troubleshoot Issues:**
   - Review error messages from test script
   - Check Space logs in Hugging Face dashboard
   - Verify environment variables (GEMINI_API_KEY, etc.)
   - Confirm vector database is accessible

---

## Best Practices

### PDF Conversion

1. **Organize Input Files:**
   - Keep PDFs in a dedicated directory (e.g., `data/pdfs/`)
   - Use consistent naming (e.g., `FAS01.pdf`, `FAS02.pdf`)

2. **Review Output:**
   - Always review converted files for quality
   - Check that section headers are properly detected
   - Verify table of contents is accurate

3. **Custom Naming:**
   - Use descriptive names for important standards
   - Follow pattern: `AAOIFI_FASXX_Descriptive-Title`

4. **Batch Processing:**
   - Process all PDFs at once for consistency
   - Review batch summary for failed conversions
   - Re-run failed conversions individually with debugging

### Error Handling

1. **Check Logs:**
   - Review console output for errors
   - Note which files failed and why

2. **Retry Failed Conversions:**
   - Identify problematic PDFs
   - Try manual conversion with custom parameters
   - Report issues for future improvements

3. **Validate Output:**
   - Ensure output files are not empty
   - Check that metadata header is present
   - Verify section structure is preserved

---

## Troubleshooting

### Common Issues

**Issue:** "PyMuPDF not installed"
```bash
# Solution:
pip install pymupdf
```

**Issue:** "No PDF files found in directory"
```bash
# Solution: Check directory path and ensure PDFs exist
ls data/pdfs/*.pdf
```

**Issue:** "Failed to extract text from PDF"
- **Cause:** Corrupted PDF or unsupported format
- **Solution:** Try opening PDF manually, re-download if needed

**Issue:** "Empty output file"
- **Cause:** PDF contains only images (scanned document)
- **Solution:** Use OCR tool first (e.g., Adobe Acrobat, Tesseract)

**Issue:** "Section headers not detected"
- **Cause:** Non-standard formatting in PDF
- **Solution:** Manually review and adjust Markdown output

---

## Contributing

When adding new scripts:

1. Follow the existing naming convention
2. Add comprehensive docstrings
3. Include usage examples in script header
4. Update this documentation
5. Add entry to README.md if user-facing

---

## Related Documentation

- [Technology Research](./technology-research.md) - Research on tools and libraries
- [README.md](../README.md) - Main project documentation
- [Requirements](../.kiro/specs/sharia-compliance-chatbot/requirements.md) - System requirements
- [Design](../.kiro/specs/sharia-compliance-chatbot/design.md) - System design
- [Tasks](../.kiro/specs/sharia-compliance-chatbot/tasks.md) - Implementation tasks

---

## Version History

- **v1.0** (2024-01-15): Initial PDF to Markdown converter
  - Basic text extraction
  - Structure detection
  - Markdown conversion
  - Metadata header generation
