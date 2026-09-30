---
type: epic
title: "Buyers share their instalment schedule safely"
parent: initiative-egypt-market-knowledge
covers: [CAP-10]
after: []
assignee: ""
risk: high
---

# Buyers share their instalment schedule safely

## Description

A user shares a screenshot of their instalment schedule to supply schedule facts, processed with redaction and without retention unless they opt in, under Egypt's PDPL (Law 151/2020). The spec's CAP-10 defines the target (V1.7).

## Outcome

Schedule facts reach the slots as `user_reported` without the document being kept (spec CAP-10 success).

## Requirements

The spec's capability ids are this epic's requirement source (covers cites them directly); children cite them.

- CAP-10: User shares an instalment-schedule screenshot; redacted, not retained unless opt-in. Success: extraction accuracy reported on labeled schedules; nothing persisted without opt-in.

## Done when

1. Extraction accuracy is reported on labeled schedules.
2. Tests prove nothing is persisted without opt-in, and documents are redacted before reading.
3. Deployed to the Hugging Face Space per the release-ladder deploy rules: `/ready` healthy and a real-query smoke for what this epic delivers.

## Boundaries

Capability boundary: user document intake. Not donated agreements (O2, O6).

## References

- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/fact-and-evidence-model.md, section Acquisition channels
- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/spec-egypt-market-poc.md, section Constraints
- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/release-ladder.md, row V1.7

## Notes

- Open question: O2 (staff donating their own agreements) and O6 (hosting and retention of donated documents).
