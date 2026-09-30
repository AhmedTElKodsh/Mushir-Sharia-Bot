---
type: epic
title: "Ask about a named company and get dated, cited terms"
parent: initiative-egypt-market-knowledge
covers: [CAP-1]
after: []
assignee: ""
risk: high
---

# Ask about a named company and get dated, cited terms

## Description

A user asks about a named company, seller or offer and receives its resolved entity, product and financier roles plus dated public terms, with every unobserved field marked unknown with a reason, and a question for the missing personal schedule. The spec's CAP-1 defines the target.

## Outcome

On the live Space, a question about a pilot company returns dated, cited public terms and asks for the missing personal schedule (spec CAP-1 success and Success signal).

## Requirements

The spec's CAP-1 are this epic's requirement source; children cite those ids. Completed at inception.

## Done when

1. For each pilot entity, every factual claim in the answer cites an exact source span and capture date; alias and wrong-company cases resolve correctly or ask.
2. No clause is reported absent by inference; unobserved fields show their reason (`not_publicly_found`, `login_gated`, `access_blocked`, `in_customer_schedule`).
3. Gate 5 holds: no named-company verdict without matching seller, financier, product and version evidence plus an approved rule; mismatched template versions give a clarification or INSUFFICIENT_DATA.
4. Company-level wording follows the architecture cross-cutting rule; every turn emits the review-log row.
5. Deployed to the Hugging Face Space per the release-ladder deploy rules: `/ready` healthy and a real-query smoke for what this epic delivers. Named-offer answers stay behind a flag on the public Space until legal review clears.

## Boundaries

Capability boundary: the named-offer lane. Files: intent routing to the named-offer lane, entity resolution and dossier lookup in `src/chatbot/application_service.py` and a new resolver module. Not dossier acquisition (epic-pilot-dossiers); company evidence and user facts never fill each other's gaps.

## References

- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/spec-egypt-market-poc.md, sections Capabilities (CAP-1), Constraints, Open Questions
- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/architecture.md, sections Answer path and Cross-cutting rules
- gates — .planning/sharia-compliance-chatbot/docs/l6-egypt-institution-scrape/dual-query-poc-answer-gates.md

## Notes

- Decision: legal/defamation review of named-company outputs gates this epic's public exposure. A hitl entry at inception gets the review; until it clears, named-offer answers ship behind a flag (chosen by the agent at the user's request, 2026-09-30).
- Waits on epic-described-operation-lane because: named-offer answers ask for the personal schedule through the same slots and gates.
- Waits on epic-pilot-dossiers because: it reads the dossier store.
