---
title: 'Showcase decision-trace panel above every answer'
type: 'feature'
ticket: ''
created: '2026-10-01'
status: 'in-review'
baseline_commit: '9497f47e6a44ac8ba076860ef846ea0e3a50a8bf'
route: 'full'
route_source: 'auto'
review: 'thorough'
review_source: 'auto'
lenses_ran: ['blind-hunter', 'edge-case-hunter', 'verification-gap']
review_loop_iteration: 0
context: ['{project-root}/.planning/sharia-compliance-chatbot/docs/runtime-safety-model.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The client showcase must prove the POC reasons step by step, asks the right question, refuses to guess and cites sources, but the UI shows none of the reasoning: `reasoning_summary` is ignored by the UI, and on two branches it is cut from LLM text anyway. Separately, internal numeric router weights leak to clients today.

**Approach:** Assemble a structured `decision_trace` from typed state on every answer branch and render it as a collapsed, smaller italic panel above each assistant answer, in EN and AR (RTL). A "what would decide this" section lists the conditions that matter, with ✓/?/✗ and never an outcome. Internal thresholds and scores never reach any client surface.

**Scope extension (user, 2026-10-01):** Add important showcase behaviors and test them. The required cases and observable expectations are specified in [the POC behavior contract](poc-showcase-behavior-evaluation.md), POC-01 through POC-16. The panel must reflect real behavior; a display-only implementation cannot mark unimplemented conversation or evidence requirements complete.

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

## Reviewed implementation contract (2026-10-01)

The user requested independent review followed by implementation. [Review findings](review-goals-2026-10-01.md) resolve ambiguities as follows without weakening the evidence or scholar gates:

- `observed` = ✓ plus "Observed in source"; `user_reported` = ✓ plus "You reported"; `unknown` = ? plus "Unknown"; `conflicting` = ✗ plus "Conflicting information". The legend must state that symbols describe information availability, not rule satisfaction. An explicit false fact is still supplied, not a failed Sharia condition. Localize all fixed labels in Arabic and English.
- Trace sources come only from final validated citations, never all retrieved chunk IDs. Carry document ID, standard, section and available capture/passage metadata; missing version/date stays unknown. A citation reference is not proof of semantic entailment: do not claim a claim-support gate passed when it was not evaluated.
- Use deterministic per-branch reason codes assigned at the decision site, not inference from answer prose or `reasoning_summary`. For LLM-generated clarification, show a fixed localized "Clarification requested; see the question below" code rather than copying the generated question into the trace. Deterministic questions may be included. No LLM text becomes a decision explanation.
- Attach the trace before audit commit; preserve it through cache restore, REST, SSE done and browser history. Cached old answers without a trace must be rebuilt honestly or receive an explicit legacy/unavailable explanation, never fabricated execution history. Distinguish definitions from judgment refusal even where both use `INSUFFICIENT_DATA`.
- Gate names are an allowlisted public vocabulary; unknown paths say unavailable, not passed. Do not expose internal outcomes through raw scenario/rule objects copied into the trace.
- Public serialization must remove whole internal signal containers and numeric/string-encoded threshold/weight values, while retaining legitimate user amounts/counts and source ages. Trace fact values are bounded display strings from typed facts, not arbitrary object dumps.

### Preservation prerequisites included in A

Before further app-starting tests, safeguard existing local review stores using SQLite's backup API where they exist, verify the backup opens and row counts match, and keep backups in ignored `data/runtime/` paths. Do not print payloads or credentials. Tests must isolate runtime stores from existing user data.

- `src/storage/decision_review_store.py`, `src/storage/postgres_decision_review_store.py`, `src/api/main.py`: enforce the default early-POC hold at current deletion/purge entry points, including direct maintenance and strict-mirror error cleanup. Preserve failed mirror attempts locally without delivering the answer. No later-policy activation is implemented by A; B owns recorded activation and cap management.
- `configured_decision_store()` must reject missing/invalid mirror configuration when strict mirroring is required; HF detection/configuration must not silently downgrade to local-only durability. Document the effective hold and strict-mode requirement in `.env.example` and runtime safety docs. Local isolated developer tests can use SQLite.
- `AnswerContract` gets a private internal-signals field excluded from `to_dict()`. Capture existing router weights there before public scrubbing; extend `DecisionAuditRecord` additively to retain them. B later extends this to complete retrieval signal classification and lifecycle provenance.
- Add focused tests proving old records survive all current purge routes, strict mirror failure retains pending records while withholding delivery, required-but-missing mirror fails closed, and router signals survive internally while REST/SSE remain clean. Existing tests of superseded deletion behavior must be explicitly updated for this changed requirement; scholar-pending gold expectations remain untouched.

### Behavior ownership and completion

A implements/tests observable conversation, evidence and UI behavior in the 16-case contract plus these preservation prerequisites. B owns richer record classification, versioned evaluation lifecycle, annotations, retry lineage, cap/retention activation and source-object lifecycle. Named-offer acquisition/dossiers remain D; A must abstain honestly where that lane is not supported. Enumerate every subcase in a result ledger with test node IDs and whether evidence is unit/service, UI, or live. No unchecked or failed A requirement may be represented as passing. No live/deployed claim without an actual live run.

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
- [ ] Implement and verify the A-owned behavior cases in [the POC behavior contract](poc-showcase-behavior-evaluation.md); record each case's status and evidence, with B-dependent recording checks tracked explicitly.
- [x] `src/models/decision_trace.py` -- structured public trace builder from typed inputs, fixed codes and validated citations; source offsets use strings and missing version is explicit.
- [x] `src/chatbot/application_service.py` -- build a trace on every return branch, attach `metadata["decision_trace"]`; drop numeric `router_signals` from client metadata (keep them in the internal review record).
- [ ] `src/chatbot/described_operation.py` -- expose slots, the asked question and the decide-list (material facts with status), with no outcome.
- [x] `src/models/evidence_display.py` -- extend the scrub so no numeric weight/threshold key reaches clients.
- [x] `src/static/js/renderer.js`, `app.js`, `src/static/css/chat.css` -- `renderTrace(trace, targetNode)`: a `<details>` sibling before the bubble, collapsed, italic, smaller font, dir from language; i18n keys EN+AR; saved and restored with the message. Existing theme tokens supply dark-mode styling.
- [x] `tests/test_decision_trace.py` -- I/O matrix cases (rows 1-4, 7); no LLM text; no digits from scores; no outcome words in the decide-list.
- [x] `e2e/decision-trace.spec.ts` -- EN+AR panel collapsed by default, expands, survives reload, old message has no panel.

**Acceptance Criteria:**
- Each A-owned POC behavior requirement has a reproducible test and recorded result; mocks, live model/retrieval tests, and UI tests are distinguished. Missing implementation or a failed required behavior stays visible as an acceptance gap.
- Given any answer branch, when the response is serialized for REST or SSE, then `metadata.decision_trace` exists and contains no float or percentage derived from scores or thresholds.
- Given the full product suite, when run, then 0 failures beyond the 12 strict xfails, and `test_evidence_display` guards still pass.

## Implementation Notes

### Authorized continuation after milestone 07207d7

The user said proceed with the remaining Goal A work. Preserve the working implementation and frozen intent; continue the incomplete cases in the case ledger. This is a resumed build, so keep the original baseline_commit. Implement A-owned observable requirements and local reproducible coverage. B-owned expanded lineage/retention activation and D-owned live offer acquisition remain explicit dependencies. Live/model/deployed validation is additional and may remain unavailable; do not invent results.

1. `src/chatbot/application_service.py`, `src/chatbot/citation_validator.py` and focused tests: extract an explicit supported definition from mixed definition/judgment requests and present it alongside a withheld assessment or the existing single clarification, without granting judgment authority or using a cached judgment. Validate literal cited passages and refuse absent/wrong sections, irrelevant definition passages and source-embedded instructions. Preserve citation passage identity; unknown versions remain explicit. A matching citation alone is never a semantic claim-support pass. Use extractive, source-limited explanation when arbitrary generated claims cannot be verified. No invented translation is necessary: label an original-language quotation honestly inside an Arabic/English explanation.
2. `src/chatbot/application_service.py`, `src/models/decision_trace.py`, evidence display and tests: handle stale dated evidence and conflicting source versions conservatively for claims that depend on unresolved freshness/identity; retain age/provenance, never merge incompatible offer claims or invent inspection of inaccessible agreements. POC-10 tests must distinguish stable standard definitions from current offer assertions. D may remain unavailable; withhold named-offer claims safely.
3. `src/chatbot/described_operation.py`, `src/chatbot/described_operation_facts.py`, clarification routing and service tests: finish EN/AR conversation subcases in POC-01..06, including explicit requested-language override, language switches preserving facts, purposeful broad clarification, compound and unambiguous short replies, explicit corrections with history, unknown/refusal replies, and ambiguous/new purchase/session isolation. Preserve unknown currency and mechanism; keep one highest-impact question. Do not change the scholar-approved evaluator to satisfy pending gold cases.
4. `src/rag/pipeline.py`, `src/rag/qdrant_store.py`, relevant adapters and tests: pin below/equal/above retrieval cutoffs, fail safely for missing or non-finite scores/configuration, and prove high relevance cannot bypass missing facts/rules. Numeric diagnostics remain internal. Diagnostic fallback must not promote invalid signals into answer evidence.
5. Application/input/source guardrails and service/API tests: cover guessing requests, claimed scholar authority, retrieved-text prompt injection, hidden-thought requests, unknown/ambiguous entities, conditional arithmetic with unknown fees, and failure behavior. Public trace contains typed facts/fixed codes only. No uncommitted substantive SSE output. Add interrupted SSE/retry observable tests, while keeping B-owned persistent retry/delivery lineage clearly incomplete.
6. `tests/` and `goal-a-case-results-2026-10-01.md`: complete paired material-change/paraphrase regressions and enumerate each A subcase with exact nodes and actual result. B-owned version attribution stays a dependency. Existing passing UI checks cover POC-15; broaden only if changed code needs it. Update this spec's checkboxes honestly; full Goal A is not done while required A behavior is unimplemented or failed.

Run focused tests as changes are made, then the full Python acceptance command. Browser tests may need a single worker on this machine; avoid simultaneous full Python/browser processes because earlier runs encountered host memory pressure. Protect operator stores; never print payloads or credentials. Do not commit or push from the implementation subagent; the primary agent handles verification/review and version control.

The first implementation slice includes the bilingual structured panel, REST/SSE and browser-history projection, cache persistence, private router signals and preservation prerequisites. [Case evidence and remaining gaps](goal-a-case-results-2026-10-01.md) keep expanded POC acceptance open. The status remains in-progress; review of this slice does not complete the 16-case contract.

Final verification: 1,322 Python tests passed, 48 skipped, 12 strict expected failures; 35 browser tests passed with one worker. Browser evidence is local/mock and the retrieval index was unavailable; deployed/model behavior is unverified.

Independent implementation review used the blind, edge-case and verification lenses. Intent alignment was inspected by the primary agent because the three available reviewer slots were occupied: the diff implements a typed public decision explanation and record hold; the broader conversation/evidence intent still has the gaps in the case ledger.

## Plan Change Log

- 2026-10-01 independent review: added explicit trace semantics, A/B ownership, source limits, preservation prerequisite and minimal private router capture before implementation. User requested review then implementation; no separate approval needed for these concrete corrections within that scope.

- 2026-10-01: User authorized additional important behaviors and tests. Added the linked 16-case evaluation contract, including corrections, unknown replies, session separation, source support, numeric boundaries, failure recovery and accessibility. No passing runtime result is implied by this plan update.

## Review Triage Log

| Finding | Verdict and evidence | Resolution / remaining scope |
| --- | --- | --- |
| Blind 1: branch-specific scope/review/asset reasons missing | Medium: authority refusal had ordinary metadata, leading to no_sources; review and unsupported-asset branches also lacked a specific reason. | Patched fixed decision-site codes for scope refusal, empty request, scholar review and unsupported asset; no answer prose is parsed. |
| Blind 2: terminal structure still says clarification | Medium: terminal structure retains structure_clarification metadata while status is INSUFFICIENT_DATA. | Patched status-specific terminal explanation; EN/AR two-turn regression tests pass. |
| Blind 3: structural information omitted | Medium: only DecisionReviewRow populated the missing/deciding lists. | Patched allowlisted structural slot projection. Free-text reply remains unverified/unknown because the legacy structure lane has not extracted a typed assertion. |
| Blind 4: evaluated rule names material-fact blocker | Medium: material_fact passes in the evaluated fixture while selective_answer blocks. | Patched selective_answer gate for the typed evaluated-but-withheld reason; test proves no result leaks. |
| Blind 5: deterministic scenario questions omitted | Medium: the origin was not recorded for the deterministic scenario and default engine paths. | Patched origin at those decision sites. Injected clarification providers retain the conservative generated/unknown behavior. |
| Blind 6: rule material slots omitted | Medium: eight-slot allowlist excluded valid late-payment, insurance, ownership, settlement and refund slots. | Patched all 17 canonical FACT_SLOTS and bilingual labels. Arbitrary noncanonical rule slots (e.g. synthetic beneficiary) still lack a public projection and remain an explicit A acceptance gap. |
| Blind 7: passage identity lost | Medium: quote offsets existed in final citations but were absent from trace. | Patched string offsets and explicit unknown source version. Actual version binding/semantic support remains open in POC-09. |
| Blind 8: non-finite numeric strings survive | Medium: NaN/Infinity matched no numeric-text filter. | Patched case-insensitive non-finite encodings; six variants pass without removing descriptive official-source labels. |
| Blind 9: malformed port deferred as outage | Medium: hostname/path checks accepted an invalid parsed port, so strict delivery failed repeatedly after startup. | Patched parser port/range and fragment validation before local-store creation; invalid syntax cases pass. |
| Blind 10: ledger and expanded coverage absent | Medium: reviewed diff lacked a case ledger and broad cases had missing tests. | Ledger now enumerates 16 cases and open subcases; small-screen long-AR light/dark checks added. Expanded behavior acceptance remains open. No full-goal completion is claimed. |
| Edge 1: terminal structural abstention | Medium: independently reproduced the same status/metadata mismatch as Blind 2. | Patched with the shared structural terminal fix. |
| Edge 2: authority refusal | Medium: independently confirmed the scope branch falls through to no_sources. | Patched with the decision-site scope code. |
| Edge 3: omitted material facts | Medium: typed canonical slots were silently excluded. | Patched all canonical slots and labels; noncanonical slots remain open as recorded above. |
| Edge 4: malformed mirror port | Medium: invalid port was accepted as a deferred network failure. | Patched configuration validation and tests. |
| Verification 1: Space detection untested | Medium: fixture removes both deployment variables and existing strict test used only explicit true. | Added each Space variable independently, with explicit false, missing URL rejection and valid strict-store construction. |
| Verification 2: symbols/legend untested | Medium: swapping unknown to reported or deleting legend would survive prior UI assertions. | Added all four localized state labels/symbols and legend checks before and after restore. |

The narrow code corrections above are within the approved typed-explanation and preservation intent. Remaining behavior work is recorded as incomplete implementation, rather than changing the frozen intent or presenting this first slice as accepted.

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

### Retrieval and answer delivery continuation

The primary agent implemented finite numeric retrieval gates at adapters, pipeline and custom service providers, with inclusive cutoff tests. Arbitrary generated factual claims are withheld unless the entire displayed proposition is a literal cited span; this conservative extractive policy does not claim semantic inference accuracy. A policy version separates old cache keys. Private-thought requests receive a fixed public explanation. SSE parsing requires a valid terminal response, discards partial output on failures, supports fragmented UTF-8/CRLF, and restores the canonical final response on retry. These changes implement authorized continuation items 4 and 5; independent review and complete verification remain pending.
