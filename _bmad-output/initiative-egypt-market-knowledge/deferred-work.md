
- source_plan: none
  summary: Fix the remaining bmad-review findings (robustness, validation, Arabic word boundaries, session-state hardening, CLI, UI, API contract, retention and missing verification-gap tests).
  evidence: Split from the "fix all" run on 2026-09-30; priorities 1-4 (atomic answer(), evaluator slot mismatch, over-triggering gates, fabricated confidence) go first. Full list in _bmad-output/implementation-artifacts/review-findings-2026-09-30.json.

- source_plan: none
  summary: Review findings still open after the second fix pass (2026-09-30).
  evidence: Not done - per-amount currency binding in extract_operation_facts (any foreign currency still disables all EGP extraction); future-dated signoff and reviewer-registry validation; retention purge is available (purge_older_than) but nothing schedules it; audit payload is still stored three ways (typed_review, response metadata, session rows) and decision_review still returns to API clients; SQLite writes are synchronous (no threadpool); ingest.main() has no positive-path test; e2e/evidence-status.spec.ts was not run (no browser run in this session); dead AAOIFICitation.confidence_score field kept because scholar_review and tests still use it; eval fixtures keep synthetic confidence values by design; the 10 gold-set ruling and 2 routing-accuracy failures pre-date this work.
