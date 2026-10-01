---
title: 'Auditable public evidence acquisition'
type: feature
created: '2026-10-01'
status: done
route: full
route_source: auto
review: 'thorough'
review_source: 'auto'
lenses_ran: [blind-hunter, edge-case-hunter, verification-gap, intent-alignment]
review_loop_iteration: 2
baseline_commit: '0c06d607fb0ae233fffdde5790e779cf4ae85b4f'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The reviewed acquisition playbook conflates missing robots with security refusals, overstates completed methods, and lacks a reproducible public capture path. The identity helper has no scoped decision ingestion, fixed-date output, unsafe robots redirects, unbounded bodies and incorrect decoding.

**Approach:** Adopt the reviewed hybrid procedure and implement its public-acquisition foundation: separate scoped decisions, classified obstacles, bounded HTML/PDF transport, immutable runs and literal extraction. User authorized the reviewed proposal with “proceed”; no new policy questions remain for this foundation.

## Boundaries & Constraints

**Always:** Work in `C:/Users/Ahmed/.codex/worktrees/evidence-acquisition/Mushir-Sharia-Bot`; use the primary checkout's `.venv/Scripts/python.exe` for tests. Before every outgoing request, including robots and redirects, invoke `ensure_public_url`. Require an unexpired exact-origin/path-scoped terms/access record with reviewer, reference and dates. Keep robots, terms, security, authentication and reuse separate. Normal missing/empty robots requires current payload-bound acknowledgement; malformed HTML policy, 401/403/challenge, 429 and unreachable policy remain explicit. Source-issued scoped robots exceptions never defeat live security/auth refusals. Preserve raw bytes, content type, SHA-256, URL chain, decision snapshot and extraction lineage. Capture success establishes acquisition, not contractual applicability or Sharia authority.

**Never:** Change legacy FRA/market collectors, chatbot/storage work, historical captures, deployment, model/retrieval code or global URL-safety behavior. No credentials, fingerprint masking, proxy rotation, challenge solving, source outreach, private document intake, automated browser/API discovery, full dossier database or national crawl. No invented reviewed pilot terms or source permissions. Document future channels as planned.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Public evidence | Current scoped decision, valid robots, substantive HTML or PDF | Raw artifact and lineage; literal HTML identity fields; PDF page text/anchors | Unknown clauses remain unknown |
| Policy gap | Missing/expired/revoked/out-of-scope decision or unknown terms | Refusal before content request; reason persisted | Never widen origin/path scope |
| Robots variants | Missing, empty, malformed HTML, denied, throttled, unreachable | Distinct states; only normal missing/empty accepts matching acknowledgement | Historical broad acknowledgement is not imported as current authority |
| Gates | 200 challenge, 401/403, login, paywall | Stop; no successful extraction | Record gate and diagnostic artifact |
| Redirects | Cross-host, private address, restricted destination | Revalidate each outgoing target and decision | No automatic redirects; bounded chain |
| Transient failure | 429/Retry-After or content 5xx/timeout | At most two extra permitted retries, honoring delay; deferred if wait exceeds budget | Never retry security refusal; preserve earlier captures |
| Resource limits | Oversized/decompressed body, request budget, redirect loop, empty shell | Bounded refusal or partial/render-needed status | No complete-evidence claim |
| Extraction | Windows-1256/UTF-8 HTML, encrypted/malformed/scanned PDF | Correct charset; PDF page anchors or explicit extraction gap | Raw artifact remains available |
| Repeat run | Existing output/run identifier | Refuse overwrite; earlier bytes/manifest unchanged | New run required |

</frozen-after-approval>

## Code Map

- `scripts/capture_entity_identity_pages.py`: retain literal extractors; replace transport/CLI and import-time writes.
- `src/acquisition/url_safety.py`: reuse `ensure_public_url` with injectable resolver; no edits.
- `src/acquisition/egypt_financial/fra_registry.py`: immutable-run and robots parser patterns only; broad unavailable override must not be reused.
- `requirements.txt`: declared `httpx`, `pypdf`; no new dependencies necessary.
- `tests/test_fra_registry.py`, `tests/test_egypt_installment_market.py`: fake transport, DNS and immutable-run conventions.
- `_bmad-output/initiative-egypt-market-knowledge/`: playbook, evidence model, architecture, pilot epic/tickets; reviewed proposal is in the primary checkout at the same relative path.

## Tasks & Acceptance

**Execution:**
- [x] `src/acquisition/public_capture.py` — add validated decision records, separate robots classifications, bounded injectable transport, immutable provenance and HTML/PDF capture/extraction.
- [x] `scripts/capture_entity_identity_pages.py` — CLI adapter accepting labelled URL file, explicit decisions file, output root and unique run ID; preserve useful literal fields; no import side effects.
- [x] `tests/test_public_capture.py` — execute every matrix class with deterministic transports, DNS and clock; assert forbidden requests never occur.
- [x] `_bmad-output/initiative-egypt-market-knowledge/evidence-acquisition-playbook.md` — adopt operational procedure, accurate method states, separate public/private retention and source requests.
- [x] `spec-egypt-market-poc/{spec-egypt-market-poc,fact-and-evidence-model,architecture}.md` and `epic-pilot-dossiers/{epic-pilot-dossiers.md,tickets.toml}` — align public foundations, manual/future boundaries and acceptance without claiming the epic complete.
- [x] `acquisition-templates/` — provide valid empty decision JSON, clearly fictional worked record, URL-input example, and five-pilot gap/request task board; document exact CLI and schema. No approved live records.

**Acceptance Criteria:**
- Given fixture public documents and current decisions, when the CLI runs, then a reviewer can verify preserved hashes, source/derived locators and complete attempt/decision records.
- Given any matrix refusal, when capture runs, then no forbidden content request or successful evidence is emitted.
- Given old pilot acknowledgements, when new decisions are configured, then old artifacts remain untouched and no security refusal is reclassified as permission.
- Given the adopted documents, when a reader follows the examples, then commands match the implemented schema and future/private work remains explicitly unimplemented.

## Implementation Notes

Second re-derivation: enforce bounded DNS for collector preflight and production resolution; use linear glob matching and explicit policy-size/rule budgets, not backtracking regex. Verify HTTP framing completeness. Preserve a literal extractor's own normalized source text, exact observation offsets and truncation metadata so its snippets have an unambiguous source despite head/visible-text differences. Production timeouts must follow existing retry/robots classification. Scope Crawl-delay to hostname/current policy, avoid caching transient policy errors, and distinguish short refusal pages from substantive contracts with prohibited-activity headings or CAPTCHA footer assets. Effective OS limits and unavailable-limit refusal require executed worker verification.

Re-derivation after independent review must use RFC 9309 rule specificity/wildcards, canonical request targets and production transport pinned to validated public addresses while retaining TLS hostname verification. Enforce whole-request deadlines and host-wide Retry-After cooldowns. Preserve every request's decision snapshot, safe response headers, wire/decoded lineage and limit-failure attempt; output errors must not trigger network retries. Ignore HTML head metadata for substantive text, check all heading levels, and stop gated robots redirects. Run PDF parsing in an isolated worker with OS memory/CPU and parent wall-time bounds, incrementally bounded page text and explicit per-page OCR gaps. Verify the actual adapter and CLI constructor, changed source-policy hashes, pacing across origins and demonstrated edge fixtures.

KEEP: scoped/dated records, refusal before unauthorized requests, distinct robots states, source-hash binding, raw/decoded artifact hashes, immutable run directories, literal Arabic fields, PDF one-based page numbers, unchanged legacy modules, five-provider zero-request gap example, and documented future/private boundaries.

## Spec Change Log

- 2026-10-01, iteration 2: v2 review demonstrated unbounded resolution/glob matching and the literal source-normalization gap; amended instructions above. KEEP all prior improvements, plus pinned TLS transport, host cooldowns, complete attempt snapshots/headers, page OCR gaps and worker containment. Reverted only this build's code/test files to the baseline and re-derived from preserved KEEP snapshots. Frozen intent unchanged.

- 2026-10-01, iteration 1: review exposed specification gaps in standards-aware policy matching, connected-address safety, whole-request/extraction resource budgets and complete attempt provenance. Added explicit implementation instructions above. Reverted only this build's three code/test files and preserved KEEP snapshots before re-deriving. The frozen intent and approved boundaries remain unchanged. All verification-gap fixes survive the loopback.

## Review Triage Log

Third pass: all remaining findings have localized corrections within the existing public foundation; no public acquisition channel or approval surface is added. Each demonstrated state is covered by a regression. Intent alignment confirms the frozen foundation reading and calls out V3-01's missing branch coverage. No findings are deferred.

| Finding | Verdict | Route | Evidence |
|---|---|---|---|
| B3-01 | high | patch | Verified long password-form page bypasses short-text guard; classify active forms outside optional footer/nav/aside widgets. |
| B3-02 | high | patch | Charset-looking script text overrides UTF-8; only actual meta declarations may supply an HTML charset. |
| B3-03 | medium | patch | Explicitly hidden source text enters the visible projection; exclude hidden attributes/inline hiding styles. |
| B3-04 | medium | patch | Port zero becomes the default origin/port; reject zero explicitly. |
| B3-05 | medium | patch | Truthy nonstring/blank reviewer/reference fields satisfy the schema; require nonblank strings. |
| B3-06 | medium | patch | Timed-out resolver threads survive; bound outstanding resolver work. |
| B3-07 | medium | patch | Repeated full-budget preflights increase the attempt limit; remove redundant checks and document/test the aggregate bound. |
| B3-08 | medium | patch | A blackholed first address consumes the deadline; reserve connection budget for remaining validated addresses. |
| B3-09 | low | patch | Acknowledged empty/missing refreshed policy leaves stale host pacing; clear its old policy delay. |
| B3-10 | medium | patch | Repeated URL attempts lack explicit capture/request join keys; add unique request IDs and capture/policy references. |
| E3-01 | high | patch | Long active login/CAPTCHA gates return success; same root cause as B3-01, plus explicit challenge prompt. |
| E3-02 | high | patch | Acceptance claim repeats the verified long-gate success defect. |
| V3-01 | high | patch | Preverified source_permission terms branch loses issuer/reference guard without any test failure. |

Second pass: findings were assessed individually before grouping. Framing, empty-agent, encoding, resolution and wildcard duplicates remain separate. No finding is deferred. Intent auditor corroborated those implementation gaps and confirmed the documented foundation/exclusion reading.

| Finding | Verdict | Route | Evidence |
|---|---|---|---|
| B2-01 | high | patch | Production read1 accepts premature declared-length EOF; verify framing before completion. |
| B2-02 | high | patch | Empty User-agent is accepted and no matching group permits content. |
| B2-03 | medium | patch | A Forbidden activities heading falsely pauses a public-document hostname. |
| B2-04 | medium | patch | CAPTCHA assets/widgets can falsely classify substantive public terms. |
| B2-05 | medium | patch | Transient robots 503 is cached for 24 hours. |
| B2-06 | medium | patch | Real CaptureStop deadline timeouts bypass documented retry/purpose normalization. |
| B2-07 | medium | bad_spec | Resolution is outside all request deadlines; bounded preflight is required. |
| B2-08 | medium | patch | Only the first public address is connected; bounded address fallback is needed. |
| B2-09 | medium | patch | Crawl-delay leaks between unrelated hosts and never falls after refresh. |
| B2-10 | medium | bad_spec | New demonstrated head/visible normalization mismatch requires explicit literal source and spans; the earlier absence-of-runtime-anchor claim itself remains rejected. |
| E2-01 | high | patch | Duplicates B2-01 declared-length framing defect. |
| E2-02 | high | patch | Corrupt DEFLATE raises uncaught zlib.error and omits its attempt. |
| E2-03 | high | patch | Duplicates B2-02 empty agent policy defect. |
| E2-04 | high | bad_spec | Wildcard regex has demonstrated catastrophic backtracking; use bounded linear matching. |
| E2-05 | medium | bad_spec | Duplicates B2-07 resolution deadline gap. |
| E2-06 | high | patch | Short div/paragraph access denial is captured without a heading. |
| E2-07 | high | patch | Claim repeats uncaught encoding failure and omitted attempt. |
| V2-01 | medium | patch | Preverified: removal of host pause still passes all 88 tests. |
| V2-02 | medium | patch | Preverified: removing OS limits still passes worker tests; assert effective limits and unavailable-limit refusal. |
| V2-03 | medium | bad_spec | Verification reviewer also demonstrated resolver delay exceeding production timeout. |

Each lens item was assessed before grouping. B = blind hunter; E = edge-case hunter; V = verification gap. Duplicate rows intentionally remain. Bad-spec groups require the re-derivation recorded above; no finding is deferred.

| Finding | Verdict | Route | Evidence |
|---|---|---|---|
| B01 | high | bad_spec | Robots wildcard/longest-match enforcement is wrong; fixture demonstrates forbidden requests. |
| B02 | high | bad_spec | Retry-After cooldown is lost across captures and on the final attempt. |
| B03 | medium | bad_spec | Origin pacing permits simultaneous requests to the same hostname on different schemes/ports. |
| B04 | medium | bad_spec | Head title can turn an empty shell into substantive text. |
| B05 | medium | bad_spec | Attempt headers and policy decoded lineage are absent. |
| B06 | medium | bad_spec | Separate robots decisions have no immutable snapshot. |
| B07 | medium | bad_spec | CaptureStop from streamed size limits omits the HTTP attempt. |
| B08 | medium | bad_spec | Artifact OSError is caught as transport error and retried. |
| B09 | medium | bad_spec | PDF expansion occurs before text cap with no extraction deadline. |
| B10 | medium | bad_spec | Mixed scanned/text PDFs conceal per-page OCR gaps. |
| B11 | high | bad_spec | Production HTTPX independently resolves DNS after preflight. |
| B12 | false | reject | Literal observations and full derived text are preserved; automated HTML observation anchors are expressly excluded with dossier integration. Analysts must add claim spans; no runtime passage-addressable claim is made. |
| E01 | high | bad_spec | Same demonstrated rule precedence/wildcard defect as B01. |
| E02 | high | bad_spec | HTTPX normalizes dot segments after exact path approval. |
| E03 | high | bad_spec | Same connection DNS rebinding defect as B11. |
| E04 | medium | bad_spec | Per-read timeout permits trickling indefinitely; no whole-request deadline. |
| E05 | high | bad_spec | Only title/h1 in the first 256KiB are checked; h2 denial is captured. |
| E06 | high | bad_spec | Robots redirect processing precedes checking a security gate. |
| E07 | medium | bad_spec | Same missing limit-attempt record as B07. |
| E08 | medium | bad_spec | Same output-as-transport error as B08. |
| E09 | medium | bad_spec | Same unbounded PDF extraction as B09. |
| E10 | medium | bad_spec | Same mixed-page OCR gap as B10. |
| E11 | medium | bad_spec | Acceptance claim repeats demonstrated omitted HTTP attempt. |
| E12 | high | bad_spec | Acceptance claim repeats demonstrated forbidden robots request. |
| V01 | high | patch | Preverified: mutating adapter follow_redirects still passes all tests. |
| V02 | medium | patch | Preverified: removing source exception hash check still passes all tests. |
| V03 | medium | patch | Preverified: CLI dropping loaded decisions still passes all tests. |

Intent alignment reported twelve descriptive readings. The reusable foundation, supplied-record enforcement, distinguishable access outcomes, preflight calls, byte caps, literal extraction, immutable directories and exclusion boundaries match the approved foundation reading. Its demonstrated policy, connected-address, cooldown, provenance, shell and PDF resource shortcomings are covered individually by B/E rows above. It establishes no live permission, full dossier, launch approval or authenticated source authority; those were never claimed.

## Verification

Final result: 185 acquisition/legacy checks plus 13 URL-safety checks passed (198 total); the empty-decision five-provider run made zero HTTP requests. See [verification record](../initiative-egypt-market-knowledge/public-acquisition-verification-2026-10-01.md).

Final matrix audit: every frozen matrix row is exercised by passing tests in `tests/test_public_capture.py`; actual adapter and worker paths are also exercised. All three review passes are triaged above. Accepted issues are corrected, rejected items have their evidence, and nothing is deferred. Full pilot contracts, outreach, browser/API/OCR automation and private intake remain the frozen exclusions, not completed work.

- Primary Python from this worktree: `-m pytest tests/test_public_capture.py tests/test_fra_registry.py tests/test_egypt_installment_market.py tests/test_summarize_market_roles.py -q --timeout=90`.
- Fixture CLI invocation, JSON/TOML parsing, artifact hashes, local document links and `git diff --check`.
- No live provider-access claim follows from fixture verification.
