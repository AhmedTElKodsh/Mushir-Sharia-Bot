# L6 Market Knowledge Strategy and POC Release Ladder

**Drafted:** 2026-09-29, after a BMAD party-mode strategy roundtable
**Status:** proposed; open decisions listed at the end must be answered before V1.6 build starts
**Builds on:**
[L6 evidence corpus plan](L6-EGYPT-FINANCIAL-INSTITUTIONS-EVIDENCE-CORPUS-PLAN.md),
[L6 rules-first evaluator plan](L6-RULES-FIRST-SHARIA-COMMERCIAL-EVALUATOR-PLAN.md),
[progressive buyer-journey crawl plan](../docs/l6-egypt-institution-scrape/progressive-buyer-journey-crawl-plan.md),
[dual-query POC answer gates](../docs/l6-egypt-institution-scrape/dual-query-poc-answer-gates.md)
**Client-facing version:** [client-egypt-market-ai-strategy.md](../docs/client-egypt-market-ai-strategy.md)

## Objective

Build a governed knowledge base of Egyptian entities that offer any financial
operation other than an ordinary cash spot sale, with consumer instalments
first. Combine it with the client's Sharia rule files, including their rules on
acceptable and unacceptable riba. Use the result to answer two kinds of
question:

1. **By operation:** "I bought X with a down payment and 12 instalments of Y. Is it permissible?"
2. **By company or seller:** "What are Contact's / valU's / this shop's instalment terms, and do they raise a Sharia issue?"

Answers must be highly reliable. A qualified scholar, provided by the client,
reviews pilot and evaluation cases, and versions are released publicly on
Hugging Face one at a time until the product is ready for launch.

## Evidence baseline on 2026-09-29

| Layer | What exists | Coverage meaning |
| --- | --- | --- |
| Regulator registry | 2,154 baseline institutions (36 banks, 797 capital-market, 996 insurance, 325 non-bank); FRA financing register 328 companies, 38 licensed consumer-finance (2026-09-23) | Near-census of **regulated financiers** |
| Bank operations | 14 of 32 bank sites scraped, 73 pages, 69 operation records with machine-proposed AAOIFI mappings | Review input only |
| Instalment market map (2026-09-27) | 85 claims, 52 page matches, 86 entities, 30 with page evidence, 39 lead-only | Purposive sample; gaps at Amazon (robots), noon (robots unavailable), B.TECH (terms forbid scraping) |
| Sharia sources | AAOIFI SS-01..54 and SS-60 machine-extracted (EN); SS-55..59 missing; `hard_sharia_ready: false` | Not answer-admissible for hard Sharia yet |
| Scholar-reviewed gold | 10 hard-case seeds, all `pending` | No gold set exists yet |

Two findings change the strategy:

- **Contact's consumer-finance appendix** ([PDF](https://contact.eg/terms-and-conditions-en.pdf)) says each transaction's price, total instalments, period and return rate appear in a *separate supplementary statement*. The public document is the contract template; the numbers live in a per-customer schedule.
- **Law 18 of 2020** requires consumer-finance providers to use a standard contract form issued by FRA. The **FRA consumer-finance rulebook published 2026-09-06** adds disclosure rules for terms, schedules, costs and fees. It also makes death and permanent-disability insurance mandatory up to age 65, and it bans blank documents and trust receipts as collateral. Every FRA consumer-finance deal therefore carries an insurance leg that needs its own Sharia question (conventional insurance vs takaful).

## Decisions

### D1. The model's weights are not the database

"Training the AI" is split across three layers. Each layer improves through its
own mechanism:

| Layer | Holds | Improves through | Never |
| --- | --- | --- | --- |
| **Evidence store** | Entities, products, mechanisms, dated field observations, source spans | Crawling, document intake, analyst verification | Fine-tuned into weights |
| **Rule cards** | Client Sharia rules plus AAOIFI/IIFA references, compiled into conditions and outcomes | Scholar sign-off per card | Averaged or blended by the model |
| **Model behavior** | Fact extraction, next-question choice, abstention, plain-language explanation | Prompting first; SFT/DPO on scholar-accepted transcripts later | Used as the source of a company fact or a verdict |

Company terms change; fine-tuned facts cannot be cited, versioned or retracted.
All answer authority stays in the evidence store and rule cards.

### D2. The unit of analysis is the financing mechanism, not the merchant

A merchant's Sharia answer usually reduces to "who finances this, under which
contract?" The knowledge base is tiered:

| Tier | Population | Target coverage |
| --- | --- | --- |
| A. Regulated financiers | FRA consumer-finance and other financing licensees, CBE banks (Islamic windows flagged) | Full census from registers |
| B. Financing products | Concrete product per financier (e.g. a 0% subsidised plan vs a 24-month plan with a return rate) | Template-level dossier per product |
| C. Merchants and channels | Stores, marketplaces, brand sites that show instalment options | Link graph to Tier B; **not** a census |
| D. Seller own-plans | Developers, furniture/jewellery shops, schools, clinics offering direct deferred payment | Own dossier per seller; long tail, prioritised by exposure |

Tier D cannot be collapsed into financiers. It is direct seller credit and needs
separate evidence.

### D3. Mechanism archetypes (draft taxonomy, for analyst and scholar review)

| Code | Mechanism (descriptive only, no Sharia label) |
| --- | --- |
| ARC-CF | FRA consumer-finance company pays the merchant; the buyer repays the company with a disclosed return |
| ARC-BANK-LOAN | Bank personal loan or card instalment conversion |
| ARC-BANK-ISL | Bank Islamic window or Islamic bank sale-based product (e.g. Murabaha) |
| ARC-SUBSIDISED | 0% plan in which the merchant bears the financing cost |
| ARC-SELLER | Seller's own deferred-price instalment sale |
| ARC-DEV | Property developer payment plan, often before delivery |
| ARC-LEASE | Lease-to-own structure |
| ARC-BNPL | Short-tenor split payment |

A product's archetype is `unknown` until a template or disclosure establishes
it. Generic words (`instalment`, `تقسيط`, `تمويل`, `BNPL`) never establish an
archetype.

### D4. Template + schedule decomposition solves most of the "missing contract" problem

Consumer-finance agreements are standard-form contracts:

- **Template** (public or requestable): ownership and possession sequence, late-payment treatment and beneficiary, early settlement, insurance leg, default and collection. Most Sharia-material clauses live here.
- **Schedule** (per customer): price, down payment, tenor, instalment amount, return rate, fees, sometimes the late-fee amount and insurance premium. The buyer can usually see it in the provider's app or on the receipt.

Answer policy: the template tells Mushir **what to ask**; the schedule and the
user's answers establish **what is true** for that customer. Material facts that
live only in the schedule must be requested from the user, never inferred.
Template version drift is tracked. When the template version the user signed
cannot be matched, the answer says so.

Evidence classes (extends the crawl plan's list):
`marketing`, `faq`, `provider_standard_terms`, `regulator_model`,
`transaction_specific_disclosure`, `user_supplied_schedule`,
`donated_agreement`, and `synthetic_counterfactual`. The last one is **never
observed evidence**.

### D5. Supervised archetype prior: predicts the type, never the verdict

The answer to "can we train the model to expect agreements from scraped company
info?" is **yes, in this bounded form**:

- **Task:** classify a financing product into a probability distribution over D3 archetypes.
- **Features already scraped or scrapable:** FRA licence type; bank vs non-bank; Islamic window flag; vocabulary on product pages (`عائد`, `فائدة`, `ربح`, `مرابحة`, `مصاريف إدارية`, `بدون فوائد`, `0%`); named lender on the page; seller-own-plan wording; down-payment and tenor phrasing; presence of an insurance clause.
- **Labels:** products whose full template has been observed, labeled by an analyst and confirmed by the scholar.
- **Evaluation:** hold out by **entity group** (e.g. `GroupKFold(groups=entity_id)`), because rows from one provider share wording and a row-level split inflates accuracy. Check calibration, not only accuracy.
- **Allowed use:** order clarification questions; choose which document to request; show a clearly labeled "typical for this provider type, not verified for your contract" note.
- **Forbidden use:** changing an `ANSWER`/`CLARIFICATION_NEEDED`/`INSUFFICIENT_DATA` decision, filling a material fact slot, or producing any verdict about a named company. A test must prove the prior cannot flip a verdict.

### D6. Contract acquisition channels, in priority order

| # | Channel | Legal / ethical gate | Feeds |
| --- | --- | --- | --- |
| 1 | Public provider standard terms and FRA standard form | Robots, site terms, no login bypass | Evidence store, archetype labels |
| 2 | Direct request to providers (standard contracts; Islamic providers have a marketing incentive) | Written permission recorded | Evidence store |
| 3 | User schedule screenshot at query time | Redact on the device; delete after extraction; opt-in donation only; comply with Egypt's Personal Data Protection Law (Law 151 of 2020) | Per-answer facts; donated set |
| 4 | Client staff donate their own agreements from real small purchases ("mystery shopper") | **Scholar must approve** entering such contracts for study; staff's own documents and consent | Ground-truth templates and schedules |
| 5 | Synthetic counterfactual twins (one-clause variations of a real template) | Stored separately and marked synthetic; never retrievable in the named-company lane | Scholar pair-review, evaluation, extractor training only |

### D7. Client Sharia rule files become versioned rule cards

Each uploaded rule is compiled into a card:

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
precedence_note: "<how this card relates to AAOIFI SS-8 / SS-3 / IIFA>"
scholar_signoff: {reviewer_id: null, date: null, decision: pending}
status: draft
```

The outcomes shown are placeholders illustrating the structure, not rulings.
A card with `decision != approved` cannot support a runtime verdict. **The
precedence between client rules and AAOIFI/IIFA must be decided before the
first card compiles** (open decision O1). A provider's self-description as
Sharia-compliant is stored as a `provider_claim` field, never as a finding.

### D8. Scholar time: review the rules, sample the answers

The scholar's review time is the scarcest input. Spend it where one decision
covers many cases:

1. Approve rule cards and the archetype taxonomy. One sign-off covers every case routed to that card.
2. Judge counterfactual twin pairs. This shows exactly where each rule's line falls.
3. Audit a stratified sample of answers (by lane, archetype, language, outcome), plus **every** case where the system issued a verdict.
4. Adjudicate conflicts and set the acceptable operating risk (D9).

### D9. "High certainty" means low risk on the answers Mushir gives

- **Primary metric:** wrong-verdict rate among answered judgment cases, on a frozen, scholar-reviewed set. The scholar sets the acceptable rate.
- **Secondary:** coverage, unsupported-claim rate, correct abstention, one-question quality, source support.
- No numeric confidence is displayed until the risk threshold has been calibrated on held-out reviewed cases. The current `confidence` in `src/chatbot/application_service.py` comes from retrieval scores and must be replaced by evidence-status labels.

### D10. Fine-tuning scope and timing

- **Not before V1.9.** Earlier versions use an API model with prompts, rule cards and deterministic gates.
- **Targets:** typed fact extraction from Egyptian Arabic and schedule text; next-question selection; abstention and explanation style.
- **Data:** scholar-accepted transcripts (SFT) and scholar preference pairs (DPO). Training and frozen evaluation sets never overlap, and they are split by entity group.
- **Candidate spike:** a small open-weight Arabic-capable model with a LoRA adapter for extraction, hosted on Hugging Face. It is adopted only if it beats the prompted API baseline on the frozen set.

## Release ladder (Hugging Face Space, building on V1.5)

| Version | Adds | Exit gate |
| --- | --- | --- |
| **V1.6: Dual-lane POC** | Five pilot dossiers (BJ-00..02, BJ-04); user-described lane with typed slots; one-question clarification; deterministic abstention; evidence-status labels, no % shown | ~100 scholar-reviewed pilot cases; zero wrong verdicts on the frozen pilot set; V1.6 blockers closed |
| **V1.7: Rules and schedules** | Rule cards v1 from client files; template/schedule split; schedule-screenshot intake (ephemeral); counterfactual twin review | Every runtime card approved; schedule extraction accuracy measured |
| **V1.8: Financier coverage** | All 38 FRA consumer-finance licensees at template level; merchant→financier graph; Arabic seed terms; PDF and rendered-page capture; per-field freshness | Conflict and staleness markers tested; access gaps explicit |
| **V1.9: Learned behavior** | Archetype prior (question ordering only); behavior fine-tune spike | Calibrated on held-out entities; tests prove the prior never changes a verdict |
| **V2.0: Launch candidate** | Scholar-set risk threshold; refresh loop; feedback→gold workflow; controlled beta | Release checklist and scholar sign-off |

Deployment note: for V1.6 the dossier store ships as SQLite inside the Space image.
Chroma remains the AAOIFI text index. Use `--skip-index` deploys when retrieval
data is unchanged.

## V1.6 blockers (from the dual-query gate spec)

- `src/chatbot/contract_classifier.py`, `src/chatbot/commercial_assessment.py`, `src/chatbot/prompt_builder.py`: stop mapping generic instalment/finance wording to Islamic contract families.
- `src/chatbot/commercial_assessment.py`: replace whole-query storage with typed slots (seller, financier, deposit, schedule, fees, late clause).
- `src/chatbot/clarification_engine.py`: rule-specific sufficiency; turn-limit exhaustion ends at `INSUFFICIENT_DATA`, never "ready".
- `src/ontology/ruling_evaluator.py`: three-state conditions (satisfied / violated / unknown); no permissibility from unobserved conditions.
- `src/chatbot/application_service.py`: replace retrieval-score confidence with evidence-status labels.
- `scripts/summarize_egypt_installment_market.py`: stop carrying a seeded financier name into a relationship that the matched passage does not establish. Until fixed, rows are not training labels.

## Pilot entities (proposed)

From the crawl plan: Contact, Souhoola, RUSHBRUSH, IKEA Egypt or Smart
Furniture, and one direct retailer with a named financing partner. Roundtable
proposal: replace one of them with a bank Islamic Murabaha consumer product, so
the POC includes a case that can pass the checks as well as cases that raise
issues (open decision O3). B.TECH/Mylo and noon stay as studied buyer journeys
until permission exists.

## Risks

| Risk | Mitigation |
| --- | --- |
| Verdict about a named company from inferred or stale data (defamation and trust) | D5 forbidden-use test; dated source on every company claim; wording "based on published terms dated …" |
| Synthetic twins leaking into company evidence | Separate store, `synthetic_counterfactual` class, excluded from named-company retrieval |
| Template version drift | Per-field history; version shown; mismatch → clarification or insufficient data |
| Client rules conflicting with AAOIFI/IIFA | O1 precedence policy before compile; conflicts routed to scholar |
| Personal data in uploaded schedules | On-device redaction; ephemeral processing; opt-in donation; PDPL compliance review |
| Scholar bottleneck | D8 ordering; rules before answers |
| Access-restricted leaders (B.TECH, Amazon, noon) missing | Separate permission queue; never bypass controls |

## Open decisions

| ID | Decision | Owner |
| --- | --- | --- |
| O1 | Precedence between client rule files and AAOIFI/IIFA, or route every conflict to the scholar | Client + scholar |
| O2 | Approve or reject the staff own-agreement ("mystery shopper") channel | Scholar |
| O3 | Final five pilot entities, including whether one is a bank Islamic product | Ahmed + client |
| O4 | Primary V1.6 user: retail buyer, or the client's internal compliance team | Client |
| O5 | Acceptable wrong-verdict rate for launch | Scholar |
| O6 | Hosting of donated documents after POC (private store and retention period) | Client |

## Immediate next steps

1. Get answers to O1, O3 and O4, and request the client's Sharia rule files.
2. Close the V1.6 blockers, test-first, including English, Arabic and code-mixed cases.
3. Run BJ-00..02 and BJ-04 for the five pilot entities; capture the Contact appendix, the FRA standard form and provider terms PDFs.
4. Draft the fact-slot schema and D3 taxonomy for analyst and scholar review.
5. Compile the first rule-card drafts once the rule files arrive.
6. Build the ~100-case frozen pilot set across both lanes and send it for scholar review.
7. Deploy V1.6 to the Hugging Face Space and run the post-deploy smoke checks.

## Sources

- [FRA consumer-finance rulebook coverage, Amwal Al Ghad, 2026-09-06](https://en.amwalalghad.com/egypts-regulator-issues-first-comprehensive-consumer-finance-rulebook/)
- [Law No. 18 of 2020, Andersen translation](https://eg.andersen.com/translation-of-law-18-of-2020/)
- [The New Egyptian Consumer Financing Law, Lexology](https://www.lexology.com/library/detail.aspx?g=efd222a5-34ab-4c28-b39d-f0d2b779d202)
- [Contact consumer-finance terms appendix](https://contact.eg/terms-and-conditions-en.pdf)
