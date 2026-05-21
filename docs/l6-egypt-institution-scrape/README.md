# L6 Egypt Institution Scrape Workstream

This folder documents the public-source evidence corpus planned for Egyptian financial institutions and their financial operations.

The detailed planning source is:

- `.kiro/specs/sharia-compliance-chatbot/next-level-plans/L6-EGYPT-FINANCIAL-INSTITUTIONS-EVIDENCE-CORPUS-PLAN.md`

## Boundary

This workstream prepares evidence and evaluation data. It does not make Mushir a fatwa engine and does not make scraped labels authoritative.

The scraper should collect:

- regulator-backed institution records;
- official websites and public disclosures;
- tariffs, fees, product pages, terms, contracts, model contracts, annual reports, prospectuses, sukuk documents, fund documents, and policy wordings;
- source URLs, timestamps, content hashes, extraction status, and evidence spans.

The engine may propose AAOIFI mappings and initial risk labels, but those labels remain `machine_proposed` until reviewed by a qualified Sharia scholar.

## Implementation Folders

Planned tracked inputs:

- `data/source_registry/` - small registry seeds and source configuration.
- `data/fixtures/l6_scrape/` - tiny test fixtures only.

Runtime output:

- `artifacts/l6_scrape/` - raw pages, PDFs, extracted text, crawl logs, and errors. This folder is for local/runtime artifacts and should not become a normal source-control dump.

Future code should extend the existing acquisition/governance direction:

- `src/governance/institution_registry.py` - canonical data contracts, registry indexes, access decisions, artifact records, operation records, machine mappings, scholar reviews, and user-fact override contracts.
- `src/governance/institution_pipeline.py` - fixture-safe executable helpers for workbook loading, bounded discovery, access-controlled artifact fetching, local artifact storage, text extraction, operation extraction, AAOIFI mapping candidate generation, scholar-review CSV import/export, accepted-gold-case export, and pilot gating.
- `src/acquisition/` - still reserved for future live crawl adapters once the pilot gate is ready.

## Current Code Status

Implemented and covered by focused tests:

- workbook/CSV/mapping loaders that emit validated `InstitutionRegistryRecord` rows;
- discovery runner with configured attempt budgets and no inferred URLs;
- access-control-first public artifact fetcher and local store under an `artifacts/l6_scrape` compatible layout;
- deterministic HTML/text extraction and evidence-span operation extraction;
- machine-only AAOIFI mapping candidates that remain review inputs, not truth;
- scholar-review CSV import/export plus accepted-gold-case projection;
- pilot gate that blocks full scrape approval until mixed coverage, hard-case gap handling, captured artifacts, extracted operations, and scholar-reviewed gold data exist.

## Safe Pilot Command

Run the fixture-backed pilot before any live crawl:

```powershell
python scripts\run_l6_institution_pilot.py --mode fixture-pilot --today 2026-05-20
```

The command loads the baseline workbook, selects a small mixed pilot, exercises bounded discovery and artifact capture with local fixture content, exports machine mapping candidates, writes a fixture gold-case CSV, and emits a manifest under `artifacts/l6_scrape/metadata/`.

This is a pipeline readiness run, not live regulator revalidation and not production scholar approval.

Run live regulator/source access revalidation:

```powershell
python scripts\run_l6_institution_pilot.py --mode live-regulator-revalidation --today 2026-05-20 --timeout-seconds 20 --delay-seconds 1
```

This checks the known regulator/source URLs from the workbook through robots.txt plus a conservative reachability probe, then writes `artifacts/l6_scrape/live_revalidation/<date>/manifest.json` and `regulator_source_access.csv`.

Run the full-scrape gate:

```powershell
python scripts\run_l6_institution_pilot.py --mode full-scrape --today 2026-05-20 --timeout-seconds 20 --delay-seconds 1 --max-targets 36 --review-file artifacts/l6_scrape/review/<pilot-id>/real_scholar_reviews.csv
```

The gate refuses broad scraping unless a real, non-fixture accepted scholar-review file exists and official or reviewed-discovery institution URLs are available. For the bank slice, public bank-directory profile pages may only be discovery aids; they do not make a URL authoritative by themselves. The output includes crawl results and a machine-mapping CSV for the next real scholar-review pass.

Any exploratory bank-slice output remains review input only. Non-bank sectors still require official website discovery before crawling.

Rerun only failed or low-quality bank targets:

```powershell
python scripts\run_l6_institution_pilot.py --mode full-scrape --today 2026-05-20 --timeout-seconds 20 --delay-seconds 1 --max-targets 36 --rerun-status failed,insufficient_text --review-file artifacts/l6_scrape/review/<pilot-id>/real_scholar_reviews.csv
```

Reruns write to `artifacts/l6_scrape/full_scrape_rerun/` and keep the primary full-scrape ledger intact.

Still not approved:

- live full-registry crawling across every sector;
- runtime answer-flow use of institution pre-knowledge before reviewed corpus data exists;
- any attempt to bypass blocked, gated, login-only, or anti-bot-protected content.

## Safety Rules

- Use regulator and official sources first.
- Treat third-party search as discovery help only.
- Stop after bounded research attempts and record the gap.
- Respect robots.txt, terms, rate limits, login walls, CAPTCHA, paywalls, and access controls.
- Mark missing contracts as `not_publicly_available`; never infer them.
- Keep user-supplied facts above stored institutional assumptions during future answers.
