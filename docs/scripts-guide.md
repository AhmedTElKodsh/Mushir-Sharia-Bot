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

### 4. acquire_aaoifi_standards.py

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

### 5. download_*.py Scripts

**Purpose:** Various utilities for downloading AAOIFI standards with different strategies.

**Available Scripts:**
- `download_aaoifi_standards.py` - Basic download script
- `download_all_aaoifi.py` - Batch download all standards
- `download_all_aaoifi_v2.py` - Improved version with retry logic
- `download_corrected_aaoifi.py` - Download with corrections
- `retry_failed_aaoifi.py` - Retry previously failed downloads

---

## Workflow

### Typical Data Acquisition and Ingestion Workflow

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
