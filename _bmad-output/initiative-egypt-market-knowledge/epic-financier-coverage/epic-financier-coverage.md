---
type: epic
title: "All 52 FRA consumer-finance entities are covered"
parent: initiative-egypt-market-knowledge
covers: [CAP-12]
after: []
assignee: ""
risk: medium
---

# All 52 FRA consumer-finance entities are covered

## Description

All 52 FRA consumer-finance entities (39 licensed companies + 13 registered providers that finance their own goods; scope widened from 38 by the user on 2026-10-03) are covered at template level, merchants link to financiers, and Arabic, PDF and rendered pages are captured with per-field freshness. The spec's CAP-12 defines the target (V1.8).

## Outcome

The named-offer lane can answer at template level for every FRA consumer-finance licensee (spec CAP-12 success).

## Requirements

The spec's capability ids are this epic's requirement source (covers cites them directly); children cite them.

- CAP-12: All 52 FRA consumer-finance entities covered at template level; merchants link to financiers; Arabic, PDF, rendered pages with per-field freshness. Success: 52 dossiers; conflict/staleness markers tested; access gaps explicit.

## Done when

1. 52 entity dossiers exist; access gaps stay explicit.
2. Conflict and staleness markers pass tests.
3. Deployed to the Hugging Face Space per the release-ladder deploy rules: `/ready` healthy and a real-query smoke for what this epic delivers.

## Boundaries

Capability boundary: evidence acquisition at scale; extends epic-pilot-dossiers' pipeline. Not a full merchant census (spec Non-goals).

## References

- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/fact-and-evidence-model.md
- crawl plan — .planning/sharia-compliance-chatbot/docs/l6-egypt-institution-scrape/progressive-buyer-journey-crawl-plan.md
- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/release-ladder.md, row V1.8
