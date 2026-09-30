# Bounded structural clarification

Status: implemented; broader POC integration remains in-progress

Scope: repair productive clarification for ambiguous Tawarruq arrangements and fixed-distribution Sukuk requests under the existing approved-only answer gates. This does not authorize religious conclusions or complete the POC.

## Behavior

- Ask one neutral structural question: who arranges onward sale, or which underlying contract generates distributions. Pure definitions remain independent.
- Keep the exact original question and follow-up reply in session review metadata. Never treat the reply as verified contract evidence or scholar approval.
- Stop after at most two questions. A supplied or unknown answer leads to an explicit request for transaction documents and approved rule evidence, rather than an unsigned verdict.
- Audit terminal replies and enqueue scholar review when those stores are configured. Do not emit numeric confidence in this path.
- Separate pending questions across topics and sessions, including personal transactions. Preserve earlier transaction evidence when suspending its pending reply.

## Evidence

- Initial 13 tests: 12 failed and 1 passed before implementation; all passed after implementation and bilingual judgment recognition.
- Independent review reproduced cross-topic question reuse, definition commands mistaken for replies, and stale structural state after entering a personal transaction. Added six regression tests and fixed these cases.
- Follow-up independent review found explicit financing-party wording could still update a suspended personal transaction. The active structure question now suspends inferred personal updates; only a fresh personal description can switch into a new transaction. A regression test confirms the earlier operation remains exactly unchanged.
- First full run: 964 passed, 11 failed, 47 skipped. Six existing ambiguity/clarification assertions now pass. Ten unsigned mocked ruling expectations remain failures; an eleventh cache test expected an unsigned compliance verdict. Changed that cache test to verify a sourced definition and added explicit bilingual judgment-cache bypass regression cases. No gold ruling or clarification labels changed.
- Latest full run: **975 passed, 10 failed, 47 skipped**, 111.03 seconds, `data/runtime/artifacts/poc-structure-final-tests.xml`. This run preceded the final suspended-transaction precedence fix and its regression test. Final focused verification after that fix: **74 passed** across structural clarification, personal-operation flow, approved application gate and L4 API/cache behavior. `git diff --check` passed.
- The ten remaining failures are GC-003, GC-005, GC-007, GC-008, GC-009, GC-010, GC-012, GC-016, GC-017 and GC-019 ruling-correctness assertions. These are unresolved acceptance failures; conservative abstention is not reported as correct ruling accuracy.
- Independent reviewer reverified the final Bank B reproduction: structural reply retained, suspended operation exactly unchanged, all **22 structural tests passed**.

## Remaining scope

General structural replies currently use session metadata and the existing answer audit, not the full typed fact/review contract used by the personal-operation lane. The approved outcome path, named-offer integration, real scholar-approved cards, frozen reviewed evaluation set and deployment validation remain incomplete.
