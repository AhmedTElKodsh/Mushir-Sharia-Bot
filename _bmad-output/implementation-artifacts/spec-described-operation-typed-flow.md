---
title: 'Described operations: typed facts and conversation flow'
type: feature
created: '2026-09-30'
status: in-progress
route: full
route_source: continuation
---

## User-facing goal

The personal iPhone/payment-plan story must preserve explicit user facts, ask one financier question, and never infer a cash price, total payable, or contract mechanism. Follow-ups must retain provenance and contradictions. Missing material evidence or exhausted clarification must request a document and abstain. This work implements portions of described-operation tickets 1-5 and integrates the runtime-2 evaluator; it does not establish production scholar approval or complete the release.

## Implementation

- `src/chatbot/described_operation_facts.py`: deterministic supported-form extraction into all shared fact slots; English, Arabic/Persian digits, and code-mixed amounts; exact Decimal money with explicit local EGP wording. Unsupported forms remain unknown. All known values retain the exact user turn, session, transaction, turn ID and revision. Generic instalment terms and financier names never establish a mechanism. Reconciliation preserves earlier facts and supported conflicting candidates instead of silently overwriting values.
- `src/chatbot/described_operation.py`: typed conversation state, bounded clarification, named financier replies, explicit new-transaction boundaries, payment arithmetic discrepancy trace, and a decision-review row for every handled turn. A discrepancy is a derived check, not an asserted replacement total. The approved evaluator runs on the reconciled snapshot. Without verified mechanism and approved material evidence, the flow cannot authorize a judgment.
- `src/chatbot/application_service.py`: routes personal descriptions before legacy heuristics/cache/retrieval/generation; persists typed state and review rows through the existing session abstraction and existing audit sink. Definition questions can use their independent path. `APPROVED_RULE_CARDS_PATH` accepts an optional operator-controlled local YAML; no synthetic test card is loaded by default.
- `tests/test_described_operation_facts.py`, `tests/test_described_operation_flow.py`: real answer path, REST multi-turn, serialization round-trip, EN/AR/code-mixed stories, unknown financier, bounded clarification, conflicting totals, arithmetic discrepancies, cross-session/scope protection, negation, alternatives, malformed amounts, explicit new transactions, and independent definition routing.

## Verification and review

- Tests were written before implementation and regressions were reproduced before fixes.
- Independent BMAD review reproduced four defects: old facts inherited into an explicit new transaction; direct named financier replies dropped; currency inherited from an unrelated sentence; transaction denial diverting a definition query. Added regression tests and fixed all four.
- Final focused combined verification: **256 passed** across described-operation facts/flow, approved application gate/evaluator, rule cards, evidence contracts and legacy evaluator safety. This includes **49 described-operation checks** and actual JSONL scholar-review queue writes. Follow-up independent review reproduced negated new-transaction resets, denial of a deposit being treated as denial of a transaction, and Arabic uncertainty being accepted as a name. All three were fixed with four regression cases.
- Initial full suite after typed-flow integration: **899 passed, 36 failed, 47 skipped**, 80.10 seconds. Follow-up fixed missing review queue writes/flags and the evaluation helper's unsafe missing-confidence=1.0 fallback. Updated one legacy test that expected plain personal instalments to imply Murabaha; it now requires unknown mechanism and one financier question, matching the adopted spec. No gold rulings were changed.
- Targeted application and scholar queue regression suite after these changes: **76 passed, 1 pre-existing missing-ontology routing failure, 19 skipped**.
- Latest full suite: **915 passed, 22 failed, 47 skipped**, 92.31 seconds; JUnit `data/runtime/artifacts/poc-described-operation-tests.xml`. This run preceded the final four wording-regression cases and their guard fixes; the 256-test final focused suite includes those. Remaining failures: four ontology tests (one also retains an obsolete unsigned conditional-verdict expectation), one ontology-dependent routing test, ten unsigned mocked ruling expectations, six ambiguity/clarification assertions across three gold cases, and one bilingual divergence. The full release gate is not passing.

## Remaining work

- Explicit resolution now supports monetary schedule fields and instalment count after the specific conflict question. A direct value or a complete field-bound schedule confirmation can select a new user-reported fact; the prior conflict remains in immutable resolution history and earlier review rows. Observed-document conflicts cannot be resolved by a user assertion. Unsupported/non-numeric conflict replies remain unresolved.
- Extractor coverage is intentionally limited to explicit supported forms. Asset extraction currently recognizes iPhone; other assets may remain unknown. Extend against frozen reviewed cases, not guessed mechanisms.
- Mechanism identification still requires verified template/disclosure integration. Configured cards alone cannot authorize an overall ruling. Successful per-rule results still need claim-scoped rendering and all required overall gates.
- Rule-specific question localization, concurrency-safe durable session updates, complete review-log persistence configuration, and full release evaluation remain to be completed. Pending-slot binding now uses the evaluator's explicit `question_slot`, rather than assuming its question targets the first unknown fact.
- Actual scholar-reviewed cards/cases, pilot dossier completion, deployment and live smoke are still outstanding requirements of the overall goal.

## Conflict-resolution continuation

- Added `FactResolution`, a validated record binding the former conflict to the selected new user assertion. Enforces transaction/slot/session ownership, chronological turn provenance and user-only authority. Decision-review rows require the selected fact to be active in that exact review turn.
- Added `resolve_operation_fact`, direct schedule-value parsing, field-bound confirmation parsing, and persistent conversation resolution history. Tests cover history after JSON session round-trip and a subsequent new contradiction.
- Independent review reproduced uncertain confirmations clearing conflicts and a schedule reference about one field endorsing a guessed later field. Replaced whole-message confirmation detection with complete field-bound parsing; the reproductions now remain conflicting.
- Targeted verification after these changes and isolated ontology fixtures: **313 passed**. Separate commercial-routing and bilingual parity verification after recognizing English `usury`/`usurious`: **96 passed**.
- Migrated ontology unit tests to explicit synthetic YAML and catalog fixtures. Tests now verify current-vs-superseded filtering, absent-directory behavior, and abstention for unsigned ontology rules. No production ontology or scholar approval was created. Corrected the routing-test diagnosis: `StandardsRouter` deliberately uses ontology candidates only when no specific commercial route exists; the test now provides broad fixture candidates and verifies that the specific SS-03/SS-08 route wins.
- Final full suite: **946 passed, 16 failed, 47 skipped**, 109.01 seconds; JUnit `data/runtime/artifacts/poc-conflict-resolution-tests.xml`. All ontology unit checks and bilingual-parity checks now pass. Remaining: ten legacy mocked ruling expectations unsupported by an approved runtime outcome path, plus six clarification assertions for GC-002, GC-013 and GC-015. No gold rulings or clarification labels were changed. The complete release acceptance gate remains unsatisfied.
