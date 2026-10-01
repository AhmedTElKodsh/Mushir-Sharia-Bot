---
type: epic
title: "Five pilot entities have evidence dossiers"
parent: initiative-egypt-market-knowledge
covers: [CAP-6]
after: []
assignee: ""
risk: medium
---

# Five pilot entities have evidence dossiers

## Description

Build the evidence side for five permitted pilot entities: entity resolution and access decision, bounded link discovery, HTML and PDF capture, and field observations with spans (BJ-00..02, BJ-04), stored in an append-only SQLite dossier store shipped in the Space image. The spec's CAP-6 defines the target.

## Outcome

Each of the five pilot entities has a dossier the named-offer lane can cite by span and capture date (spec CAP-6 success).

## Requirements

The spec's capability ids are this epic's requirement source (covers cites them directly); children cite them.

- CAP-6: Dossiers for five permitted pilot entities (BJ-00..02, BJ-04). Success: entity record, access decision with reason, capture manifest, field observations with spans, first gated step.

## Done when

1. Five dossiers exist, each with an entity record, access decision with reason, link graph, capture manifest (URL, time, hash, content type, language), field observations with spans, and the first gated step recorded.
2. The store is append-only: the current view is the latest valid observation per field plus the latest failed attempt, and a test proves a partial or failed recrawl never erases older evidence.
3. `scripts/summarize_egypt_installment_market.py` emits only roles the passage establishes; a provider's Sharia self-label is stored as a `provider_claim`, never a finding.
4. Every public route has current scoped terms/access decisions and separate robots/security/auth outcomes; source-issued scoped robots exceptions are recorded, and no capture crosses a live login, CAPTCHA/security or gated step. B.TECH, Amazon and noon stay in the permission queue without source permission. Private/manual gated intake is separately authorized and deferred.
5. Deployed to the Hugging Face Space per the release-ladder deploy rules: `/ready` healthy and a real-query smoke for what this epic delivers. The dossier SQLite file ships in the image.

## Boundaries

Capability boundary: evidence acquisition. Files: a new journey-discovery pass beside the market collector, the observation extractor extending `src/governance/institution_pipeline.py`, `scripts/summarize_egypt_installment_market.py`, the dossier store (reusing or extending `src/institution_db/schema.py`, decided at inception), the Space image. Not the existing one-page claim checker `scripts/scrape_egypt_installment_market.py` (unchanged), not answering.

## References

- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/spec-egypt-market-poc.md, sections Capabilities (CAP-6) and Constraints
- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/architecture.md, section Evidence acquisition
- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/fact-and-evidence-model.md, sections Dossier contents and Access boundary
- crawl plan — .planning/sharia-compliance-chatbot/docs/l6-egypt-institution-scrape/progressive-buyer-journey-crawl-plan.md
- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/brownfield.md, sections Existing assets and V1.6 blockers

## Notes

- 2026-10-01: The reviewed hybrid procedure is adopted in `evidence-acquisition-playbook.md`; the public HTML/PDF capture foundation is implemented separately from the legacy market checker. Full link discovery, dossier-store/observation integration, current pilot access decisions, complete contracts and deployment remain pending. This foundation does not complete CAP-6 or this epic.

- Open question: O3, the final five pilot entities; the spec's shortlist (Contact, Souhoola, RUSHBRUSH, IKEA Egypt or Smart Furniture, one direct retailer with a named financier) stands until answered. A hitl entry at inception confirms them and each host's access decision.
- Waits on epic-evidence-safe-runtime because: observation statuses and the dossier schema are its shared contracts. It can run beside epic-described-operation-lane (no shared code), but their Space deploys go one at a time.
- Decision: Space deploys are serialized by `after`: epic-evidence-safe-runtime 7, then epic-described-operation-lane 6, then epic-pilot-dossiers 7.
