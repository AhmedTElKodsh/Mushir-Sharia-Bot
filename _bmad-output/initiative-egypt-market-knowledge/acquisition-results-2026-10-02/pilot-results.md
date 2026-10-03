# Five-provider public financing-evidence results — 2026-10-02

The reviewed plan is finalized and the bounded acquisition cycle has run. Two immutable PublicCollector v0.3 batches made 17 network requests, including robots checks, captured 11 artifacts and recorded two deliberately unpermitted automated sources. The first batch captured six of eight requested sources; the second captured five of five. These counts exclude ordinary browser/web research. No private/customer records, security tests or provider messages were involved.

## Verification and source pack

The final collector correction passes 196 focused tests in both the isolated worktree and primary workspace. The independent quick reviewer reproduced the remaining ARIA-navigation shell finding, checked its correction, and returned no remaining findings in this bounded diff. The earlier double review's other legacy-route findings remain open; those routes were excluded.

[Evidence register](evidence-register.json) contains 32 source-linked observations with exact extraction pointers, Unicode offsets, capture IDs and original/derived hashes, plus separately labelled manual observations. [Provenance verification](provenance-verification.json) independently recomputed all 45 distinct referenced raw/derived artifact hashes and byte counts; all 32 selected span checks passed. Two convenient PDF copies are byte-identical to their raw captures. [Inventory](capture-inventory.md) records every source outcome.

Raw manifests and summaries remain in `data/runtime/artifacts/l6_scrape/public_capture/pilot-20261002-reviewed-01` and `pilot-20261002-reviewed-02`. Replay the offline register builder at `acquisition-templates/pilot-2026-10-02/build_evidence_register.py` from the primary repository. It does not contact sources. Access reviews and exact decisions are stored beside that builder. Narrow public operator decisions are not source permission or legal clearance; their expiry does not erase historical research provenance or permit a later crawl without renewed review.

Two independent final consistency reviews found passage-coverage and review-chronology defects. Corrected passage coverage for 18 multi-fact entries, including the three specifically flagged; the builder checks contextual passages and required subfact terms rather than just short-anchor existence. These checks still do not replace human semantic review. The follow-up decision records accidentally copied the initial `reviewed_at` for newly added paths. A [dated audit correction](../acquisition-templates/pilot-2026-10-02/scope-extension-audit-correction.json) records that mistake and bounds the later review between the first batch, follow-up input creation and second batch; its exact instant is unknown. Original inputs/manifests remain preserved. Later scope changes must use fresh actual review timestamps.

Both reviewers independently checked their reported resolutions and closed the findings. The [final review disposition](final-review-disposition.json) records their bounded checks and practical limits.

## Provider findings and remaining contract coverage

| Provider | What this cycle established as a source observation | Contract and role boundary |
|---|---|---|
| Contact | Corporate email/hotline, published product categories, readable five-page English customer-terms appendix and separately captured Arabic two-page appendix. | Goods/services, post-purchase Fatorty and club finance are distinct arrangements. Main agreement and per-transaction schedules remain missing; seller/creditor legal identities and effective applicability remain unresolved. |
| Halan | Public own-shop and external-vendor financing descriptions; advertised BNPL tenor/limit, programme leads and corporate contact. | Multiple advertised channels; a shop branded Halan does not establish the same legal seller and creditor. Applicable blank credit agreement, fee/repayment annexes and title/risk chronology were not obtained. |
| Aman | Public online-store and merchant-network instalment descriptions; regular/Islamic variants, typical advertised tenor and corporate contact route/hotline. | Multiple advertised channels. The Islamic marketing claim is not a scholar-approved conclusion. Exact seller/financier parties and separate product agreements remain missing. |
| Souhoola | Ordinary browser rendering disclosed substantive February 2026 general terms, partner-merchant financing description, fee/default references and corporate email. | Automated source remains unknown/unpermitted. Terms name Contact Investment for Consumer Finance while the page title says CI Consumer Finance; equivalence/effective identity remains unresolved. Exact instalment agreement and charges are not supplied by this general page. |
| ValU | Brief manually reviewed terms observations distinguish a financier/operator lead and establish an automated-collection restriction. | No full copied contract artifact from this route. Applicable agreement cover, schedules and selected merchant/channel roles remain unresolved. |

### Contact: document observations, not a current-offer verdict

The [English appendix](documents/Contact-English-terms-appendix.pdf) names Contact Credit Tech, distinguishes a merchant, asserts company ownership until repayment and describes monthly dues, a late fine capped at 9% of unpaid instalments, security interests and settlement by reference to missing main-contract clauses. Fatorty concerns already purchased goods/services; its telecom variant describes wallet disbursement after fees. Club finance has separate conditions. Retain each provision's scope; do not apply one product's fee/tenor to all Contact offers. No publication/effective date or selected customer/channel applicability was established. [Published English source](https://contact.eg/terms-and-conditions-en.pdf)

The [Arabic appendix](documents/Contact-Arabic-terms-appendix.pdf) is visually legible on both pages, but extraction is punctuation/OTP rather than the Arabic clauses. Reject that extracted text despite `page_text` and an empty OCR-needed list. This is a new parser-quality issue for separate correction; it does not invalidate preserved original bytes. The Arabic and English appendices are not established as matching effective versions. Early-settlement wording differs visibly and needs bilingual human comparison; do not combine them as translations of a single operative contract. [Published Arabic source](https://contact.eg/wp-content/uploads/2020/11/Digital-Terms-and-Conditions-Form-03.pdf)

### Halan and Aman: answer the channel question without inventing parties

Halan advertises shop instalments over 6/12/36 months and a credit-limit application up to EGP 500,000. Its separate consumer-finance page describes an external-vendor network and advertises no administrative fees. Record that as published marketing; do not infer that no contractual charge exists. Corporate hotline 16303 is in the raw capture; Info@halan.com was observed after ordinary browser rendering of the obfuscated contact address. [Shop](https://halan.com/shop/), [consumer finance](https://halan.com/personal-lending/), [contact](https://halan.com/contact-us-2/)

Aman's instalment page explicitly lists its store, merchant network and branches, with typical 3–36 month plans depending on product. Its online-store FAQ describes variable interest and promotions. Treat the advertised Islamic limit as a separate document task requiring its own mechanism and agreement. Corporate hotline 19910 is observed; no corporate email was established from the inspected contact page. [Instalments](https://aman.eg/en/service/get-aman-installment-limit/), [store](https://aman.eg/en/service/shop-online/), [contact](https://aman.eg/en/contact-us/)

### Souhoola and ValU: preserve useful review while respecting source restrictions

Souhoola's general terms describe a financing facilitator for partner-merchant purchases. Actual interest/charges and late penalties are deferred to transaction/agreement disclosures. The page restricts reproduction; only minimal manually written observations and a short role excerpt were stored, with section references and no full source-copy claim. Corporate email help@souhoola.com and hotline 15227 were displayed. [Terms](https://souhoola.com/terms-conditions)

ValU's licence/use clauses restrict automated data gathering, so the collector recorded `terms_not_permitted` before any provider request. Its public agreement party/operator leads remain brief manually reviewed observations and require original Arabic verification and complete applicable schedules. [Terms](https://valugroup.com/terms-and-conditions)

## Next evidence closure tasks

1. Verify Contact's Arabic extraction, compare effective versions and obtain the main agreement with paragraphs 3/b–3/c and per-transaction annexes. Ask who is the legal seller, creditor, owner and risk bearer at each stage.
2. For Halan and Aman, obtain separate standard packs for the own-store and third-party-merchant channels. Obtain Aman's Islamic-product pack independently; no generic brand verdict is justified.
3. Resolve Souhoola's dated legal-name conflict with authoritative company/licence records and obtain the actual instalment agreement. For ValU, use an eligible source-delivered/licensed document route instead of the restricted crawler.
4. Have a second human reviewer check material source passages, especially Arabic names, rates, negations and ownership clauses. Then the human scholar can select relevant AAOIFI rules and evaluate sufficiently established arrangements.

These are remaining evidence tasks, not dispatched requests. This acquisition cycle is complete; complete five-provider agreement coverage, accepted contractual roles and scholar verdicts remain unestablished. The resulting dataset is a bounded pilot, not a representative Egyptian-market census.
