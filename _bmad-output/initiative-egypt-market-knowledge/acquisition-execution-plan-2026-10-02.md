# Public financing-evidence pilot: finalized execution plan

Finalized 2026-10-02 under the user's instruction to review/update the plan and proceed with collection. This supersedes the October 1 pilot sequence, preserves its historic captures and incorporates the [double review](acquisition-double-review-2026-10-02.md).

## Research scope and evidence acceptance

Research five providers: valU, Contact, Souhoola, Aman and Halan. Collect publicly published, nonpersonal corporate contacts, descriptions of consumer loan/instalment arrangements, standard blank agreements and applicable fee/repayment annexes. Exclude individual applications, signed customer agreements, account records, personal contacts and security testing. Acquisition is for internal research; publication/reuse rights remain separate.

Classify each arrangement, with legal parties and document/channel/date scope: (1) the same legal entity sells the goods and finances the customer; (2) a separate vendor sells while the financier provides credit; (3) multiple arrangements with different roles; or (4) unresolved. A brand's own shop establishes an advertised sales channel, not the legal identity of seller/creditor or ownership transfer. Merchant lists, brand mentions and financing keywords are leads until relationship passages support the particular claim.

Capture and extraction do not constitute analyst acceptance. Every material observation needs artifact/hash plus a literal page/span, completeness/applicability assessment and review status. This pilot uses automated analyst observations, with second-human review pending. No Sharia verdict or company-wide compliance label is produced. A human scholar selects the applicable AAOIFI rules and reviews sufficiently established transaction facts.

## Executable route and corrections

Use only `scripts/capture_entity_identity_pages.py` / PublicCollector v0.3 for automated acquisition. Do not use the legacy FRA collector, market collector, relationship summarizer or CrawlerEngine for this pilot: the double review found weaker policy gates or unsupported role promotion there. Localized v0.3 corrections preserve known HTTP refusal/host cooldown before decoding and reject navigation/footer/header/ARIA-landmark-only shells as complete documents. Full text remains preserved when extraction succeeds.

Use fresh exact-path access records with named automated reviewer, bounded reference and expiry. `reviewed_allowed` is a recorded project decision from the inspected public context; it is not website-owner permission or legal clearance. Never record that a human approved the policy unless one actually did. ValU's inspected terms expressly restrict automated data collection, so its automated route remains restricted. Souhoola's substantive site-policy text is unresolved, so automated content collection remains unknown. For other providers, record exactly which public pages/documents were reviewed and the limits of any decision; uninspected terms must not be described as reviewed.

Before content, the collector must obtain usable current robots rules. A missing 404/410 or truly empty/comment-only policy can be acknowledged only after inspecting that exact preserved payload, in a new run. Malformed robots, denial, challenge, login, unreachable policy and disallowed paths remain stop conditions. Every redirect needs exact destination scope and its own robots decision. No source-issued exceptions exist for this pilot.

Use one serial worker, minimum two seconds per host, maximum 45 network requests per run, three MiB per wire/decoded response and the collector's bounded retries. Honor longer source delays. Never route around a security refusal through proxies, identities, hidden endpoints or alternative origins. Ordinary manual public-page review is eligible only as its own assessed route, not an automated robots exception. Do not send provider requests during this batch.

## Provider worklist

| Provider | Bounded starting sources | Purpose and current boundary |
|---|---|---|
| Contact | Official `/en`, `/en/contact-us`, `/terms-and-conditions-en.pdf` | Collect publicly published customer terms appendix and corporate contact; appendix alone does not establish the complete main agreement, amounts, parties or current applicability. |
| Halan | Official `/shop/`, `/contact-us-2/`; separately scoped linked shop homepage if eligible | Record advertised shop financing and contact. Separate seller/creditor and ownership remain unresolved. Halan Cash wallet terms cannot close a Halan Shop credit-contract gap. |
| Aman | Official `/en/`, selected linked consumer instalment/store service page | Preserve advertised channels and identify document leads; holding/microfinance information cannot fill consumer-finance contract roles. |
| valU | Official `/terms-and-conditions` | Restricted automated route. Retain brief manually reviewed observations and source reference, not a full automated copy. Applicable cover/schedules and party roles need further evidence. |
| Souhoola | Official `/terms-conditions`, `/about` | Static web text is incomplete. Policy/complete render and conflicting legal-name observations remain unresolved; snippets are leads only. |

## Execution and deliverables

1. Finish focused regression verification and independent quick review of the collector correction. Transfer only these verified collector/test files from the isolated worktree to the primary workspace.
2. Save dated source-policy review, exact decisions and URL inputs; run immutable collector batch. If eligible missing/empty robots requires review, preserve the initial gap run and use a separately named follow-up run with payload-bound acknowledgement.
3. Inspect original/extracted results and relevant clauses. Produce an evidence register covering every provider, including blocked/unknown sources and contextual web observations. Independently recompute all artifact hashes; validate span pointers for recorded capture observations.
4. Report actual request/capture counts, readable/partial document coverage and material gaps: legal parties, ownership/delivery, cash price, principal, total payable, payment dates, mandatory fees, late/default provisions and beneficiary, early settlement, annexes, version and channel applicability.

Completion of this cycle means the corrected collector is reviewed/tested, the authorized bounded acquisition has run, the evidence/gap register is saved and provenance checks are recorded. It does not mean all five agreements are complete, the market is representative, source permissions have been obtained, or scholar/legal approval exists.
