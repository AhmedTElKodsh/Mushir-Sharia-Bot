---
title: 'Showcase decision-trace panel above every answer'
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

**Problem:** The client showcase must prove the POC reasons step by step, asks the right question, refuses to guess and cites sources, but the UI shows none of the reasoning: `reasoning_summary` is ignored by the UI, and on two branches it is cut from LLM text anyway. Separately, internal numeric router weights leak to clients today.

**Approach:** Assemble a structured `decision_trace` from typed state on every answer branch and render it as a collapsed, smaller italic panel above each assistant answer, in EN and AR (RTL). A "what would decide this" section lists the conditions that matter, with ✓/?/✗ and never an outcome. Internal thresholds and scores never reach any client surface.

## Boundaries & Constraints

**Always:** The trace is built only from typed state: intent/lane, language, scenario, contract family or "mechanism unknown", fact observations with status, the clarification asked, retrieved citation ids, the gate that decided, and a fixed reason code mapped to bilingual text. It goes into `metadata["decision_trace"]` on both REST and SSE `done`. Restored messages without a trace render with no panel. Build the DOM with `createElement` and `textContent` only.

**Never:** No raw or paraphrased LLM chain-of-thought or LLM-generated text in the trace. No outcome, ruling or permissibility word in the "what would decide this" section. No number from thresholds, scores, weights or confidence in the trace or anywhere else in client metadata. Don't change the approved-card evaluator's approved-only rule or the single-question contract.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| iPhone story (described lane) | "deposit + 12 × EGP 3,000", no financier | trace: understood=described operation; known=deposit, instalments; missing=financing party; gate=clarification; decide-list shows financing party `?` | one question only, no verdict |
| Definition (EN/AR) | "What is murabaha?" | trace: understood=definition; sources=cited standards; gate=answered from sources | no LLM text in trace |
| Judgment, no approved card | "Is this murabaha halal?" | gate=approved-rule gate blocked; why=no scholar-approved rule | INSUFFICIENT_DATA as today |
| Retrieval down / no chunks | backend unavailable | trace present with gate=retrieval unavailable / no sources | no exception |
| Arabic query | AR text | panel labels AR, `dir=rtl` | — |
| Old restored message | history without trace | no panel, no console error | skip silently |
| Router signals | engine clarification branch | client metadata has no numeric weights | kept internal |

**Decisions (user, 2026-10-01):** The "what would decide this" list comes from the described-operation lane's material fact slots, with state ✓/?/✗. No rule cards are drafted in this goal; cards replace the slot list once scholar-approved cards exist. The full plan is kept despite exceeding 1600 tokens.

</frozen-after-approval>

## Code Map

- `src/chatbot/application_service.py` -- `answer()` returns at 202-673 (13 branches; table in investigation). `_metadata()` 1137-1169. Router signals at 1700/1733 leak floats. The `reasoning_summary` from LLM text at 630/1620 must not feed the trace.
- `src/chatbot/described_operation.py:87-227` -- `FactSnapshot`, `AnswerDecision` gates (182-188), question priority (144-178). Outcome stripping at 225-226 must stay.
- `src/models/evidence.py` -- `FactObservation` statuses `observed|user_reported|conflicting|unknown` (232-270), `FACT_SLOTS` 94-100, `GateDecision` 408-413.
- `src/models/evidence_display.py:5,31-48` -- score-key scrub regex. Extend it to router-signal keys or drop `router_signals` from client metadata.
- `src/models/ruling.py:138-177` -- `AnswerContract` metadata scrub at 155/167. The trace attaches here.
- `src/api/routes.py:170-174,281-299` -- `_query_response` is the single client scrub point; SSE `done`.
- `src/static/js/renderer.js` -- copy the `renderBadge` 306-364 pattern (`insertBefore` the bubble, as a sibling). `restoreMessages` 484-499. The typewriter and `renderCitations` wipe bubble children, so the panel must sit outside the bubble.
- `src/static/js/app.js` -- `I18N` en 42-93 / ar 94-145; `onDone` 334-366 saves the message shape at 356-363.
- `src/static/css/chat.css` (+ `dark.css`) -- tokens in base.css 2-57; RTL rules 67-87, 371-385.
- `tests/test_evidence_display.py:102-108` -- guard regex over app.js/renderer.js; it must still pass (avoid the words "confidence", "score").
- `e2e/evidence-status.spec.ts` -- SSE mock pattern to copy.

## Tasks & Acceptance

**Execution:**
- [ ] `src/models/decision_trace.py` -- new `DecisionTrace` builder: sections + reason codes, from typed inputs only; `to_client()` returns strings/ids/statuses, no numbers.
- [ ] `src/chatbot/application_service.py` -- build a trace on every return branch, attach `metadata["decision_trace"]`; drop numeric `router_signals` from client metadata (keep them in the internal review record).
- [ ] `src/chatbot/described_operation.py` -- expose slots, the asked question and the decide-list (material facts with status), with no outcome.
- [ ] `src/models/evidence_display.py` -- extend the scrub so no numeric weight/threshold key reaches clients.
- [ ] `src/static/js/renderer.js`, `app.js`, `src/static/css/chat.css`, `dark.css` -- `renderTrace(trace, targetNode)`: a `<details>` sibling before the bubble, collapsed, italic, smaller font, dir from language; i18n keys EN+AR; saved and restored with the message.
- [ ] `tests/test_decision_trace.py` -- I/O matrix cases (rows 1-4, 7); no LLM text; no digits from scores; no outcome words in the decide-list.
- [ ] `e2e/decision-trace.spec.ts` -- EN+AR panel collapsed by default, expands, survives reload, old message has no panel.

**Acceptance Criteria:**
- Given any answer branch, when the response is serialized for REST or SSE, then `metadata.decision_trace` exists and contains no float or percentage derived from scores or thresholds.
- Given the full product suite, when run, then 0 failures beyond the 12 strict xfails, and `test_evidence_display` guards still pass.

## Implementation Notes

## Plan Change Log

## Review Triage Log

## Design Notes

Trace client shape (golden):
```json
{"understood_as": {"lane": "described_operation", "language": "en", "mechanism": "unknown"},
 "known": [{"slot": "instalment_count", "status": "user_reported", "value": "12"}],
 "missing": [{"slot": "financing_party", "status": "unknown"}],
 "question_asked": "Who provides the instalment plan?",
 "sources": [{"standard": "SS-08", "section": "3/1"}],
 "decided_by": {"gate": "clarification", "reason_code": "missing_material_fact"},
 "would_decide": [{"condition": "financing_party", "state": "unknown"}]}
```
Values are user-reported text, never computed scores. `reason_code` maps to bilingual strings in the UI.

## Verification

**Commands:**
- `.venv/Scripts/python -m pytest tests -q --timeout=90` -- expected: 0 failed, 12 xfailed
- `npx playwright test e2e/decision-trace.spec.ts e2e/evidence-status.spec.ts` -- expected: all pass
