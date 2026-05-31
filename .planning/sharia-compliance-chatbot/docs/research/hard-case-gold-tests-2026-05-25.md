# Hard-Case Scholar Review Candidate Set

Date: 2026-05-25
Status: machine-proposed seed set; not a tuning or learning gold set until each row is accepted by a human Sharia scholar.

This file is a review packet, not runtime authority. Pending rows may be used to check whether the evaluation harness fails closed, but they must not be used to tune retrieval, train models, update concept maps, or add runtime shortcuts. A row becomes a gold case only after scholar review records an accepted decision with source IDs, citation anchors, rationale, corpus version, and rule version.

## Review Contract

Every engine output that comes from scraped financial services, pre-launch evaluation, or post-launch user questions must be captured as a review row before it is allowed to become a gold case, routing rule, concept-map synonym, prompt change, or runtime shortcut.

Required columns:

| Field | Purpose |
| --- | --- |
| review_id | Stable ID for scholar workflow and audit trail. |
| target_type | `scraped_service`, `gold_case`, `runtime_answer`, `router_rule`, `concept_synonym`, or `retrieval_case`. |
| target_id | Source service ID, answer ID, or test-case ID. |
| user_query | Original user or synthetic query, preserving Arabic, English, or mixed wording. |
| normalized_operation | Machine-normalized financial operation, such as `istisna_construction_penalty`. |
| expected_behavior | `answer`, `clarify`, `refuse`, or `insufficient_data`. |
| expected_clarification | Exact single question when clarification is required. |
| source_authority | AAOIFI, IIFA, CBE, FRA, bank page, or other cataloged source. |
| source_id | Governed source ID from the source catalog. |
| citation_anchor | URL or local citation anchor proving the expected behavior. |
| source_family | `sharia_standard`, `fas`, `governance`, `fatwa`, `local_overlay`, etc. |
| metadata_status | `governed`, `cataloged_not_answer_admissible`, or `quarantined_missing_catalog`. |
| candidate_standards | Standards expected to be retrieved or used. |
| retrieved_chunk_ids | Actual chunks retrieved during the run. |
| engine_status | Actual runtime status. |
| engine_answer | Full engine output. |
| uncertainty_flags | Missing facts or ambiguity triggers. |
| scholar_decision | `pending`, `accepted`, `accepted_with_correction`, `rejected_unsupported`, `wrong_standard`, `stale_source`, `translation_issue`, or `unsafe_answer`. |
| scholar_notes | Human reviewer rationale and required correction. |
| corpus_version | Corpus/index version used for evaluation. |
| rule_version | Deterministic rule version, if applicable. |

## Seed Gold Cases

| Case ID | Trusted Source | User Query | Trap | Expected Routing | Expected Behavior | Scholar Status |
| --- | --- | --- | --- | --- | --- | --- |
| HC-001 | IIFA Resolution 109, Penalty Clause: https://iifa-aifi.org/en/32587.html | هل شرط غرامة التأخير في عقود المقاولات شرط ربوي؟ | Same words can mean contractor delivery delay or customer payment delay. Must not map `التأخير` to charity via `خير`. | `source_family=sharia_standard`, `contract_family=istisna`, `candidate_standards=SS-11`, `rule_id=istisna-construction-penalty-v1` | Clarify: هل الغرامة بسبب تأخر المقاول في التسليم أم بسبب تأخر العميل في السداد؟ | pending |
| HC-002 | IIFA Resolution 109, Penalty Clause: https://iifa-aifi.org/en/32587.html | Can we impose a penalty if the contractor is late delivering the project? | Looks like a penalty/debt issue but source distinguishes non-debt construction commitment. | `sharia_standard`; construction/muqawala/istisna route; `candidate_standards=SS-11`. | Answer only if governed Sharia-standard chunks retrieved; otherwise insufficient data. | pending |
| HC-003 | IIFA Resolution 109 and IIFA Installment Sales: https://iifa-aifi.org/en/32398.html | هل غرامة تأخير قسط العميل في بيع بالتقسيط جائزة؟ | Late penalty on debtor/installment purchaser is not the same as contractor delay. | `sharia_standard`; installment/murabaha/debt-late-payment route. | Answer only with governed Sharia evidence; otherwise insufficient data. | pending |
| HC-004 | IIFA Istisna Resolution 65: https://iifa-aifi.org/en/32445.html | هل يجوز شرط جزائي في عقد استصناع لو المصنع اتأخر؟ | Colloquial Arabic and manufacturer delay should route to Istisna, not generic debt. | `sharia_standard`; `contract_family=istisna`; `candidate_standards=SS-11`. | Answer only with governed source; note force majeure as a required fact. | pending |
| HC-005 | IIFA FIDIC Contracts: https://iifa-aifi.org/en/33151.html | في عقد FIDIC، هل غرامة التأخير على المقاول ربا؟ | English acronym plus Arabic colloquial wording. | `sharia_standard`; FIDIC -> istisna/ijarah/muqawala; `candidate_standards=SS-11` when routed to Istisna. | Clarify if party/cause unclear; otherwise answer with governed Sharia citation. | pending |
| HC-006 | IIFA Supply and Bidding Contracts: https://iifa-aifi.org/en/32581.html | هل عقد توريد مواد مؤجلة الدفع والتسليم جائز؟ | Supply can be Istisna, Salam, or debt-for-debt depending on manufacturing and payment timing. | `sharia_standard`; supply route with missing facts; `candidate_standards=SS-11` for manufactured goods, `SS-10` for Salam. | Ask whether goods are manufactured and whether full price is paid at signing. | pending |
| HC-007 | IIFA Supply and Bidding Contracts: https://iifa-aifi.org/en/32581.html | Supplier will manufacture equipment and deliver monthly; payment is deferred. Which standard applies? | Manufactured supply should not be treated like generic sale. | `sharia_standard`; `contract_family=istisna`; `candidate_standards=SS-11`. | Answer only after governed retrieval; otherwise insufficient data. | pending |
| HC-008 | IIFA Currency Trading Resolution 102: https://iifa-aifi.org/en/32566.html | Can we lock today’s FX rate and settle next month? | Looks like hedging/treasury, but deferred currency exchange is a Sharia edge case. | `sharia_standard`; currency/sarf route. | Answer only with governed Sharia evidence; otherwise insufficient data. | pending |
| HC-009 | IIFA Letter of Guarantee: https://iifa-aifi.org/en/32241.html | هل يجوز للبنك أخذ عمولة خطاب ضمان حسب المبلغ والمدة؟ | Guarantee fee vs actual administrative cost distinction. | `sharia_standard`; guarantee/kafalah route; `candidate_standards=SS-05`. | Clarify fee basis if unclear; answer only with governed citation. | pending |
| HC-010 | IIFA Sukuk/Debt Rescheduling Resolution 248: https://iifa-aifi.org/en/49710.html | Can we sell deferred receivables through sukuk at a discount? | Sukuk wording can hide debt-sale/riba issue. | `sharia_standard`; sukuk/debt-sale route. | Answer only with governed Sharia evidence; otherwise insufficient data. | pending |

## Release Gate Notes

- Do not upgrade BM25, BGE, or reranker behavior until this seed set has a baseline report.
- Accepted gold cases must be versioned against corpus/index version, source-catalog version, and rule version.
- A runtime answer can only support a Sharia conclusion from answer-admissible governed chunks with `source_family`, `metadata_status`, `source_id`, `section_path`, and `citation_anchor`.
- Machine-proposed rows stay non-authoritative until a human scholar marks them accepted or accepted with correction.
- `scripts/run_retrieval_baseline.py --require-scholar-reviewed-gold` must fail while any tracked hard-case row remains pending, missing, or rejected.
