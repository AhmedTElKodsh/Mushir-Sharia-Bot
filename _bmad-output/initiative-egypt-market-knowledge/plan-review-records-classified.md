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
| Size pressure | local DB over the size cap | synced rows past the local window are archived (gzip JSONL by month) then deleted; VACUUM | unsynced rows never touched |

**Decisions (user, 2026-10-01):** During the POC (small data), review records are kept indefinitely until the scholar phase ends: no automatic purge of the mirror. Implement 365-day mirror retention and the local size cap as configuration that is off by default and switched on later. On the HF Space the Supabase mirror is required (strict mode): an answer is not delivered unless its record is mirrored.

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
- [ ] `src/chatbot/application_service.py` -- collect internal signals (threshold, min relevance, chunk id→score, router weights) per answer and pass them to the record; remove `router_signals` from client metadata.
- [ ] `src/storage/decision_review_store.py`, `postgres_decision_review_store.py` -- classification columns + indexes, additive migration, `query(filters)`, `compact(max_bytes, archive_dir)`.
- [ ] `src/api/main.py` -- run compaction inside the existing 24-hour purge task when `DECISION_REVIEW_LOCAL_MAX_MB` is set; document the variable and `DECISION_REVIEW_RETENTION_DAYS` in `.env.example`.
- [ ] `scripts/review_answers.py` -- filter by lane/status/language/gate/since, output table/JSONL/CSV, `--stats` (counts per class plus DB size).
- [ ] `tests/test_review_records.py` -- I/O matrix; record has signals while client JSON (REST and SSE) has none; migration on a legacy DB; compaction never drops unsynced rows.

**Acceptance Criteria:**
- Given any answer, when it is returned, then its committed record holds the trace and internal signals, and the response JSON holds no numeric signal.
- Given the full suite, then 0 failures beyond the 12 strict xfails.

## Implementation Notes

## Plan Change Log

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
