---
type: initiative
title: "Egypt Market Knowledge"
parent: none
covers: [CAP-1, CAP-2, CAP-3, CAP-4, CAP-5, CAP-6, CAP-7, CAP-8, CAP-9, CAP-10, CAP-11, CAP-12, CAP-13, CAP-14, CAP-15]
after: []
assignee: ""
risk: high
---

# Egypt Market Knowledge

## Description

Egyptian buyers and the client's compliance reviewers can ask whether an instalment or other non-cash financing offer raises a Sharia issue, about a named company or their own deal, and get an answer only the evidence and a scholar-approved rule earn. The spec owns the capabilities, constraints and non-goals; this initiative delivers V1.6 (dual-lane POC) and the release ladder to V2.0 on the public Hugging Face Space.

## Outcome

The spec's success signal: on the live Space a pilot-company question returns dated, cited public terms and asks for the missing schedule, the iPhone story gets exactly one financier question and no verdict, and scholar review of the frozen set finds zero wrong verdicts; V2.0 then meets the scholar-set risk threshold.

## Done when

1. V1.6 passes its release-ladder exit gate on the live Space: ~100 frozen cases pass the feature gold set (bilingual understanding, reasoning summary, cited sources, one-question clarification, correct abstention, with coverage reported), scholar review finds zero wrong verdicts, live smoke green.
2. No answer surface shows a numeric confidence, and no permissibility result is ever produced from an unknown or contradicted condition or an unapproved rule.
3. Every runtime rule card is scholar-approved, and synthetic material is provably absent from named-company retrieval.
4. All 52 FRA consumer-finance entities (39 licensed companies + 13 registered providers, register of 2026-10-02) are covered at template level with explicit access gaps.
5. V2.0 meets the scholar-set risk threshold on held-out reviewed cases, with release checklist and scholar sign-off complete.

## Boundaries

Capability boundary per the spec; see its Non-goals (no merchant census, no automated checkout or private agreement intake in V1.6, no fatwas, legal or investment advice). Tracer path: the iPhone story through the evidence-safe runtime and the described-operation lane on the live Space.

- Touch point: Chroma AAOIFI index — consumed unchanged (deploy `--skip-index`); owner: epic-evidence-safe-runtime
- Touch point: OpenRouter LLM — consumed; owner: epic-evidence-safe-runtime
- Touch point: HF Space Dockerfile and deploy scripts — configured per release; image change for the dossier SQLite file owned by epic-pilot-dossiers
- Touch point: `scripts/scrape_egypt_installment_market.py` one-page claim checker and its immutable runs — unchanged; owner: epic-pilot-dossiers
- Touch point: `scripts/scrape_fra_registry.py` and the FRA register — consumed as input; owner: epic-pilot-dossiers, extended by epic-financier-coverage

## References

- spec — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/spec-egypt-market-poc.md
- constraint — the same spec, section Constraints (access policy, PDPL, synthetic isolation, no fatwas)
- release — _bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/release-ladder.md

## Notes

- Decision: shared decisions have one home each. Semantics live in the spec companions (the spine); code-level contracts for slots, gates, review log, intent taxonomy, rule-card loader and dossier schema live in epic-evidence-safe-runtime entry 1; the frozen-set format lives in epic-scholar-verified-v1-6-release, which every adopter follows (2026-09-30).
- Decision: scholar pilot decisions promote rule cards to `approved` inside V1.6 (user, 2026-09-30).
- Decision: the golden set tests general features, and correct abstention is one of them; verdict accuracy grows progressively with scholar feedback and client training material. Developer-written rulings remain scholar-pending targets (user, 2026-10-01; spec companion `release-ladder.md`).
- Decision: legal review gates public named-company answers in epic-named-offer-lane (2026-09-30).
- Decision: primary V1.6 user is a retail buyer (O4, user, 2026-09-30).
- Decision: pilot entities are seven: valU (established financier), Contact, Souhoola, Aman, Halan, B.TECH/Mylo, Drive/Forsa (user, 2026-10-02); client confirmation is requested in the client guide and the review pack.
- Decision: V1.8 coverage scope is all 52 FRA consumer-finance entities: 39 licensed companies plus 13 registered providers (sellers financing their own goods), per the register of 2026-10-02 (user, 2026-10-03).
- Open question: O1 precedence, O2 staff agreements, O3 pilot entities, O5 wrong-verdict rate, O6 donated-document hosting; each is recorded on the epic it blocks.
