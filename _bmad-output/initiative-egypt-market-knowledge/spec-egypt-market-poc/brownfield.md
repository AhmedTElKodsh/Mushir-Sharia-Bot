# Brownfield: Existing State and V1.6 Blockers

## Existing assets (V1.5, 2026-09-29)

| Asset | Location | State |
| --- | --- | --- |
| Registry baseline | 2,154 institutions (36 banks, 797 capital-market, 996 insurance, 325 non-bank) | Identity facts only |
| FRA financing register | 328 companies, 38 consumer-finance, 2026-09-23; `scripts/scrape_fra_registry.py` | Identity facts only |
| Bank operations | 69 records from 14 bank sites; `data/runtime/artifacts/l6_scrape/full_scrape/2026-06-01/` | Machine mappings, review input |
| Instalment market map | 85 claims, 52 page matches, 86 entities (30 evidenced, 39 lead-only); `scripts/scrape_egypt_installment_market.py`, `scripts/summarize_egypt_installment_market.py` | Static HTML, English seed terms; misses Arabic-only and JS-rendered content |
| Scholar review tooling | Bilingual review lists, CSV import/export, gold-case projection in `src/governance/institution_pipeline.py` | Implemented |
| Hard-case seeds | HC-001..HC-010 | All pending |
| Deployment | Docker Space, OpenRouter, Chroma multilingual index | V1.5 live path |

Key discovery findings: the Contact consumer-finance appendix puts per-transaction price, instalments, period and return rate in a separate supplementary statement. The noon FAQ says interest and fees depend on the bank. The B.TECH/Mylo buyer path is documented, but its terms forbid automation.

## V1.6 blockers (must close before the POC)

| File | Defect | Required behavior |
| --- | --- | --- |
| `src/chatbot/contract_classifier.py`, `src/chatbot/commercial_assessment.py`, `src/chatbot/prompt_builder.py` | Map generic instalment/finance wording to Islamic contract families | Mechanism stays unknown until evidenced; EN/AR/code-mixed tests |
| `src/chatbot/commercial_assessment.py` | Stores the buyer story as whole-query text | Typed slots per `fact-and-evidence-model.md` |
| `src/chatbot/clarification_engine.py` | Generic field list; family bypass; turn limit can mark ready with missing facts | Rule-specific sufficiency; exhaustion → INSUFFICIENT_DATA |
| `src/ontology/ruling_evaluator.py` | Returns permissibility with unobserved conditions | Tri-state conditions; no verdict on unknown/contradicted |
| `src/chatbot/application_service.py` | `confidence` from retrieval scores; review queued after answering | Evidence-status labels; no % |
| `scripts/summarize_egypt_installment_market.py` | Carries seeded financier name into relationships the passage does not establish | Only passage-established roles; until fixed, rows are not training labels |

## Test environment note

The checkout has no `.venv`; the instalment and FRA tests pass (42) under `uv run --no-project --with pytest`.
