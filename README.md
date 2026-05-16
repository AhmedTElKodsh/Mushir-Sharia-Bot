---
title: Mushir Sharia Bot
emoji: ⚖️
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Sharia Compliance Chatbot

RAG-based Islamic finance compliance analysis system using AAOIFI FAS standards.

## Features

- **AAOIFI FAS Standards**: Acquires and indexes Accounting Standards
- **RAG Pipeline**: Semantic search with Chroma vector database
- **Compliance Analysis**: LLM-powered rulings with citations (OpenRouter API)
- **Semantic Chunking**: LangChain text splitters for legal/financial documents

## Quick Start

```bash
# Create virtual environment (Python 3.11+ recommended, 3.9+ minimum)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your API key (OPENROUTER_API_KEY)

# Convert AAOIFI PDFs to Markdown
python scripts/convert_pdf_to_markdown.py --input-dir data/pdfs/ --output-dir data/markdown/

# Verify corpus is ready for ingestion
python scripts/check_corpus.py

# Ingest AAOIFI standards into vector database
python scripts/ingest.py

# Run RAG pipeline tests
pytest tests/ -v
```

## Project Structure

```
src/
├── models/          # Data models (Document, Chunk, Ruling)
├── rag/            # RAG pipeline (chunking, embeddings, vector store)
├── chatbot/        # Chatbot coordination and generation
│   ├── answer_generator.py      # LLM generation coordinator
│   ├── application_service.py   # Main application orchestrator
│   ├── llm_client.py            # LLM client wrappers (OpenRouter, OpenAI)
│   ├── prompt_builder.py        # AAOIFI-grounded prompt construction
│   ├── citation_validator.py    # Citation extraction and validation
│   ├── clarification_engine.py  # Multi-turn clarification logic
│   └── session_manager.py       # Session state management
├── api/            # FastAPI REST endpoints
├── storage/        # Caching and persistence
└── config/         # Configuration management

scripts/
├── check_corpus.py               # Verify AAOIFI corpus exists and is ready
├── ingest.py                     # Ingest markdown files into ChromaDB
├── convert_pdf_to_markdown.py    # Convert AAOIFI PDFs to Markdown format
├── convert_aaoifi_to_markdown.py # AAOIFI-specific converter with metadata
├── test_space_query.py           # Test deployed Hugging Face Space endpoints
├── deploy_to_hf_space.py         # Deploy application to Hugging Face Space
└── download_*.py                 # Various download utilities

test_bot.py                       # End-to-end API testing script

data/
├── raw/            # Raw AAOIFI PDF files
└── markdown/       # Converted Markdown documents
```

## Environment Variables

Create a `.env` file with:

```bash
# LLM Configuration - OpenRouter
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free

# Vector Database
CHROMA_PERSIST_DIRECTORY=./data/chroma_db
CHROMA_DIR=./chroma_db_multilingual

# Corpus Location
CORPUS_DIR=./gemini-gem-prototype/knowledge-base

# Embedding Model
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2
EMBED_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2

# Hugging Face (for deployment)
HF_TOKEN=your_huggingface_token_here
```

## Requirements

- Python 3.9+ (minimum) / Python 3.11+ (recommended for better performance)
- OpenRouter API key (supports multiple LLM providers including Gemini, GPT-4, Claude)
- ~2GB disk space for embedding model (sentence-transformers)

## Scope

Covers AAOIFI FAS (Financial Accounting Standards) series only. Does NOT include Sharia, Governance, or Ethics standards.

**Disclaimer**: This system provides guidance based on AAOIFI FAS standards only. It does NOT replace consultation with qualified Islamic finance scholars.

## Testing

### Unit Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test modules
pytest tests/test_rag_pipeline.py -v
pytest tests/test_semantic_chunking.py -v
```

### End-to-End API Testing

Test the running API server with the quick test script:

```bash
# Ensure the server is running first
# Then run the end-to-end test
python test_bot.py
```

**Features:**
- ✅ Health check endpoint (`/health`)
- 📊 Readiness check with infrastructure status (`/ready`)
- 🔍 Real compliance query test (`/api/v1/query`)
- Displays answer, citations, and response metadata
- 30-second timeout with error handling

**Expected Output:**
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

**Prerequisites:**
- Server must be running on `http://127.0.0.1:8000`
- Vector database must be populated (run `python scripts/ingest.py`)
- Environment variables configured in `.env`

## Core Dependencies

- **sentence-transformers** (>=2.2.0): Generate embeddings for semantic search
- **chromadb** (>=0.4.22): Vector database for storing and retrieving document chunks
- **langchain-text-splitters** (>=0.0.1): Semantic text chunking for legal/financial documents
- **openai** (>=1.0.0): OpenAI-compatible client for OpenRouter API access
- **python-dotenv** (>=1.0.0): Environment variable management
- **pyyaml** (>=6.0): YAML configuration parsing
- **pytest** (>=7.4.0): Testing framework
- **numpy** (>=1.24.0): Numerical operations for embeddings

## Scripts

### Corpus Verification

Before ingesting AAOIFI standards into the vector database, verify your corpus is ready:

```bash
python scripts/check_corpus.py
```

**Features:**
- Checks if corpus directory exists (default: `./data/aaoifi_md`)
- Verifies markdown files are present
- Displays sample files with sizes
- Provides actionable next steps if corpus is missing

**Environment Variables:**
- `CORPUS_DIR`: Path to AAOIFI markdown corpus (default: `./data/aaoifi_md`)

**Expected Output:**
```
============================================================
L0 Corpus Check
============================================================

✓ Corpus directory exists: ./data/aaoifi_md
✓ Found 15 markdown files

Sample files:
  • AAOIFI_Standard_01_en_Murabaha.md (45.2 KB)
  • AAOIFI_Standard_02_en_Ijarah.md (38.7 KB)
  ... and 13 more

============================================================
✓ Corpus is ready for ingestion!
============================================================

Next step: python scripts/ingest.py
```

### Vector Database Ingestion

Chunk and embed AAOIFI markdown files into ChromaDB:

```bash
python scripts/ingest.py
```

**Features:**
- Semantic chunking with LangChain (512 tokens, 50 overlap)
- Generates embeddings using sentence-transformers
- Stores chunks in ChromaDB with metadata
- Tracks processing progress per file

**Environment Variables:**
- `CORPUS_DIR`: Path to AAOIFI markdown corpus (default: `./data/aaoifi_md`)
- `CHROMA_DIR`: ChromaDB storage location (default: `./chroma_db`)
- `EMBED_MODEL`: Embedding model (default: `sentence-transformers/all-mpnet-base-v2`)

**Workflow:**
1. Run `check_corpus.py` to verify corpus exists
2. Run `ingest.py` to populate vector database
3. Vector database is ready for RAG queries

### AAOIFI Standards Converter (Recommended)

Convert AAOIFI Shari'ah Standards PDFs to Markdown with comprehensive metadata for Gemini Gem knowledge base:

```bash
# Automatically converts all Standard_*.pdf files from data/raw/aaoifi_standards/
python scripts/convert_aaoifi_to_markdown.py
```

**Features:**
- Extracts title from first page automatically
- Detects standard number and language (AR/EN) from filename
- Generates comprehensive Sharia compliance metadata (YAML frontmatter)
- Creates bilingual document pairs (links Arabic ↔ English versions)
- Generates INDEX.md with organized standards list
- Page-by-page extraction with proper formatting
- Sanitized filenames for cross-platform compatibility

**Input Format:** `Standard_{number}_{AR|EN}.pdf` (e.g., `Standard_01_EN.pdf`, `Standard_01_AR.pdf`)

**Output:** `gemini-gem-prototype/knowledge-base/AAOIFI_Standard_{number}_{lang}_{title}.md`

**Requirements:** `pip install PyPDF2`

## Current Implementation Status

This project is currently in **Phase 3: RAG Pipeline Development**. The following components are implemented or in progress:

- ✅ Core dependencies installed (sentence-transformers, chromadb, langchain-text-splitters)
- ✅ LLM provider support (OpenRouter API with multiple model options)
- ✅ PDF to Markdown conversion scripts
- 🚧 Semantic chunking implementation
- 🚧 Vector database setup and indexing
- 🚧 RAG retrieval pipeline
- ⏳ Compliance analysis engine (Phase 4)
- ⏳ Web API interface (Phase 4)
- ⏳ Session management and clarification loop (Phase 4)

**Note**: Web scraping (Playwright), API framework (FastAPI), and authentication components will be added in later phases as the core RAG pipeline is completed.

### Generic PDF to Markdown Converter

Convert any AAOIFI PDF standards to clean Markdown format:

```bash
# Convert single PDF
python scripts/convert_pdf_to_markdown.py --input "data/pdfs/FAS01.pdf" --output "data/markdown/"

# Convert all PDFs in directory
python scripts/convert_pdf_to_markdown.py --input-dir "data/pdfs/" --output-dir "data/markdown/"

# With custom naming
python scripts/convert_pdf_to_markdown.py --input "FAS01.pdf" --output "data/markdown/" --name "AAOIFI_FAS01_General-Presentation"
```

**Features:**
- Extracts text from PDF with layout preservation
- Detects document structure (sections, subsections)
- Converts to clean Markdown with proper headers
- Adds metadata header with standard info and TOC
- Removes page numbers and common headers/footers
- Fixes broken hyphenation and OCR errors

**Requirements:** `pip install pymupdf`

See `scripts/CONVERTER_IMPROVEMENTS.md` for enhancement ideas.

## Development Roadmap

The project follows a 4-phase implementation approach:

1. **Phase 1: Research** ✅ - Technology selection and architecture design
2. **Phase 2: Data Acquisition** ✅ - PDF conversion scripts and document processing
3. **Phase 3: RAG Pipeline** 🚧 - Current focus: semantic chunking, embeddings, vector storage
4. **Phase 4: Chatbot Logic** ⏳ - Session management, clarification engine, compliance analyzer
5. **Phase 5: Operations** ⏳ - API deployment, monitoring, documentation

See `.kiro/specs/sharia-compliance-chatbot/tasks.md` for detailed implementation tasks.

## Deployment

### Deploy to Hugging Face Space

Deploy the application to Hugging Face Space using the automated deployment script:

```bash
# Deploy current code to Hugging Face Space
python scripts/deploy_to_hf_space.py
```

**Prerequisites:**
- Hugging Face account with write access
- `HF_TOKEN` configured in `.env` file (get from https://huggingface.co/settings/tokens)
- Required packages: `pip install huggingface_hub python-dotenv`

**Features:**
- Authenticates with Hugging Face Hub API
- Uploads source code, scripts, and vector database
- Excludes unnecessary files (`.env`, `.git`, `__pycache__`, etc.)
- Provides deployment status and Space URL
- Automatic commit message generation

**What Gets Deployed:**
- `src/` - Application source code
- `scripts/` - Utility scripts
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container configuration
- `README.md` - Documentation
- `chroma_db_multilingual/` - Vector database

**Expected Output:**
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

**Troubleshooting:**
- Verify `HF_TOKEN` has write access to the Space
- Check Space exists at https://huggingface.co/spaces/AElKodsh/mushir-sharia-bot
- Review build logs if deployment succeeds but Space fails to start
- For large uploads, ensure stable internet connection

### Testing Deployed Space

Test the deployed Hugging Face Space endpoints:

```bash
# Test both query and streaming endpoints
python scripts/test_space_query.py
```

**Features:**
- Tests `/api/v1/query` endpoint with sample compliance query
- Tests `/api/v1/query/stream` endpoint with SSE streaming
- Displays response times, status codes, and formatted results
- Provides diagnostic information for common errors

**Expected Output:**
```
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
```

## Docker Deployment

Docker deployment will be available after Phase 4 completion.

```bash
# Coming soon
docker-compose up -d
```
