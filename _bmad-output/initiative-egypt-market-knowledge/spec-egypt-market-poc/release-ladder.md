# Release Ladder (Hugging Face Space, from V1.5)

## Pre-scholar developer/client showcase iterations

Early showcase iterations may precede the scholar-reviewed V1.6 milestone below. Their scope is supported explanations, Arabic/English understanding, guided clarification, citations, safe abstention and structured decision explanations. They must not claim reviewed judgment accuracy or bypass the approved-rule gate. Use [the POC behavior and evaluation contract](../poc-showcase-behavior-evaluation.md) for the 16 required behavior cases and versioned evidence of results.

Preserve all in-scope POC review records and supporting evidence until the scholar finishes reviewing. Age retention and storage-cap eviction are disabled by default across all stores; later 365-day retention and caps require explicit policy activation after review completion. Goal B defines implementation and verification; this planning requirement is not proof that the runtime hold is already active.

## Purpose of the golden evaluation set (user decision, 2026-10-01)

The golden set tests Mushir's general features. It does not certify Sharia verdict accuracy. The features it scores:

- understanding of Arabic, Egyptian Arabic, English and code-mixed questions, with equivalent facts and gate decisions across languages;
- the reasoning path behind every answer, shown to the user as the reasoning summary (the decision trace panel). Private chain-of-thought is never displayed or stored (POC-11);
- citations that resolve to supporting passages;
- one-question clarification;
- correct abstention.

**Saying "I don't know" is a scored feature.** It applies when a realistic customer request needs more than the AAOIFI evidence and the scholar-approved rules support. A case passes only when it abstains *for the right reason*: the question is recognised as a judgment, Mushir stops at the approved-rule gate, shows its sources, answers in the user's language, and queues the question for the scholar. Abstaining at the wrong gate is a failure even though the output says "I don't know". Per [the POC contract](../poc-showcase-behavior-evaluation.md), answer coverage is always reported alongside abstention, so refusing everything cannot look like success.

This is the first step in progressive model development. Scholar feedback, approved rule cards and further training material from the client widen what Mushir can answer over successive releases. The developer-written `expected_ruling` in each gold case stays unedited as the scholar-pending target. It is asserted only once a scholar-approved rule card named by the case (`rule_card`) is loaded (`tests/evaluation/test_critical_goldset.py`).

## Scholar-reviewed milestones

| Version | Capabilities | Exit gate |
| --- | --- | --- |
| V1.6 Dual-lane POC | CAP-1..CAP-8 | ~100 frozen pilot cases pass the feature gold set (above) with coverage reported beside abstention; the scholar reviews them and finds zero wrong verdicts, and that feedback opens the next improvement cycle; V1.6 blockers in `brownfield.md` closed; live smoke passes |
| V1.7 Rules and schedules | CAP-9, CAP-10, CAP-11 | Every runtime card approved; schedule extraction accuracy reported; synthetic isolation test green |
| V1.8 Financier coverage | CAP-12 | 52 FRA consumer-finance entities (39 licensees + 13 providers) at template level; conflict/staleness markers tested |
| V1.9 Learned behavior | CAP-13, CAP-14 | Prior calibrated on held-out entities; prior-never-changes-verdict test green; fine-tune beats baseline or is dropped |
| V2.0 Launch candidate | CAP-15 | Scholar-set risk met on held-out reviewed cases; release checklist and scholar sign-off |

## Frozen evaluation set (V1.6 minimum)

Both lanes plus general definitions:
- complete and incomplete iPhone-style stories;
- one-fact counterfactuals;
- unknown financier; unknown late fee; contradictory totals;
- named-company alias and wrong-company cases;
- stale or conflicting public pages; inaccessible agreement;
- unsupported or injected source text;
- Arabic, English and code-mixed phrasing;
- multi-turn corrections.

Measure: unsupported claims, wrong permissibility conclusions, correct abstention/clarification, one-question quality, source support, coverage. Verify the full deployed answer path, not mocked retrieval.

## Metrics

- Primary: wrong-verdict rate among answered judgment cases (scholar-set target, O5).
- Secondary: coverage, unsupported-claim rate, correct abstention, one-question quality, source support.

## Deploy rules

UI-only: `--ui-only`; runtime without retrieval change: `--skip-index`; retrieval change: full deploy + `/ready` + real query smoke (`.planning/sharia-compliance-chatbot/docs/ops/huggingface-spaces.md`).
