---
title: 'Runtime 1: Shared evidence contracts'
type: 'feature'
created: '2026-09-30'
status: 'done'
route: 'full'
route_source: 'auto'
review: 'thorough'
review_source: 'auto'
lenses_ran: ['blind-hunter', 'edge-case-hunter', 'verification-gap', 'intent-alignment']
review_loop_iteration: 0
baseline_commit: '3f59ddfe44d6c31ec77f82f7fd5fc4c51f2adb35'
context:
  - '{project-root}/project-context.md'
  - '{project-root}/_bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/fact-and-evidence-model.md'
  - '{project-root}/_bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/rule-card-schema.md'
  - '{project-root}/.planning/sharia-compliance-chatbot/docs/l6-egypt-institution-scrape/dual-query-poc-answer-gates.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The first evidence-safe runtime ticket is unimplemented. Both answer lanes need a common validated record for provenance, decisions, dossier observations, and approved rule eligibility before runtime integration.

**Approach:** Add additive, serializable contracts and a strict local rule-card loader following the adopted companions. Restore the local Python test environment. This is ticket 1 in `epic-evidence-safe-runtime/tickets.toml`; later tickets integrate these contracts into the answer path. The user's instruction to continue implementing/testing authorizes this existing planned work.

## Boundaries & Constraints

**Always:** Preserve existing answer APIs in this foundation slice. Retain source/user-turn identity, exact text, scope, date/version, and observed/user_reported/conflicting/unknown statuses. Retain false and zero as known values. Keep company facts separate from personal facts. Keep all unavailable clauses unknown. A card is eligible only with approved status and approved scholar signoff, reviewer identity and date. Card loading must never approve anything. Model validation establishes structure, not truth or human authenticity.

**Never:** Infer a price, financier, mechanism, missing clause, or verdict; present rule-card placeholder outcomes as rulings; use synthetic/provider self-claims as verified company facts; contact external providers, deploy, scrape, or modify the Chroma index. No precedence choice or real rule authoring: pending cards may load for review, but a runtime-eligible card requires an explicit precedence note. No automatic promotion from existing review queues.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| iPhone facts | User states EGP 5,000 down and 12 instalments of EGP 3,000 | Separate typed values with turn provenance; financier and total remain unknown | No inferred total/contract |
| Public evidence | Source URL, capture time/hash, exact span, scope/version | Observed field serializes with complete provenance | Missing source/date/span rejected |
| Inaccessible clause | Unknown with one of four unobserved reasons | Unknown preserved; no value manufactured | Contradictory unknown + known value rejected |
| Conflicting statements | Two incompatible supported values | Conflict and both candidates preserved | No automatic overwrite/selection |
| Misattributed evidence | User turn in observed fact, public page as user fact, synthetic observation, provider self-label as mechanism | Invalid authority combination rejected | Explicit validation error |
| Pending/superseded card | Example rule schema with pending review or superseded status | Loads for review; cannot support verdict | Malformed schema rejected |
| Approved card | Approved status/signoff with reviewer, date, source anchor, material facts and precedence | Eligible metadata only; no evaluator result | Missing signoff/authority rejected |
| Decisions | ANSWER, clarification, insufficient | Reasoned envelope; clarification exactly one question, insufficiency names missing document/review | Invalid question/decision combinations rejected |
| Review | Fact snapshot, gates, cited answer, intent, turn/version | Round-trip without loss | Missing trace identifiers rejected |

</frozen-after-approval>

## Code Map

- `src/models/commercial.py`: legacy dataclass/enum contracts; retain behavior and do not overload old confidence-bearing verdicts.
- `src/models/schema.py`, `src/api/schemas.py`: existing Pydantic validation patterns; use validated models where useful, avoiding coercion of booleans/numbers to strings or silent extra-field loss.
- `src/models/evidence.py` (new): fact vocabulary, source/user provenance, scoped observations/dossier metadata, intent, gate envelope and decision review row. Include every named companion slot plus extensible rule-specific slots.
- `src/governance/rule_cards.py` (new): versioned card model, safe YAML/local mapping loader, duplicate/version validation and approved-only selection. Match schema keys from companion; no runtime wiring yet.
- `src/governance/scholar_review.py`: existing append-only review vocabulary; do not repurpose nonblocking queue as decision log.
- `tests/test_evidence_contracts.py`, `tests/test_rule_cards.py` (new): normal, malformed and adversarial construction plus serialization and loader tests.
- `requirements.txt`, `requirements-dev.txt`: current declared dependencies; `.venv` is ignored. Parent handles installation and baseline verification.

## Tasks & Acceptance

**Execution:**
- [x] `src/models/evidence.py` — implement validated shared records with explicit JSON round-trip support and stable field names.
- [x] `src/governance/rule_cards.py` — load reviewable cards and expose approved-only eligibility without invented rule semantics; reject duplicate IDs/versions and ambiguous YAML keys.
- [x] `tests/test_evidence_contracts.py`, `tests/test_rule_cards.py` — exercise all matrix rows and every companion field/class; test false/zero, timezone/version and mutation/round-trip invariants.
- [x] `.venv` — install declared runtime/dev dependencies and run existing regression tests.

**Acceptance Criteria:**
- Given companion examples, when constructed and serialized, then all fact, source, scope, date/version, access, intent, decision and review fields survive without silent coercion or loss.
- Given missing or contradictory provenance, when validated, then invalid observed facts are rejected and legitimate unknown/conflicting facts retain their evidence.
- Given pending, superseded or malformed cards, when loading runtime-eligible rules, then none can support a verdict and malformed data fails explicitly.
- Given the existing application, when baseline API/governance tests run, then additive contracts do not change existing behavior.

## Implementation Notes

- 2026-09-30: Clean baseline on `feat/egypt-instalment-market-strategy`; existing initiative supplies scope and build order. Proceeding under the user's implementation authorization without an additional routine plan approval. Scholar approval and public release remain separate evidence requirements.
- 2026-09-30: Created ignored Python 3.12 `.venv`; dependency installation in progress.

## Spec Change Log

## Review Triage Log

- Blind 1: medium, patched duplicate gate results. The broader demand to reject every ANSWER with any blocked gate is false for this contract: the adopted gates explicitly allow independently supported facts while withholding the requested conclusion. Runtime must scope this distinction to claims; envelope shape alone does not authorize a verdict.
- Blind 2 / Edge 2: high, patched. CitedClaim now applies the same source admissibility checks as FactCandidate; synthetic and inaccessible captures are rejected. Dedicated regression tests pass.
- Blind 3 / Edge 1: high, patched. Every nested user-turn source in facts, conflicts, citations and clarifying turns is checked against the decision-review session. Four injection locations are tested.
- Blind 4: medium, patched. Snapshots reject duplicate active slot/scope pairs; historical records belong outside a snapshot and conflicts retain candidate values.
- Blind 5: medium, patched. Capture identity is source ID plus capture timestamp plus document version; duplicate identities cannot disagree on hash, URL or other metadata. Different dated captures of a source remain valid history.
- Blind 6: deferred to mechanism and claim-support integration. Document classification alone cannot prove that text establishes a mechanism. Structural validation never claims semantic truth; future extraction must ground the mechanism in clauses and cannot relabel a marketing self-claim as proof.
- Blind 7 / Edge 3: medium, patched. Added separate access_attempts to facts so unknown values retain failed capture provenance without pretending to have a supporting span.
- Blind 8: deferred. Private schedule uploads and donated agreements require non-URL capture locators when intake is implemented in V1.7; V1.6 explicitly excludes private agreement intake. Publicly hosted disclosure documents remain representable.
- Verification-gap 1: medium, patched. Complete valid YAML control cards now receive duplicate top-level, duplicate condition and merge-key mutations; tests require parser-specific errors, so later schema errors cannot mask regression.
- Intent alignment: foundation-only interpretation confirmed. Runtime gates, reviewer authentication and semantic claim support are explicitly not established by structural records. Cross-session defect fixed as above. Punctuation validation follows existing API convention; overlapping draft outcomes remain a documented conservative schema choice. Environment/test changes are intentional preflight repairs. No full POC completion claim is made.

Latest focused verification: 229 passed across contracts, rule cards, ingestion, API schemas, scholar review and source governance. Broad regression: 847 passed, 6 failed, 47 skipped. All six failures match the recorded baseline; ten ingestion failures are resolved. JUnit evidence: `data/runtime/artifacts/poc-contract-tests.xml`. This completes the foundation build, not runtime adoption or POC release.

## Verification

- `.venv/Scripts/python.exe -m pytest tests/test_evidence_contracts.py tests/test_rule_cards.py -q --timeout=60` — every matrix case passes.
- `.venv/Scripts/python.exe -m pytest tests/test_api_schemas.py tests/test_scholar_review.py tests/test_source_governance.py -q --timeout=60` — existing boundary regression.
- `.venv/Scripts/python.exe -m pytest -q --timeout=90` — broad baseline; separate unavailable-service skips and pre-existing failures from regressions.
