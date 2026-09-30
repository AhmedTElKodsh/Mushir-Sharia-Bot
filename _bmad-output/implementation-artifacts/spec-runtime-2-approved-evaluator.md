---
title: 'Runtime 2: Approved-only tri-state evaluator'
type: feature
created: '2026-09-30'
status: in-progress
route: full
route_source: auto
---

## Intent

Implement evidence-safe-runtime ticket 2: unknown or conflicting material facts and unapproved rules must never authorize a verdict. Adopt the typed fact and rule-card contracts in the real application answer path. Preserve grounded definitions and independently supported facts. No scholar approval may be fabricated.

## Scope and acceptance

- `src/ontology/ruling_evaluator.py`: retire authority from unsigned legacy ontology rules; provide an approved-card evaluator with known/mismatched/unknown conditions and explicit conflicts, matching all material facts within the selected scope and version.
- `src/models/ruling.py`: remove fixed numeric confidence from ontology results and distinguish unobserved conditions from observed violations.
- `src/chatbot/application_service.py`: enforce approved-rule gating before cached or generated judgment answers; no approved rule yields INSUFFICIENT_DATA naming the needed review. Typed extraction and productive clarification follow the described-operation tickets; do not bypass that work or claim this first patch is complete integration.
- Tests: pending/superseded card, unknown/conflicting facts, wrong scope/version, multiple matching rules, exact typed comparisons, valid approved fixture outcome, missing ontology concept, cached verdict, and real API answer path.

## Progress and evidence

- Four newly written safety tests failed against the previous evaluator, demonstrating unsigned conditional verdicts, missing-condition misclassification, negated substring matches, and absent-concept crashes.
- Repaired the legacy path: unsigned ontology entries now abstain, absent concepts abstain, exact normalized assertions replace substring matching, and missing conditions are unknown. Removed RulingResult numeric confidence and legacy 0.82/0.62 constants.
- Focused verification: **172 passed** across `test_ruling_evaluator_safety.py`, `test_evidence_contracts.py`, and `test_rule_cards.py`.
- Added `src/ontology/approved_card_evaluator.py`: approved-only cards, exact typed conditions, all material facts required, explicit conflicts, exact scope matching, session checks, snapshot revision checks, and observation/source time checks. Outcomes remain rule-scoped; no global verdict is inferred from a single card. Multiple applicable cards abstain until reviewed precedence can select safely.
- Independent review found and regression tests now cover mixed versions of one source, inconsistent manifests under one capture identity, and static clarification questions targeting already-known facts. Optional immutable `unknown_fact_questions` maps reviewed questions to their material slots; multi-slot cards without a suitable mapped question abstain.
- Application safeguard now skips response cache for recognized judgments and blocks their generation without an approved typed evaluation. Clarification and existing source-gap/review diagnostics remain available. An independent review also found mixed definition/judgment cache bypasses; positive judgment detection now takes precedence. The ordinary definition cache path remains available.
- API test exercises the actual service through REST and verifies productive clarification without generation. Fixtures are synthetic engineering evidence, not scholar approval.
- Final focused verification: **206 passed** across approved application gate, approved card evaluator, rule cards, evidence contracts, and legacy evaluator safety.
- Full suite after preserving existing diagnostics: **856 passed, 28 failed, 47 skipped**, 81.87 seconds. This run preceded the final mixed-intent precedence fix and seven final regression tests; final focused suite above covers those edits. JUnit: `data/runtime/artifacts/poc-evaluator-tests.xml`.
- Remaining full-suite failures: four missing-ontology tests, one source-routing expectation tied to missing ontology, and 23 legacy evaluation assertions (ruling correctness, productive clarification, bilingual/confidence parity). Compared with the six-failure foundation baseline, 22 additional failures are exposed by blocking legacy fixture-generated judgments. They remain visible; no tests were skipped or gold labels altered to manufacture a pass. The legacy fixture installs a neutral rule evaluator and mocks judgment text without approved cards. Some failures also expose genuine missing typed clarification/parity behavior and must be resolved during integration.
- Still unfinished: loading trusted deployed cards; extracting/reconciling scoped user facts; invoking the approved evaluator from the real answer path; rendering supported rule-scoped outcomes and collecting all required gates for any overall conclusion. The current safeguard deliberately cannot authorize judgments. This story and the overall POC remain active.

### Subsequent typed-flow integration

The continuation in `spec-described-operation-typed-flow.md` adds operator-controlled local card loading and typed extraction/reconciliation for personal descriptions. That real answer path now invokes the approved evaluator and writes decision-review rows. Incomplete cases and blocked judgment gates enqueue actual scholar-review records when the queue store is configured. Verified mechanism/dossier integration, supported outcome rendering, overall gates and release acceptance remain unfinished; the earlier standalone-evaluator progress is not a claim of completed POC behavior.

## Known baseline

Foundation verification had 847 passed, 6 failed, 47 skipped. Missing ontology seeds account for four failures; tests tied to those external seeds will be migrated to explicit fixtures for evaluator behavior without inventing runtime approval. The old conditional-verdict expectation conflicts with this adopted approved-only requirement.
