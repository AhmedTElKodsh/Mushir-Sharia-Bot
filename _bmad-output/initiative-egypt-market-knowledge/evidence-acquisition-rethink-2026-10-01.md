# Evidence acquisition rethink: a research plan for accurate Egyptian financing data

Prepared 2026-10-01. Status: **proposed operating procedure**, supported by a document review and current technical/legal source checks. This document does not establish new provider permission, completed acquisitions, deployed collectors, or legal clearance. The [preserved original](evidence-acquisition-playbook-reviewed-baseline-2026-10-01.md) remains the reviewed baseline; full findings are in [the review](evidence-acquisition-review-2026-10-01.md).


Follow-up: this historical proposal was adopted into the [operative playbook](evidence-acquisition-playbook.md), with the public capture foundation implemented on 2026-10-01. Other channels remain governed by that playbook's implementation status. This proposal does not establish live provider permission or completed contract dossiers.

## 1. Acquire the missing fact, then choose the transport

The existing playbook is a useful source inventory. Its next version should become a procedure for closing specific evidence gaps. A firewall is a transport problem; a missing fee schedule is an evidence problem. Opening more pages does not necessarily solve the latter.

For each research question, create an acquisition task with:

- The precise fact or clause needed: legal counterparty, total payable, late-payment provision, ownership transfer, early-settlement treatment, or another material term.
- Its scope: entity × product/operation × merchant × financier × channel × document version, plus customer cohort and transaction period when relevant.
- The document or observation capable of establishing it, and an exact acceptance condition.
- The available acquisition routes, an assigned owner, current status, next action, and a stopping condition.

For example: “Identify the financier signing Contact instalment agreements for merchant X through channel Y during period Z” is closable. “Find more information about Contact” is not. A support reply describing the brand cannot close the first task unless it identifies the applicable legal party and supporting document.

Use separate statuses for `lead`, `attempt_failed`, `captured_partial`, `captured_complete`, `analyst_verified`, `scope_unresolved`, and `provider_confirmation_pending`. These are proposed vocabulary, not existing runtime enums. Verified acquisition and scholar-approved interpretation are separate stages.

## 2. Distinguish crawler policy, technical failure, and authorization

RFC 9309 says robots instructions are not access authorization. It distinguishes a missing/unavailable robots resource, unreachable server/network conditions, and parseable rules. Its protocol treatment of 4xx does not make an HTTP 403 security refusal into legal permission. A robots allowance also says nothing about contractual reuse rights. [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html)

Keep `robots_state`, `terms_state`, `security_state`, `authentication_state`, `source_permission`, and `reuse_rights` separately. Record the response status, content type, and body classification. A 200 HTML challenge page is not a successfully obtained robots policy; a 200 application shell is not the same thing as a valid empty robots file.

The existing public acquisition spec stops at robots restrictions, terms restrictions, authentication, CAPTCHA, and security gates. This proposal adds better routes around missing evidence; it does not silently change those implemented or specified boundaries. Existing operator acknowledgements remain evidence of the operator's project decision. They are not permission issued by FRA, Souhoola, or another website owner.

**An effective authorized override is issued by the source:** a path-specific permission, official export, API credential for the documented research scope, research portal, or owner-configured WAF exception. Store its issuer, authority, hosts/paths, allowed methods, request limits, dates, expiry/revocation conditions, and permitted uses. If it differs from the public-crawl policy, record it as a separate permitted acquisition channel and carry the change through the spec before implementation.

## 3. Obstacle decision table

These are proposed project decisions. They deliberately distinguish failure classes rather than treating every obstacle as a reason to retry with a different identity.

| Observed condition | Next acquisition action | Evidence/result to retain |
|---|---|---|
| Valid robots permits the path; terms reviewed; public substantive response | Bounded HTTP capture, then extraction | Policy snapshot, raw bytes, headers, URL chain, passage and version |
| Valid robots disallows the path | Stop that automated route; request scoped access, an official copy, or a separately published permitted source | Explicit path restriction and the alternative's own access/reuse decision |
| Robots genuinely missing, such as a normal 404/410 | Review and record a scoped project access decision before collection; check the other permission dimensions | Missing-file response, terms decision, scope and decision expiry |
| Robots returns 200 HTML app shell or another malformed response | Record `policy_unresolved`; inspect only already permitted context; request clarification or document delivery if unresolved | Raw response and classification; do not treat “no directives” as permission |
| Robots or content returns a security denial/challenge, including 200 block HTML or 401/403 | Pause the affected route; submit a diagnostic package to the source or request another official delivery channel | URL, UTC time, status, request/correlation ID and non-sensitive block excerpt |
| Public page loads normally but static extraction has no text | Use a normal browser render after access checks; inspect the public page's own delivered content | Rendered DOM/text, screenshot, selected language and relevant page state |
| 429/rate limit | Honor Retry-After; reduce work; defer the batch when the allowed retry budget ends | Attempt history and next permitted attempt time |
| Timeout or transient 5xx on permitted content | Bounded retry; preserve earlier valid observations | Failure separate from absence; current observation and latest failed attempt |
| Robots unreachable through server/network failure | Pause automated collection pending restored policy or source-authorized alternative | Unreachable-policy state; no automatic “missing robots” acknowledgement |
| CAPTCHA/login/app gate | Public crawler records the first gate and stops; obtain source-delivered documents | Gate description, requested missing artifact and follow-up status |
| Single-page terms restrict scraping | Request a copy/license or permitted manual research scope; assess viewing, capture and redistribution separately | Terms clause and date; rights decision for the chosen route |
| PDF/image/table available but extraction fails | Download through the approved route, render locally, OCR or transcribe, and verify material fields | Original file, page images, derived text and human correction lineage |
| Historic or archived copy exists | Use for the period it establishes; pursue a current version separately | Original URL, archive URL, snapshot date, retrieval date and completeness |
| Official sources disagree | Keep both observations and seek dated resolution evidence | Conflicting claims, temporal scope, supporting records and unresolved fields |

Apply the most restrictive unresolved condition when several occur together. An allowed public home page does not authorize a restricted document path. Re-evaluate each redirect, CDN document host, embedded frame and data endpoint needed for an automated acquisition; ordinary page rendering does not authorize arbitrary secondary crawling.

**Proposed starting budgets:** one automated worker per host, minimum two seconds between permitted requests, at most two additional retries for a transient content failure, and a predeclared page/byte budget. These are engineering defaults, not measurements or guarantees of permission. Source limits and Retry-After take precedence. For robots, refresh before a new batch and no later than the adopted policy TTL; do not reuse a stale acknowledgement after the access state changes. RFC 6585 defines 429 and the optional Retry-After signal. [RFC 6585, section 4](https://www.rfc-editor.org/rfc/rfc6585.html#section-4)

## 4. Acquisition methods that materially extend the toolbox

### 4.1 Repair permitted delivery and extraction

Use HTTP capture for normal public HTML and downloadable documents. Correct charset decoding, compression handling, redirect classification, language selection, and HTML-versus-PDF detection. Retain the original bytes before cleaning. A encoding or parser failure should not become a missing-facts conclusion.

Discover documents through the site's linked terms, help, FAQ, product and disclosure pages; permitted sitemaps; official investor-relations document libraries; and regulator publication pages. Keep a bounded link graph. Record every candidate document's title, publisher, date, and the page that linked it. Search exact Arabic and English legal names and known register identifiers to locate candidate sources; search snippets remain leads.

When a public page delivers its content through JavaScript, render it with the actual permitted browser session and capture the complete relevant sections, expanded terms and visible footnotes. Playwright can support a repeatable authorized browser workflow; using it does not establish access rights. [Playwright Page API](https://playwright.dev/docs/api/class-page)

Inspect JSON-LD or structured data already delivered with the permitted page as an extraction aid. For a terms page's ordinary network responses, supervised DevTools inspection can identify which delivered response contains the displayed text and why extraction failed. Direct automated API requests require a documented public API or separate source permission; the presence of a URL in DevTools is insufficient. Do not expand queries to obtain records the approved page/session did not authorize.

Export a sanitized HAR only when needed to diagnose rendering or document delivery. Chrome provides this export and excludes sensitive authentication/cookie headers by default. Manually check URLs, query strings, bodies and response content as well: a sanitized export is not a guarantee that every personal field or secret was removed. [Chrome DevTools network reference](https://developer.chrome.com/docs/devtools/network/reference#save-as-har)

For scanned Arabic contracts, use Arabic/English OCR appropriate to the page, retain page numbers and bounding boxes, and visually verify parties, amounts, decimal separators, percentages, dates, negations and annex references. Reconstruct tables with headers and row context, not a flattened text stream. Tesseract provides language models, and its documentation explains the effect of image quality on OCR. [Tesseract language installation](https://tesseract-ocr.github.io/tessdoc/Installation.html), [image-quality guidance](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html)

### 4.2 Resolve false-positive security blocks with the source

Send the site owner a short reproducible diagnostic: blocked URL, timestamp in UTC, research bot identity, request rate, status, correlation/Ray ID where provided, purpose, precise pages needed, and a request for an official export or narrow allowlist. An approved fixed egress address and honest research identity can make the access auditable. Cloudflare explicitly directs blocked visitors to the owner and describes owner-side allowlisting or rule adjustments for false positives. [Cloudflare WAF FAQ](https://developers.cloudflare.com/waf/troubleshooting/faq/)

Possible deliverables are a downloadable file bundle, a time-limited research workspace, a path-specific bot allowance, a documented API, or scheduled exports. Ask for the simplest route that supplies the facts. A crawler exception is useful for recurring changes; a one-time authoritative contract pack may be better for the initial five dossiers.

Repair ordinary local network or client configuration failures when there is no denial signal. Preserve TLS verification. When a security restriction is present, source cooperation resolves it; moving to rotating proxies, imitating Googlebot, masking browser fingerprints or bypassing application security would not establish source authorization.

### 4.3 Follow document publishers and counterparties

The same legitimate document may be published by a financier, merchant, regulator, investor-relations site or official document CDN. Follow links actually published by those parties, and independently assess access and reuse at the destination. Check version and publisher authenticity before treating a copy as equivalent. Do not hunt alternative origins to evade a site's security restriction.

Ask merchants for the financier's current standard agreement and all applicable annexes, not only “which payment brands do you accept?” A merchant relationship page establishes an advertised relationship; the executed or applicable standard agreement establishes the legal parties and obligations. Merchant onboarding teams may be able to route a research request to the proper compliance/document owner without supplying confidential commercial schedules.

Use EGX/corporate disclosures and commercial-register records for legal identities, group structure and dated name changes. A group chart, app-store publisher, email domain, trademark or website title does not by itself identify the contracting financier. Official social announcements and app listings can locate a new product or document owner; their contractual authority remains limited.

### 4.4 Manual public-page and supervised source research

Manual review is a primary research method. For permitted public material, an operator can record the page sequence, save a PDF/MHTML where suitable, capture screenshots of hidden-on-print panels and compare the saved copy with the live display. Record what was omitted and why. Printing alone may lose expanded clauses, tables or offer context.

If material is available only through a provider app or account, first request a demo environment, supervised document review or source-delivered sample pack. A consenting operator may donate their own already-held, suitably redacted agreement through a separately authorized private-document process. The existing V1.6 public collector still stops at the gate. Account ownership alone does not establish research retention, onward disclosure or publication rights.

A future supervised manual protocol may allow a real person to complete a normal challenge for access they are entitled to, with project and source scope recorded. That is a proposed policy exception, not an enabled path in the current spec, and never authority for automated challenge solving or authenticated crawling. No new registration, OTP workflow, credit inquiry, purchase, loan application, agreement acceptance, or order submission is required by this plan.

Offline routes include an official brochure or blank agreement supplied at a branch, a provider-approved research interview, and a scheduled review with compliance or legal staff. Preserve document identifiers and written confirmations. Interview recollections and frontline explanations are attributable testimony; use them to locate documents and clarify ambiguity rather than silently replacing a contractual clause. Do not secretly record conversations or assume a research interview grants redistribution rights.

### 4.5 Historical repositories and licensed research sources

Use Wayback snapshots for what an identified snapshot actually shows. Common Crawl can supply the original WARC record when available; retain crawl/index identifiers and record locators. Both are incomplete discovery sources, and archive presence does not establish present applicability or blanket republication rights. Archive replay may omit JavaScript or link to live content. [Internet Archive guidance](https://archivesupport.zendesk.com/hc/en-us/articles/360004651732-Using-The-Wayback-Machine), [Common Crawl retrieval guide](https://commoncrawl.org/get-started)

Replace “the site never adopted the BM name” with “the inspected snapshots retained the CI title on the listed dates.” Check the legal-name clauses themselves before concluding anything about corporate ownership or rebranding.

A licensed registry extract, publisher-approved document library, institution-provided research dataset or academic partnership can supply evidence when a website cannot. Check the license against internal analysis, scholar sharing, excerpts, public citations and future product reuse separately. A scraping vendor's successful delivery is not proof of authorized acquisition; require its source provenance and rights basis.

## 5. An official request that can close a dossier

Prepare this package for the operator to send through a verified official contact. No outreach was sent during this review.

> Subject: Research request — current standard financing documents for [product / merchant / channel]
>
> We are conducting a research-stage study of Egyptian consumer-financing arrangements. For [specified product, merchant, channel and relevant period], please provide or direct us to the applicable blank standard agreement, all incorporated annexes, repayment/fee schedule, early-settlement provisions, late-payment/default provisions, and the document version/effective date.
>
> Please identify the legal contracting financier, its regulator activity/licence reference, and any separate app operator, agent or assignee. Please state which documents apply to the selected arrangement and identify any terms that depend on customer eligibility or campaign dates. We do not need customer identities, credit files, credentials or internal underwriting records.
>
> Please confirm permitted internal research storage, access by our named analyst and scholar reviewers, quotation/citation conditions, and whether future product reuse requires a separate agreement. If automated public-document access is acceptable, please specify allowed hosts/paths, methods, limits, validity period and a technical contact. An official file bundle is equally useful.
>
> Please identify your role and the team responsible for document/version confirmation. We will preserve qualifications and mark unanswered points as unknown.

If no reply arrives, record `no_response`, use another eligible channel, and retain the gap. A non-response is neither approval nor evidence that a clause does not exist. Verify a reply through a known official contact if its sender or scope is uncertain.

## 6. Capture acceptance and provenance

Accept each material observation only when a reviewer can retrieve the preserved artifact and identify the exact supporting passage, page, table cell or screen. Hashes detect changes to stored bytes; they do not establish truth, authenticity, completeness or correct applicability.

| Record group | Required content |
|---|---|
| Acquisition | Task ID; capture ID; route; requested/final URL; redirect chain; access outcome; capture UTC timestamp; source permission/decision ID |
| Artifact | Restricted/public locator; raw-file SHA-256 and byte count; MIME type; original filename; language; complete/partial flag and omissions |
| Context | Publisher and entity role; product, merchant, financier, channel; locale; session category without secrets; offer/cohort selection |
| Dates | Publication/effective date; transaction applicability; archive snapshot date where relevant; retrieval time kept separate |
| Extraction | Tool/version and parameters; derived-file hash; parent artifact; page/span or screenshot coordinates; OCR uncertainty and reviewer corrections |
| Claim | Literal observation; field; applicable scope; supporting capture/span; analyst and time; conflicting observations and remaining unknowns |
| Rights | Acquisition, retention, reviewer access, redistribution and product reuse assessed separately; expiry and revocation handling |

Check page counts, annex references, amendments, fee tables and linked documents. A partial capture may establish an identity clause but cannot establish that an unobserved penalty clause is absent. Retain source-language names verbatim; create separately evidenced identity relationships and dated resolutions without rewriting original observations. Client decisions can select display labels; factual legal identity requires supporting evidence.

For public artifacts, preserve correction lineage and earlier valid observations alongside the latest failed attempt. For private documents, follow the spec's redaction, ephemeral-by-default and opt-in-retention requirements; define restricted reviewer access and approved disposal separately. Keep minimal non-sensitive deletion/audit records where appropriate. Do not apply “nothing is deleted” universally to customer documents, tokens or account details. Resolve any applicable review hold against the private-document policy before accepting such material; this proposal does not decide that conflict by retaining everything.

## 7. Scientific research and Egyptian legal review timing

Research intent supports a transparent protocol and can help obtain cooperation. It is not a documented permission grant from a system owner. Collection and commercial reuse need separate decisions; a future launch review cannot retroactively establish the authority for today's access.

The FRA-hosted Arabic text of Law 175/2018 covers prohibited entry in article 14, exceeding a granted access right in article 15, and unlawful interception in article 16. These provisions justify examining the actual route and scope before acquiring restricted material. This review has not established a blanket scientific-research exemption or determined the legality of a particular host's terms. [FRA-hosted Law 175/2018, articles 14–16](https://fra.gov.eg/wp-content/uploads/2025/01/%D9%82%D8%A7%D9%86%D9%88%D9%86-%D8%B1%D9%82%D9%85-175-%D9%84%D8%B3%D9%86%D8%A9-2018-%D8%A8%D8%AA%D8%A7%D8%B1%D9%8A%D8%AE-2018-08-14.pdf), [WIPO official-law record](https://www.wipo.int/wipolex/en/legislation/details/19959)

Egypt's PDPC identifies Law 151/2020 and Executive Regulations 816/2025 as the personal-data framework. Have Egyptian counsel assess applicability, research conditions, sensitive financial data, consent/other lawful basis, transfers to cloud or model providers, licenses/permits where required, and retention for the proposed private-document protocol. Avoid assuming consent alone resolves every requirement. The PDPC's indexed official material was available during this check, but direct access to parts of its portal failed; no case-specific exemption, deadline, or permit determination is asserted here. [PDPC legal-framework information](https://www.pdpc.gov.eg/)

Use two recorded reviews: acquisition-stage review before restricted/private collection, then product-reuse review before publication or launch. Permitted public research can continue while requests for restricted documents remain pending. No dossier or legal review here substitutes for scholar approval of a rule or a launch gate.

## 8. Immediate application to the five pilot dossiers

The table uses the checked-in 2026-10-01 worksheet as a dated research state, not fresh verification of the providers' current offers.

| Pilot | Specific unresolved need | Route and closure criterion |
|---|---|---|
| valU | Separate app/operator identity from the legal financier and applicable product contract | Applicable blank agreement + dated fee/repayment annexes; map each role to the exact document clause; use disclosures for supporting corporate identity |
| Contact | Identify the contracting party for a selected merchant/channel among the entities carrying the brand | Merchant or provider compliance request naming the exact arrangement; close only with the legal counterparty and applicable version, not a group-domain match |
| Souhoola | Resolve the dated CI/BM/“Contact Investment” name observations and obtain complete operative terms | Preserve all observations; complete permitted render or official document pack; commercial-register/change records or authoritative written clarification with effective dates |
| Aman | Distinguish holding company, consumer-finance licensee and other financing activities | Obtain the selected consumer-finance standard agreement and fee schedule; retain holding-company material only for its established role |
| Halan | Establish a particular seller–financier relationship and actual applicable terms | Selected merchant/provider evidence and documents; keep it as the insufficient-evidence control until that specific gap closes |

For each entity, first assemble existing valid public captures and a clause-completeness matrix. Then pursue the shortest eligible route for the remaining gaps. Parallel operator tasks may prepare source requests and document extraction; this plan itself does not send messages or collect gated material.

Suggested closure matrix fields: identity; parties/roles; cash price; financed principal; contractual total payable; instalment count/dates; mandatory fees; late/default provisions; early settlement; ownership/delivery; applicable annexes; effective period; explicit unknowns. These guide completeness; the scholar's applicable rule ultimately determines which facts are material.

## 9. What the local review actually established

- The original playbook's “every technique was used or tested” sentence is contradicted by its planned/recommended/deferred rows. Methods need per-route status and capture/attempt IDs.
- The entity-resolution manifest contains two explicit operator acknowledgements for FRA and Souhoola and fourteen earlier correction records. Their stated scope excludes security-block circumvention. They remain historical project decisions.
- `scripts/capture_entity_identity_pages.py` checks robots but contains no branch consuming those acknowledgement records. Its labels also combine server failure and HTML-without-directives as unavailable. Therefore the acknowledgement narrative is not proof that this helper implements a corresponding acquisition path. This is a read-only observation, not a completed fix or full code review.
- The Souhoola browser record is explicitly `text/plain; excerpt`, with omissions marked. It supports its captured observations, not a complete contract assessment.
- The checked-in identity worksheet says site terms had not been reviewed for any host in that acquisition pass. An Allow directive cannot close that separate check.
- The present spec defers private agreement intake beyond V1.6 and requires redacted, ephemeral handling by default. The playbook's account/manual rows and universal retention sentence need reconciliation with that version boundary.

These findings support a proposal. They do not demonstrate a new crawler, a successful new provider request, complete five-dossier evidence, or legal clearance.

## 10. Scientific validity of the acquired dataset

Keep an acquisition protocol with the research questions, inclusion/exclusion rules, chosen entities/channels, search dates and stopping rules. Track successful and blocked routes with equal visibility. A dataset built only from easy-to-crawl providers can systematically omit app-only or restricted arrangements; do not present it as representative of the Egyptian market.

Triangulate at the claim level. An official filing can establish a legal name while the applicable agreement establishes the contractual counterparty. Two pages copying the same press release are one underlying source family, not independent confirmation. Preserve disagreements and look for dated amendments or authoritative explanations rather than averaging conflicting clauses.

For material terms, have a second analyst compare the extracted Arabic/English text with the actual artifact and verify applicability. Check tempting negative claims explicitly: a search that found no late-payment clause in an excerpt cannot establish that no penalty exists. Record which complete documents were searched and what remains unavailable. The scope of the evidence determines the scope of the conclusion.

Use a reproducibility pack containing the permitted artifacts, capture decisions, versioned extraction configuration, claim-to-span mappings and a gap log. Measure closure of material fields, extraction errors found by reviewers, and unresolved applicability/conflicts. Do not attach invented confidence scores to source authority or interpret high capture volume as high factual coverage.

If “inside data” means unpublished underwriting rules, confidential pricing, internal approval criteria or portfolio data, request a specifically authorized provider research dataset, supervised review or properly scoped agreement. Public pages and customer screenshots cannot establish that internal information. A data-sharing agreement must specify confidentiality, access, security, permissible analysis and publication; an unanswered request remains an unresolved need.

## 11. Completion criteria for the next acquisition cycle

1. Each missing material fact has a scoped task, eligible route and expected artifact.
2. Every automated route has separate robots, terms, security and scope decisions; each permissioned exception has a source-issued record.
3. Every accepted observation has retrievable bytes and a supporting span, with version, completeness and applicability checked.
4. Conflicts, missing annexes, historical sources and failed attempts remain explicit; missing text is never promoted into “no such clause.”
5. Private collection uses its own approved intake/retention procedure and does not enter the public evidence store through an informal manual exception.
6. The output reports closed gaps and unresolved gaps by dossier, rather than presenting request count, page count or tool success as financing accuracy.

The next implementation scope should be the public acquisition decision record, failure classification and reproducible capture path. Source-request tracking and a separate private research protocol can follow as their own scoped work. This review does not alter tickets, the spec, access acknowledgements or runtime code.
