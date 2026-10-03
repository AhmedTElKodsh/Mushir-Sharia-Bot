# Scraping and acquisition double review

Prepared 2026-10-02 for the stated research scope: published company identities and corporate contact channels, standard blank customer agreements and schedules, and the roles of sellers, financiers, suppliers and platforms. Personal/customer records and security testing are outside that scope.

**User clarification applied:** the research concern is whether a company acts as vendor and financier in the selected transaction, or acts as financier for purchases from other vendors; the nonpersonal mechanics of its loans/instalments; and the standard contract templates and schedules customers sign. The eventual purpose is human-scholar assessment against applicable AAOIFI standards and Sharia requirements. Corporate contacts are acquisition aids. Cybersecurity assessment is not a deliverable, and the earlier stated intention to report security gaps is not a basis for acquisition authority.

The unit of analysis is a specific financial arrangement, with its legal parties, product, channel, period and document version. The same company can support both routes. Evidence acquisition, factual relationship verification and scholar-approved interpretation remain separate stages. The applicable AAOIFI standard and version, material requirements, clause mapping and final assessment are recorded with human-scholar involvement; absent contractual facts remain unknown.

## Assessment

The operating playbook supports useful public research and source-authorized alternatives. Its implemented collector is a capture foundation, not a general firewall bypass or a complete contract-discovery system. It has substantial tested controls, but the reviews reproduced an access-stop defect and a false completion outcome. Legacy acquisition entry points have different controls. The role summarizer also cannot establish contractual finance relationships from name matches.

An unbiased assessment cannot accept either blanket proposition: that all scraping is unauthorized, or that nonprofit research and a future disclosure intention authorize every access route. Source policy, actual access authority, document applicability and permitted reuse must be assessed separately. This report does not establish that any historical acquisition was unlawful or that a provider has a cybersecurity vulnerability.

## Review method and evidence

Two reviewers worked independently before seeing one another's findings: BMad edge-case-hunter and verification-gap. The primary reviewer separately checked the legal/standards sources, operational documents and seller/financier evidence model. Findings from both lenses remain separately identifiable in the accompanying JSON, including overlap. No severity labels or forced finding counts are used.

The staged scope included the operative playbook, public-acquisition implementation spec, `public_capture.py`, identity capture CLI, legacy FRA and market collectors, and `CrawlerEngine`. Reviewers checked original source files and relevant tests. The primary reviewer additionally inspected the market relationship summarizer and its nine tests.

Fresh command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_public_capture.py tests/test_fra_registry.py tests/test_egypt_installment_market.py tests/test_summarize_market_roles.py -q
```

Result: **185 passed in 7.71 seconds**. Additional local deterministic reproductions used fake transports, DNS, clocks and sleeps. No acquisition collector contacted a provider during these checks. Web browsing was used for legal, standards, site-terms and vendor documentation verification; those results do not establish newly acquired provider contracts.

The primary reviewer independently re-executed the two public-capture reproductions after the verification review returned:

| Fixture | Observed result |
|---|---|
| 401 with unsupported `br` encoding, then another approved URL on the same host | First state `unsupported_content_encoding`; paused map empty; second state `captured`; transport requested both content URLs. |
| 403 with unsupported `br` encoding, then another approved URL on the same host | Same result as the 401 case. |
| Empty terms application root with ordinary navigation, footer and `renderTerms()` script | `state=captured`, `acquisition_complete=true`; extracted text contains only navigation and copyright. |
| Negated valU relationship | `_established_financiers` retains `valU` and reports the alias match despite the negative statement. |

Reviewed repository HEAD: `dfadd5df3afc387c47cb36da375153553d59204f`. The workspace also contains unrelated uncommitted work. Reviewed acquisition code was not modified.

SHA-256 snapshot:

| File | SHA-256 |
|---|---|
| `src/acquisition/public_capture.py` | `A06FA3F73D4222AF2F545616EA7A5AAC460EAEAEA3372FC342C4AF1A0287AD91` |
| `tests/test_public_capture.py` | `E2DD2EF963A0EF80CFE61F571A281AA39922B4CF6618A304F700B95FD421BDCD` |
| `src/acquisition/egypt_financial/fra_registry.py` | `E2A0CD305A67DC643A7D5AD7E275F43EAD33A6D6AE68FA130ACE5B7A63B1A4C3` |
| `src/acquisition/egypt_financial/crawler.py` | `933B2BD7B560565C22765CDD70C96766E94E0FEC11A2ACE9A87644D12D12E375` |

## Findings and corrective requirements

### Known refusal can lose its host stop

`src/acquisition/public_capture.py:592` decodes a response before `:602` classifies its status and pauses the hostname. A fixture HTTP 403 with unsupported `Content-Encoding: br` produced `unsupported_content_encoding`, left the paused-host map empty, and allowed a subsequent URL on the same host to be requested. The verification reviewer also reproduced HTTP 401. Both independent lenses found this overlap.

Correction: apply status-based security/authentication/rate handling before decoding and preserve decoding failure as a separate diagnostic. Verification must combine refusal status with encoding failure and assert that the next same-host capture sends no request. The observed behavior concerns continuing a batch after a known refusal; it is not proof of gaining access to protected data.

### A document shell can be reported as fully captured

`src/acquisition/public_capture.py:745` accepts HTML based on extracted text length. Ordinary navigation/footer text can exceed the 20-character threshold while the terms application root remains empty. The verification reviewer reproduced `state=captured` and `acquisition_complete=true` for that case. `applicability=unreviewed` still limits interpretation, but does not identify the missing rendering step.

Correction: make document-content sufficiency explicit, account for navigation/footer-only pages and route incomplete rendering to a partial/render-needed outcome. This should not assert automatic understanding of contractual completeness.

### Legacy robots acknowledgement is broader than the operative policy

`src/acquisition/egypt_financial/fra_registry.py:710` collapses HTTP errors, network errors and security-block HTML into `unavailable`. `:423` then permits this state when the broad boolean acknowledgement is set. A local operator acknowledgement therefore cannot distinguish an ordinary missing file from a security refusal or unreachable policy in this path.

Correction: use distinct policy states and the current scoped decision model, or explicitly withdraw this entry point from the operative acquisition workflow. This older collector was deliberately excluded from the 2026-10-01 foundation build; its remaining behavior is not proof that that build changed it incorrectly. Historical captures and prior decisions must remain intact.

### Same-origin is insufficient redirect authorization

`src/acquisition/egypt_financial/fra_registry.py:682` checks only origin before following redirects. A reviewed starting URL can redirect to another path on the same host without the target path's robots/access decision being checked in this transport. Correcting cross-host redirects alone does not close that path.

Correction: perform target-specific policy and scope checks before every outgoing redirect request; record the complete URL chain. Do not equate shared origin with shared access scope.

### CrawlerEngine has a separate, weaker collection path

`src/acquisition/egypt_financial/crawler.py:25` uses verified website discovery as its eligibility condition. Its `:68` fetch helper enforces public-address/redirect safety through `fetch_public`, but does not consume the new terms/access/robots decisions. Its artifact record labels a fetched homepage as a public product page, and its local filename can be overwritten on a subsequent run.

Correction: designate one operative public capture entry point and route any retained jobs through it. Preserve prior captures and actual document/access outcomes. Verified website identity establishes the destination, not the authority or document type. This is an existing alternate route, not an allegation that it was newly introduced by the foundation build.

### A named financier is not an established relationship

Primary-review observation: `scripts/summarize_egypt_installment_market.py:77` retains a seeded financier if an alias appears in the passage. A local call with `valU` and `We do not offer financing through valU.` returned the financier as retained. `:255` counts retained names as established financing links. The inspected tests cover positive names, absence, Arabic variants and boundaries, but not a negated relationship. The summarizer's scope note already warns that page matches do not establish lender identity or contractual terms; that limitation needs to govern its relationship fields and counts too.

Correction: keep name mentions as candidates. Accept seller/financier relationships only from a positive, scoped observation naming the legal role, with a supporting span and analyst review. Negation, historical relationships, alternative products and everyday-word aliases remain explicit uncertainty. Do not fix this only by adding an English negation keyword.

### Additional independent edge-case findings

The full canonical JSON retains all **11 edge-case findings and two verification-gap findings**. The status/encoding refusal appears separately in both lenses because independent corroboration is useful. The primary role-summarizer observation above is additional supporting analysis, outside that lens count.

The edge reviewer also traced HTTP 429 decoding before Retry-After cooldown recording; legacy market capture without a terms/access decision; continuation on a host after 401/403; omission of Retry-After between seeded market URLs; and required-word matching that marks a negative financing statement as verified page evidence. These are source-traced findings. The explicit executed reproductions in the review-method section are distinguished from that tracing; no live-provider behavior is asserted.

Correction: classify status and persist host stop/cooldown before body decoding, enforce consistent recorded access scope across operative entry points, and keep matched passages as candidates until the actual financial claim and party roles have been verified. Older collectors were expressly excluded from the foundation build, so these findings identify remaining workflow boundaries rather than a newly introduced migration regression.

## Access and legal assumptions

[RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html) defines crawler policy, not access authorization. Its optional treatment of unavailable robots resources is not a legal permission grant. The project's stricter treatment of denials and missing-policy decisions should be described as project policy rather than an Egyptian statutory robots requirement.

The [FRA-hosted Law 175/2018](https://fra.gov.eg/wp-content/uploads/2025/01/%D9%82%D8%A7%D9%86%D9%88%D9%86-%D8%B1%D9%82%D9%85-175-%D9%84%D8%B3%D9%86%D8%A9-2018-%D8%A8%D8%AA%D8%A7%D8%B1%D9%8A%D8%AE-2018-08-14.pdf) addresses prohibited entry and exceeding granted access in articles 14–15. No blanket nonprofit or security-reporting exemption was established in this review. A case-specific Egyptian legal determination remains outside this technical review. The PDF text was available through browsing; a later page-image request returned an access rejection and was not retried.

[B.TECH's published terms](https://btech.com/en/terms-and-conditions) explicitly restrict scraping/data mining. This is evidence of that source's stated restriction, not a finding that every website has the same restriction or a court determination about enforceability. An independently legitimate document publisher can be assessed on its own terms.

[Cloudflare's WAF guidance](https://developers.cloudflare.com/waf/troubleshooting/faq/) supports resolving false positives through the owner, including trusted-IP allowances or rule adjustments. A narrow source-issued allowance, official export or blank-document pack can advance the research without a general exception to all controls.

The [PDPC's official indexed material](https://www.pdpc.gov.eg/) identifies Law 151/2020 and Regulations 816/2025. Direct portal content was unavailable during this check. This review makes no claim about a case-specific personal-data research exemption. The intended dataset should use corporate contact channels and blank standard documents, and handle any accidentally received personal or customer-specific material outside the public dataset.

## Evidence needed for the requested market distinctions

Classify an arrangement and its period/channel, not a brand for all time. Record the legal seller, legal financier/creditor, supplier, platform/operator, customer agreement, debt/receivable holder, assignment if relevant, repayment recipient and regulator activity separately.

| Proposed classification | Evidence required before acceptance |
|---|---|
| Seller finances its own sale | Applicable sale/instalment clauses identify the same legal entity as seller and creditor; later assignment is checked separately. |
| Retailer and affiliated financier | Separate legal entities appear in the sale and finance instruments; group relationship has its own evidence. |
| Independent financier funds merchant purchases | Applicable agreement and merchant/channel evidence name the financier and seller separately. |
| Platform/agent arranges another provider's finance | Disclosures and contract identify the intermediary and actual creditor; a payment logo is only a lead. |
| Bank/card instalment route | Applicable bank/card programme terms and selected merchant/channel establish that specific route. |
| Mixed or unresolved | Separate evidenced arrangements, or preserve unknown fields; do not force a company-wide binary label. |

For financial mechanisms, retain the actual obligation structure: cash loan versus purchase financing, cash price, principal, total payable, mandatory fees, payment dates, late/default terms, early settlement, ownership/delivery and applicable annexes. A marketing term such as loan, instalment or BNPL does not supply an absent clause or determine a Sharia verdict.

## Operational follow-through

The concrete repair work is to close the status/encoding stop, correct shell completion, isolate or align older entry points, and prevent name mentions from becoming relationship claims. The acquisition task then closes only when a current applicable blank agreement and schedules support the material fields, or records exactly which fields remain unavailable.

Public capture, source-supplied documents, manual public-page review and supervised source research remain the four recorded routes. For app-only documents, seek a source-issued blank pack or approved demonstration. Record issuer, exact scope, dates, limits and reuse conditions for any source permission. The collector validates the supplied record; it does not authenticate the issuer or determine legal authority.

Cybersecurity investigation and vulnerability reporting are outside the clarified research objective. A readable public company page, a missing robots file or a WAF false positive does not establish a security gap or contribute contractual proof. No company was contacted during this review.

The five-provider gap board and request packages remain useful preparation. The reviewed files do not establish dispatched letters, new source permissions, complete operative contracts, legal clearance or scholar approval. This review adds findings; it does not change those acceptance states.
