# Acquisition procedure walkthrough

Target: the operating evidence-acquisition playbook and its provider request and five-pilot gap-board templates.

Review state: in progress. Original Block 1 and revised Blocks 2–4 accepted by the user; Block 5 is current. The overall review is not complete.

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

- [ ] **Block 5 — Five-provider priority and concrete requests — in progress.**

  **Order attention by evidence impact and readiness.** Use the dated [identity worksheet](../initiative-egypt-market-knowledge/pilot-entity-resolution.md) and [priority proposal](../initiative-egypt-market-knowledge/acquisition-templates/provider-request-priorities-2026-10-01.md) to prioritize material gaps, specific existing leads and arrangement dependencies, without assuming market share or response probability. Output: the proposed operator-attention order below; prepare all briefs in parallel, and do not wait for one provider's reply before preparing another.

  | Priority | Provider/task | First request and expected evidence |
  |---|---|---|
  | 1 | valU / VALU-01 | Applicable blank finance agreement and all schedules, with the financier and app/payment operator roles distinguished. |
  | 2 | Contact / CONTACT-01 | Identify the legal financier for the selected arrangement through a dated supporting document; then request that owner's agreement pack. |
  | 3 | Souhoola / SOUHOOLA-01 | Complete applicable terms/agreement and annexes, plus authoritative dated clarification of the observed CI/BM/“Contact Investment” names. |
  | 4 | Aman / AMAN-01 | Applicable consumer-finance agreement and schedules, with licensee/holding/microfinance roles kept distinct. |
  | 5 | Halan / HALAN-01 | Dated evidence of the selected merchant–financier relationship, then its applicable agreement and schedules, distinguishing consumer finance from factoring. |

  **Make each brief issuable.** The operator resolves product, merchant/channel and period where needed, explicitly marks remaining discovery unknowns, verifies the official recipient/document-owner role and identifies the requested artifacts and research-use terms. Output: a scoped agreement request or a focused clarification request using the [provider-specific briefs](../initiative-egypt-market-knowledge/acquisition-templates/provider-request-priorities-2026-10-01.md#provider-specific-request-briefs) and [common package](../initiative-egypt-market-knowledge/acquisition-templates/provider-request.md); current placeholders are not ready-to-send letters and no outreach has been sent.

  **Close only the supported task.** Apply Block 4's provenance, readability, completeness, applicability and exact-support checks to each response, assigning follow-ups to unanswered fields. Output: verified task-level evidence or an explicit gap on the [board](../initiative-egypt-market-knowledge/acquisition-templates/pilot-gap-board.md); the ranking remains unaccepted until this block is accepted, and Halan's insufficient-evidence status changes when adequate evidence arrives.

- [ ] **Block 6 — Periphery and historical artifacts — unvisited.** Review supporting and historical records that provide context for the current operating procedure.
