
- source_plan: none
  summary: Fix the remaining bmad-review findings (robustness, validation, Arabic word boundaries, session-state hardening, CLI, UI, API contract, retention and missing verification-gap tests).
  evidence: Split from the "fix all" run on 2026-09-30; priorities 1-4 (atomic answer(), evaluator slot mismatch, over-triggering gates, fabricated confidence) go first. Full list in _bmad-output/implementation-artifacts/review-findings-2026-09-30.json.

- source_plan: none
  summary: Review findings still open after the second fix pass (2026-09-30).
  evidence: Not done - per-amount currency binding in extract_operation_facts (any foreign currency still disables all EGP extraction); future-dated signoff and reviewer-registry validation; retention purge is available (purge_older_than) but nothing schedules it; audit payload is still stored three ways (typed_review, response metadata, session rows) and decision_review still returns to API clients; SQLite writes are synchronous (no threadpool); ingest.main() has no positive-path test; e2e/evidence-status.spec.ts was not run (no browser run in this session); dead AAOIFICitation.confidence_score field kept because scholar_review and tests still use it; eval fixtures keep synthetic confidence values by design; the 10 gold-set ruling and 2 routing-accuracy failures pre-date this work.

- source_plan: none
  summary: Closed in the third fix pass (2026-09-30) - no action needed, listed so the earlier entry is read correctly.
  evidence: Per-amount currency binding, future-dated signoff/verification, startup retention purge, client-facing decision_review removal and the ingest.main() positive-path test are done (tests/test_review_hardening.py). Still open from the earlier entry - session and audit payload duplication inside the stores, synchronous SQLite writes, unrun e2e specs, dead AAOIFICitation.confidence_score, and the 12 pre-existing failures.

- source_plan: none
  summary: Findings from the independent review of the fix commits (2026-09-30) that were judged and not fixed.
  evidence: Concurrent requests on one session_id can race snapshot/restore (needs a per-session lock design); financier names are truncated at "and"/"with" (deliberate trade-off, needs confirmation UX); bare-number replies to money questions are still rejected (explicit-currency rule); retention purge runs at startup only; foreign-currency window is +/-12 characters rather than token-adjacent; DNS names that resolve to private ranges pass the public-URL check (no resolution is done); reviewer denylist is exact-match, not a registry.

- source_plan: none
  summary: State after the fourth fix pass (2026-09-30): what is still genuinely open.
  evidence: Fixed since the previous entry - per-session commit locks, periodic retention purge, optional REVIEWER_REGISTRY_PATH, clause-aware financier names, bare-number replies under a single known currency, amount-adjacent currency binding, single-copy audit snapshot. Still open - (1) 12 stale test expectations (10 tests/evaluation/test_critical_goldset.py ruling cases expect verdicts the judgment gate now withholds; tests/eval/test_routing_accuracy.py TC-F1/TC-G1 expect a contract family that generic wording no longer infers) need scholar or product owners to restate expectations, not a code change; (2) 12 Playwright UI specs (chat-ui, evidence-status) have not run because Chromium is not installed - run `npx playwright install chromium` then `npx playwright test`; (3) DNS names resolving to private ranges pass the public-URL check - enforce at fetch time in the acquisition code, not in the model validator; (4) SQLite writes and LLM calls are synchronous inside async routes; (5) AAOIFICitation.confidence_score is dead but kept for scholar_review and scrub tests.

- source_plan: none
  summary: Known trade-off after the final review pass (2026-10-01): negation masking window.
  evidence: mechanism_terms._topic_matches treats a negation as applying to a contract name only within the three preceding words, so "this is not an actual real murabaha" still affirms murabaha, while "what is not permitted in a murabaha" correctly keeps it. Widening the window re-breaks the second case; a parse-based approach (negation scope by clause head) is the real fix.
