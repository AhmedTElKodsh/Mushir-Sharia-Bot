---
type: epic
title: "Client Sharia rules become scholar-approved rule cards"
parent: initiative-egypt-market-knowledge
covers: [CAP-9, CAP-11]
after: []
assignee: ""
risk: high
---

# Client Sharia rules become scholar-approved rule cards

## Description

Client Sharia rule files compile to versioned rule cards with scholar sign-off and a documented precedence against AAOIFI/IIFA, and the scholar judges one-clause counterfactual contract pairs whose decisions land as rule evidence. The pair is coupled: pair decisions are card evidence. The spec's CAP-9 and CAP-11 define the target (V1.7).

## Outcome

Every card in runtime use is scholar-approved, and synthetic material never reaches the named-company lane (spec CAP-9, CAP-11 success).

## Requirements

The spec's capability ids are this epic's requirement source (covers cites them directly); children cite them.

- CAP-9: Client Sharia rule files become versioned rule cards with scholar sign-off and documented precedence against AAOIFI/IIFA. Success: no verdict from a card without an approved decision; every runtime card approved.
- CAP-11: Scholar reviews one-clause counterfactual pairs from real templates. Success: synthetic material never retrievable in the named-company lane; pair decisions land as rule evidence.

## Done when

1. A test proves a card without an approved decision cannot support a runtime verdict; every runtime card is approved.
2. Precedence against AAOIFI/IIFA (O1) is documented before the first client card compiles.
3. A test proves synthetic counterfactual material is never retrievable in the named-company lane; pair decisions land as rule evidence.
4. The archetype taxonomy is scholar-approved with the cards.
5. Deployed to the Hugging Face Space per the release-ladder deploy rules: `/ready` healthy and a real-query smoke for what this epic delivers.

## Boundaries

Capability boundary: rule authority. Not schedule intake, not coverage.

Owns: Archetype taxonomy approval (adopted by epic-learned-behavior).

## References

- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/rule-card-schema.md
- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/mechanism-archetypes.md
- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/release-ladder.md, row V1.7

## Notes

- Open question: O1, precedence of client rules vs AAOIFI/IIFA.
