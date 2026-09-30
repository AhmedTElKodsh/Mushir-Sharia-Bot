# Generic mechanism gate

Status: implemented and locally verified; dataset adjudication and broader integration pending

Implements evidence-safe-runtime ticket 3 and tightens ticket 2's mechanism prerequisite. Generic financing wording must not become an Islamic contract classification. Explicit contract names remain retrieval topics, not verified transaction mechanisms.

## Changes

- Removed instalment, BNPL, deferred-sale and generic property-financing aliases from the contract classifier, plus its uncalibrated numeric confidence. Matched terms remain as routing diagnostics.
- Classification no longer uses generated query expansions as assertions about the user's contract.
- Removed scenario extractor's generic instalment/BNPL fallback to Murabaha.
- Neutralized generic instalment query expansions and removed the prompt instruction equating تقسيط with Murabaha and تمويل with Islamic financing.
- Shared generic-plan detection now prevents incidental markup, insurance, manufacturing, negated interest and prior session families from resolving a generic plan. Deferred-payment and pay-in-four descriptions are included.
- ApprovedCardEvaluator now requires observed mechanism provenance from terms, a transaction disclosure or an agreement. A user-reported archetype cannot select an approved outcome. This remains a necessary provenance check under the trusted reconciled-snapshot boundary, not semantic proof that a document supports an annotation.

## Verification

- Initial generic-wording matrix: 26 failures, 24 passes before implementation.
- Additional tests reproduced weak-markup/session-family promotion and acceptance of a user-reported archetype. Fixed all four failures.
- Independent review reproduced residual Qard/Wakala/Istisna assignments and uncovered deferred-payment vocabulary. Added six review reproductions to the matrix and fixed the shared guard.
- Follow-up review reproduced negated named contracts and the Arabic substring سلم inside مسلم. Added token boundaries and conservative negation handling; negated labels are removed only from generic-plan routing text, while the original user evidence remains intact. An affirmative topic after a contrast can still route correctly. Reviewer independently verified all **96 generic-mechanism tests**, including the real application path in EN/AR and a configured-card personal-label case.
- Latest focused checks: **166 passed** across generic terms, classifier, commercial assessment and approved evaluator. An earlier broader routing/cache/application run passed **213 checks**, before the final shared guard.
- Updated legacy unit assertions that demanded numeric classifier confidence or treated BNPL as Murabaha. No scholar gold labels changed. Approved evaluator fixtures now explicitly carry synthetic documentary annotations instead of user mechanism labels; these are test mechanics, not actual scholar approvals.
- First full suite: **1071 passed, 13 failed, 47 skipped**, 113.16 seconds. Ten existing ruling-correctness failures remain. One obsolete query-expansion unit assertion expected generic instalments to add Murabaha; it now requires neutral plan expansion and preserves penalty terms. The other two failures are pending-review gold label conflicts, described below. This run preceded the final negation/boundary changes.
- Final full suite: **1090 passed, 12 failed, 47 skipped**, 110.03 seconds; `data/runtime/artifacts/poc-mechanism-final-tests.xml`. Remaining failures are exactly the ten existing ruling-correctness assertions plus TC-F1/TC-G1. All final code and tests are included in this run. `git diff --check` passed.

## Dataset adjudication issues

`tests/data/gold_eval_set.json` contains PENDING cases TC-F1 (generic deferred sale labeled Murabaha) and TC-G1 (property financing labeled Ijarah). The questions do not establish those mechanisms. Their original labels and tests remain unchanged and visibly fail under the adopted generic-mechanism guard. `mechanism-label-review.json` records the original queries, labels, requested adjudication and source-dataset SHA-256. Its review decision remains pending; it is not a relabeling or scholar approval.

## Remaining scope

Verified dossier-to-transaction binding, semantic claim support, scholar-approved annotations/cards and positive overall outcome rendering are still unfinished. The mechanism guard does not fill unknown facts or certify a named product. The broader POC remains active.
