---
title: 'Export FRA Consumer-Finance Companies to CSV'
type: 'feature'
created: '2026-08-31'
status: 'done'
baseline_commit: '403f1fadc11f8a13dd76af9f54f374ef477d937b'
context:
  - '{project-root}/project-context.md'
  - '{project-root}/.planning/sharia-compliance-chatbot/next-level-plans/L6-EGYPT-FINANCIAL-INSTITUTIONS-EVIDENCE-CORPUS-PLAN.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Mushir's guarded Egypt-institution pipeline has a baseline non-bank registry, but no reproducible export for the currently accessible FRA Arabic consumer-finance register. The existing generic FRA helper assumes an older/English table layout and cannot truthfully represent company number, address, repeated activities, source absence, and per-company technical failures.

**Approach:** Add a dedicated, dependency-free FRA registry acquisition module and thin CLI that paginate the selected type, retrieve each same-host detail page conservatively, preserve one row per company, and produce an Excel-safe CSV plus provenance manifest and raw captures.

## Boundaries & Constraints

**Always:** Export one row per company. Every row must state `regulator=FRA`, `registry_name_ar=سجلات لشركات التمويل`, `fra_type_code=consumer-finance`, and `fra_type_ar=تمويل استهلاكي`. A successfully retrieved page with an unpublished field serializes exactly `No data exists`; a field unavailable because collection failed serializes exactly `Not scraped due to technical error`, with `scrape_status` and a sanitized `scrape_error`. Retain listing data after detail failure. Preserve multiple activity/date pairs losslessly in deterministic JSON. Use UTF-8-SIG, stable listing order, same-host detail URLs, bounded pagination, visited-URL detection, single-threaded requests, configured delay/timeout, raw SHA-256 provenance, and truthful manifest counts. Stop on CAPTCHA, login/paywall, explicit robots disallow, or security controls. Robots unavailable/malformed remains fail-closed by default; an explicit human-approved CLI acknowledgement may permit only a conservative run while recording that state.

**Ask First:** Any non-FRA host access, new dependency, database ingestion, change to the canonical institution schema, or relaxation beyond the narrowly approved unavailable-robots acknowledgement.

**Never:** Infer missing names/details, fuzzy-merge companies, bypass access controls, hard-code 38 companies or two pages, treat registry facts as Sharia compliance evidence, commit full live HTML/CSV artifacts, or modify the older SQLAlchemy placeholder crawler.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Complete run | Accessible paginated register and detail pages | One ordered row per unique company; CSV and manifest totals agree | Exit 0 |
| Source field absent | Detail succeeds but FRA omits a field | Affected field is `No data exists` | Row remains complete |
| Detail failure | Listing row exists; detail times out, fails parsing, or is blocked | Listing values remain; detail-only fields use technical-error sentinel | Row/run partial, sanitized error, nonzero exit |
| Listing/access failure | Universe cannot be enumerated or access policy blocks | No fabricated rows; manifest records blocker | Fail closed, nonzero exit |
| Duplicate/multiple activities | Duplicate listing URL/number or repeated activity rows | One company row; all activity/date pairs retained once | Deduplicate by detail URL, then company number, never fuzzy name |

</frozen-after-approval>

## Code Map

- `src/acquisition/egypt_financial/fra_registry.py` -- source-native record, HTML parsers, access policy, bounded scraper, CSV/manifest/raw export.
- `scripts/scrape_fra_registry.py` -- CLI defaults and exit-code reporting for the consumer-finance run.
- `tests/test_fra_registry.py` -- fixture-driven parser, orchestration, safety, CSV, and manifest tests with no live network.
- `data/fixtures/l6_scrape/fra_consumer_finance/` -- tiny sanitized current-layout listing/detail fixtures.
- `.planning/sharia-compliance-chatbot/docs/l6-egypt-institution-scrape/README.md` -- repeatable command, output, and evidence-boundary documentation.

## Tasks & Acceptance

**Execution:**
- [x] `tests/test_fra_registry.py`, `data/fixtures/l6_scrape/fra_consumer_finance/*` -- write failing tests and sanitized current-layout fixtures for all matrix cases.
- [x] `src/acquisition/egypt_financial/fra_registry.py` -- implement pure parsers, source-native row model, conservative client, deduplication, and artifact writers.
- [x] `scripts/scrape_fra_registry.py` -- expose type/date/output/timeout/delay/access-policy options and meaningful exit codes.
- [x] `.planning/sharia-compliance-chatbot/docs/l6-egypt-institution-scrape/README.md` -- document invocation, fields, sentinels, and non-authoritative boundary.
- [x] `data/runtime/artifacts/l6_scrape/fra_registry/2026-08-31/` -- run the approved live consumer-finance export without adding runtime artifacts to Git.

**Acceptance Criteria:**
- Given two current-layout fixture pages, when scraped, then pagination is deterministic and each unique company detail is fetched once in listing order.
- Given Arabic-only names, four-cell detail rows, and repeated activities, when exported, then every value survives a UTF-8-SIG round trip in one company row.
- Given source absence versus detail failure, when serialized, then the exact distinct sentinels and status/error columns prove which condition occurred.
- Given access blockers or an off-host detail URL, when encountered, then prohibited fetches do not occur and the manifest/exit code truthfully report incompleteness.
- Given the approved live run, when it completes, then discovered-page totals—not historical constants—prove CSV completeness and every row carries the FRA type code and Arabic title.

## Spec Change Log

## Design Notes

Keep missing values as `None` internally until serialization so source absence cannot conceal parser or transport failure. Use a source-native company record because the canonical `InstitutionRegistryRecord` requires English identity and lacks FRA company number, address, and repeated activity fields; canonical ingestion is a separate reviewed adapter.

## Verification

**Commands:**
- `.\.venv\Scripts\python.exe -m pytest tests\test_fra_registry.py -q --timeout=60` -- expected: focused suite passes with no network.
- `.\.venv\Scripts\python.exe -m pytest tests\test_l6_institution_pilot_script.py tests\test_institution_pipeline.py -q --timeout=90` -- expected: existing institution pipeline remains green.
- `.\.venv\Scripts\python.exe scripts\scrape_fra_registry.py --fra-type consumer-finance --fra-type-ar "تمويل استهلاكي" --today 2026-08-31 --delay-seconds 1 --site-terms-review-state no-separate-terms-found` -- expected: truthful CSV/manifest or fail-closed blocker report.

**Observed evidence (2026-08-31):**
- Focused fixture suite: 32 passed.
- Focused plus existing institution regressions: 76 passed.
- Approved live refresh: 38 unique company rows, 0 technical errors, 10 exact source-absence sentinel cells.
- Provenance audit: UTF-8-SIG confirmed, CSV hash matched, and 41/41 raw captures matched SHA-256.
- Environment boundary: repository `.venv` is broken; verification used the available Anaconda Python and is recorded in `deferred-work.md`.

## Suggested Review Order

**Entry point and governed scope**

- Review CLI scope binding, operator acknowledgements, and bounded runtime options first.
  [`scrape_fra_registry.py:46`](../../scripts/scrape_fra_registry.py#L46)

- Trace the single-threaded crawl state machine and truthful completion accounting.
  [`fra_registry.py:343`](../../src/acquisition/egypt_financial/fra_registry.py#L343)

**Access safety and provenance**

- Verify one cached robots policy authorizes every listing and detail path.
  [`fra_registry.py:710`](../../src/acquisition/egypt_financial/fra_registry.py#L710)

- Inspect redirect confinement, response bounds, and configured crawler identity.
  [`fra_registry.py:690`](../../src/acquisition/egypt_financial/fra_registry.py#L690)

- Confirm atomic Excel-safe CSV publication and generation-specific raw evidence.
  [`fra_registry.py:817`](../../src/acquisition/egypt_financial/fra_registry.py#L817)

**Source parsing and row contract**

- Review fail-closed listing parsing, pagination provenance, and candidate-row detection.
  [`fra_registry.py:221`](../../src/acquisition/egypt_financial/fra_registry.py#L221)

- Review Arabic detail extraction, identity checks, and activity/date pairing.
  [`fra_registry.py:282`](../../src/acquisition/egypt_financial/fra_registry.py#L282)

**Verification and operator handoff**

- Start with the complete-run fixture proving ordered, deduplicated UTF-8-SIG output.
  [`test_fra_registry.py:67`](../../tests/test_fra_registry.py#L67)

- Inspect fail-closed enumeration and per-path access regression coverage.
  [`test_fra_registry.py:408`](../../tests/test_fra_registry.py#L408)

- Follow the exact live command, sentinels, blockers, and evidence boundary.
  [`README.md:68`](../../.planning/sharia-compliance-chatbot/docs/l6-egypt-institution-scrape/README.md#L68)
