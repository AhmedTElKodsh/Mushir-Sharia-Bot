---
title: 'Classified review records with internal signals for every answer'
type: 'feature'
ticket: ''
created: '2026-10-01'
status: 'ready-for-dev'
route: 'full'
route_source: 'auto'
review: ''
review_source: ''
lenses_ran: []
review_loop_iteration: 0
context: ['{project-root}/.planning/sharia-compliance-chatbot/docs/runtime-safety-model.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** During the early POC stages the team must review every answer and improve from it. Today each answer's review record is one JSON blob that can't be filtered by lane, outcome, language or gate. The internal numbers behind each answer (retrieval threshold, per-chunk scores, router weights) are scrubbed *before* the record is built, so they are lost.

**Approach:** Capture an internal-signals block and the decision trace (from plan A) into the existing decision-review record before client scrubbing. Promote classification fields to indexed columns. Add a review CLI to filter, export and report size. Add size management for the local store.

## Boundaries & Constraints

**Always:** Extend the existing `decision_review_store` and mirror; no new store. Keep the "no answer delivered unless its record is committed" rule and the strict-mirror behavior. Internal signals live only in the review record; the client-facing response never carries them. Classification columns are derived from typed state at write time. Schema changes are additive and migrate existing rows (null classification is allowed).

**Never:** Don't send internal signals, the record, or any score to REST/SSE clients. Don't purge unsynced rows. No new external services. Don't store uploaded user documents (out of V1.6 scope).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Grounded answer | retrieval with 4 chunks | record has threshold, 4 chunk ids with their scores, the deciding gate, the trace, and columns lane/status/language/gate | — |
| Described-lane clarification | iPhone story | lane=described_operation, status=CLARIFICATION_NEEDED, gate=clarification | — |
| Router clarification | engine clarification | router weights stored in the record, absent from client JSON | — |
| Legacy rows | pre-migration DB | migration adds columns, old rows readable with nulls | — |
| Review CLI filter | `--lane described_operation --status INSUFFICIENT_DATA --since 7d` | matching rows as table/JSONL/CSV | unknown filter → clear error |
| POC review hold | old records, startup/scheduled/manual maintenance, numeric retention/cap settings present | no age purge or cap eviction in local store, archive, mirror or linked evidence; records remain reconstructible | settings cannot implicitly lift the hold |
| POC size pressure | storage approaching capacity while hold active | alert and verify lossless backups/compression; no automatic history deletion | withhold new answers if durable recording is impossible |
| Later explicit retention activation | scholar review complete and operator enables policy | dry-run eligible counts; record activation; apply configured 365-day age limit and cap only to eligible records | unsynced, held and unreviewed records remain protected |
| Later local size pressure | cap enabled after review hold is lifted | eligible synced rows are archived with checksums and restore verification before local eviction; VACUUM | failed archive or insufficient eligible space means no unsafe deletion |

**Decisions (user, 2026-10-01, clarified):** During the early POC, preserve all in-scope review data until the scholar finishes reviewing, across working SQLite, archive, mirror and supporting evidence. A default review hold disables every age purge, short local window and cap eviction. After review completion, separately enable the later 365-day retention and storage cap by a recorded operator action; neither elapsed time nor a release automatically activates deletion. The preservation and evaluation contract is [defined here](poc-showcase-behavior-evaluation.md). On the HF Space the Supabase mirror is required (strict mode): an answer is not delivered unless its record is mirrored.

</frozen-after-approval>

## Code Map

- `src/models/evidence_display.py:5,31` -- `without_answer_scores` scrubs numeric keys. `ruling.py:155,167` applies it, so internal signals must be captured before this point, on a separate internal attribute that `to_dict()` never emits.
- `src/models/decision_audit.py:14-52` -- `DecisionAuditRecord` (extra fields forbidden) and `prepare_decision_record` (builds from `answer.to_dict()`). Add `internal_signals` and `decision_trace`, plus a `classify()` deriving lane/status/language/deciding_gate/mechanism.
- `src/storage/decision_review_store.py:30-299` -- SQLite table `decision_reviews` (payload JSON). Add classification columns + index and an additive migration. `purge_older_than` 92, mirror 102-183, `configured_decision_store` 271.
- `src/storage/postgres_decision_review_store.py:24` -- add the same columns to the mirror (JSONB payload kept).
- `src/chatbot/application_service.py` -- threshold 84/108/376; router signals 1700/1733 (move to internal); `_metadata` 1137-1169 adds chunk ids at 1153; `answer()` commit 129-166.
- `src/rag/pipeline.py:446-482`, `src/chatbot/retrieval_coordinator.py:140,162` -- per-chunk scores available in chunk metadata.
- `src/chatbot/commercial_assessment.py:567` -- `MIN_RELEVANCE_SCORE`.
- `scripts/backup_decision_reviews.py` -- pattern for the new `scripts/review_answers.py`.
- Tests to extend: `tests/test_decision_review_store.py`, `tests/test_decision_review_mirror.py`, `tests/test_answer_surface_continuation.py` (no-leak).

## Tasks & Acceptance

**Execution:**
- [ ] `src/models/decision_audit.py` -- add `internal_signals`, `decision_trace`, `classify()`; build from an internal side-channel instead of the scrubbed `to_dict()`.
- [ ] Extend record provenance and append-only annotations per the behavior contract: turn/attempt links, input corrections, observable execution events, model/prompt/code/corpus/rule versions, delivery/errors and review status. Preserve source snapshots once with immutable references; no hidden chain-of-thought or credentials.
- [ ] `src/chatbot/application_service.py` -- collect internal signals (threshold, min relevance, chunk id→score, router weights) per answer and pass them to the record; remove `router_signals` from client metadata.
- [ ] `src/storage/decision_review_store.py`, `postgres_decision_review_store.py` -- classification columns + indexes, additive migration, `query(filters)`, `compact(max_bytes, archive_dir)`.
- [ ] `src/storage/decision_review_store.py`, `postgres_decision_review_store.py`, `src/api/main.py`, maintenance scripts -- enforce the default review hold at every deletion entry point, including startup, periodic jobs and direct maintenance. A configured numeric age/cap cannot override the hold.
- [ ] `.env.example`, `docker-compose.yml` and deployment guidance -- declare the default hold and later opt-in 365-day retention/cap consistently; expose effective policy in operator status. Add recorded activation and dry-run eligibility before releasing existing history to retention.
- [ ] `src/api/main.py` -- run later compaction only after explicit hold release and cap activation; verify archives before local eviction. Monitor capacity during hold and preserve the no-record/no-answer rule on storage failure.
- [ ] `scripts/review_answers.py` -- filter by lane/status/language/gate/since, output table/JSONL/CSV, `--stats` (counts per class plus DB size).
- [ ] `tests/test_review_records.py` -- I/O matrix; record has signals while client JSON (REST and SSE) has none; migration on a legacy DB; compaction never drops unsynced rows.
- [ ] Preservation tests -- records older than 365 days survive every maintenance route under the default hold, including configured age/cap values; explicit later activation respects protected rows; backup/restore preserves counts, payload hashes, annotations and source references; failed archive or full storage cannot silently discard history.

**Acceptance Criteria:**
- Default configuration preserves all in-scope POC data until scholar review completion and explicit later policy activation; verify working store, archive, mirror and evidence references, not just remote rows.
- Every B-owned behavior/evaluation requirement in the linked contract has a recorded result. Old records retain honest unknown provenance, and annotations never overwrite the original response or evidence.
- Given any answer, when it is returned, then its committed record holds the trace and internal signals, and the response JSON holds no numeric signal.
- Given the full suite, then 0 failures beyond the 12 strict xfails.

## Implementation Notes

Current code inspected on 2026-10-01 still defaults to 365-day retention and a 7-day mirrored local window; strict mirroring defaults to false. These are implementation gaps against the clarified POC policy, not evidence that the hold is active. This plan change does not alter runtime configuration or deploy code.

## Plan Change Log

- 2026-10-01: User clarified that all small, crucial early POC data stays until the scholar finishes reviewing. Expanded the hold from mirror-only wording to all stores and linked evidence; added explicit later activation, lossless recovery checks, storage-pressure behavior and reproducibility fields.

## Review Triage Log

## Design Notes

Internal signals shape (record only):
```json
{"retrieval_threshold": 0.3, "min_relevance": 0.3,
 "chunks": [{"id": "SS-08:3/1", "final": 0.71, "dense": 0.64, "rerank": 0.58}],
 "router": {"surface:murabaha": 0.4, "conflict_penalty": -0.2},
 "deciding_gate": "approved_rule_gate", "model": "openrouter/..."}
```
Classification is derived once at write time, so the CLI filters with indexed SQL instead of JSON scans.

## Verification

**Commands:**
- `.venv/Scripts/python -m pytest tests -q --timeout=90` -- expected: 0 failed, 12 xfailed
- `.venv/Scripts/python scripts/review_answers.py --stats` -- expected: counts per lane/status and DB size
