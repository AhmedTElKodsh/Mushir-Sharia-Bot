# L6 Egypt Institution Scrape Workstream

Last refreshed: 2026-06-01
Current app version: V1.5 (`1.5.0`)

This folder documents the public-source evidence corpus planned for Egyptian financial institutions and their financial operations.

The detailed planning source is:

- `.planning/sharia-compliance-chatbot/next-level-plans/L6-EGYPT-FINANCIAL-INSTITUTIONS-EVIDENCE-CORPUS-PLAN.md`

## Boundary

This workstream prepares evidence and evaluation data. It does not make Mushir a fatwa engine and does not make scraped labels authoritative.

The scraper should collect:

- regulator-backed institution records;
- official websites and public disclosures;
- tariffs, fees, product pages, terms, contracts, model contracts, annual reports, prospectuses, sukuk documents, fund documents, and policy wordings;
- source URLs, timestamps, content hashes, extraction status, and evidence spans.

The engine may propose AAOIFI mappings and initial risk labels. For the crawl-first phase, these become Mushir engine assessment rows with blank human-scholar-review fields; scholar review is a later improvement step, not a blocker before public crawling.

## Implementation Folders

Planned tracked inputs:

- `data/source_registry/` - small registry seeds and source configuration.
- `data/fixtures/l6_scrape/` - tiny test fixtures only.

Runtime output:

- `data/runtime/artifacts/l6_scrape/` - raw pages, PDFs, extracted text, crawl logs, and errors. This folder is for local/runtime artifacts and should not become a normal source-control dump.

Future code should extend the existing acquisition/governance direction:

- `src/governance/institution_registry.py` - canonical data contracts, registry indexes, access decisions, artifact records, operation records, machine mappings, scholar reviews, and user-fact override contracts.
- `src/governance/institution_pipeline.py` - fixture-safe executable helpers for workbook loading, bounded discovery, access-controlled artifact fetching, local artifact storage, text extraction, operation extraction, AAOIFI mapping candidate generation, database-ready Mushir engine assessment export, bilingual scholar-review list export, scholar-review CSV import/export, accepted-gold-case export, and pilot gating.
- `src/acquisition/` - still reserved for future live crawl adapters once the pilot gate is ready.

## Current Code Status

Implemented and covered by focused tests:

- workbook/CSV/mapping loaders that emit validated `InstitutionRegistryRecord` rows;
- discovery runner with configured attempt budgets and no inferred URLs;
- access-control-first public artifact fetcher and local store under an `data/runtime/artifacts/l6_scrape` compatible layout;
- deterministic HTML/text extraction and evidence-span operation extraction;
- machine-only AAOIFI mapping candidates that remain review inputs, not truth;
- database-ready engine assessment export with institution name, operation/contract, Mushir engine review, AAOIFI references, and blank human-scholar-review columns;
- scholar-facing bilingual review lists, including `scholar_review_list_bilingual.csv`, `scholar_review_list_en.csv`, and `scholar_review_list_ar.csv`, with the same `review_item_number` and `operation_id` in Arabic and English so reviewers can connect matching entities;
- scholar-review CSV import/export plus accepted-gold-case projection for the later improvement layer;
- pilot gate that blocks full scrape approval until mixed coverage, hard-case gap handling, captured artifacts, and extracted operations exist.

## V1.5 Runtime Evidence Status

The 2026-06-01 V1.5 run produced the first guarded bank-slice evidence export:

- Official registry completion loaded 2,154 baseline institutions: 36 banks, 797 capital-market entities, 996 insurance entities, and 325 non-bank finance entities.
- CBE official bank PDF access was blocked by upstream security, and FRA capital-market/insurance register pages were blocked by CAPTCHA; both were recorded as gaps.
- `bank-evidence-scrape` discovered 32 bank website candidates, scraped 14, failed or blocked 18, fetched 73 public pages, extracted 69 operation records, and exported 69 machine-proposed AAOIFI mapping rows.
- Output folder: `data/runtime/artifacts/l6_scrape/full_scrape/2026-06-01/`.
- Key files: `bank_scrape_results.csv`, `engine_assessment_rows.csv`, `scholar_review_list_bilingual.csv`, `chunk_ready_spans.jsonl`, and `manifest.json`.

These outputs are review inputs only. They are not runtime answer authority and are not scholar-reviewed ground truth.

## 2026-08-31 Consumer-Finance Registry Refresh

The dedicated FRA typed-register command completed the `consumer-finance` /
`تمويل استهلاكي` slice from the current Arabic registry:

- 2 listing pages fetched;
- 38 listing records and 38 unique company rows;
- 38 detail pages fetched successfully;
- 0 technical-error rows and 0 duplicate detail URLs or company numbers;
- output: `data/runtime/artifacts/l6_scrape/fra_registry/2026-08-31/`.

The FRA robots endpoint returned non-robots authorization content, so this run
used the documented, human-approved unavailable-robots acknowledgement. The
registry and detail pages themselves remained public and returned no CAPTCHA or
security-control page. The acknowledgement did not override an explicit robots
disallow. The exact approved refresh command was:

```powershell
.\.venv\Scripts\python.exe scripts\scrape_fra_registry.py --fra-type consumer-finance --fra-type-ar "تمويل استهلاكي" --today 2026-08-31 --delay-seconds 1 --site-terms-review-state no-separate-terms-found --acknowledge-unavailable-robots
```

These rows remain regulator identity facts and are not Sharia
compliance judgments or runtime-eligible knowledge.

## Safe Pilot Command

### FRA typed company-register export

The dedicated FRA registry command exports one row per company while retaining
the FRA type on every row. For consumer finance:

```powershell
.\.venv\Scripts\python.exe scripts\scrape_fra_registry.py --fra-type consumer-finance --fra-type-ar "تمويل استهلاكي" --today 2026-08-31 --delay-seconds 1 --site-terms-review-state no-separate-terms-found
```

Output is written under
`data/runtime/artifacts/l6_scrape/fra_registry/<date>/` as an Excel-safe
UTF-8-SIG CSV, `manifest.json`, and hashed raw HTML captures. Each execution
uses a unique `raw/<run-id>/` capture directory so a shorter rerun cannot mix
current evidence with stale files. CSV and manifest publication use atomic file
replacement, with the manifest committed last. Runtime output is ignored by
Git; only the small sanitized fixtures are tracked.

The CSV always includes `regulator`, `registry_name_ar`, `fra_type_code`, and
`fra_type_ar`. A successfully retrieved FRA page that does not publish a field
uses the exact value `No data exists`. A field unavailable because of a timeout,
blocked detail page, parser failure, or another collection problem uses
`Not scraped due to technical error`, plus `scrape_status` and a sanitized
`scrape_error`. Multiple activity/date pairs are retained in `activities_json`
without creating duplicate company rows.

The command checks robots policy before registry access, stays single-threaded,
rechecks the loaded policy for every pagination/detail path, honors any larger
published crawl delay, uses bounded pagination and response sizes, rejects
cross-origin URLs/redirects, and stops on CAPTCHA, login/paywall, HTTP
401/403/429, explicit robots disallow, or another security control. Blockers
are classified in the manifest as `robots_unavailable`, `robots_disallowed`,
`blocked_by_security`, `requires_login`, `document_not_public`, or
`rate_limited`. If the robots endpoint is missing, unavailable, or returns
non-robots content, the default is fail-closed. Only a human-reviewed run may add
`--acknowledge-unavailable-robots`; that flag never overrides an explicit
disallow or a target-page security control.

The default crawler identity can be replaced with a reviewed operator contact
using `--user-agent`. Before a live run, review any published FRA terms and use
the acknowledgement flag only for the exact unavailable-robots condition that
was manually inspected. The required `--site-terms-review-state` records whether
no separate terms page was identified or published terms were reviewed as
compatible. Raw robots content is retained and hashed whenever a
response body is received so the access decision remains auditable.

Values beginning with Excel formula trigger characters are prefixed with an
apostrophe in the CSV. The raw hashed HTML remains the unmodified source record.

This export contains regulator identity facts only. It does not create Sharia
compliance evidence, scholar-reviewed ground truth, or runtime eligibility.

Run the fixture-backed pilot before any live crawl:

```powershell
python scripts\run_l6_institution_pilot.py --mode fixture-pilot --today 2026-05-20
```

The command loads the baseline workbook, selects a small mixed pilot, exercises bounded discovery and artifact capture with local fixture content, exports machine mapping candidates, writes a fixture gold-case CSV, and emits a manifest under `data/runtime/artifacts/l6_scrape/metadata/`.

This is a pipeline readiness run, not live regulator revalidation and not production scholar approval.

Run live regulator/source access revalidation:

```powershell
python scripts\run_l6_institution_pilot.py --mode live-regulator-revalidation --today 2026-05-20 --timeout-seconds 20 --delay-seconds 1
```

This checks the known regulator/source URLs from the workbook through robots.txt plus a conservative reachability probe, then writes `data/runtime/artifacts/l6_scrape/live_revalidation/<date>/manifest.json` and `regulator_source_access.csv`.

Run the full-scrape gate:

```powershell
python scripts\run_l6_institution_pilot.py --mode full-scrape --today 2026-05-20 --timeout-seconds 20 --delay-seconds 1 --max-targets 36 --max-pages-per-target 5
```

The gate refuses broad scraping unless official or reviewed-discovery institution URLs are available. For the bank slice, public bank-directory profile pages may only be discovery aids; they do not make a URL authoritative by themselves. The live crawl then fetches a bounded number of same-domain operation/product pages per institution. The output includes crawl results, machine-mapping CSV, `engine_assessment_rows.csv` with human-scholar-review columns intentionally blank, and bilingual scholar-review lists where Arabic and English rows share the same review number and operation ID.

Any exploratory bank-slice output remains review input only. Non-bank sectors still require official website discovery before crawling.

Run the V1.5 pre-review bank evidence scrape directly:

```powershell
python scripts\run_l6_institution_pilot.py --mode bank-evidence-scrape --today 2026-06-01 --timeout-seconds 20 --delay-seconds 0.25 --max-targets 36 --max-pages-per-target 6
```

This mode intentionally skips the scholar-review precondition because it only builds review files. It keeps all exported machine mappings non-runtime-eligible.

Rerun only failed or low-quality bank targets:

```powershell
python scripts\run_l6_institution_pilot.py --mode full-scrape --today 2026-05-20 --timeout-seconds 20 --delay-seconds 1 --max-targets 36 --max-pages-per-target 5 --rerun-status failed,insufficient_text
```

Reruns write to `data/runtime/artifacts/l6_scrape/full_scrape_rerun/` and keep the primary full-scrape ledger intact.

Still not approved:

- live full-registry crawling across every sector before the crawl-first bank slice is stable;
- runtime answer-flow use of institution pre-knowledge before the crawled corpus is reviewed and promoted;
- any attempt to bypass blocked, gated, login-only, or anti-bot-protected content.

## Safety Rules

- Use regulator and official sources first.
- Treat third-party search as discovery help only.
- Stop after bounded research attempts and record the gap.
- Respect robots.txt, terms, rate limits, login walls, CAPTCHA, paywalls, and access controls.
- Mark missing contracts as `not_publicly_available`; never infer them.
- Keep user-supplied facts above stored institutional assumptions during future answers.
