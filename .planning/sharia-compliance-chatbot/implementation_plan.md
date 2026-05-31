# Mushir Sharia-Bot — Implementation Plan
## Post-Party-Mode Strategic Decisions Locked

---

## Current Implementation Update (2026-05-31)

The recent implementation and review pass landed the first hard-case routing corrections and evaluation harness fixes:

- GC-001 is now a clarification-first case: Mushir asks whether the construction penalty is due to contractor delivery delay or customer payment delay before any verdict.
- Construction / muqawala / istisna penalty routing targets `SS-05` and `SS-11`; `SS-10` is Salam and is explicitly forbidden for this route unless the query actually implicates Salam.
- Organized banking tawarruq remains routed to `SS-30`; Arabic currency/Sarf detection must not match the substring inside banking wording.
- `tests/fixtures/hard_case_routing_matrix.yaml` is the canonical launch-blocking hard-case routing matrix, loaded by `tests/routing_matrix.py`.
- The evaluation mock LLM now adapts structured response dicts into text before calling `ApplicationService`, preserving `CitationValidator` as the text citation boundary.
- Verification snapshot: critical goldset `19 passed, 19 skipped`; evaluation suite `96 passed, 44 skipped`; full local suite `619 passed, 48 skipped, 2 warnings`.

Planning language below that says `SS-5` should be read as normalized `SS-05`. Historical examples are retained where useful, but new code and tests should use `SS-05`.

---

## Two Decisions That Unlock Everything

> **Decision 1 — Ruling-as-Function ✅**
> Rulings are not stored as facts. They are the *output* of evaluating a function over context parameters:
> `f(concept, contract_type, party_role, madhab, jurisdiction, conditions) → RulingResult`

> **Decision 2 — Continuous Human-in-the-Loop Scholar Review ✅**
> A Sharia Scholar reviews system outputs continuously — before launch (eval set validation), during launch (new query review), and **after launch (random sampling of live outputs)**. The loop never closes.

These two decisions resolve all downstream open questions identified in the party mode session.

---

## What This Means Architecturally

### Decision 1 Impact: Ruling-as-Function

The system **reasons** about rulings; it does not **recall** them.

```python
@dataclass
class RulingContext:
    concept: str                    # e.g., "late_penalty", "profit_margin"
    contract_type: ContractFamily   # e.g., ISTISNA, MURABAHAH, IJARAH
    party_role: PartyRole           # e.g., CONTRACTOR, DEBTOR, LESSOR
    madhab: Optional[str]           # e.g., "Hanafi", "Maliki", "Shafi'i"
    jurisdiction: Optional[str]     # e.g., "EG", "MY", "SA"
    conditions: list[str]           # e.g., ["bank_owns_asset", "penalty_to_charity"]
    exceptions: list[str]           # e.g., ["additional_fee_charged"]

@dataclass
class RulingResult:
    permissibility: str             # "PERMISSIBLE" | "PROHIBITED" | "CONDITIONAL" | "DISPUTED"
    confidence: float               # 0.0 – 1.0
    applicable_standards: list[str] # e.g., ["SS-11", "SS-5"]
    conditions_met: list[str]       # conditions from ruling_conditions that are satisfied
    conditions_violated: list[str]  # conditions that the exception triggers
    alternative_views: list[str]    # for DISPUTED cases — named scholarly positions
    requires_scholar_review: bool   # True when confidence < 0.75 or DISPUTED
    source_chunks: list[str]        # AAOIFI chunk IDs used to derive ruling
    scholar_reviewed: bool          # True if a scholar has validated this result
```

**Stored in the ontology YAML (not in Python code):**
```yaml
# data/concept_ontology/late_penalty.yaml
concept_id: "late_penalty"
arabic_terms:
  - "غرامة التأخير"
  - "شرط الجزاء"
  - "غرامة الإخلال"

ruling_by_context:
  - context:
      contract_type: istisna
      party_role: contractor     # the one who delays
    ruling: CONDITIONAL
    conditions:
      - "penalty not proportional to loan amount"
      - "penalty represents actual damage to commissioning party"
      - "contractor is the delaying party"
    applicable_standards: ["SS-11", "SS-5"]
    key_question: "Is the delaying party the contractor (not the client)?"
    scholar_notes: ""            # filled by scholar review

  - context:
      contract_type: loan_debt
      party_role: debtor         # delayed repayment
    ruling: PROHIBITED
    conditions: []
    exception:
      - condition: "penalty goes 100% to charity"
        ruling_override: CONDITIONAL
        applicable_standards: ["SS-3"]
    applicable_standards: ["SS-3"]
    scholar_notes: ""

  - context:
      contract_type: ijarah
      party_role: lessee         # delayed rent payment
    ruling: CONDITIONAL
    conditions:
      - "delay is intentional (مماطلة)"
      - "penalty amount donated to charity, not retained by lessor"
    applicable_standards: ["SS-9"]
    scholar_notes: ""
```

### Decision 2 Impact: Continuous Scholar Review Loop

```
PRE-LAUNCH:
  Scholar validates 26-query gold eval set
  Scholar seeds concept ontology YAML with anchor rulings
  Scholar reviews system outputs on test set
  Gate: scholar_sign_off required before any deployment

POST-LAUNCH (Continuous):
  Every query answered → logged to ScholarReviewStore
  3 review queues:
    Q1 — AUTO-FLAGGED: confidence < 0.75 OR requires_scholar_review=True
    Q2 — RANDOM SAMPLE: 5% of all answered queries (sampled daily)
    Q3 — USER-REPORTED: user flags answer as incorrect
  Scholar reviews each queue item using structured review form
  Corrections feed back into:
    → concept_ontology YAML patches (data layer)
    → gold eval set additions (test layer)
    → contrastive training pairs (future fine-tuning layer)
```

---

## Project Module Structure (Mary's M1–M6)

| Module | Status | Priority |
|---|---|---|
| **M1 — Contract Intelligence Engine** | 🔴 Not built as explicit gate | **Sprint 1–2** |
| **M2 — Sharia Knowledge Base** | 🟡 Partial (FAS done, SS partial) | **Sprint 0–1** |
| **M3 — Egypt Market Intelligence** | 🔴 Not started | Sprint 4–5 |
| **M4 — Fatwa & Scholarly Reference Layer** | 🟡 Infrastructure exists | Sprint 3+ |
| **M5 — Scholar Review Workflow** | 🟡 Code exists, not wired | Sprint 2–3 |
| **M6 — Client-Facing Interface** | ✅ Working (L5) | Maintain throughout |

---

## Three-Gate Pipeline (Confirmed Architecture)

```
User Query (Arabic / English / Mixed / Arabizi)
    │
    ▼
┌─────────────────────────────────────────────────┐
│  GATE 1: ContractTypeClassifier                 │
│  Method: Deterministic keyword/regex FIRST      │
│          LLM confirmation only if ambiguous     │
│  Output: {contract_type, confidence}            │
│  If confidence < 0.60 → ClarificationEngine    │
│  If 0.60–0.90 → LLM confirms                   │
│  If > 0.90 → proceed directly                  │
└─────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────┐
│  GATE 2: ConceptOntologyRouter                  │
│  Method: YAML lookup                            │
│  Input:  contract_type + detected concepts      │
│  Output: eligible_standard_ids[]               │
│          + party_role resolution               │
│          + ruling_conditions to check          │
│          + supersession filter applied         │
└─────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────┐
│  GATE 3: ScopedHybridRetrieval                  │
│  Method: Dense (multilingual) + BM25 sparse     │
│          merged with RRF                        │
│  Filter: metadata where ss_number IN            │
│          eligible_standard_ids                  │
│  Output: ranked chunks, scoped corpus           │
└─────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────┐
│  RULING FUNCTION EVALUATOR                      │
│  Input: retrieved chunks + RulingContext        │
│  Process: evaluate f(context) → RulingResult   │
│  Exception check: user's conditions vs.        │
│                   ruling_conditions in YAML    │
│  Output: RulingResult with confidence          │
└─────────────────────────────────────────────────┘
    │
    ├── confidence > 0.75 AND NOT DISPUTED
    │   → PromptBuilder → LLM → CitationValidator → Answer
    │
    ├── confidence 0.60–0.75 OR DISPUTED
    │   → Answer with explicit uncertainty + alternative views
    │   → Auto-flagged to Scholar Review Queue Q1
    │
    └── confidence < 0.60
        → Structured refusal or Clarification
        → Auto-flagged to Scholar Review Queue Q1
```

---

## Sprint Plan (Single Developer, 6-Week Horizon)

### ⚡ PREREQUISITE ZERO — Scholar Eval Set Validation
**Before Sprint 0 begins. Non-negotiable.**

The developer cannot write code against invalid ground truth.

**Scholar delivers:**
```json
[
  {
    "query_ar": "هل شرط غرامة التأخير في عقود المقاولات شرط ربوي؟",
    "query_en": "Is the penalty clause in construction contracts riba?",
    "contract_type": "istisna",
    "party_role": "contractor",
    "ruling": "CONDITIONAL",
    "dalil": "SS-11, Clause 4.3",
    "applicable_standards": ["SS-11", "SS-5"],
    "forbidden_standards": ["SS-3", "FAS-30"],
    "khilaf_flag": false,
    "conditions": ["penalty represents actual damage", "contractor is delaying party"],
    "scholar_sign_off": "Dr. [Name], [Institution], [Date]"
  }
]
```

26 queries across 6 categories (A: Istisna trap, B: debt trading, C: paid guarantee,
D: controversial rulings, E: Mudaraba guarantee, F: deferred sale delivery) + 13 hard cases
from Dr. Quinn + Murat's IMB trap case.

**File location:** `tests/data/gold_eval_set.json`

---

### Sprint 0 — Foundation (3 days)

**Goals:**
- Fix the two active-harm bugs
- Stand up the eval harness infrastructure
- Define the YAML ontology schema (no data yet)

**Commits:**

1. `fix(clarification): remove duplicate dict assignments (BUG-001)`
   - File: `src/chatbot/clarification_engine.py`
   - Delete lines 36–51 (first `QUESTION_TEMPLATES_AR` assignment)
   - Delete lines 84–98 (first `operation_keywords_ar` assignment)

2. `fix(clarification): add _is_judgment_query bypass for حكم queries (BUG-004)`
   - File: `src/chatbot/clarification_engine.py`
   - Add `_is_judgment_query()` method
   - Wire into `ask_if_needed()`: `if self._is_judgment_query(query): return None`
   - Judgment terms: `["حكم", "يجوز", "جائز", "حلال", "حرام", "ruling", "permissible", "halal", "haram"]`

3. `feat(schema): define RulingContext, RulingResult, PartyRole dataclasses`
   - New file: `src/models/ruling.py`

4. `feat(schema): define ConceptOntology YAML schema + loader`
   - New file: `src/ontology/concept_ontology.py` (loads from `data/concept_ontology/*.yaml`)
   - New dir: `data/concept_ontology/` (empty, schema defined)

5. `feat(test): gold eval set pytest fixture + eval harness skeleton`
   - New file: `tests/data/gold_eval_set.json` (scholar-validated, required before merge)
   - New file: `tests/eval/test_routing_accuracy.py`

**Exit criteria:**
- BUG-001 + BUG-004 fixed, CI green
- `tests/data/gold_eval_set.json` present (scholar sign-off on all entries)
- YAML schema agreed, loader tested

---

### Sprint 1 — Gate 1: ContractTypeClassifier (4 days)

**Goals:**
- Deterministic contract type classification
- Emergency override for the `غرامة التأخير / عقود المقاولات` class
- First passing eval harness run

**Commits:**

1. `feat(classifier): ContractTypeClassifier — deterministic keyword/regex Gate 1`
   - New file: `src/chatbot/contract_classifier.py`
   - `ContractFamily` enum: ISTISNA, MURABAHAH, IJARAH, MUDARABAH, MUSHARAKAH,
     SALAM, KAFALA, WAKALA, QARD, TAWARRUQ, BAY_DAYN, SUKUK
   - `FAMILY_PATTERNS` dict: Arabic + English + transliteration triggers per family
   - `classify(query) → ContractFamily | None`
   - LLM fallback triggered only when `classify()` returns None AND len(query.split()) > 15

2. `feat(classifier): wire ContractTypeClassifier into ApplicationService`
   - File: `src/chatbot/application_service.py` ~L130
   - Add after `cleaned_query = self._normalize_query(...)`
   - Pass `contract_family_hint` into `scenario.contract_family`

3. `fix(query_preprocessor): consolidate DOMAIN_QUERY_EXPANSIONS (BUG-003)`
   - File: `src/rag/query_preprocessor.py`
   - Remove all `.update()` calls
   - Merge all keys into one dict literal, union of all expansion tuples on collision
   - Add: `"عقود المقاولات"`, `"غرامة التأخير"` expansion entries

4. `test: Sprint 1 test suite (12 new tests)`
   - `tests/test_contract_classifier.py` (8 tests — see test suite below)
   - Extend `tests/test_clarification_engine.py` (3 tests)
   - Extend `tests/test_query_preprocessor.py` (1 test)

**Exit criteria:**
- `هل شرط غرامة التأخير في عقود المقاولات شرط ربوي؟` → routes to `ISTISNA`, no clarification asked
- Forbidden Standard Hit Rate = 0% for this query class on eval harness
- All 12 Sprint 1 tests pass

---

### Sprint 2 — Gate 2: Concept Ontology Router (1 week)

**Goals:**
- YAML-driven concept ontology with first 10 nodes
- Standard family router: `contract_type × concept → eligible_standard_ids[]`
- Supersession filter from existing governance catalog
- Fix BUG-002 structurally (contract-specific routing replaces generic 'contract' type)

**Commits:**

1. `feat(ontology): seed 10 concept nodes in YAML`
   - `data/concept_ontology/late_penalty.yaml`
   - `data/concept_ontology/profit_margin.yaml`
   - `data/concept_ontology/guarantee_fee.yaml`
   - `data/concept_ontology/debt_sale.yaml`
   - `data/concept_ontology/capital_guarantee.yaml`
   - `data/concept_ontology/deferred_delivery.yaml`
   - `data/concept_ontology/maintenance_obligation.yaml`
   - `data/concept_ontology/tawarruq.yaml`
   - `data/concept_ontology/promise_binding.yaml`
   - `data/concept_ontology/surplus_distribution.yaml`

2. `feat(router): ConceptOntologyRouter — YAML lookup → eligible_standard_ids`
   - New file: `src/ontology/concept_router.py`
   - `route(contract_type, concepts[]) → RouteResult{standard_ids, ruling_conditions, party_roles}`
   - Applies supersession filter from `data/sources/source_catalog.yaml` (existing)

3. `feat(router): wire ConceptOntologyRouter into ApplicationService`
   - Between Gate 1 and retrieval
   - Output `eligible_standard_ids` passed to retrieval as Chroma `where` filter

4. `feat(ruling): RulingFunctionEvaluator — evaluates f(RulingContext) → RulingResult`
   - New file: `src/ontology/ruling_evaluator.py`
   - Checks ruling_conditions against user's described situation
   - Exception detection: matches exception signals against ruling_conditions
   - Sets `requires_scholar_review = True` when confidence < 0.75

5. `fix(clarification): expand OPERATION_KEYWORD_GROUPS_AR (BUG-002)`
   - Replace generic 'contract' bucket with per-family groups
   - This commit is now safe because Gate 1 handles routing; clarification handles only data collection

**Exit criteria:**
- `عقود المقاولات` queries route to `eligible_standard_ids = ["SS-11", "SS-5"]`
- BUG-002 structurally resolved
- All YAML nodes schema-valid
- Routing accuracy ≥ 85% on gold eval set (Murat's gate)

---

### Sprint 3 — Gate 3: Scoped Hybrid Retrieval + Scholar Loop Wiring (1 week)

**Goals:**
- BM25 sparse retrieval alongside existing dense retrieval, merged with RRF
- Retrieval scoped to `eligible_standard_ids` from Gate 2
- Scholar review loop wired (Q1 auto-flag + Q2 random sample)

**Commits:**

1. `feat(retrieval): BM25Retriever — zero stack replacement`
   - File: `src/rag/pipeline.py` (extend, not replace)
   - New class `BM25Retriever` using `rank_bm25.BM25Okapi`
   - BM25 corpus: serialized at index time, loaded on startup (~50MB RAM for full corpus)
   - `retrieve(query, top_k=20) → list[ScoredDoc]`

2. `feat(retrieval): RecipocalRankFusion merger`
   - `rrf_merge(dense_results, sparse_results, k=60) → ranked_ids`

3. `feat(retrieval): scope retrieval to eligible_standard_ids`
   - Pass Gate 2 output as Chroma `where={"ss_number": {"$in": eligible_standard_ids}}`
   - If no eligible_standard_ids → full corpus search (fallback, logged as anomaly)

4. `feat(scholar): wire ScholarReviewStore to routing pipeline`
   - Every `RulingResult` with `requires_scholar_review=True` → appended to `scholar_review_queue.jsonl`
   - Random 5% sampling: `if random.random() < 0.05: → append to Q2 queue`
   - User-flag endpoint: `POST /api/flag-answer` → appends to Q3 queue

5. `feat(scholar): scholar review form schema`
   - New file: `src/scholar/review_schema.py`
   ```python
   class ScholarReview(BaseModel):
       query_id: str
       scholar_name: str
       scholar_institution: str
       ruling_accuracy: Literal["CORRECT", "WRONG", "PARTIALLY_CORRECT"]
       standard_citation: Literal["CORRECT", "WRONG", "MISSING"]
       disagreement_disclosed: Literal["YES", "NO", "NA"]
       severity_if_wrong: Literal["CRITICAL", "HIGH", "MEDIUM", "NA"]
       corrected_answer_ar: Optional[str]
       corrected_ruling: Optional[str]
       corrected_standards: Optional[list[str]]
       review_timestamp: str
       new_edge_case: bool  # scholar-identified new hard case
   ```

**Exit criteria:**
- Hybrid retrieval live (dense + BM25 + RRF)
- Scholar review queue populating for auto-flagged queries
- Random 5% sampling of live answers feeding Q2 queue
- All existing tests pass

---

### Sprint 4 — Egypt Corpus Integration (1 week)

**Goals:**
- Egypt acquisition pipeline: scraper → entity extractor → EgyptRuling schema → ingest
- Separate retrieval path (not merged into AAOIFI corpus)
- `governed=False` on all Egypt chunks until routing accuracy ≥ 85% confirmed in CI

**Commits:**

1. `feat(acquisition): EgyptRuling Pydantic schema`
   - New file: `src/acquisition/schemas/egypt_ruling_schema.py`
   - Key fields: `source_institution`, `contract_family`, `party_roles`, `ruling_text_ar`,
     `permissibility`, `conditions`, `legal_basis`, `source_url`, `source_file_hash`, `governed=False`

2. `feat(acquisition): EgyptInstitutionScraper`
   - New file: `src/acquisition/egypt_institution_scraper.py`
   - Sources: Dar al-Ifta, EFSA, Al-Azhar, CBE (regulatory circulars)
   - pdfplumber for PDF extraction (preserves Arabic RTL)
   - ALL scraper network calls use saved HTML fixtures in tests (never live in CI)

3. `feat(acquisition): EgyptEntityExtractor`
   - New file: `src/acquisition/egypt_entity_extractor.py`
   - Deterministic regex layer first; LLM structured extraction fallback
   - Outputs `EgyptRuling` objects, not raw text chunks
   - Phase A: Inventory only (map ~40 CBE/FRA institutions, no product scraping)

4. `feat(retrieval): Egypt corpus as separate Qdrant collection`
   - `source_family = SourceFamily.EGYPT_INSTITUTION` (new enum value)
   - Separate retrieval path: question_type = "operational" → Egypt collection
   - `governed=False` chunks blocked by existing `is_answer_admissible_metadata` gate

5. `feat(router): hybrid question routing (normative vs. operational vs. hybrid)`
   ```python
   QUESTION_TYPE_ROUTING = {
       "normative":   ["AAOIFI_SS", "AAOIFI_FAS"],
       "operational": ["EGYPT_INSTITUTION"],
       "hybrid":      ["AAOIFI_SS", "EGYPT_INSTITUTION"],  # merge + rank
   }
   ```

**Exit criteria:**
- Egypt acquisition pipeline produces valid `EgyptRuling` objects from fixture HTML
- Egypt chunks in Qdrant but `governed=False` (not answer-admissible)
- Zero Egypt corpus pollution of AAOIFI standard corpus
- Scraper tests use fixture HTML only (no live network in CI)

---

### Sprint 5 — Scholar Review Activation + Known Operations Cache + Dashboard (1 week)

**Goals:**
- Flip Egypt chunks to `governed=True` after routing accuracy ≥ 85% confirmed
- Operations Dashboard for the development and review team
- Known-operations cache with ruling_conditions (exception detection)
- Post-launch QA random sampling operational

**Commits:**

1. `feat(dashboard): Operations & Review Dashboard UI`
   - Build into existing UI/FastAPI stack
   - Views for Queue Health, Eval Accuracy, SLA tracking, and Ontology diffs
   - Endpoint: `GET /api/dashboard/stats`

2. `feat(cache): KnownOperationsCache with ruling_conditions`
   - New file: `src/cache/known_operations.py`
   - `{product_id, product_name, ruling, ruling_conditions[], governed}`
   - Exception detector: `detect_exceptions(query, ruling_conditions) → list[ViolatedCondition]`
   - Cache used as context, never as direct answer without exception check

3. `feat(acquisition): activate governed Egypt chunks after CI gate passes`
   - CI gate: `tests/eval/test_routing_accuracy.py` must pass (≥ 85% on gold eval set)
   - Governance script: `scripts/approve_egypt_corpus.py` flips `governed=True` in batch

4. `feat(scholar): post-launch random sampling operational`
   - Q2 queue (5% random) operational
   - Scripts for export/import formalized (`scripts/export_scholar_review.py`, `scripts/import_scholar_corrections.py`)

5. `feat(ontology): scholar corrections feed back into ontology YAML`
   - Import script maps `corrected_ruling` → patches corresponding YAML node
   - Import script maps `new_edge_case = True` → creates new entry in gold eval set
   - Ontology patches trigger CI re-run automatically

**Exit criteria:**
- Scholar review loop fully operational (export/import scripts working)
- Operations Dashboard live and displaying accurate queue/eval stats
- Egypt chunks `governed=True` only after CI gate confirmed
- Known operations cache exception detection working
- Full test suite passes: L1 unit + L2 integration + L3 ATDD + L4 nightly eval

---

## Scholar Review — Operational Model

### How It Works (Document-Based Loop + Operations Dashboard)

The scholar does NOT interact with any complex interface to perform reviews. The primary review mechanism for the scholar is a **structured Excel document**.
However, for the **Development Team, Review Managers, and QA**, a **Review & Operations Dashboard** is required to track the health of the system.

```
[System] Generates review items
    ↓
[Dashboard] Review Managers monitor queue sizes and system confidence metrics
    ↓
[Script] scripts/export_scholar_review.py
    → writes: scholar_review_YYYY-MM-DD.xlsx
    ↓
[Human] Sends document to Scholar (email / WhatsApp / shared drive)
    ↓
[Scholar] Annotates the document in Excel
    ↓
[Human] Receives annotated document from Scholar
    ↓
[Script] scripts/import_scholar_corrections.py scholar_review_YYYY-MM-DD.xlsx
    → patches: data/concept_ontology/*.yaml
    → updates: tests/data/gold_eval_set.json
    → appends: data/scholar_corrections_log.jsonl
    → triggers: CI re-run of gold eval set
    ↓
[Dashboard] Updates routing accuracy, reflects new ontology patches, and clears queue counts
```

---

### The Review & Operations Dashboard (M5 Deliverable)

While the scholar uses Excel, the core team needs a web dashboard (built into the existing FastAPI/UI stack) to monitor the entire pipeline:

**Key Dashboard Views:**
1. **Queue Health:** Real-time counts of Q1 (Auto-Flagged), Q2 (Random Sample), and Q3 (User-Flagged) queues.
2. **System Accuracy Tracker:** Live display of the *Forbidden Standard Hit Rate* and *Standard Routing Accuracy* against the Gold Eval Set (from the latest CI run).
3. **Scholar SLA Monitor:** Time elapsed since items were added to the queue vs. when they were imported back.
4. **Ontology Changelog:** Visual diff of recent patches made to the YAML ontology files.
5. **Egypt Corpus Status:** (Once M3 is active) Number of scraped operations, extraction success rate, and `governed` status.

---

### Three Review Queues

| Queue | Trigger | Cadence | Volume |
|---|---|---|---|
| **Q1 — Auto-Flagged** | confidence < 0.75 OR DISPUTED OR CONDITIONAL | Per batch (weekly or on-demand) | ~10–20% of queries |
| **Q2 — Random Sample** | 5% random of all answered queries | Weekly | ~5% of queries |
| **Q3 — User-Flagged** | User clicks "Flag this answer" in UI | As needed (highest priority) | User-driven |

All three queues are written to `data/scholar_review_queue.jsonl` (append-only).
The export script reads this file and produces the review document.

---

### Scholar Review Document Format

**Format:** Excel (.xlsx) — bilingual columns (Arabic + English), one row per review item.
The scholar fills in the shaded columns. All other columns are read-only for the scholar.

| Column | Who fills it | Content |
|---|---|---|
| `query_id` | System | Unique ID e.g. `q-20260527-001` |
| `query_ar` | System | Original Arabic query |
| `query_en` | System | English translation |
| `system_answer_ar` | System | System's generated answer in Arabic |
| `system_ruling` | System | PERMISSIBLE / PROHIBITED / CONDITIONAL / DISPUTED |
| `system_standards` | System | e.g. SS-3, FAS-30 |
| `system_confidence` | System | 0.0 – 1.0 |
| `flag_reason` | System | Why this was queued (low confidence / random / user-flagged) |
| `queue` | System | Q1 / Q2 / Q3 |
| **`scholar_ruling`** | **Scholar** | صحيح / خاطئ / صحيح جزئياً |
| **`corrected_ruling`** | **Scholar** | جائز / لا يجوز / جائز بشروط / خلافي |
| **`corrected_standards`** | **Scholar** | e.g. SS-11, SS-5 |
| **`corrected_answer_ar`** | **Scholar** | Scholar's correct Arabic answer (if wrong) |
| **`conditions`** | **Scholar** | Conditions on permissibility (comma-separated) |
| **`dalil`** | **Scholar** | Legal basis / Quran / Hadith / AAOIFI clause |
| **`new_edge_case`** | **Scholar** | نعم / لا — if Yes, adds to gold eval set |
| **`severity`** | **Scholar** | حرج / عالي / متوسط (CRITICAL / HIGH / MEDIUM) |
| **`scholar_notes`** | **Scholar** | Any free-text notes in Arabic |

**The document is RTL-aware (Arabic columns right-aligned).** The scholar only touches the shaded columns.

---

### Export Script — `scripts/export_scholar_review.py`

```python
"""
Usage: python scripts/export_scholar_review.py
Outputs: scholar_review_YYYY-MM-DD.xlsx in project root
"""
import json, openpyxl, random
from datetime import date
from pathlib import Path

QUEUE_FILE = Path("data/scholar_review_queue.jsonl")
OUTPUT = Path(f"scholar_review_{date.today()}.xlsx")

# Load pending items (not yet reviewed)
pending = [
    json.loads(line)
    for line in QUEUE_FILE.read_text(encoding="utf-8").splitlines()
    if json.loads(line).get("scholar_sign_off") != "DONE"
]

# Random 5% sample from Q2 (answered queries log)
answered = load_answered_queries_log()  # reads data/answered_queries.jsonl
random_sample = random.sample(answered, k=max(1, len(answered) // 20))
for item in random_sample:
    item["queue"] = "Q2"
    pending.append(item)

# Write to Excel
wb = openpyxl.Workbook()
ws = wb.active
ws.sheet_view.rightToLeft = True  # RTL for Arabic
# ... write headers and rows ...
wb.save(OUTPUT)
print(f"Review document ready: {OUTPUT}")
print(f"Items for scholar review: {len(pending)}")
```

---

### Import Script — `scripts/import_scholar_corrections.py`

```python
"""
Usage: python scripts/import_scholar_corrections.py scholar_review_2026-05-27.xlsx
Applies scholar corrections to:
  - data/concept_ontology/*.yaml  (ruling patches)
  - tests/data/gold_eval_set.json  (new edge cases)
  - data/scholar_corrections_log.jsonl  (audit trail)
"""
import sys, json, yaml, openpyxl
from pathlib import Path

doc = openpyxl.load_workbook(sys.argv[1])
ws = doc.active

for row in ws.iter_rows(min_row=2, values_only=True):
    query_id, *_, scholar_ruling, corrected_ruling, corrected_standards, \
        corrected_answer_ar, conditions, dalil, new_edge_case, severity, notes = row

    if not scholar_ruling:  # scholar left this row blank = not reviewed yet
        continue

    correction = {
        "query_id": query_id,
        "scholar_ruling": scholar_ruling,
        "corrected_ruling": corrected_ruling,
        "corrected_standards": [s.strip() for s in (corrected_standards or "").split(",")],
        "corrected_answer_ar": corrected_answer_ar,
        "conditions": [c.strip() for c in (conditions or "").split(",") if c.strip()],
        "dalil": dalil,
        "new_edge_case": new_edge_case == "نعم",
        "severity": severity,
        "scholar_notes": notes,
    }

    # 1. Patch ontology YAML if ruling was wrong
    if scholar_ruling != "صحيح":
        patch_ontology_yaml(correction)   # updates data/concept_ontology/*.yaml

    # 2. Add to gold eval set if scholar flagged as new edge case
    if correction["new_edge_case"]:
        append_to_gold_eval_set(correction)  # updates tests/data/gold_eval_set.json

    # 3. Mark queue item as reviewed
    mark_reviewed(query_id)               # sets scholar_sign_off="DONE" in queue

    # 4. Append to audit log
    log_correction(correction)            # appends to data/scholar_corrections_log.jsonl

print("Import complete. Run CI to validate ontology patches.")
print("Command: pytest tests/eval/test_routing_accuracy.py -v")
```

---

### Scholar Corrections Feed the System

```
Scholar returns annotated .xlsx
    ↓
python scripts/import_scholar_corrections.py scholar_review_YYYY-MM-DD.xlsx
    ↓
├── Patches data/concept_ontology/*.yaml  (wrong rulings corrected)
├── Appends tests/data/gold_eval_set.json (new edge cases added)
└── Appends data/scholar_corrections_log.jsonl (full audit trail)
    ↓
pytest tests/eval/test_routing_accuracy.py
    ↓
IF routing_accuracy ≥ 85% → patches committed to git
IF routing_accuracy < 85% → developer alerted, patch held
    ↓
Contrastive training pairs auto-generated from corrected entries
(for future fine-tuning of Gate 1 classifier)
```

---

### What the Scholar Actually Sees (Example Row)

```
Query ID:      q-20260527-001
السؤال:       هل شرط غرامة التأخير في عقود المقاولات شرط ربوي؟
Question:      Is the penalty clause in construction contracts considered riba?

System Answer: تعد غرامة التأخير في عقود المقاولات من قبيل الفائدة الربوية...
System Ruling: PROHIBITED
System Cited:  SS-3, FAS-30
Confidence:    0.43
Flagged for:   Low confidence + incorrect routing suspected

[SCHOLAR FILLS IN:]
حكم النظام:    خاطئ
الحكم الصحيح:  جائز بشروط
المعايير:      SS-11، SS-5
الجواب الصحيح: غرامة التأخير في عقد الاستصناع تختلف عن الغرامة في عقود الدين...
الشروط:        أن يكون التأخير من المقاول، أن تمثل الغرامة ضرراً فعلياً
الدليل:        المعيار الشرعي رقم 11 البند 4/3
حالة جديدة؟:   لا
الخطورة:       حرج
ملاحظات:       يجب التمييز بين عقود المقاولات وعقود الدين
```

The scholar annotates directly in the Excel file, returns it, and the import script does the rest.
No system access required. No training required. Just Excel.

---

## Gold Evaluation Set — 26+ Queries (Scholar-Validated)

### Category A: Istisna Trap (3 queries)
- TC-A1: غرامة التأخير في عقود المقاولات → SS-11 + SS-5 (NOT SS-3)
- TC-A2: تأخر تسليم المشروع في الاستصناع → SS-11
- TC-A3: غرامة مقاول على البنك → SS-11 + SS-5

### Category B: Debt Trading (2 queries)
- TC-B1: بيع الدين → SS-60 (at par vs. discount clarification required)
- TC-B2: بيع الصكوك بأقل من قيمتها → SS-60 + Sukuk standards

### Category C: Paid Guarantee (2 queries)
- TC-C1: كفالة مقابل أجر → SS-5 (contested; scholarly disagreement required)
- TC-C2: رسوم خطاب الضمان → SS-5 (operational fee vs. % fee distinction)

### Category D: Controversial Rulings (2 queries)
- TC-D1: التورق المصرفي المنظم → SS-30 + OIC Fiqh Academy position
- TC-D2: الفرق بين التورق الفردي والمنظم → SS-30 with explicit comparison

### Category E: Mudaraba Guarantee (2 queries)
- TC-E1: ضمان رأس مال المضاربة → SS-13 + SS-5 (BOTH required)
- TC-E2: ضمان طرف ثالث لرأس المضاربة → SS-13 boundary case

### Category F: Deferred Sale Delivery (1 query)
- TC-F1: تأخير تسليم المبيع في البيع المؤجل → SS-1 (NOT Salam SS-7)

### Category G: Egyptian Practice Traps (4 queries — from Murat)
- TC-G1: هامش ربح على التمويل العقاري → IMB (SS-9, SS-14) NOT Murabaha (SS-8)
- TC-G2: مشاركة متناقصة في شراء شقة → SS-12 + promise binding conditions
- TC-G3: وديعة استثمارية + جائزة سنوية → Qard + prize draw = PROHIBITED
- TC-G4: تأمين تكافلي + فائض → SS for Takaful, surplus to participants not operator

### Category H: Hard Fiqh Cases (10 queries — from Dr. Quinn)
- TC-H1: Bay' al-Wafa (repurchase obligation) → OIC Res. 40/2/5, PROHIBITED
- TC-H2: Tawarruq Munazzam → OIC Res. 179/2009, PROHIBITED; individual tawarruq PERMITTED
- TC-H3: Ijarah floating rate → madhab-dependent (Hanafi/Maliki vs. Shafi'i)
- TC-H4: Parallel Salam linkage → PROHIBITED if delivery chain linked
- TC-H5: Mudarib employee negligence → LIABLE (Majallah Art. 92)
- TC-H6: Istisna for software/IP → DISPUTED (jurisdiction-specific)
- TC-H7: Kafala percentage fee → PROHIBITED; only admin costs permitted
- TC-H8: Ijarah maintenance on lessee → VOID if structural maintenance transferred
- TC-H9: Bilateral Wa'd → treated as contract, all sale conditions must be present
- TC-H10: Takaful surplus to operator → PROHIBITED; surplus belongs to participants

---

## QA Gates

### Gate L5: Pre-Scholar Review (ALL blocking)
| Check | Threshold |
|---|---|
| Standard Routing Accuracy | ≥ 85% |
| **Forbidden Standard Hit Rate** | **= 0% (zero tolerance)** |
| Precision@5 | ≥ 0.80 |
| Disagreement Disclosure Rate | ≥ 90% on contested queries |
| MRR | ≥ 0.75 |

### Gate L6: Production Launch (ALL blocking)
| Check | Threshold |
|---|---|
| Scholar-validated ruling accuracy | ≥ 95% |
| Scholar-flagged hallucinations | = 0 |
| Standard citation accuracy | ≥ 98% |
| All 26+ gold eval set queries | 100% pass |

### Post-Launch Continuous Gates
| Metric | Target | Alert |
|---|---|---|
| Forbidden Standard Hit Rate (weekly) | = 0% | Immediate |
| Scholar Q1 queue depth | < 50 pending | > 100 = escalate |
| Scholar Q2 review accuracy | ≥ 95% | < 90% = alert |
| Ontology patch success rate | ≥ 98% CI pass | Any failure = block |

---

## Critical Path

```
PREREQUISITE ZERO: Scholar validates gold_eval_set.json
    ↓
Sprint 0: Fix BUG-001+004, eval harness, ontology schema
    ↓
Sprint 1: ContractTypeClassifier (Gate 1)
    → عقود المقاولات query class no longer gives wrong answers
    ↓
Sprint 2: ConceptOntologyRouter + RulingFunctionEvaluator (Gate 2)
    → Routing accuracy ≥ 85% on gold eval set
    → BUG-002 structurally resolved
    ↓
Sprint 3: Hybrid Retrieval + Scholar Loop Wiring (Gate 3)
    → Scholar review queues active
    → Random post-launch sampling live
    ↓
Sprint 4: Egypt Corpus
    → governed=False until CI gate confirmed
    ↓
Sprint 5: Scholar Activation + Known Operations Cache
    → Egypt chunks governed=True after CI pass
    → Exception detection for known operations
    → Full system live
```

**Total: ~6 weeks. HuggingFace deployment stays live throughout (strangler fig pattern).**

---

## What Must NOT Change

- ✅ FastAPI + SSE stack — keep
- ✅ Source Governance Catalog (YAML, SS-01–SS-60) — keep, extend with supersession graph
- ✅ ScholarReviewStore as append-only JSONL — keep, wire to routing
- ✅ OpenRouter as LLM abstraction — keep
- ✅ CitationValidator — keep, strengthen with contract-family awareness
- ✅ PromptBuilder AAOIFI-only constraint — **do not loosen this under any circumstances**
- ✅ Fail-closed guard for permissibility questions without Sharia evidence — keep

---

*Implementation plan locked. Two decisions made. Prerequisite zero is the scholar.*
