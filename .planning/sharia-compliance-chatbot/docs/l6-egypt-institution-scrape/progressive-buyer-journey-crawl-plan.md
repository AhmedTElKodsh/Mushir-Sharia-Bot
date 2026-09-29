# Progressive buyer-journey evidence acquisition

**Drafted:** 2026-09-29  
**Purpose:** Enrich the Egyptian instalment market map one company and one financing operation at a time. The first public POC needs a few well-evidenced journeys, not complete market coverage.

## Starting point and evidence boundary

The [existing market collector](../../../../scripts/scrape_egypt_installment_market.py) checks reviewed, single-page claims in static HTML. Its [2026-09-27 summary](../../../../data/runtime/artifacts/l6_scrape/installment_market/2026-09-27/summary/20260927T024008Z-faabcb/manifest.json) contains 85 claim checks, 52 page-text matches, 30 entities with page evidence, and 39 lead-only entities. Those matches do not establish a current checkout plan, a contract, or Sharia compliance. The current summarizer can carry a seeded financier name into a page-evidence relationship without independently proving that relationship in the matched passage. Do not use such rows as verified training labels.

The unit of enrichment is **entity × product or operation × seller × financier × sales channel × document version**, rather than a single company-level verdict. An observed public offer, provider standard terms, a regulator model contract, and a customer-specific supplementary statement are different evidence classes. A missing clause is `unknown`, never `absent` by inference.

## Prioritization without invented market ranks

Maintain separate queues for finance providers, marketplace domains, direct retailers, and services/property. Within a queue, consider:

| Factor | Proposed weight | Admissible evidence |
| --- | ---: | --- |
| Egyptian user exposure | 30% | Dated Egypt-specific site traffic, or comparable company-level financed transaction volume with the reporting entity and period named |
| Relevance of instalment terms | 25% | Material financing questions and operation types exposed to Egyptian buyers |
| Primary-document yield | 20% | Public FAQ, terms, agreement appendix, plan disclosure, or calculator |
| Relationship coverage | 15% | Evidenced links across sellers, financiers, products, and channels |
| Refresh feasibility | 10% | Stable sources that the project is permitted to access and revisit |

`unknown` reach stays unknown; it does not become a zero or an estimated transaction count. Compare like with like: website visits do not measure financing transactions, and a group revenue figure does not rank Egyptian instalment providers. The [August 2026 Similarweb Egypt shopping list](https://www.similarweb.com/top-websites/egypt/e-commerce-and-shopping/) can seed a high-reach marketplace queue, but it cannot rank financing use. Keep high-reach entities with access barriers in a separate queue rather than dropping them.

The first **evidence-yield pilot shortlist**, subject to each host's access review, is Contact, Souhoola, RUSHBRUSH, IKEA Egypt or Smart Furniture, and one additional direct retailer with a named financing partner. Study B.TECH/Mylo and noon as high-value buyer journeys; automated B.TECH crawling requires permission because its [platform terms](https://btech.com/en/terms-and-conditions) expressly forbid scraping and data mining. Existing Amazon and noon access gaps remain explicit. This shortlist is not a claim that these are the most visited or largest by financed volume.

Initial public scouting on 2026-09-29 found [Contact's consumer-finance agreement appendix](https://contact.eg/terms-and-conditions-en.pdf), which says each transaction's price, total instalments, period and return rate appear in a separate supplementary statement. [Noon's Egypt instalments FAQ](https://helpegypt.noon.com/portal/en/kb/articles/easy-installments-everything-you-need-to-know-6-3-2024) describes a checkout option and bank-dependent interest and fees. [B.TECH's mylo explainer](https://btech.com/en/mylo-explore) describes the buyer path, while its platform terms limit automation. These URLs are discovery findings, not completed automated dossiers or proof of a customer's agreed terms.

## Progressive tasks

Each task can close for one company while other companies remain shallow. Preserve all previous captures and gaps.

| ID | Task | Completion evidence | POC boundary |
| --- | --- | --- | --- |
| BJ-00 | Resolve legal entity, brand, official domain, product family, and a dated priority source. Review site terms and robots for each host. | Entity record, ranking evidence or `unknown`, access decision and reason. | Required for pilot entities. |
| BJ-01 | Discover official product, payment, FAQ, terms, fee, contract, and PDF links in Arabic and English. Record parent URL and link text. | Bounded link graph with reviewed official-domain starts, per-link decisions and stop reasons. | Required for pilot entities. |
| BJ-02 | Capture permitted public HTML and linked PDFs. Use separate HTML and PDF extraction, retaining page anchors. | Immutable raw artifact, final URL, content type, capture time, hash, language and extraction status. | Static pages and PDFs first. |
| BJ-03 | Follow the public buyer path where site policy permits: product → payment options → instalment-plan information available without identity or payment. | Ordered journey steps, visible terms, screenshots where needed, and the first gated step. | Add browser navigation after static pilot. |
| BJ-04 | Extract field observations and exact supporting passages. Link seller, channel and financier only where a source passage establishes their roles. | Append-only fact rows with source span, product scope, document class, review state and explicit missing fields. | Required for pilot answers. |
| BJ-05 | Review conflicts and material clauses. Let an analyst verify extraction and a qualified scholar approve rule application and conditional case answers. | Dated correction, reviewer, source/rule versions, and accepted or rejected case status. | Start with pilot cases; expand continuously. |
| BJ-06 | Refresh volatile offers, compare changed passages and preserve both last successful evidence and latest access attempt. | Per-field history, conflict alerts, source age and supersession status. | Basic recrawl after POC; continuous before broad release. |
| BJ-07 | Seek direct provider feeds or voluntarily supplied redacted transaction documents for terms hidden behind identity or credit checks. | Permission/consent record and private, versioned evidence packet. | Controlled beta and later. |

Start BJ-01 with reviewed URLs and a same-host depth of at most two, a small per-host page budget, and a delay. Do not follow a new host, a redirect, or a downloadable document until its access policy is checked. A browser is an extraction method for public rendered pages; it is not a way to bypass login, CAPTCHA, a robot restriction, or site terms. An anonymous cart step is eligible only after site-policy review. Stop before registration, OTP, credit inquiry, accepting a financing agreement, card entry, payment, or order submission. Record the gated boundary as a useful result.

## Company dossier output

Each completed increment produces a dated dossier with:

- Entity and aliases; official domain; seller, channel and financier roles with their own evidence.
- Product/operation identifier, offer period if actually published, and checkout context.
- Link graph and ordered public buyer journey; capture manifest with URL, timestamp, hash, content type, language and access status.
- Field observations for cash price, financed price, deposit, instalment amount/count, total payable, fees, late-payment terms, ownership, early settlement, cancellation/refund, insurance, and approval conditions. Every populated value has an exact source span or PDF page; unobserved fields have a reason such as `not_publicly_found`, `login_gated`, or `access_blocked`.
- Document scope: `marketing`, `faq`, `provider_standard_terms`, `regulator_model`, or `transaction_specific_disclosure`. Conflicting claims and older versions remain visible.
- Analyst verification and separate scholar review of rule mapping. No provider's self-description of Sharia compliance becomes Mushir's conclusion automatically.

Build the current company view from the latest valid observation **per field**, while also showing the most recent failed attempt and age of the successful source. The existing summary's latest-run-per-stage selection is insufficient for incremental dossiers: a partial or failed recrawl must not silently erase older evidence or make it appear current.

## POC cut line and next implementation slice

For the first Hugging Face POC, implement BJ-00 through BJ-02 and BJ-04 for three to five permitted, evidence-rich entities. Demonstrate a source-linked company lookup, public terms, buyer-path map, conflict or gap markers, and focused questions for transaction-specific missing terms. The same POC must also handle **user-described operations without a named company** by extracting facts supplied across turns and asking for the material missing detail before any unsupported Sharia conclusion. See the [dual-query answer and guardrail specification](dual-query-poc-answer-gates.md). A full market census, automated checkout navigation, or private agreement intake is not a POC prerequisite.

The next code slice is a **separate bounded `journey_discovery` pass** and append-only observation store. Retain the current one-page claim checker and immutable outputs. Add PDF handling before JavaScript navigation. Before any named-company Sharia answer, require matching seller/financier/product/version evidence and scholar-approved conditional rules; otherwise return the observed facts and the missing-document question.
