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

Mushir is a RAG-based Islamic finance research assistant. It answers English and Arabic questions from the configured AAOIFI corpus, validates citations, asks focused clarification questions when facts are missing, and refuses binding fatwas, legal advice, and financial advice.

The current implementation is a FastAPI application with browser chat, REST API, SSE streaming, multilingual retrieval, OpenRouter generation, citation validation, readiness checks, and deployment support. The active roadmap gate is L5 quality and release readiness. The proposed future L6 direction is a rules-first Sharia commercial-process evaluator.

## Features

- **AAOIFI-grounded retrieval**: indexes the configured AAOIFI markdown corpus and retrieves relevant excerpts.
- **Arabic and English support**: uses a multilingual embedding model and Arabic-aware query preprocessing.
- **Safe answer contract**: returns cited answers, focused clarification questions, safe refusals, or insufficient-data responses.
- **Citation validation**: accepts only citations backed by retrieved chunks.
- **OpenRouter provider**: uses an OpenAI-compatible OpenRouter client, with `openrouter/free` supported for constrained demos.
- **FastAPI runtime**: exposes `/chat`, `/health`, `/ready`, `/metrics`, `/api/v1/query`, and `/api/v1/query/stream`.
- **Operational modes**: supports local Chroma and optional Qdrant, Redis, PostgreSQL, cache, audit, sessions, and rate limiting.
- **Sharia Ontology Engine**: maps abstract definitions to financial contracts via `ConceptRouter` and `RulingEvaluator`.
- **Evaluation Framework**: includes YAML-based Gold Sets (GC-001+) and Expected Calibration Error (ECE) metrics.
- **Data Acquisition Layer**: active scrapers and extractors designed for building a robust evidence corpus (e.g., Egypt Financial).

## Current Status

| Area | Status |
| --- | --- |
| Browser chat UI | Implemented |
| REST query API | Implemented |
| SSE streaming API | Implemented |
| Arabic/English retrieval | Implemented with multilingual Chroma index |
| Citation validation | Implemented |
| Clarification loop | Implemented as one focused follow-up question |
| Safe fatwa/legal/financial-advice refusal | Implemented |
| Sharia Ontology Engine (Concept Router, Ruling Evaluator) | Implemented |
| Sharia Compliance Evaluation Framework (Gold Sets, ECE) | Implemented |
| L5 release readiness | Active gate |
| L6 rules-first evaluator | Proposed future direction; foundational scenario/routing/source-gap scaffolding is implemented, full evaluator is not active runtime scope |
| Egypt institution evidence corpus | Data acquisition framework implemented; active scraping and evaluation corpus building in progress |

## Planning Direction

Older L0-L4 planning files are retained as historical implementation context. The current planning direction is:

- **L5 now:** prove the implemented runtime through tests, retrieval evaluation, live smoke checks, readiness gates, documentation, and secret-safe deployment practices.
- **L6 next:** widen Mushir into a rules-first commercial-process assessment assistant only after L5 is green. The first runtime scaffold now supports transaction-scenario metadata, standards routing metadata, source-family detection, and a fail-closed source-gap guard for late-payment/default permissibility questions. Full L6 still requires Shari'ah-source acquisition, executable rules, structured verdict exposure, and human-review workflows.
- **L6 evidence corpus:** build a public-source Egypt financial institutions operations corpus for supervised evaluation and future institution-aware retrieval. The scraper must preserve source provenance, stop after bounded discovery attempts, respect access controls, record missing details explicitly, and keep machine-proposed AAOIFI labels separate from scholar-reviewed ground truth.

Mushir must not be marketed as a fatwa engine. It provides evidence-backed, non-binding assistance.

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

# Ingest cataloged AAOIFI standards into vector database
python scripts/ingest.py --source-catalog path/to/aaoifi-source-catalog.yaml

# Run RAG pipeline tests
pytest tests/ -v
```

## Project Structure

```
src/
+-- models/          # Data models (Document, Chunk, Ruling)
+-- rag/             # RAG pipeline (chunking, embeddings, vector store)
+-- chatbot/         # Chatbot coordination and generation
|   +-- answer_generator.py      # LLM generation coordinator
|   +-- application_service.py   # Main application orchestrator
|   +-- llm_client.py            # LLM client wrappers (OpenRouter, OpenAI)
|   +-- prompt_builder.py        # AAOIFI-grounded prompt construction
|   +-- citation_validator.py    # Citation extraction and validation
|   +-- clarification_engine.py  # Multi-turn clarification logic
|   +-- commercial_assessment.py # L6 scenario/routing/source-gap scaffold
|   +-- session_manager.py       # Session state management
+-- api/             # FastAPI REST endpoints
+-- storage/         # Caching and persistence
+-- config/          # Configuration management
+-- acquisition/     # Source acquisition primitives and active extractors (Egypt Financial)
+-- governance/      # Source catalog, concept map, router seeds, chunk metadata
+-- ontology/        # Sharia Ontology mapping, Concept Router, and Ruling Evaluator

scripts/
+-- check_corpus.py                # Verify AAOIFI corpus exists and is ready
+-- ingest.py                      # Ingest markdown files into ChromaDB
+-- convert_pdf_to_markdown.py     # Convert AAOIFI PDFs to Markdown format
+-- convert_aaoifi_to_markdown.py  # AAOIFI-specific converter with metadata
+-- test_space_query.py            # Test deployed Hugging Face Space endpoints
+-- deploy_to_hf_space.py          # Deploy application to Hugging Face Space
+-- download_*.py                  # Various download utilities

tests/test_api_query.py           # API query contract tests

data/
+-- raw/            # Raw AAOIFI PDF files
+-- markdown/       # Converted Markdown documents
+-- source_registry/ # Tracked planning seeds for Egypt institution source categories
+-- fixtures/       # Small tracked scrape fixtures for tests only

artifacts/
+-- l6_scrape/      # Local/runtime scrape output, ignored except README
```

## Environment Variables

Create a `.env` file with:

```bash
# LLM Configuration - OpenRouter
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=openrouter/free
OPENROUTER_MAX_TOKENS=1024

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

`openrouter/free` is the intended demo default so the runtime can use whichever
free OpenRouter chat model is currently available. Treat it as a constrained
shared provider: do not run large live-answer loops or repeated matrix probes
against OpenRouter. For evaluation work, prefer fake LLM fixtures, retrieval-only
checks, and `RAG_EVAL_MODE=true`; keep live `/api/v1/query` smoke tests to a few
requests with backoff so the API node is not overloaded or blocked.

## Requirements

- Python 3.9+ (minimum) / Python 3.11+ (recommended for better performance)
- OpenRouter API key (supports multiple LLM providers including Gemini, GPT-4, Claude)
- ~2GB disk space for embedding model (sentence-transformers)

## Scope

The current demo/runtime covers the acquired and indexed AAOIFI corpus configured for retrieval, with emphasis on FAS material. FAS is useful for accounting, recognition, measurement, presentation, and disclosure. It is not sufficient by itself for every permissibility or halal/haram question.

The planned L6 direction separates source families:

- AAOIFI Shari'ah Standards or approved Sharia sources for permissibility and contract validity;
- FAS for accounting and reporting treatment;
- governance, ethics, auditing, fatwa, and local overlays only after acquisition, review, and versioning.

**Disclaimer**: This system provides informational guidance only. It does not replace consultation with qualified Islamic finance scholars, Sharia boards, legal advisors, accountants, or financial advisors.

## Testing

### Unit Tests

```bash
# Run all tests through the repo virtual environment
.\.venv\Scripts\python.exe -m pytest -q --timeout=90 --basetemp=.tmp\pytest

# Run specific test modules
pytest tests/test_rag_pipeline.py -v
pytest tests/test_chunker.py -v
```

### End-to-End API Testing

Test the running API server with the quick test script:

```bash
# Ensure the server is running first
# Then run the API contract smoke tests
.\.venv\Scripts\python.exe -m pytest tests\test_api_query.py tests\test_api_streaming.py -q
```

**Features:**
- [OK] Health check endpoint (`/health`)
- [INFO] Readiness check with infrastructure status (`/ready`)
- Real compliance query test (`/api/v1/query`)
- Displays answer, citations, and response metadata
- 30-second timeout with error handling

**Expected Output:**
```
============================================================
Mushir Sharia Bot - End-to-End Test
============================================================

[OK] Health check: {'status': 'healthy'}

[INFO] Readiness check:
  Status: ready
  Level: L2
  Infrastructure:
    - vector_db: ready
    - llm: ready
    - embedding_model: ready

Testing query: I want to invest in a company that produces halal food...

[OK] Query successful!

Answer:
  Based on AAOIFI standards...

Citations: 3
  Status: complete

  First citation:
    - Document: FAS-21
    - Standard: FAS-21
    - Score: 0.856

============================================================
[OK] Testing complete!
============================================================

Next steps:
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

## Current Documentation

For the current maintained documentation set, start with:

- `.planning/sharia-compliance-chatbot/docs/index.md` - Documentation map.
- `.planning/sharia-compliance-chatbot/docs/project-documentation.md` - Full current technical documentation.
- `.planning/sharia-compliance-chatbot/docs/pipeline-architecture-v2.md` - Visual architecture graphs for the new intelligent routing pipeline.
- `.planning/sharia-compliance-chatbot/docs/client-plain-language-logic.md` - Simple client-facing explanation of the whole logic.
- `.planning/sharia-compliance-chatbot/docs/l6-egypt-institution-scrape/README.md` - Project-facing guide for the planned Egypt institution scraping/evidence corpus.
- `project-context.md` - Implementation context and rules for AI agents and developers.

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

[OK] Corpus directory exists: ./data/aaoifi_md
[OK] Found 15 markdown files

Sample files:
  - AAOIFI_Standard_01_en_Murabaha.md (45.2 KB)
  - AAOIFI_Standard_02_en_Ijarah.md (38.7 KB)
  ... and 13 more

============================================================
[OK] Corpus is ready for ingestion!
============================================================

Next step: python scripts/ingest.py --source-catalog path/to/aaoifi-source-catalog.yaml
```

### Vector Database Ingestion

Chunk and embed cataloged AAOIFI markdown files into ChromaDB:

```bash
python scripts/ingest.py --source-catalog path/to/aaoifi-source-catalog.yaml
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
- `SOURCE_CATALOG_FILE`: YAML source catalog used to mark chunks answer-admissible

**Workflow:**
1. Run `check_corpus.py` to verify corpus exists
2. Run `ingest.py --source-catalog ...` to populate vector database
3. Vector database is ready for RAG queries

Diagnostic-only ingests can pass `--allow-uncataloged`; those chunks are quarantined and cannot ground answers.

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
- Creates bilingual document pairs (links Arabic <-> English versions)
- Generates INDEX.md with organized standards list
- Page-by-page extraction with proper formatting
- Sanitized filenames for cross-platform compatibility

**Input Format:** `Standard_{number}_{AR|EN}.pdf` (e.g., `Standard_01_EN.pdf`, `Standard_01_AR.pdf`)

**Output:** `gemini-gem-prototype/knowledge-base/AAOIFI_Standard_{number}_{lang}_{title}.md`

**Requirements:** `pip install PyPDF2`

## Implementation Status

The early build-status snapshot has been replaced by the maintained current-state docs. The current implementation includes FastAPI, browser chat, REST and streaming endpoints, multilingual retrieval, clarification, citation validation, OpenRouter generation, readiness checks, deployment helpers, and tests. See `.planning/sharia-compliance-chatbot/docs/project-documentation.md` for details.

Current implementation summary:

- Core dependencies, ingestion scripts, and PDF/Markdown conversion utilities are available.
- OpenRouter provider support is implemented through an OpenAI-compatible client.
- Multilingual Chroma retrieval is implemented for the demo path, with optional Qdrant support.
- FastAPI REST, SSE streaming, `/chat`, `/health`, `/ready`, and `/metrics` are implemented.
- The answer service, clarification engine, citation validator, cache/audit/session/rate-limit abstractions, and tests are implemented.
- L5 release readiness and L6 rules-first evaluator planning remain the active planning tracks.

FastAPI, the browser chat UI, API endpoints, clarification, retrieval, and citation validation are already part of the current runtime. Future work is tracked through the L5 readiness plan and proposed L6 evaluator plan.

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

Use these docs as the current roadmap sources:

- `.planning/sharia-compliance-chatbot/docs/project-documentation.md` - implemented runtime and architecture.
- `.planning/sharia-compliance-chatbot/docs/client-plain-language-logic.md` - non-technical client explanation of planning and implementation.
- `.planning/sharia-compliance-chatbot/docs/l5-production-readiness.md` - active L5 release/readiness runbook.
- `.planning/sharia-compliance-chatbot/next-level-plans/README.md` - planning index.
- `.planning/sharia-compliance-chatbot/next-level-plans/L6-RULES-FIRST-SHARIA-COMMERCIAL-EVALUATOR-PLAN.md` - proposed L6 future direction.
- `.planning/sharia-compliance-chatbot/next-level-plans/L6-EGYPT-FINANCIAL-INSTITUTIONS-EVIDENCE-CORPUS-PLAN.md` - Egypt financial institutions public-source scraping, gap handling, and scholar-review data plan.

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
Deploying Mushir Sharia Bot to Hugging Face Space
============================================================

Step 1: Authenticating with Hugging Face...
[OK] Authenticated successfully

Step 2: Uploading files to AElKodsh/mushir-sharia-bot...
  Uploading from: d:\AI Projects\Freelance\Sabry\Mushir-Sharia-Bot
  To Space: AElKodsh/mushir-sharia-bot

[OK] Upload successful!

============================================================
[OK] Deployment Complete!
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
Mushir Sharia Bot - Space Testing
============================================================

Testing /api/v1/query endpoint
   URL: https://AElKodsh-mushir-sharia-bot.hf.space/api/v1/query

Sending query: I want to invest in a company that produces halal food. Is this permissible?

Response time: 3.45s
[INFO] Status code: 200

[OK] Query successful!

Response:
   Answer: Based on AAOIFI standards...
   Status: complete
   Citations: 3 found
```

## Docker Deployment

Docker is the current deployment shape for Hugging Face Spaces. The container starts the FastAPI app on port `7860`.

```bash
docker build -t mushir-sharia-bot .
docker run --env-file .env -p 7860:7860 mushir-sharia-bot
```

Then open `http://127.0.0.1:7860/chat` and verify `/health`, `/ready`, and at least one English and Arabic smoke query.
