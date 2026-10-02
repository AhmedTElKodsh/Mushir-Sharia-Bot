# Deferred Work (initiative ledger)

## Open Now (summary, 2026-10-01)

This ledger is canonical; entries below are append-only history. Still open:

| # | Item | Waits for |
| --- | --- | --- |
| 1 | 15 stale test expectations (GC-003, 004, 005, 007, 008, 009, 010, 011, 012, 016, 017, 018, 019; TC-F1, TC-G1) | A scholar decision per case ([review pack](../../outputs/client-review-pack/index.html)) |
| 2 | Semantic mechanism evidence and claim-scoped verdict eligibility (claim-support gate, ticket T6) | Pilot dossiers and runtime adoption |
| 3 | Private document locators for schedule intake | V1.7 |
| 4 | DNS names resolving to private addresses pass the public-URL check | Fetch-time check in acquisition code |
| 5 | Negation masks a contract name only within three preceding words | Clause-aware parsing |
| 6 | SQLite writes and LLM calls are synchronous inside async routes | Performance work |
| 7 | `AAOIFICitation.confidence_score` kept internally | Scholar-review code cleanup |
| 8 | Permissibility questions (e.g. GC-004/011/018, Arabic "هل يحق…") route to FAS accounting informational routes with `requires_rule_evaluation: false` | Router change: question type PERMISSIBILITY must select a rule-evaluation route |
| 10 | FRA-first table, opened 2026-10-02: 41 of 52 entity rows have only `lead` brand links and 1 provider is unlinked (Fine Stone); the seller-financier pass (2026-10-02) left Raya Trade vs Raya Electronics and Contact-backed dealer plans as open creditor questions. Sympl stays `not_found_by_name`. Press reports 48 licensed consumer-finance companies at end-2025, but the FRA register shows 39; the difference is unexplained (revocations? FRA Decision 43/2026 suspended new applications) | First-party captures naming each legal entity; an FRA licence-decisions source |
| 11 | Open findings from the 2026-10-02 double review, not fixed by the FRA-first work: the role summarizer still keeps a negated financier ("We do not offer financing through valU") as established (`scripts/summarize_egypt_installment_market.py:77`); the FRA collector checks only origin, not path policy, on redirects; CrawlerEngine is a weaker parallel route | Separate correction slice |

Closed since the earlier entries: Playwright UI specs ran 30/30 on 2026-10-01 (Chromium installed); the broken `.venv` noted in the former implementation-artifacts ledger was rebuilt.

## History

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

- source_plan: none
  summary: Closed in the code-fix round (2026-10-01): negation scope, fetch-time URL safety, REST threadpool.
  evidence: mechanism_terms now scopes negation by clause (permission words flip it); src/acquisition/url_safety.py refuses hosts resolving to non-public addresses and re-validates every redirect hop, used by the crawler and scraper; REST /query runs the service in the threadpool. Left on purpose - AAOIFICitation.confidence_score (four test files construct it to prove legacy input never leaks). Provenance URL validation in models still cannot resolve DNS by design; fetch-time is the enforcement point. Still open - the 12 stale test expectations (need scholar/product owner).

- source_plan: `_bmad-output/implementation-artifacts/deferred-work.md` (moved here 2026-10-01)
  summary: Enforce semantic mechanism evidence and claim-scoped verdict eligibility during runtime adoption.
  evidence: Structural source classes cannot distinguish marketing self-labels from mechanism clauses; blocked conclusion gates may coexist with independently supported facts under the adopted dual-query contract. Runtime must enforce that separation explicitly.

- source_plan: `_bmad-output/implementation-artifacts/deferred-work.md` (moved here 2026-10-01)
  summary: Add private document locators when V1.7 schedule intake is implemented.
  evidence: CaptureManifest requires public HTTP(S) provenance; local uploads need a distinct immutable locator and the planned consent/redaction controls. Private agreement intake is excluded from V1.6.

- source_plan: none
  summary: Durable early-stage review records for every answer (answer, full decision trace, internal threshold numbers, gate results, retrieved sources), classified by lane, outcome, language and gate, with storage-size management (compaction/rotation).
  evidence: Split from the POC showcase slice on 2026-10-01 (user chose sequential plan->build->test per goal); depends on the decision trace built first, and extends the existing audit_store.py / decision_review_store.py rather than adding a new store.

- source_plan: none
  summary: Mary proposes five pilot financiers for next week's scholar meeting, from the FRA consumer-finance register and the 2026-09-24/27 crawl coverage.
  evidence: Split from the POC showcase slice on 2026-10-01; an analysis deliverable (resolves open question O3) rather than code, done after the reasoning panel and review records.

- source_plan: `plan-showcase-decision-trace-panel.md` (Goal A continuation)
  summary: Generated verdicts reached three critical gold cases through misrouted informational routes (2026-10-01).
  evidence: At commit 07207d7, GC-004/011/018 passed only because the router sent permissibility questions to `mudaraba-accounting`, `wakala-investment-accounting` and `musharaka-accounting` (FAS, `requires_rule_evaluation: false`), so the mock LLM's NON_COMPLIANT/COMPLIANT text became the ruling. The extractive-only policy withheld them. A final guard (`ApplicationService._enforce_verdict_authority`) now downgrades any verdict lacking an evaluated approved rule on every delivery path, including cache; covered by `tests/test_verdict_authority.py`. The three cases joined the strict-xfail scholar-pending list with their own reason; gold labels unchanged. Router fix remains open (item 8).
