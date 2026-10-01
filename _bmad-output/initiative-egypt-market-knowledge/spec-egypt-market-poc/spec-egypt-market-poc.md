---
id: SPEC-egypt-market-poc
companions:
  - architecture.md
  - fact-and-evidence-model.md
  - mechanism-archetypes.md
  - rule-card-schema.md
  - release-ladder.md
  - brownfield.md
  - ../../../.planning/sharia-compliance-chatbot/docs/l6-egypt-institution-scrape/dual-query-poc-answer-gates.md
  - ../../../.planning/sharia-compliance-chatbot/docs/l6-egypt-institution-scrape/progressive-buyer-journey-crawl-plan.md
  - ../../../project-context.md
sources:
  - ../../../.planning/sharia-compliance-chatbot/next-level-plans/L6-MARKET-KNOWLEDGE-AND-POC-RELEASE-STRATEGY.md
  - ../../../.planning/sharia-compliance-chatbot/docs/client-egypt-market-ai-strategy-legacy.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Egypt Market Knowledge: Dual-Lane POC (V1.6) and Release Ladder to V2.0

## Why

This spec covers an opportunity with a trust mandate attached. Egyptian buyers and the client's compliance reviewers need to know whether an instalment or other non-cash financing offer raises a Sharia issue. They ask either about a named company or seller, or about their own deal. Mushir (V1.5) holds AAOIFI evidence and a scraped Egyptian market map: 38 FRA consumer-finance licensees, 69 bank operations, and 86 market entities, 30 of them with page evidence. The runtime can't answer either question safely. It maps generic instalment wording to Islamic contracts, derives "confidence" from retrieval scores, and returns permissibility on unobserved conditions. Real per-customer agreements are private. However, consumer-finance deals are standard-form: FRA issues the form under Law 18/2020, and a public template is paired with a per-customer schedule. The missing contract is therefore mostly a question to ask, not data to infer. The client provides a qualified scholar. Versions ship publicly on Hugging Face until launch.

## Capabilities

V1.6 (POC scope):

- **CAP-1**
  - **intent:** A user can ask about a named company, seller or offer and receive its resolved entity, product and financier roles plus dated public terms, with every unobserved field marked unknown with a reason.
  - **success:** For each pilot entity, every factual claim in the answer cites an exact source span and capture date; alias and wrong-company cases resolve correctly or ask; no clause is reported absent by inference.
- **CAP-2**
  - **intent:** A user can describe their own financing operation across turns, with or without a known company, and have its facts captured as typed slots with provenance status.
  - **success:** On frozen cases (including the iPhone deposit + 12 × EGP 3,000 story), slots match the expected record; contradictions are flagged; follow-up text never overwrites a slot without reconciliation.
- **CAP-3**
  - **intent:** The system decides ANSWER, CLARIFICATION_NEEDED or INSUFFICIENT_DATA per the dual-query gates, asking exactly one highest-impact question when a user-answerable fact is missing.
  - **success:** For the iPhone story, the first reply has no verdict and asks who provides the plan; when the turn limit is exhausted with a material fact missing, the result is INSUFFICIENT_DATA naming the needed document.
- **CAP-4**
  - **intent:** A Sharia conclusion is given only from an approved rule whose every material condition is observed or user-reported.
  - **success:** Tests prove an unknown or contradicted condition never yields a permissibility result; scholar review of the frozen pilot set finds zero wrong verdicts.
- **CAP-5**
  - **intent:** Answers show evidence-status labels and source dates instead of a numeric confidence.
  - **success:** No answer surface displays a percentage; every answer states its evidence status and source age.
- **CAP-6**
  - **intent:** Five permitted pilot entities have dossiers covering entity resolution, access decision, link graph, captures and field observations (BJ-00..02, BJ-04).
  - **success:** Each dossier has an entity record, access decision with reason, capture manifest (URL, time, hash, content type, language), field observations with spans, and the first gated step recorded.
- **CAP-7**
  - **intent:** Pilot cases and every judgment answer are logged with fact record, gate decisions and cited answer for bilingual scholar adjudication, feeding a versioned frozen set kept apart from training data.
  - **success:** About 100 frozen cases across both lanes and definitions are exported bilingually; scholar decisions import with reviewer, date and rule/corpus version; the frozen set is immutable per version.
- **CAP-8**
  - **intent:** V1.6 runs publicly on the Hugging Face Space.
  - **success:** `/ready` is healthy; live smoke passes for English, Arabic, unanswerable, one named-offer and one described-operation case.

Later versions (see `release-ladder.md`):

- **CAP-9** (V1.7)
  - **intent:** Client Sharia rule files become versioned rule cards with scholar sign-off and a documented precedence against AAOIFI/IIFA.
  - **success:** A card without an approved decision cannot support a runtime verdict (test); every card in runtime use is approved.
- **CAP-10** (V1.7)
  - **intent:** A user can share a screenshot of their instalment schedule to supply schedule facts, processed with redaction and without retention unless they opt in.
  - **success:** Extraction accuracy is reported on labeled schedules; tests prove nothing is persisted without opt-in.
- **CAP-11** (V1.7)
  - **intent:** The scholar reviews one-clause counterfactual contract pairs generated from real templates.
  - **success:** Synthetic material is never retrievable in the named-company lane (test); pair decisions land as rule evidence.
- **CAP-12** (V1.8)
  - **intent:** All 38 FRA consumer-finance licensees are covered at template level, merchants link to financiers, and Arabic, PDF and rendered pages are captured with per-field freshness.
  - **success:** 38 licensee dossiers exist; conflict and staleness markers pass tests; access gaps stay explicit.
- **CAP-13** (V1.9)
  - **intent:** A supervised archetype prior orders clarification questions and chooses documents to request.
  - **success:** Calibration on entity-grouped held-out data is reported; a test proves the prior never changes a decision or fills a slot.
- **CAP-14** (V1.9)
  - **intent:** A behavior fine-tune (extraction, next question, abstention, explanation) is evaluated against the prompted baseline.
  - **success:** A comparison report on the frozen set; adoption only if it beats the baseline.
- **CAP-15** (V2.0)
  - **intent:** Selective answering runs at the scholar-set risk threshold, with a refresh loop, feedback-to-gold workflow and controlled beta.
  - **success:** Risk measured on held-out reviewed cases meets the scholar threshold; the release checklist and scholar sign-off are complete.

## Constraints

- Model weights never hold company facts or verdict authority; facts live in the evidence store, judgment in scholar-approved rules.
- Generic instalment, BNPL, تقسيط or تمويل wording never establishes a contract mechanism or archetype.
- No named-company Sharia verdict without matching seller, financier, product and version evidence plus an approved rule.
- Company evidence and user-supplied facts are separate inputs; neither fills the other's gaps; a missing clause is unknown, never absent.
- No bypass of robots, site terms, login, CAPTCHA or security controls; stop before registration, OTP, credit inquiry, agreement acceptance, card entry or payment; B.TECH automation requires permission.
- Synthetic counterfactual material never enters named-company evidence or retrieval.
- A provider's Sharia self-label is stored as a claim, never as a finding; Mushir never issues fatwas.
- Frozen evaluation data never trains a model; splits are grouped by entity.
- User-supplied documents are redacted before reading, ephemeral by default, retained only on opt-in, and handled under Egypt's PDPL (Law 151/2020).
- A partial or failed recrawl never erases or silently supersedes older evidence; the current view is the latest valid observation per field.

## Non-goals

- Full census of Egyptian merchants, or sales/traffic rankings presented as market share.
- Automated checkout navigation or private agreement intake in V1.6.
- Archetype prior, fine-tuning and numeric confidence in V1.6.
- Automated crawling of B.TECH, Amazon or noon without permission.
- Binding rulings, legal advice or investment advice.

## Success signal

On the live V1.6 Space, a question about a pilot company returns dated, cited public terms and asks for the missing personal schedule. The iPhone story gets exactly one financier question and no verdict. Scholar review of the ~100-case frozen pilot set finds zero wrong verdicts.

## Assumptions

- V1.6 keeps the OpenRouter API LLM and the Chroma AAOIFI index; the dossier store is SQLite shipped in the Space image.
- Pilot entities are the crawl-plan shortlist (Contact, Souhoola, RUSHBRUSH, IKEA Egypt or Smart Furniture, one direct retailer with a named financier) until O3 is answered.

## Open Questions

- O1: Do client rules or AAOIFI/IIFA take precedence on conflict, or does every conflict go to the scholar?
- O2: Does the scholar approve staff donating their own agreements from real purchases?
- O3: What are the final five pilot entities, and should one be a bank Islamic Murabaha product?
- O4: Is the primary V1.6 user a retail buyer or the client's compliance team?
- O5: What wrong-verdict rate is acceptable for launch?
- O6: Where are donated documents hosted after the POC, and for how long?
- Which scholar-approved rule source backs V1.6 verdicts before the client rule files (V1.7)? The default until answered: rules approved during pilot review only, otherwise INSUFFICIENT_DATA.
- Is legal review of named-company outputs (defamation exposure) required before the public Space shows company-level conclusions?
