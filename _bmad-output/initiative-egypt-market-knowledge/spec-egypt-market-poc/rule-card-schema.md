# Rule Card Schema

Each rule from the client's Sharia files (and each referenced AAOIFI/IIFA rule) compiles to one card:

```yaml
rule_id: riba-late-payment-benefit-v1
version: 1
source_authority: client_rulebook   # or aaoifi_ss / iifa
source_anchor: "<file, section, paragraph>"
applies_to_archetypes: [ARC-CF, ARC-SELLER, ARC-BANK-ISL]
material_facts: [late_fee_exists, late_fee_beneficiary, late_fee_basis]
outcomes:        # one row per material-fact combination
  - when: {late_fee_exists: false}
    outcome: no_issue_under_this_rule
  - when: {late_fee_exists: true, late_fee_beneficiary: financier}
    outcome: impermissible_under_this_rule
  - when: {late_fee_exists: true, late_fee_beneficiary: charity}
    outcome: conditional
unknown_fact_question: "<the one question to ask when a material fact is unknown>"
precedence_note: "<relation to AAOIFI SS-8 / SS-3 / IIFA>"
scholar_signoff: {reviewer_id: null, date: null, decision: pending}
status: draft   # draft | approved | superseded
```

These outcomes are structural placeholders, not rulings.

## Rules

- A card with `decision != approved` never supports a runtime verdict.
- Precedence against AAOIFI/IIFA is fixed before the first card compiles (O1); conflicts are never averaged.
- Unknown material fact → the card's `unknown_fact_question` (user-answerable) or INSUFFICIENT_DATA.
- Supersession keeps prior versions; answers log `rule_id` + `version`.

## Scholar-time order

1. Approve cards and the archetype taxonomy.
2. Judge one-clause counterfactual pairs.
3. Audit a stratified answer sample (lane, archetype, language, outcome) plus every verdict.
4. Adjudicate conflicts; set the launch wrong-verdict rate (O5).

## Current Sharia source state

AAOIFI SS-01..54 and SS-60 are machine-extracted (EN); SS-55..59 are missing; `hard_sharia_ready: false`; 10 hard-case seeds are pending review.
