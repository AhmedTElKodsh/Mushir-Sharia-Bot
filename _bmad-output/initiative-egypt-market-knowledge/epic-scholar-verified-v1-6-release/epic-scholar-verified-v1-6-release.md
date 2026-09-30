---
type: epic
title: "V1.6 is live and scholar-verified"
parent: initiative-egypt-market-knowledge
covers: [CAP-7, CAP-8]
after: []
assignee: ""
risk: high
---

# V1.6 is live and scholar-verified

## Description

Pilot cases and every judgment answer are logged for bilingual scholar adjudication, feeding a versioned frozen set kept apart from training data; scholar decisions in this round promote the rule cards V1.6 verdicts rely on; V1.6 runs publicly and passes the release-ladder exit gate. The spec's CAP-7 and CAP-8 define the target.

## Outcome

Scholar review of the ~100-case frozen pilot set finds zero wrong verdicts on the live V1.6 Space (spec Success signal, release-ladder V1.6 exit gate).

## Requirements

The spec's CAP-7, CAP-8 are this epic's requirement source; children cite those ids. Completed at inception.

## Done when

1. About 100 frozen cases across both lanes and definitions, covering the release-ladder frozen-set list, are exported bilingually.
2. Scholar decisions import with reviewer, date and rule/corpus version; approved decisions promote their rule cards to `approved`; the frozen set is immutable per version and excluded from training.
3. Scholar review of the frozen set finds zero wrong verdicts.
4. V1.6 is live: `/ready` healthy; live smoke passes for English, Arabic, unanswerable, one named-offer and one described-operation case.

## Boundaries

Capability boundary: scholar review and release. Files: `src/governance/institution_pipeline.py` review export/import, `src/governance/scholar_review.py`, `src/scholar/review_schema.py`, `scripts/export_scholar_review.py`, `scripts/import_scholar_corrections.py`, frozen-set versioning, the V1.6 release.

Owns: The frozen-set format and versioning, adopted by epic-learned-behavior and epic-launch-candidate (both after this epic).

## References

- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/spec-egypt-market-poc.md, sections Capabilities (CAP-7, CAP-8) and Success signal
- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/release-ladder.md, sections Frozen evaluation set, Metrics, Deploy rules
- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/rule-card-schema.md, section Scholar-time order
- ops — .planning/sharia-compliance-chatbot/docs/ops/huggingface-spaces.md

## Notes

- Decision: scholar decisions in the pilot round promote rule cards to `approved` inside V1.6; this epic owns that promotion (user's decision, 2026-09-30).
- Open question: O5, the acceptable wrong-verdict rate for launch; V1.6 targets zero on the frozen set.
- Handoff: epic-scholar-rule-cards builds the full client-rule card pipeline on this epic's review loop.
