# Dual-query POC answer gates

**Drafted:** 2026-09-29  
**Scope:** Public Mushir POC for named Egyptian financing offers **and** user-described financial operations. This defines required behavior; it is not a claim that the current runtime implements it.

## Questions the same POC must handle

1. **Named offer:** "What are Contact's terms for this car instalment offer? Is my transaction permissible?" Resolve entity, product, financier and dated source versions. Public terms can explain observed standard clauses; a customer's unobserved supplementary statement remains unknown.
2. **User-described transaction:** "I bought an iPhone, paid EGP 5,000 down, and owe EGP 3,000 monthly for 12 months. Is it halal?" Use facts supplied by the user even if the shop is not in the market database. Those numbers do not establish the financier, contract mechanism, full charges or relevant clause conditions.
3. **General concept:** "What is a deferred sale?" An approved, cited definition may be answered without demanding a buyer's contract details.

The company evidence corpus and user-supplied transaction facts are separate inputs. A company advertisement does not fill gaps in a customer's agreement; a user's story does not establish a company's published policy.

## Shared fact and evidence record

Extract typed slots with value, source, exact supporting text or user turn, scope, date/version where relevant, and one of `observed`, `user_reported`, `conflicting`, or `unknown`. At minimum the schema must distinguish the asset, seller, sales channel, financing party, contract family if established, cash price, financed or final price, down payment, number and amount of instalments, additional fees, late-payment clause and beneficiary, ownership or risk sequence where the selected rule requires it, and early settlement/refund terms where relevant. **Do not treat every slot as universally required:** the requested answer and scholar-approved rule determine the material facts.

For multi-turn clarification, retain and reconcile these typed slots. Do not infer that the first EGP figure is the full price or merge follow-up text into an unverified free-text scenario. Arithmetic consistency can flag a contradiction, but calculating `deposit + instalments` does not prove the contractual total payable or the absence of other fees.

## Answer decision

| Result | Required behavior |
| --- | --- |
| `ANSWER` | Give only factual claims supported by exact source spans or the user's clearly attributed facts, and only rule applications supported by an approved, versioned rule and all its material facts. Cite every external claim. A general definition needs the approved definition source, not a full transaction dossier. |
| `CLARIFICATION_NEEDED` | Withhold the requested Sharia conclusion when a missing or ambiguous user-answerable fact could change the rule or outcome. Ask exactly one highest-impact question and retain the rest of the fact record. |
| `INSUFFICIENT_DATA` / scholar review | Withhold the conclusion when the needed source or reviewed rule is absent, evidence conflicts, a contract is gated, or further questions cannot resolve the gap. State which document or review is needed; do not repeat an unproductive clarification loop. |

For the iPhone example, the first response should contain no tentative halal/haram judgment. A useful first question is: **"Who provides the instalment plan—the store itself, or a bank or finance company?"** The answer then determines the next rule-specific question. If the buyer does not know, ask for the relevant agreement or repayment disclosure and stop at `INSUFFICIENT_DATA` if it is unavailable.

## Layered guardrails, in order

1. **Intent and scope:** distinguish named-offer lookup, described transaction, general definition and out-of-scope request. Do not make a company lookup a prerequisite for analyzing a user's own facts.
2. **Typed extraction with provenance:** separate price, deposit, monthly instalment, fees and total; resolve parties independently; reject contradictions and ambiguous aliases.
3. **Contract-family discipline:** generic `instalment`, `BNPL`, `تقسيط`, and `تمويل` do not prove Murabaha or Islamic financing. Keep the mechanism unknown until evidence establishes it.
4. **Material-fact gate:** evaluate the scholar-approved rule's required conditions even when a router has confidently named a contract family. An unanswered condition is `unknown`; it is not automatically violated or satisfied.
5. **Source and version gate:** require an admissible Sharia source for a permissibility answer and exact company/product/financier/version evidence for a named offer. An old or conflicting page cannot silently become current terms.
6. **Claim support gate:** validate each generated external claim against the cited passage. A citation to a related standard or page alone does not support every sentence.
7. **Selective-answer gate:** after all hard gates pass, apply a risk threshold calibrated on held-out scholar-reviewed end-to-end cases. Until those cases exist, use deterministic abstention and do not display a numeric correctness percentage. Retrieval similarity and fixed rule scores are not answer probability.
8. **Review and feedback:** log the fact record, gate decisions, clarifying turn and final cited answer for scholar adjudication. Keep training and frozen evaluation cases separate.

A failed guardrail blocks the *requested conclusion*. A factual query may still receive independently supported facts; a judgment query that lacks a material fact receives the clarification or insufficiency response without a partial verdict.

## Current implementation gaps to close

- `src/chatbot/contract_classifier.py`, `src/chatbot/commercial_assessment.py`, and `src/chatbot/prompt_builder.py` currently map generic instalment or finance wording to Islamic contract families. Remove those assumptions and test English, Arabic and code-mixed cases.
- `src/chatbot/commercial_assessment.py` stores much of a buyer story as whole-query text and does not fill seller, financier, labeled deposit or repayment schedule. Add typed extraction and validation.
- `src/chatbot/clarification_engine.py` checks a short generic purchase field list and can bypass clarification once a family is known. `process_query` can mark a case ready after its turn limit with missing fields. Make rule-specific sufficiency authoritative, and return insufficient data when a material fact remains unavailable.
- `src/ontology/ruling_evaluator.py` returns the rule's permissibility even when required conditions are unobserved. Do not use that path for a POC verdict until unknown and contradicted conditions are separated and scholar approval is enforced.
- `src/chatbot/application_service.py` computes `confidence` from retrieval scores and may queue low-score review after generating an answer. Replace that display with evidence-status labels; future numeric risk thresholds require calibration.
- Existing AAOIFI-only citations and the absent named-market runtime path need the market-data, source-link and dated-version additions described in [the crawl plan](progressive-buyer-journey-crawl-plan.md).

## Minimum live evaluation before showing the POC

Freeze cases across both query lanes and general definitions: complete and incomplete iPhone-style stories, one-fact counterfactuals, unknown financier, unknown late fee, contradictory totals, named-company alias/wrong company, stale or conflicting public pages, inaccessible agreement, unsupported or injected source text, Arabic, English, code-mixed phrasing, and multi-turn corrections. Verify the full deployed answer path, not only mocked retrieval and generation. Measure unsupported claims, wrong permissibility conclusions, correct abstention/clarification, one-question quality, source support, and answer coverage. The qualified scholar adjudicates material rule cases and the acceptable operating risk before a numeric threshold is enabled.
