---
title: 'Restore evidence-safe answer surfaces after review fixes'
type: bugfix
created: '2026-09-30'
status: done
route: oneshot
route_source: auto
baseline_commit: 0e130f92858cf1f24aa92a323bac2701842301c3
review: quick
review_source: auto
lenses_ran: []
---

<frozen-after-approval reason="user authorized review and continuation">

## Intent

Repair regressions in the existing evidence-status answer contract. A withheld rule outcome and its supporting fact snapshots must remain absent from client-facing evaluation metadata regardless of which earlier gate determines the answer. Restored historical messages without evidence metadata must show the localized unavailable status, without claiming there were no sources or retaining a previous source label.

Acceptance: Given an evaluated synthetic rule and a conflicting fact or inconsistent payment schedule, when REST or SSE serializes the answer, then the outcome and supporting facts are absent and the clarification/abstention remains intact. Given a restored historical assistant message without an evidence block, when rendered in English or Arabic, then the unavailable evidence label appears. Source dates and ordinary evidence labels continue working.

No scholar authority or gold labels will be created or changed. This is a local developer/client POC correction; it does not complete the dual-lane release or authorize deployment.

</frozen-after-approval>

## Implementation Notes

- Small continuation of CAP-5 answer surfaces; estimated production edits below 20 lines and focused regression extensions below 80 lines.
- Baseline browser run: 11 passed, 1 failed. The historical-message fallback fails at `e2e/evidence-status.spec.ts:35`.
- Review located conditional stripping in `src/chatbot/described_operation.py`: stripping depended on the final reason rather than the evaluator result, so an earlier gate could preserve withheld fields.
- Reuse synthetic fixture helpers from `tests/test_review_blockers.py`; these do not supply production approval.

## Spec Change Log

## Review Triage Log

## Verification

- Run regression cases before and after the fix through the actual service and REST/SSE serializers.
- Run the review regression, typed-operation, evidence-display, decision-store, API and streaming suites.
- Run `npx.cmd playwright test e2e/chat-ui.spec.ts e2e/evidence-status.spec.ts --workers=1 --reporter=list`.
- Record fresh full-suite results and remaining failures without changing expected gold rulings.
