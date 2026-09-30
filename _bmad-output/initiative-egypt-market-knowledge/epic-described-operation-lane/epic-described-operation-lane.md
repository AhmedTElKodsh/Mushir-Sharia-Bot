---
type: epic
title: "A buyer describes their deal and gets the one right question"
parent: initiative-egypt-market-knowledge
covers: [CAP-2, CAP-3]
after: []
assignee: ""
risk: high
---

# A buyer describes their deal and gets the one right question

## Description

A user describes their own financing operation across turns, with or without a known company. Its facts become typed slots with provenance, and the dual-query gates decide ANSWER, CLARIFICATION_NEEDED or INSUFFICIENT_DATA, asking one highest-impact question when a user-answerable fact is missing. The spec's CAP-2 and CAP-3 define the target.

## Outcome

On the frozen iPhone story (deposit + 12 × EGP 3,000), the first reply has no verdict and asks who provides the plan (spec CAP-2, CAP-3 success).

## Requirements

The spec's capability ids are this epic's requirement source (covers cites them directly); children cite them.

- CAP-2: Described operation captured across turns as typed slots with provenance. Success: frozen cases (incl. iPhone deposit + 12 x EGP 3,000) match expected slots; contradictions flagged; follow-up never overwrites a slot without reconciliation.
- CAP-3: ANSWER / CLARIFICATION_NEEDED / INSUFFICIENT_DATA per the dual-query gates, one highest-impact question. Success: iPhone first reply has no verdict and asks who provides the plan; turn-limit exhaustion with a material fact missing is INSUFFICIENT_DATA naming the document.

## Done when

1. Frozen described-operation cases, including the iPhone story, produce slot records that match the expected record; contradictions are flagged and follow-up text never overwrites a slot without reconciliation.
2. The iPhone story's first reply has no verdict and asks exactly one question: who provides the plan.
3. When the turn limit is exhausted with a material fact missing, the result is INSUFFICIENT_DATA naming the needed document; the turn limit never marks a case ready.
4. Every turn emits the review-log row defined by epic-evidence-safe-runtime, which epic-scholar-verified-v1-6-release consumes.
5. Deployed to the Hugging Face Space per the release-ladder deploy rules: `/ready` healthy and a real-query smoke for what this epic delivers.

## Boundaries

Capability boundary: the described-operation lane. Files: slot extraction in `src/chatbot/commercial_assessment.py` (replacing whole-query storage), `src/chatbot/scenario_extractor.py`, rule-specific sufficiency in `src/chatbot/clarification_engine.py`, and `src/eval/runner.py` where it reads scenarios. Not company evidence (epic-named-offer-lane); company evidence and user facts never fill each other's gaps.

## References

- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/spec-egypt-market-poc.md, sections Capabilities (CAP-2, CAP-3) and Success signal
- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/fact-and-evidence-model.md, sections Fact slots and Template and schedule
- gates — .planning/sharia-compliance-chatbot/docs/l6-egypt-institution-scrape/dual-query-poc-answer-gates.md
- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/brownfield.md, section V1.6 blockers

## Notes

- Waits on epic-evidence-safe-runtime because: slots, gates and the review-log row are its shared contracts.
- Handoff: its Space deploy and epic-pilot-dossiers' deploy share one Docker image; deploy one at a time.
