# Evidence acquisition playbook review

Reviewed 2026-10-01 using BMad Review: adversarial, edge-case-hunter and editorial structure. Content class: document with operational behavior. The three independent lenses ran in parallel. Verification-gap was inapplicable to the document class; prose was not selected because this request concerns strategy and acquisition behavior, not copy-editing.

Baseline: [preserved reviewed playbook](evidence-acquisition-playbook-reviewed-baseline-2026-10-01.md), SHA-256 `1222e97fb440ef5e7edf480379cfc1356e91f7cfda5a2e914a8a7186f6084ddd`. Original reviewed bytes are preserved in that baseline file. The [operative playbook](evidence-acquisition-playbook.md) was subsequently adopted and its public foundation implemented; the 45 findings below remain the historical review.

The playbook identifies useful sources, but needs explicit evidence-gap tasks, independent permission checks, acquisition-state classification, reproducible capture procedures and version-specific private-document handling. The concrete research proposal is [evidence-acquisition-rethink-2026-10-01.md](evidence-acquisition-rethink-2026-10-01.md). The proposed methods were not executed during this review.

Findings: 18 adversarial, 19 edge-case, 8 structure; 45 lens findings total. Overlapping observations are retained because they reflect independent lenses, not distinct defect counts. No severity or ranking is assigned.

## Cross-lens observations

- Access-policy ambiguities recur across adversarial and edge-case findings: denied robots responses, acknowledgement versus source permission, and gated manual routes.
- Evidence fidelity and applicability recur across both behavioral lenses: incomplete contracts, archived versions, personalized offers, missing artifacts and extraction errors.
- Private-data retention is independently raised by both behavioral lenses and conflicts with the universal retention language.
- The structure lens recommends placing the operational decision before the source inventory and separating dated pilot observations from reusable instructions.

## Adversarial

### Finding 1

**Location:** The toolbox, best evidence first

**Trigger condition:** The statement that every technique was used or tested on 2026-10-01 conflicts with rows explicitly marked Planned, Recommended, Next step, or deferred.

**Concrete guard or improvement:** Give each technique a verified state: exercised with capture IDs, tested unsuccessfully with attempt IDs, planned, or deferred. Limit the introductory empirical claim to methods supported by those records.

**Potential consequence:** Readers may treat proposed acquisition routes as demonstrated capabilities and overestimate the completeness of the pilot evidence.

### Finding 2

**Location:** The line we hold, and why it helps us / Decision rules when something blocks us

**Trigger condition:** A firewall page returned from robots.txt is classified as unavailable directives and may enable fetching after operator acknowledgement, while a firewall or security block elsewhere requires a stop.

**Concrete guard or improvement:** Classify a security response at the robots endpoint as blocked_by_security. Make operator acknowledgement record awareness only; require a separately documented basis before any acquisition affected by the security block resumes.

**Potential consequence:** The same security restriction may produce opposite collection decisions depending on which endpoint exposes it.

### Finding 3

**Location:** The line we hold, and why it helps us

**Trigger condition:** Robots directives, site terms, authentication, security restrictions, and legal authorization are grouped together without identifying which rule is a project policy and which concerns an access control or legal obligation.

**Concrete guard or improvement:** Track robots policy, terms restrictions, security response, authentication requirement, source permission, and legal review as separate fields. State that this project's robots stop is an operational policy and that robots availability or allowance does not establish authorization.

**Potential consequence:** Operators may interpret a robots allowance or missing file as permission, or misstate the legal meaning of a robots restriction.

### Finding 4

**Location:** The line we hold, and why it helps us

**Trigger condition:** The project constraint forbids crossing login or gated steps, but later rows permit captures through the operator's own account without explaining whether that is an authorized exception.

**Concrete guard or improvement:** Distinguish public automated discovery from separately approved authenticated manual research. Cite the governing project exception or require a documented permission decision before authenticated evidence enters that workflow.

**Potential consequence:** Operators may treat account ownership as sufficient to override a stricter project constraint.

### Finding 5

**Location:** Decision rules when something blocks us / Terms of use forbid scraping

**Trigger condition:** Manual capture of single pages is offered after terms prohibit scraping without checking whether the applicable terms also restrict copying, research reuse, disclosure, or redistribution.

**Concrete guard or improvement:** Record the relevant terms and distinguish permission to view, permission to capture, and permission to reuse or distribute. Route unclear or restricted manual reuse to a source-permission request.

**Potential consequence:** Changing the capture method may be mistaken for resolving a restriction that also applies to subsequent use.

### Finding 6

**Location:** Decision rules when something blocks us / CAPTCHA

**Trigger condition:** The CAPTCHA row says Never solve but directs operators to manual capture without defining whether a CAPTCHA encountered during the manual route is an authorized user interaction or remains a project stop.

**Concrete guard or improvement:** Define the manual route precisely: use already authorized accessible material or request source assistance; any permitted normal human challenge completion must have an explicit project authorization basis and must not become outsourced automated challenge solving.

**Potential consequence:** Different operators will apply incompatible rules to the same challenged page and produce inconsistent acquisition records.

### Finding 7

**Location:** The toolbox, best evidence first / Public archives

**Trigger condition:** The claim that Souhoola's site never adopted the FRA BM name is inferred from archived page titles across a period without stating snapshot coverage or uncertainty.

**Concrete guard or improvement:** Replace the universal conclusion with the observed result: identified snapshots retained the stated title on specified dates. Record archive gaps and preserve the unresolved relationship among the names.

**Potential consequence:** Incomplete archival observations may be promoted into a definitive historical claim.

### Finding 8

**Location:** The toolbox, best evidence first / Public archives

**Trigger condition:** Archives are offered as a response to present-day blocks without requiring the archived content's original date, applicable period, completeness, or current relevance to be assessed.

**Concrete guard or improvement:** Store snapshot timestamp, retrieval timestamp, original URL, archive URL, completeness checks, and historical/current applicability. Require current corroboration before historical terms support a present-offer claim.

**Potential consequence:** Expired fee schedules, former entities, or superseded contracts may be presented as current evidence.

### Finding 9

**Location:** The toolbox, best evidence first / Product documents

**Trigger condition:** The playbook prioritizes actual mechanisms and terms but does not specify the contextual fields needed to connect a contract or fee schedule to the offer under investigation.

**Concrete guard or improvement:** Require document version and effective date, financing entity, merchant, channel, product, eligibility or customer cohort, transaction date, fees, repayment schedule, and referenced annexes. Mark missing applicability facts explicitly.

**Potential consequence:** A genuine first-party document may be applied to the wrong merchant plan, product, entity, or period.

### Finding 10

**Location:** The toolbox, best evidence first / Regulator records and App-store listings

**Trigger condition:** Email domains and publishing entities are described as linking companies to sites or apps without a verification rule for brand operators, affiliates, shared group domains, or the actual financing counterparty.

**Concrete guard or improvement:** Treat domain and publisher matches as relationship leads. Establish the financing entity separately through an applicable contract, regulator identity, and corroborating first-party evidence; record each relationship's type and confidence.

**Potential consequence:** An app operator, holding company, or related affiliate may be mistaken for the entity financing a transaction.

### Finding 11

**Location:** The toolbox, best evidence first / Ask the source

**Trigger condition:** The source-request method lacks a defined request package and a way to assess whether a response is authoritative, complete, and applicable.

**Concrete guard or improvement:** Provide a request template for dated standard agreements, annexes, fee schedules, entity identity, applicability, and reuse permissions. Preserve the complete response and attachments, responder role, channel, date, and unresolved questions.

**Potential consequence:** An informal support reply may be treated as equivalent to a controlled contractual or compliance document.

### Finding 12

**Location:** Decision rules when something blocks us / robots.txt unavailable

**Trigger condition:** A universal spacing floor of two seconds is the only stated rate-management rule, with no handling for Retry-After, HTTP 429, repeated failures, or source-specific limits.

**Concrete guard or improvement:** Use documented source limits where available, honor Retry-After, define bounded exponential backoff and retry budgets, and stop repeated blocked or overloaded responses. Record request count and timing.

**Potential consequence:** A nominally polite crawler may continue stressing a site or repeatedly retry a restriction without an auditable stopping rule.

### Finding 13

**Location:** Provenance fields every capture carries

**Trigger condition:** The listed provenance fields do not identify which stored bytes are hashed or preserve a reproducible acquisition record for rendered, manual, archived, or extracted evidence.

**Concrete guard or improvement:** Assign capture IDs and retain a raw artifact locator, artifact hash definition, extraction hash, tool and version, response status and relevant headers, render conditions, and extraction lineage. Link claims to exact page, section, or screen spans.

**Potential consequence:** A hash and URL may be insufficient to reproduce the observation or prove that extracted text faithfully represents the captured source.

### Finding 14

**Location:** The toolbox, best evidence first / Rendering client-side pages and Operator manual capture

**Trigger condition:** Rendered and manual evidence can depend on locale, session state, consent choices, offer selection, or personalization, but those conditions are not recorded.

**Concrete guard or improvement:** Record language, selected offer, capture sequence, authentication category, relevant session or consent state, and visible applicability context without retaining credentials or session secrets. Link multi-screen captures in order.

**Potential consequence:** A personalized or incomplete screen may be generalized as a universal public offer and cannot be independently reconstructed.

### Finding 15

**Location:** The toolbox, best evidence first / Customer-supplied documents / Provenance fields every capture carries

**Trigger condition:** Customer agreements are admitted with consent, while the blanket Nothing is deleted rule provides no privacy, redaction, access, retention, withdrawal, or correction treatment for sensitive documents.

**Concrete guard or improvement:** Separate restricted originals from sanitized research derivatives. Define purpose-specific consent, access controls, sensitive-field minimization, retention and deletion rules, and append-only audit metadata that can survive deletion of personal content.

**Potential consequence:** The evidence store may retain and expose customer identifiers or financial details indefinitely despite a legitimate request or obligation to remove them.

### Finding 16

**Location:** Name handling (standing rule)

**Trigger condition:** The instruction never to settle disagreement and to let the client decide provides no evidence-based resolution procedure or distinction between display preferences and legal identity facts.

**Concrete guard or improvement:** Keep original name observations intact, but maintain separately sourced relationship and identity determinations with effective dates, supporting records, reviewer authority, and unresolved status. Client preference must not replace factual corroboration.

**Potential consequence:** A subjective naming decision may silently become the legal identity used for contracts, regulator linkage, or financial conclusions.

### Finding 17

**Location:** The line we hold, and why it helps us / Legal exposure

**Trigger condition:** The playbook invokes Egyptian cybercrime law and legal caution but has no research-stage authorization record or distinction between permission to acquire now and permission to reuse at product launch.

**Concrete guard or improvement:** Add acquisition-stage and reuse-stage review checkpoints covering the relevant access, terms, privacy, confidentiality, and licensing questions. Record reviewed legal sources and decisions; do not defer all authorization assessment until launch.

**Potential consequence:** The team may assume that a scientific purpose or a future launch review resolves obligations arising during present collection.

### Finding 18

**Location:** The toolbox, best evidence first

**Trigger condition:** The toolbox lists useful source categories but does not turn difficult cases into a prioritized acquisition plan with explicit closure criteria.

**Concrete guard or improvement:** For each blocked evidence need, identify the exact missing fact, ranked public and source-authorized routes, owner, request or capture status, expected artifact, and acceptance criterion. Include source-provided exports, permissioned APIs, documented public downloads, and authorized supervised document review where appropriate.

**Potential consequence:** Blocked cases may cycle through alternative sources without obtaining the precise fact needed for an accurate dossier.

## Edge-case hunter

### Finding 1

**Location:** evidence-acquisition-playbook.md:14,38 — Robots availability and decision rules

**Trigger condition:** Robots response is denied, rate-limited, malformed, or a security page.

**Concrete guard or improvement:** Classify robots responses separately; operator acknowledgement cannot convert denial or security blocking into permission.

**Potential consequence:** Acknowledgement permits fetching despite an unresolved denial or security block.

### Finding 2

**Location:** evidence-acquisition-playbook.md:38 — Decision rules when something blocks us

**Trigger condition:** Robots or site terms change after acknowledgement or between collection batches.

**Concrete guard or improvement:** Revalidate host policy before each batch and invalidate acknowledgements when policy or access state changes.

**Potential consequence:** Collection continues under obsolete access conditions.

### Finding 3

**Location:** evidence-acquisition-playbook.md:31,38,44 — Permission and acknowledgement

**Trigger condition:** Permission expires, is revoked, or excludes requested paths, methods, or downstream uses.

**Concrete guard or improvement:** Record permission issuer, scope, allowed methods, reuse rights, expiry, and revocation; enforce them before capture.

**Potential consequence:** An earlier permission becomes blanket authorization for later unsupported collection.

### Finding 4

**Location:** evidence-acquisition-playbook.md:23,38-44,52 — Discovery, access decisions, and final URL

**Trigger condition:** A sitemap, PDF link, or redirect leads to another host or restricted path.

**Concrete guard or improvement:** Evaluate destination host and path permissions before following every redirect or discovered link.

**Potential consequence:** An allowed starting URL silently crosses into a restricted destination.

### Finding 5

**Location:** evidence-acquisition-playbook.md:24,41 — Client-side rendering

**Trigger condition:** Rendering requests APIs, frames, or resources beyond the approved page scope.

**Concrete guard or improvement:** Apply access checks to browser requests and stop rendering when required requests cross approved boundaries.

**Potential consequence:** A public-page render collects data through an unapproved secondary endpoint.

### Finding 6

**Location:** evidence-acquisition-playbook.md:40-41 — Security blocking versus rendered content

**Trigger condition:** HTTP 200 contains a challenge, error template, empty app shell, or partial content.

**Concrete guard or improvement:** Validate expected substantive content after rendering; classify challenges and incomplete shells before evidence ingestion.

**Potential consequence:** Blocked or empty responses are stored as successful evidence.

### Finding 7

**Location:** evidence-acquisition-playbook.md:38-44 — Decision rules when something blocks us

**Trigger condition:** Requests time out, disconnect, return transient server errors, or receive throttling.

**Concrete guard or improvement:** Record transient failures separately, honor Retry-After, and use bounded retries only where access remains permitted.

**Potential consequence:** Temporary failure becomes apparent absence, or repeated requests aggravate throttling.

### Finding 8

**Location:** evidence-acquisition-playbook.md:42 — CAPTCHA

**Trigger condition:** An operator supplies a capture obtained after a CAPTCHA or security challenge.

**Concrete guard or improvement:** Record the access route and operator authority; manual submission never authorizes automated challenge handling.

**Potential consequence:** A manual capture silently legitimizes subsequent automated collection through the challenge.

### Finding 9

**Location:** evidence-acquisition-playbook.md:12,30,43 — Login and app-only flows

**Trigger condition:** The collector possesses valid credentials and interprets the automated-fetch column as permission.

**Concrete guard or improvement:** Stop automated acquisition at login or app gates; accept authorized account captures through the manual route.

**Potential consequence:** Owned credentials trigger automated gated collection contrary to the stated project boundary.

### Finding 10

**Location:** evidence-acquisition-playbook.md:30,32,43-44 — Manual and customer-supplied evidence

**Trigger condition:** Account access is authorized but research retention, sharing, or publication rights are unspecified.

**Concrete guard or improvement:** Record capture, retention, reviewer access, and redistribution permissions separately before ingesting nonpublic evidence.

**Potential consequence:** Entitlement to view becomes assumed permission to retain or disclose private material.

### Finding 11

**Location:** evidence-acquisition-playbook.md:25,39 — Public archives

**Trigger condition:** An archive snapshot is unavailable, incomplete, redirected, or missing linked terms and assets.

**Concrete guard or improvement:** Record original URL, snapshot timestamp, replay URL, archive identity, completeness, and failed dependencies.

**Potential consequence:** An incomplete replay is treated as a complete historical source.

### Finding 12

**Location:** evidence-acquisition-playbook.md:25-29,48,52 — Source versions and dates

**Trigger condition:** A historical filing or cached document is captured today but describes an earlier entity or offer.

**Concrete guard or improvement:** Record publication, effective, and snapshot dates separately from captured_at; mark applicability and currentness explicitly.

**Potential consequence:** The capture date makes historical evidence appear current.

### Finding 13

**Location:** evidence-acquisition-playbook.md:29,32 — Product and customer documents

**Trigger condition:** A contract lacks pages, annexes, amendments, signatures, or the applicable fee schedule.

**Concrete guard or improvement:** Check document completeness and linked instruments; withhold mechanism conclusions when material provisions are missing.

**Potential consequence:** An incomplete agreement supports an inaccurate financing-mechanism conclusion.

### Finding 14

**Location:** evidence-acquisition-playbook.md:29-30,32 — PDFs and manual app captures

**Trigger condition:** OCR, printing, scrolling, or screenshot selection omits or corrupts material text.

**Concrete guard or improvement:** Preserve original captures and verify extracted material against page images; flag unreadable or omitted regions.

**Potential consequence:** A valid hash preserves inaccurate extraction without revealing the transcription error.

### Finding 15

**Location:** evidence-acquisition-playbook.md:29,32,43 — Applicability of account and offer evidence

**Trigger condition:** A captured offer depends on customer, merchant, product, region, or campaign-specific conditions.

**Concrete guard or improvement:** Record offer context and applicability; do not generalize personalized or merchant-specific terms to the brand.

**Potential consequence:** One customer's agreement is presented as the company's general financing terms.

### Finding 16

**Location:** evidence-acquisition-playbook.md:31 — Ask the source

**Trigger condition:** A reply comes from an unverified sender or answers only part of the request.

**Concrete guard or improvement:** Verify respondent authority, preserve the complete exchange, and label unanswered facts and qualified statements.

**Potential consequence:** An unauthenticated or partial reply becomes authoritative confirmation.

### Finding 17

**Location:** evidence-acquisition-playbook.md:48 — Name handling

**Trigger condition:** Client review resolves a disagreement without documenting evidence, effective dates, or the decision.

**Concrete guard or improvement:** Append the review decision, reviewer, timestamp, evidence references, temporal scope, and unresolved qualifications.

**Potential consequence:** A client decision silently replaces an auditable source disagreement.

### Finding 18

**Location:** evidence-acquisition-playbook.md:48,52 — Evidence hashes and correction records

**Trigger condition:** The source disappears or changes and the hash has no retrievable original artifact.

**Concrete guard or improvement:** Link each hash to a preserved immutable artifact, extraction version, and correction lineage.

**Potential consequence:** Reviewers cannot reproduce the cited evidence from its URL and hash.

### Finding 19

**Location:** evidence-acquisition-playbook.md:32,52 — Private evidence retention

**Trigger condition:** Private evidence contains personal data, credentials, or information whose retention consent is withdrawn.

**Concrete guard or improvement:** Restrict private evidence access, define retention and deletion rules, and retain only non-sensitive audit tombstones.

**Potential consequence:** The nothing-is-deleted rule preserves private information indefinitely despite withdrawn authority.

## Editorial structure

This document exists to help research operators select an acquisition method when access obstacles prevent them from obtaining accurate, citable company or product evidence. The closest structure model is **Tutorial/Guide (Linear)**, with a reference table for the available methods: an operator needs access prerequisites first, a clear decision sequence second, and capture requirements before declaring the work complete. Review calibrated to human readers and the Microsoft Writing Style Guide.

Exact word counts from `word_metrics.py`:

| Section | Words |
|---|---:|
| Title-level introduction | 32 |
| The line we hold, and why it helps us | 202 |
| The toolbox, best evidence first | 512 |
| Decision rules when something blocks us | 177 |
| Name handling (standing rule) | 84 |
| Provenance fields every capture carries | 34 |
| **Total** | **1,087** |

| Pass | Original Text | Revised Text | Changes |
|---|---|---|---|
| structure | §The toolbox, best evidence first — 512 words appears before §Decision rules when something blocks us — 177 words. | **MOVE** the decision table directly after the opening access boundary; follow it with the toolbox. | Operators encounter eleven methods before learning which are applicable to their obstacle. The reordered sequence becomes: establish the access boundary → identify the obstacle → select a permitted method → capture evidence. Moves the existing 177-word section; **0-word reduction**. |
| structure | §The toolbox, best evidence first — opening sentence and the “Example from 2026-10-01” column mix completed observations, planned acquisition, recommended outreach and deferred product work. | **MOVE** dated observations into a clearly labelled “Pilot observations and pending work — 2026-10-01” subsection after the operational instructions. Keep the technique descriptions together in the method reference. | Distinguish reusable instructions from the dated implementation state without discarding either. Preserve the link to `pilot-entity-resolution.md` alongside the observations. Reorganizes material inside the existing 512-word section; **0-word reduction**, excluding any added headings. |
| structure | §The toolbox, best evidence first — single numbered sequence combines regulator records, rendering, archives, product documents, operator capture and outreach. | **QUESTION** whether “best evidence first” and the numbered order are intended to express authority, acquisition sequence, or effort. Organize the existing entries around the operator’s goal, with access method as a separate field. | The current table mixes evidence sources with acquisition mechanisms, so its ranking gives an operator no consistent basis for choosing the next step. Reorganize existing content into consistent fields such as “Source or method,” “Evidence obtained,” and “When to use”; preserve every existing technique and example. Applies to the 512-word section; **0-word reduction**. |
| structure | §Decision rules when something blocks us — each row is independently useful, but the document does not state how to resolve multiple conditions on the same source. | **CONDENSE** the existing access conditions into a short, explicit decision sequence above the table; retain the table as the quick reference. | The operational reader needs to know how the access checks relate before choosing HTTP fetching, browser rendering or an alternative source. Build the sequence from the existing conditions rather than introduce new policy. Reorganizes the 177-word section; **0-word reduction** if the sequence replaces equivalent table wording. |
| structure | §Provenance fields every capture carries — 34 words at the end, after §Name handling — 84 words. | **MOVE** provenance immediately after the method-selection instructions, under “Record the capture”; place name handling after it under “Record company names.” | Capture metadata is a prerequisite for producing usable evidence, while name handling is a specialized downstream rule. The revised sequence follows the operator’s work: acquire → record capture → record extracted names. Moves the existing 34-word section; **0-word reduction**. |
| structure | §The line we hold, and why it helps us — 202 words of access boundaries and rationale precede the first actionable decision table. | **MOVE** the evidence-value and legal-exposure rationale below the quick decision table, while keeping the access boundary, project constraint and unavailable-versus-disallowed distinction at the start. | Preserve the prerequisite rules but let an operator reach the operational decision sooner. The explanatory paragraphs remain available to readers who need their rationale. Reorganizes the existing 202-word section; **0-word reduction**. |
| structure | §Name handling — 84 words; §Provenance fields — 34 words. The document ends with fields rather than an explicit completion checkpoint. | **MERGE** these into a final “Capture completion check” section with two subsections: capture record and company-name rows. | The guide model needs a clear end condition. Turn the existing requirements into a short checklist so the operator can determine whether the acquisition record is complete. Preserve the exact-name, pending-review and append-only correction requirements. Reorganizes **118 existing words**; **0-word reduction**, excluding any added heading. |
| structure | The document uses two compact tables, followed by short name-handling and provenance sections. | **PRESERVE** the table format, standalone distinction between “unavailable” and “disallowed,” and concrete pilot examples. | These support scanning and comprehension. Relocate and label the examples instead of deleting them; retain the key access distinction as an early callout. Preserves existing material within the 1,087-word document; **0-word reduction**. |

**Eight recommendations. Estimated reduction if all are accepted: 0 words, 0% of the original 1,087 words.** These are organizational changes, with minor heading additions possible. No length target was supplied. The principal trade-off is that dated examples move farther from the method reference, so each method should retain a clear pointer to its corresponding observation; the operational sequence becomes easier to scan without sacrificing the examples or rationale.


## Validation and evidence limits

Reviewed findings against the original document and the current local spec, fact/evidence model, pilot worksheet, capture helper and 2026-10-01 entity-resolution manifest. The manifest confirms the previously recorded acknowledgements; this review does not rescind, extend or reinterpret them as source-issued permission.

The current spec stops public automated acquisition at gates and defers private intake. Proposals to create a separately authorized manual/private channel require an explicit specification and implementation change; no such change is claimed here.

The checked-in capture helper does not consume the manifest acknowledgements, and the rendered Souhoola record identifies its stored text as an excerpt. These are supplementary read-only observations, not a full code review or proof of a new acquisition failure.

Current primary technical and Egyptian legal sources are linked beside the relevant claims in the research proposal. Some government portal requests failed; their access failures are not permission or evidence of missing law. No provider outreach, gated collection, or new scientific/legal exemption was established.

Machine-readable findings: [evidence-acquisition-review-2026-10-01.json](evidence-acquisition-review-2026-10-01.json). All independent-lens findings are preserved without deduplication.
