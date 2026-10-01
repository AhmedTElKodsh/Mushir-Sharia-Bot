# Acquisition procedure walkthrough

Target: the operating evidence-acquisition playbook and its provider request and five-pilot gap-board templates.

Review state: in progress. Original Block 1 and revised Blocks 2–4 accepted by the user; the operational Intent and Block 5's Track 2 order were accepted on 2026-10-01; Block 6 is next. The overall review is not complete.

## Blocks

- [x] **Block 1 — Intent — original intent accepted; historical spec text unchanged.**

  **Problem:** The reviewed acquisition playbook conflates missing robots with security refusals, overstates completed methods, and lacks a reproducible public capture path. The identity helper has no scoped decision ingestion, fixed-date output, unsafe robots redirects, unbounded bodies and incorrect decoding.

  **Approach:** Adopt the reviewed hybrid procedure and implement its public-acquisition foundation: separate scoped decisions, classified obstacles, bounded HTML/PDF transport, immutable runs and literal extraction. User authorized the reviewed proposal with “proceed”; no new policy questions remain for this foundation.

  Source: the Problem and Approach paragraphs in [the public evidence acquisition implementation spec](spec-public-evidence-acquisition.md#intent).

- [x] **Block 2 — Broad strokes — accepted; shape revised during review.**

  1. **Choose one arrangement.** The research operator selects a provider, product, merchant/channel and applicable period, adding customer cohort where relevant. Output: a scoped research question, using the [priority proposal](../initiative-egypt-market-knowledge/acquisition-templates/provider-request-priorities-2026-10-01.md) to order attention; the proposed ranking remains unaccepted.
  2. **Define what evidence would close the gap.** The operator and analyst identify the missing party, relationship, document or clause and the supporting artifact needed. Output: a task with an owner, closure criterion and next action on the [five-pilot gap board](../initiative-egypt-market-knowledge/acquisition-templates/pilot-gap-board.md).
  3. **Select an eligible route.** The operator chooses public capture, a source-supplied document bundle or permitted supervised research, recording access conditions and stated rights for that route. Output: a documented route under the [playbook](../initiative-egypt-market-knowledge/evidence-acquisition-playbook.md); automated public capture additionally requires the current exact-scope [input record](../initiative-egypt-market-knowledge/acquisition-templates/README.md).
  4. **Acquire and preserve the documents.** The operator requests or captures the applicable agreement, incorporated terms and schedules, preserving originals, provenance, versions, dates and the source's qualifications. Output: an evidence pack or a recorded failed/partial attempt, following the [request package](../initiative-egypt-market-knowledge/acquisition-templates/provider-request.md); source delivery and supervised collection remain distinct from implemented automated capabilities.
  5. **Verify and decide the next action.** The analyst checks the parties, completeness, applicable period and material clauses against exact passages, then records supported, conflicting and unknown fields. Output: a verified record of the scoped facts, or an unresolved gap with an owner and next action under the [playbook's acceptance procedure](../initiative-egypt-market-knowledge/evidence-acquisition-playbook.md#6-capture-acceptance-and-provenance); scholar-approved interpretation is a separate gate.

- [x] **Block 3 — Task scope and access routes — accepted; revised during review.**

  **Separate discovery scope from claim scope.** The operator starts discovery with a specific provider/offer lead, target fact and known arrangement details, retaining unknown financier/version fields as clarification targets; claim acceptance later needs a demonstrated match to product, merchant, financier, channel, period and relevant cohort. Output: a scoped research question with known, unresolved and not-applicable fields, following the [task-scope procedure](../initiative-egypt-market-knowledge/evidence-acquisition-playbook.md#1-acquire-the-missing-fact-then-choose-the-transport); these labels describe the manual review record, not new runtime enums.

  **Specify a closable task.** The operator and analyst record task ID, the question, needed artifact, exact closure condition, owner and next action; a dated identity/relationship clarification may precede the agreement-pack request. Output: a task on the [gap board](../initiative-egypt-market-knowledge/acquisition-templates/pilot-gap-board.md), using the [provider briefs](../initiative-egypt-market-knowledge/acquisition-templates/provider-request-priorities-2026-10-01.md); closing an identity question does not close obligations or the entire dossier.

  **Choose the route and classify readiness.** Select an eligible route capable of supplying the needed artifact with the least unnecessary work: public capture, source-supplied files or permitted manual public review; no universal transport order is assumed. Output: a manual route record stating method, access/rights reference, scope, limits, stop/defer trigger, current readiness (eligible, awaiting clarification, blocked or capability deferred) and next action; automated requests require the [exact-scope input record](../initiative-egypt-market-knowledge/acquisition-templates/README.md), while the [obstacle table](../initiative-egypt-market-knowledge/evidence-acquisition-playbook.md#3-obstacle-decision-table) and [source request](../initiative-egypt-market-knowledge/acquisition-templates/provider-request.md) guide alternatives, and gated/private intake remains deferred to its separate protocol.

- [x] **Block 4 — Capture and claim acceptance — accepted; revised during review.**

  **Check provenance independently of byte integrity.** The operator retains originals, task/capture identifiers, source/owner verification, URL chain where relevant, access references, capture/receipt time and hashes, recording failures separately. Output: a retrievable artifact with a source-verification assessment under the [capture foundation](../initiative-egypt-market-knowledge/evidence-acquisition-playbook.md#implemented-public-capture-foundation); a hash verifies stored bytes, not issuer authenticity or factual authority.

  **Check readability and completeness separately.** The analyst checks legibility/extraction first, then page coverage, referenced annexes, amendments, schedules, language and omissions; any derived text retains its parent artifact, tool/version, page/span and correction lineage. Output: two independent assessments under the [acceptance procedure](../initiative-egypt-market-knowledge/evidence-acquisition-playbook.md#6-capture-acceptance-and-provenance); missing annexes keep affected claims unresolved even when an identity clause is readable, and browser/OCR automation remains unimplemented.

  **Check applicability before accepting a claim.** The analyst verifies the parties, version, effective period, merchant/channel and relevant cohort, keeping publication, effective and capture dates separate; a failed refresh preserves historical evidence but leaves present applicability subject to reassessment. Output: a recorded arrangement/version match or explicit mismatch/unknown under the [acceptance procedure](../initiative-egypt-market-knowledge/evidence-acquisition-playbook.md#6-capture-acceptance-and-provenance).

  **Check exact support and record the decision.** Map each literal observation to a page/span, table cell or screen; a second analyst checks material Arabic fields against the original, with corrections retained. Output: observed, conflicting or unknown fields on the [material-field matrix](../initiative-egypt-market-knowledge/acquisition-templates/pilot-gap-board.md#material-field-matrix), including reviewer, time and next action for gaps; an unobserved clause is unknown, and reuse rights and scholar-approved interpretation remain separate gates.

  *Amended 2026-10-01 by the Block 5 decision:* with no second analyst available, a material field is recorded as `single-review`, marked `[HUMAN-REVIEW:NEEDED]`, and supports no accepted claim until a second human check against the original is recorded. See the [playbook's human-review marks](../initiative-egypt-market-knowledge/evidence-acquisition-playbook.md#human-review-marks).

- [x] **Block 5 — Operational Intent, five-provider priority and concrete requests — accepted 2026-10-01 (operational Intent and Track 2 order).**

  **Accept the operational Intent.** The user accepted the [operational Intent](../initiative-egypt-market-knowledge/acquisition-templates/provider-request-priorities-2026-10-01.md#proposed-operational-intent) inside this block: five scoped provider dossiers, each with an applicable, traceable evidence pack or an explicit unresolved record with owner and next action. Output: the outcome that Blocks 2–4 serve; analyst verification, acquisition/reuse rights and scholar-approved interpretation remain separate decisions.

  **Mark human review, then order two tracks.** Anything that needs or would benefit from a human reviewer carries `[HUMAN-REVIEW:NEEDED]` or `[HUMAN-REVIEW:BENEFICIAL]`, with the reviewer role and the exact question. Marked items are optimised to be showable at the human review around 2026-10-15; unmarked work is optimised for the best eventual evidence. Output: the two orders below, under the [playbook's human-review marks](../initiative-egypt-market-knowledge/evidence-acquisition-playbook.md#human-review-marks).

  *Track 1 — marked items, showable by ~2026-10-15:*

  | # | Mark | Item | Reviewer and question | Showable form |
  |---|---|---|---|---|
  | 1 | NEEDED | HALAN-01 dispatch draft | Operator (user): confirm the scope, verify the recipient and send | Issue-ready draft in the [Halan brief](../initiative-egypt-market-knowledge/acquisition-templates/provider-request-priorities-2026-10-01.md#5-halan--merchant-relationship-before-general-contract-collection) |
  | 2 | NEEDED | Material fields per arrangement | Scholar: which fields does the applicable rule make material? | [Material-field matrix](../initiative-egypt-market-knowledge/acquisition-templates/pilot-gap-board.md#material-field-matrix) with every field still open |
  | 3 | NEEDED | Single-review Arabic names and fields, including the 61 `pending_client_review` registry rows and the أمان everyday-word matches | Client or second reviewer: does the recorded literal match the original? | Original artifact and recorded literal, side by side |
  | 4 | NEEDED | Scope and recipient for the VALU-01, CONTACT-01, SOUHOOLA-01 and AMAN-01 briefs | Operator: select product, merchant/channel and period; verify the official recipient | Briefs with the remaining blanks listed |
  | 5 | BENEFICIAL | valU app company vs. legal financier | Scholar: whose obligations should the rule evaluate? | Worksheet passages naming both companies |
  | 6 | BENEFICIAL | Souhoola's CI/BM/“Contact Investment” names | Client or scholar: is any reconciliation known? | All names verbatim; conflict still open |
  | 7 | BENEFICIAL | Contact brand spread across six entities | Scholar: does the clarifying question ask for the right fact? | The bot's clarification next to the unresolved entities |
  | 8 | BENEFICIAL | Halan: insufficient evidence, request pending | Scholar: is the refusal shown at the right point? | Gap record and the withheld answer |
  | 9 | BENEFICIAL | Aman's EN/AR parent-name mismatch | Client: which observation is current? | Both footers verbatim |

  *Track 2 — unmarked request content, best evidence eventually (order accepted 2026-10-01):*

  | Priority | Provider/task | First request and expected evidence | Why this position |
  |---|---|---|---|
  | 1 | Halan / HALAN-01 | Dated evidence naming the financier for the selected merchant offer; then the applicable agreement and schedules, keeping consumer finance and factoring separate | User decision: send now. The whole dossier is blocked on one relationship fact. User-supplied context, not yet evidenced: Halan may itself sell goods in-app (sourced mainly via 2B and others), so the scope may be its own offer `[HUMAN-REVIEW:NEEDED]`. |
  | 2 | Contact / CONTACT-01 | Identify the legal financier for the selected arrangement through a dated document, listing “Contact Investment for Consumer Finance” as an observed name to confirm or deny; then that owner's pack | One answer can unlock Contact's agreement request and inform SOUHOOLA-01. |
  | 3 | valU / VALU-01 | Applicable blank finance agreement and all schedules, with the financier and app/payment operator roles distinguished | Identity is already supported by valU's own terms; the remaining gap is the operative contract. |
  | 4 | Souhoola / SOUHOOLA-01 | Complete applicable terms/agreement and annexes, plus authoritative dated clarification of the observed names | Partly informed by CONTACT-01, but issued without waiting for it. |
  | 5 | Aman / AMAN-01 | Applicable consumer-finance agreement and schedules, with licensee, holding and microfinance roles kept distinct | Role separation; holding-company text alone is insufficient. |

  Prepare all briefs in parallel. No brief waits for another provider's reply, and every dispatch passes Track 1's operator review first.

  **Make each brief issuable.** The operator resolves product, merchant/channel and period where needed, explicitly marks remaining discovery unknowns, verifies the official recipient/document-owner role and identifies the requested artifacts and research-use terms. Output: a scoped agreement request or a focused clarification request using the [provider-specific briefs](../initiative-egypt-market-knowledge/acquisition-templates/provider-request-priorities-2026-10-01.md#provider-specific-request-briefs) and [common package](../initiative-egypt-market-knowledge/acquisition-templates/provider-request.md); only the HALAN-01 draft is near issue-ready, and no outreach has been sent.

  **Close only the supported task.** Apply Block 4's provenance, readability, completeness, applicability, exact-support and review-status checks to each response, assigning follow-ups to unanswered fields. Output: verified task-level evidence or an explicit gap on the [board](../initiative-egypt-market-knowledge/acquisition-templates/pilot-gap-board.md). Halan is no longer held back as a control: its insufficient-evidence status stays factual until adequate evidence arrives, and then it changes.

- [ ] **Block 6 — Periphery and historical artifacts — unvisited.** Review supporting and historical records that provide context for the current operating procedure.
