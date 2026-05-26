# Complete AAOIFI Sharia Evidence Base Plan

Date: 2026-05-25
Status: planning artifact from BMAD party-mode rethink

## Current State

The local Chroma index is now governed and safe, but it is not a complete Sharia Standards evidence base.

| Item | Current value |
| --- | --- |
| Active Chroma collection | `aaoifi` |
| Total governed chunks | `21,160` |
| Chunks with `source_family=sharia_standard` | `3,152` |
| Local Sharia-standard files | `10` markdown files |
| Local Sharia standard numbers | `SS-02`, `SS-04`, `SS-09`, `SS-11`, `SS-15` |
| Catalog records | `102` |
| Cataloged status | All chunks are `cataloged` |
| Missing governed metadata | `0` in the rebuilt local index |

AAOIFI's official Shari'ah Standards page is the acquisition authority for the standards class and exposes an official Sharia standards PDF download path. The page also presents AAOIFI's standards navigation, e-standards, development/revision process, exposure drafts, standards progress, technical releases, and guidance notes. Production acquisition must respect AAOIFI licensing and should not rely on unauthorised copies.

## Definition of Complete

Complete does not mean Mushir can answer every Sharia question. It means Mushir can prove its authority boundary.

The evidence base is complete for launch only when:

1. The in-scope AAOIFI Sharia Standards corpus is acquired from official or licensed sources.
2. Every standard has bilingual catalog records where available.
3. Every ingested chunk has source ID, source family, metadata status, section path, citation anchor, title, source hash, currentness, review status, and license status.
4. Every hard Sharia answer can cite exact AAOIFI standard, clause/section, and evidence text.
5. If exact AAOIFI evidence is unavailable, Mushir refuses or asks a focused clarification question.
6. Scholar-reviewed gold cases cover all high-risk product families and ambiguity traps.
7. Retrieval, citation, and answer behavior are measured against the same locked gold set before any model/reranker upgrade.

## Target Source Classes

| Source class | Runtime authority | Use |
| --- | --- | --- |
| Official AAOIFI Sharia Standards text/PDF | Primary | Answer support for Sharia standard claims |
| Licensed AAOIFI e-standards export | Primary | Preferred source when contractually available |
| Verified local markdown derived from official source | Primary after governance | Chroma/Qdrant ingestion after checksum and review |
| AAOIFI guidance notes / technical releases | Supporting | Contextual support, not replacement for standard clauses |
| AAOIFI exposure drafts | Non-current unless approved | Candidate/planning only; not answer-admissible unless policy says so |
| IIFA resolutions and other trusted fiqh bodies | Secondary support | Gold-case research and conflict detection; never presented as AAOIFI |
| Bank/FRA/CBE/service pages | Scenario evidence | Product/service facts, not Sharia authority |
| Scholar-reviewed internal cases | Supervised evaluation | Gold tests and reviewed answer outlines tied to primary sources |

## Required Catalog Schema Enhancements

The current `data/source_registry/aaoifi-source-catalog.yaml` is a useful machine-generated seed, but a complete Sharia evidence base needs a richer Sharia catalog.

Add or maintain:

| Field | Reason |
| --- | --- |
| `standard_id` | Stable ID independent of filename |
| `standard_number` | SS number as published |
| `title_en`, `title_ar` | Bilingual routing and display |
| `edition`, `publication_date`, `effective_date` | Version control |
| `language` | Arabic/English authority handling |
| `source_url`, `source_file`, `source_hash` | Provenance and rebuild verification |
| `license_status` | Prevent unsafe production use |
| `currentness`, `superseded_by`, `supersedes` | Stop stale answers |
| `topics` | Retrieval pre-filtering |
| `financial_products` | Murabaha, Ijarah, Sukuk, etc. |
| `risk_domains` | Riba, gharar, guarantee, penalty, purification, etc. |
| `related_standards` | Cross-standard retrieval |
| `review_status` | Machine checked vs scholar/human reviewed |
| `answer_admissible` | Hard runtime gate |

## Clause-Level Ingestion Requirements

Flat semantic chunks are not enough for hard Sharia cases. Ingestion should create clause-aware records.

Each clause/child chunk should include:

- `source_id`
- `source_family=sharia_standard`
- `metadata_status=cataloged`
- `standard_number`
- `standard_title_en`
- `standard_title_ar`
- `language`
- `clause_id`
- `section_path`
- `section_depth`
- `citation_anchor`
- `page_number` when PDF-derived
- `paragraph_number` when available
- `normative_role`: `definition`, `rule`, `condition`, `exception`, `evidence_basis`, `application`, `appendix`
- `parent_chunk_id`
- `neighbor_previous_id`
- `neighbor_next_id`
- `cross_references`
- `operation_tags`
- `risk_tags`
- `source_hash`
- `catalog_version`
- `corpus_version`
- `index_version`

## Recommended Index Architecture

Keep Chroma acceptable for local/demo, but stop treating one collection as the whole evidence model.

| Index / collection | Purpose |
| --- | --- |
| `aaoifi_clause_index` | Exact clause-level retrieval |
| `aaoifi_section_index` | Parent section context |
| `aaoifi_definition_index` | Definitions and terminology |
| `aaoifi_crossref_index` | Standard-to-standard and clause-to-clause links |
| `aaoifi_topic_index` | Catalog-driven topic/product/risk routing |
| `fiqh_support_index` | Secondary trusted sources, always lower authority |
| `institution_operation_index` | Bank/FRA/CBE product facts, not Sharia authority |

Runtime retrieval flow:

1. Classify query language, intent, financial product, and risk domain.
2. Route to candidate standards using the catalog before vector search.
3. Retrieve exact clauses and definitions from the Sharia indexes.
4. Expand to parent section and neighboring clauses.
5. Check cross-references and exceptions.
6. Rerank by catalog relevance, normative role, clause anchor quality, and language match.
7. Generate only if citation coverage satisfies the hard-case gate.

## Hard Sharia Case Taxonomy

Initial high-risk domains:

| Domain | Typical trap |
| --- | --- |
| Late penalties | Contractor delivery delay vs debtor payment delay |
| Murabaha | Ownership/risk sequence, binding promise, agency ambiguity |
| Tawarruq | Organised tawarruq vs genuine commodity transaction |
| Ijarah | Ownership, maintenance, risk, late rent penalties |
| Istisna / Muqawala / Supply | Manufacturing vs non-manufacturing supply; payment timing |
| Salam | Full price at contract vs deferred mutual obligations |
| Guarantees / Kafalah | Actual cost fee vs amount/duration-based fee |
| Sukuk | Asset-backed vs debt-backed, principal guarantee, purchase undertaking |
| Mudarabah / Musharakah | Capital guarantee and profit/loss allocation |
| Currency / Sarf | Spot exchange vs deferred settlement |
| Securities screening | Mixed-income ratios, debt ratios, purification |
| Insurance / Takaful | Cooperative structure vs conventional risk transfer |
| Agency / Wakala | Agent role, principal risk, fee/profit conflict |
| Debt trading / receivables | Discounting, sale of debt, rescheduling |
| Hedging / derivatives | Promise, exchange, gharar, speculation |

## Scholar Gold Case Program

Gold cases should be authored from evidence, not from model outputs.

Lifecycle:

1. `machine_proposed`
2. `pending_evidence_mapping`
3. `pending_scholar_review`
4. `accepted`
5. `accepted_with_correction`
6. `rejected_unsupported`
7. `wrong_standard`
8. `stale_source`
9. `translation_issue`
10. `unsafe_answer`

Each accepted gold case must include:

- original user query
- Arabic/English/mixed variants
- normalized financial operation
- ambiguity triggers
- expected behavior: `answer`, `clarify`, `refuse`, or `insufficient_data`
- expected source family
- required standards and clauses
- accepted answer outline
- allowed limitations
- forbidden answer claims
- corpus version
- catalog version
- index version
- rule version if applicable
- scholar reviewer and decision metadata

## Evaluation Gates

No production claim of complete Sharia coverage until these gates pass:

| Gate | Minimum |
| --- | --- |
| Corpus coverage | All in-scope Sharia standards cataloged, licensed, and indexed |
| Clause anchoring | 100% answer-admissible chunks have clause/section anchors |
| Metadata completeness | 100% chunks have governed source metadata |
| Standard retrieval | Gold queries retrieve expected standard at top-k |
| Clause retrieval | Gold queries retrieve expected clause/section |
| Source-family precision | No FAS-only support for Sharia permissibility answers |
| Citation support | Every cited answer has retrieved source text |
| Refusal correctness | Missing-authority cases refuse instead of guessing |
| Clarification precision | Ambiguous cases ask one highest-value question |
| Arabic parity | Arabic and English variants route to equivalent authority |
| Translation drift | Arabic/English conflicts are flagged, not merged silently |
| Hard-case traps | Known traps do not collapse into the wrong standard |

## Runtime No-Go Criteria

Block answer generation when:

- no AAOIFI Sharia clause is retrieved for a permissibility/prohibition answer;
- retrieved evidence lacks source ID, citation anchor, standard number, or currentness;
- retrieved evidence is secondary-only;
- query maps to a hard Sharia case and the expected standard domain is absent;
- Arabic and English sources conflict or one is missing for a language-sensitive case;
- the user asks for a binding fatwa or personal financial/legal advice;
- the answer would require facts not present in the user query or retrieved scenario evidence;
- scholar gold cases for the domain are not yet accepted.

## Implementation Milestones

### M0: Authority Inventory Lock

- Build `aaoifi_sharia_inventory.csv`.
- Record all official Sharia standards, available languages, source URLs, license status, and acquisition status.
- Mark current local state as partial: `SS-02`, `SS-04`, `SS-09`, `SS-11`, `SS-15`.

### M1: Licensed Source Acquisition

- Acquire official/licensed standards.
- Store raw source files under a governed source folder.
- Generate checksums.
- Produce source records before text conversion.

### M2: Structured Extraction

- Convert PDFs/e-standards into structured markdown or JSON.
- Preserve pages, headings, clause numbers, footnotes, tables, and appendices.
- Run extraction QA per standard.

### M3: Sharia Catalog Upgrade

- Replace filename-inferred Sharia catalog with reviewed catalog.
- Add topics, risk domains, product families, related standards, and license status.
- Mark incomplete or unlicensed sources not answer-admissible.

### M4: Clause-Aware Index Rebuild

- Build to a temp index.
- Validate all governed metadata.
- Validate counts per standard and per language.
- Swap atomically only after gates pass.

### M5: Hard-Case Retrieval Baseline

- Expand gold fixtures from FAS-heavy cases to Sharia hard cases.
- Measure standard hit, clause hit, refusal correctness, clarification precision, and Arabic parity.

### M6: Scholar Review Loop

- Create review tables for evidence mappings and answer outlines.
- Require accepted scholar review before a case becomes a release gate.

### M7: Runtime Hard-Case Policy

- Add `hard_sharia_case` routing.
- Require clause-level Sharia evidence and cross-standard checks.
- Expose readiness counts by source family, standard, language, and metadata status.

### M8: Controlled Expert Beta

- Release to internal reviewers only.
- Log weak retrieval, missing standards, and unsafe attempts.
- Feed corrections back into catalog/gold set, not silent prompts.

## Immediate Next Engineering Slices

1. Add a corpus coverage command that reports standard counts by source family, language, and answer admissibility.
2. Add `/ready` fields for Sharia-standard coverage, not just total Chroma readiness.
3. Add a Sharia inventory file seeded from official AAOIFI pages and current local corpus.
4. Add clause/citation-anchor extraction tests using a controlled PDF/markdown sample.
5. Expand `tests/fixtures/gold_eval_fixture_baseline.yaml` with hard Sharia retrieval-only cases.
6. Create a no-go test: permissibility question cannot answer from FAS-only or secondary-only evidence.
7. Add reviewed topic/risk tags for the current five local Sharia standards.

## Decision

The next phase should be named **Evidence Completion and Scholar Validation**, not model improvement.

Retrieval upgrades such as BM25, BGE-M3, rerankers, or Qdrant hybrid search are useful only after the complete governed Sharia corpus, clause anchors, and hard-case gold set exist.
