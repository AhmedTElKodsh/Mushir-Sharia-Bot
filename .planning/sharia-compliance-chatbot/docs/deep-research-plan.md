```python
markdown_content = """# SYSTEM CONTEXT: Mushir RAG & Crawler Research
## METADATA
- **Domain**: Source-governed Islamic finance assistant.
- **Current State**: L5 (Release readiness, citation-backed RAG).
- **Target State**: L6 (Rules-first commercial-process evaluator backed by structured institution evidence).
- **Format Intended For**: Autonomous AI Agents, RAG Pipelines, and Automated Evaluators.

---

## 1. IMMUTABLE SYSTEM CONSTRAINTS (HARD RULES)
- `RULE_01_SCOPE`: **NO BINDING FATWAS.** Assistant is informational only. Reject requests for legal/financial advice or binding rulings.
- `RULE_02_SAFETY`: **FAIL CLOSED.** Return `INSUFFICIENT_DATA` if evidence, citations, or retrieval quality fail. Do not guess.
- `RULE_03_GROUNDING`: **NO HALLUCINATED CITATIONS.** `CitationValidator` must strictly match generated LLM citations to retrieved chunk IDs.
- `RULE_04_CRAWLER_ETHICS`: **RESPECT ACCESS CONTROLS.** Obey `robots.txt`, CAPTCHAs, and paywalls. Record blocks as a gap status (e.g., `official_site_not_found`); do not bypass.
- `RULE_05_AUTHORITY_LADDER`:
  1. AAOIFI / Approved Shari'ah Standards (Permissibility).
  2. FAS Standards (Accounting/Reporting).
  3. Official Regulator / Institution Artifacts (Public Contracts).
  4. Machine-proposed labels (Require human scholar review).
  5. Third-party snippets (`DISCOVERY_ONLY` - Never use for compliance).
- `RULE_06_ARCHITECTURE`: **NO OSS FRAMEWORK REPLACEMENT.** Enhance existing `ApplicationService`; do not replace core routing with LangChain, LlamaIndex, or autonomous web-search agents.

---

## 2. OSS TOOLING MATRIX (APPROVED EXPERIMENTS)

| Capability | Selected Primary Candidate | Alternative/Secondary | Rejection/Hold Status |
| :--- | :--- | :--- | :--- |
| **RAG Evaluation** | `DeepEval` (pytest-like metrics) | Custom Pytest metrics | `Ragas` (Testgen needs human review) |
| **Hybrid Retrieval** | `bm25s` (Python-native lexical) | `Qdrant` (Production vector DB) | `Pyserini` (Java/Lucene complexity) |
| **Reranking & Embed** | `BAAI/bge-m3` + `bge-reranker-v2` | `multilingual-e5` | `RAGatouille` (Hold, too complex) |
| **Ingestion/Parsing** | `Docling` (PDF/Table/Markdown) | `pdfplumber` (Registry PDFs) | `Marker` (GPL-3.0 - License blocked) |
| **Trace/Observability**| `Phoenix/OpenInference` (OTel) | `TruLens` | `Langfuse` (Hold, full platform) |
| **Extraction** | `Instructor` (Pydantic enforcement)| Base Pydantic | `Guardrails` (Secondary only) |
| **Rules Engine** | `OPA` (Open Policy Agent) | `Catala` (Literate DSL) | `Drools` (JVM complexity - Reject) |

---

## 3. EXECUTION GRAPH: UPGRADE SLICES

### SLICE_01: RAG Evaluation Baseline (BLOCKER)
- **Condition**: Must be completed before ANY retrieval or LLM updates.
- **Actions**:
  - Implement metrics: `expected_standard_hit_at_k`, `citation_support_rate`, `refusal_correctness`.
  - Validate against standard definition cases (Murabaha, Ijarah).

### SLICE_02: Official Regulator Crawler (L6 Data Engine)
- **Node_A**: Crawl CBE/FRA registry endpoints deterministically.
- **Node_B**: Extract entity data -> emit `institution_identity`.
- **Node_C**: Execute domain-constrained search: `site:{official_domain} "{operation_title}" filetype:pdf`.
- **Node_D**: Fetch official artifacts (PDFs, Tariffs). Parse via `pdfplumber` or `Docling`.
- **Validation**: Halt if institution marked `ready_for_product_crawl` without official website confidence.

### SLICE_03: Hybrid Retrieval Spike
- **Action**: Inject `bm25s` parallel to `sentence-transformers` dense retrieval.
- **Target Optimization**: Exact AAOIFI standard numbers (e.g., FAS-28), Arabic/English terminology, transliterations (Murabaha/Morabaha).

### SLICE_04: Traceability Injection
- **Action**: Instrument `ApplicationService` with Phoenix traces.
- **Required Payloads**: Original query, normalized query, detected language, source route, retrieved chunk IDs, citation valid status, refusal reason.

---

## 4. SYSTEM DATA SCHEMAS (L6 TARGET)

### Evidence Artifact Schema

```

```text
File created successfully at /mnt/data/ai-optimized-research-mushir-2026.md

```json
{
  "artifact_id": "string (UUID)",
  "url": "string (URL)",
  "raw_path": "string",
  "sha256": "string (Hash)",
  "extraction_status": "enum[success, failed, blocked, CAPTCHA]",
  "evidence_quality": "enum[official_pdf, regulator_html, marketing_html, third_party]"
}

```

### Financial Operation Schema

```json
{
  "operation_id": "string (UUID)",
  "institution_id": "string (UUID)",
  "source_artifact_id": "string (UUID)",
  "evidence_grade": "enum[title_only, disclosure, contract]",
  "verdict_status": "enum[insufficient_contractual_evidence, requires_clarification, scholar_review_ready]"
}

```

### Retrieval Trace Schema

```json
{
  "trace_id": "string",
  "query_normalized": "string",
  "language": "enum[en, ar, mixed]",
  "dense_scores": "array[float]",
  "sparse_scores": "array[float]",
  "citation_validation_passed": "boolean",
  "fallback_triggered": "boolean"
}

```

"""

file_path = "/mnt/data/ai-optimized-research-mushir-2026.md"
with open(file_path, "w", encoding="utf-8") as f:
f.write(markdown_content)

print(f"File created successfully at {file_path}")

```
Your MD file is ready
[file-tag: code-generated-file-0-1779474248378283125]

I have restructured the research into a highly formatted Markdown file specifically optimized for AI agents and automated parsers. 

Here are the key adjustments made for agent readability:
* **Immutable System Constraints:** Hardcoded as boolean rules (e.g., `RULE_01_SCOPE`, `RULE_02_SAFETY`) so an AI orchestration script can interpret fail-closed parameters directly.
* **OSS Tooling Matrix:** Formatted into a strict markdown table mapping capabilities directly to approved tools and highlighting explicit rejections (like Langchain replacements or GPL-licensed tools).
* **Execution Graph Nodes:** Transformed the project implementation slices into logical nodes (`Node_A`, `Node_B`) to allow a workflow agent to treat them as step-by-step state machine actions.
* **JSON Schemas:** Replaced abstract descriptive data models with explicit JSON schemas (`evidence_artifact`, `financial_operation`) so LLMs acting as extractors or validators can enforce correct typing during L6 assessments.

```