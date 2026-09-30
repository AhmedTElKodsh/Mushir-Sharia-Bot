---
type: epic
title: "Learned behavior improves questions without touching verdicts"
parent: initiative-egypt-market-knowledge
covers: [CAP-13, CAP-14]
after: []
assignee: ""
risk: high
---

# Learned behavior improves questions without touching verdicts

## Description

A supervised archetype prior orders clarification questions and chooses documents to request, and a behavior fine-tune is evaluated against the prompted baseline. Both are evaluated on entity-grouped held-out data. The spec's CAP-13 and CAP-14 define the target (V1.9).

## Outcome

Better next questions with a proven firewall between the prior and the verdict (spec CAP-13, CAP-14 success).

## Requirements

The spec's CAP-13, CAP-14 are this epic's requirement source; children cite those ids. Completed at inception.

## Done when

1. Calibration on entity-grouped held-out data is reported; a test proves the prior never changes a decision or fills a slot.
2. A comparison report on the frozen set; the fine-tune is adopted only if it beats the baseline, otherwise dropped.
3. Deployed to the Hugging Face Space per the release-ladder deploy rules: `/ready` healthy and a real-query smoke for what this epic delivers.

## Boundaries

Capability boundary: model behavior. Model weights never hold company facts or verdict authority.

## References

- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/architecture.md, section Three layers
- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/release-ladder.md, row V1.9
