---
type: epic
title: "Mushir never gives an unearned verdict"
parent: initiative-egypt-market-knowledge
covers: [CAP-4, CAP-5]
after: []
assignee: ""
risk: high
---

# Mushir never gives an unearned verdict

## Description

Close the V1.6 runtime blockers so that no answer path can produce a permissibility result from generic wording, an unobserved condition, an unapproved rule, or a retrieval score. This epic also owns the code-level shared contracts both answer lanes build on. The spec's CAP-4 and CAP-5 define the target.

## Outcome

A retail buyer never receives a Sharia conclusion the evidence does not earn, and every answer shows its evidence status and source date instead of a percentage (spec CAP-4, CAP-5 success).

## Requirements

The spec's CAP-4, CAP-5 are this epic's requirement source; children cite those ids. Completed at inception.

## Done when

1. Generic instalment, BNPL, تقسيط or تمويل wording never sets a contract family or archetype; EN, AR and code-mixed tests prove it across `contract_classifier.py`, `contract_family_router.py`, `commercial_assessment.py` and `prompt_builder.py`.
2. The ruling evaluator is tri-state: tests prove an unknown or contradicted material condition never yields a permissibility result.
3. A verdict is produced only from a rule card with `decision: approved`; with none approved, a judgment request returns INSUFFICIENT_DATA naming what is missing.
4. No answer surface shows a numeric confidence: API schema, SSE events, web UI, CLI; every answer states its evidence status and source age, worded for a retail buyer.
5. The review-log row is written as part of the answer decision, not queued after answering.
6. Deployed to the Hugging Face Space per the release-ladder deploy rules: `/ready` healthy and a real-query smoke for what this epic delivers.

## Boundaries

Capability boundary: the shared answer runtime. Files: `src/chatbot/contract_classifier.py`, `src/chatbot/contract_family_router.py`, `src/chatbot/prompt_builder.py`, the contract-family part of `src/chatbot/commercial_assessment.py`, `src/ontology/ruling_evaluator.py`, `src/chatbot/citation_validator.py` (gate 6 claim support), the confidence and review-queue parts of `src/chatbot/application_service.py`, `src/api/schemas.py`, `src/api/routes.py`, `src/static/js/app.js`, `src/static/js/renderer.js`, `src/chatbot/cli.py`. Not slot extraction or clarification sufficiency (epic-described-operation-lane), not dossiers.

Owns: Shared contracts (its first entry): typed fact-slot record and status vocabulary (`observed`, `user_reported`, `conflicting`, `unknown` + unobserved reasons); gate-decision envelope (ANSWER, CLARIFICATION_NEEDED, INSUFFICIENT_DATA + reasons) and the review-log row; intent taxonomy (named offer, described operation, definition, out of scope); rule-card loader per `rule-card-schema.md`; dossier observation schema (written by epic-pilot-dossiers, read by epic-named-offer-lane). Also restores the local test environment (no `.venv` today).

## References

- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/spec-egypt-market-poc.md, sections Capabilities (CAP-4, CAP-5) and Constraints
- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/architecture.md, sections Answer path, Components, Cross-cutting rules
- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/fact-and-evidence-model.md
- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/rule-card-schema.md
- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/mechanism-archetypes.md
- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/brownfield.md, section V1.6 blockers
- gates — .planning/sharia-compliance-chatbot/docs/l6-egypt-institution-scrape/dual-query-poc-answer-gates.md

## Notes

- Decision: no separate platform-baseline epic. V1.5 is live on the Space with working deploy scripts; this epic's first entry restores the local test environment (2026-09-30).
- Decision: the spec companions are the architecture spine for semantics; the code-level types for decisions shared by several epics live in this epic's first entry (2026-09-30).
- Decision: the V1.6 primary user is a retail buyer (O4); answer-surface wording targets them (2026-09-30).
