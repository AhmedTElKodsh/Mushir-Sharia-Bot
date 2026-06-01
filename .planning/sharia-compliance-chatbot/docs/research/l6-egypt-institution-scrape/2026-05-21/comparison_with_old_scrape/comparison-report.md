# Current scrape vs old workbook comparison

Old workbook: `data\runtime\artifacts\l6_scrape\full_scrape\2026-05-21\Egypt_Financial_Institutions_old.xlsx`
Current scrape: `data\runtime\artifacts\l6_scrape\full_scrape\2026-05-21\bank_scrape_results.csv`

## Scope

- Old workbook total registry rows: 2,154.
- Old bank registry rows: 36.
- Old non-bank registry rows not in current scrape scope: 2,118.
- Current scrape bank candidates: 32.
- Current scrape pages fetched: 61.
- Current engine operation rows: 57 across 14 institutions.
- Current manifest says the 2026-05-21 run is only a bank official-site slice; capital-market, insurance, and non-bank-finance rows were not crawled in this output.

## Old workbook sector coverage

- bank: 36
- capital_market: 797
- insurance: 996
- non_bank_finance: 325

## Current bank scrape status

- extracted: 11
- access_check_failed: 7
- failed: 7
- insufficient_text: 4
- partial_extracted: 3

## Bank-name comparison

- Exact normalized matches between old bank registry and current candidates: 32.
- Old bank rows missing from current candidates: 4.
- Current candidates not found in old bank registry: 0.

## Old bank rows missing from current candidates

- Emirates National Bank of Dubai S.A.E. (manual-review nearest current: National Bank Of Kuwait - Egypt (NBK), fuzzy score 0.69)
- Arab Investment Bank (manual-review nearest current: Arab International Bank, fuzzy score 0.698)
- Ahli United Bank - Egypt (manual-review nearest current: The United Bank, fuzzy score 0.839)
- National Bank of Greece (manual-review nearest current: National Bank of Egypt, fuzzy score 0.821)

## Current rows not found in old bank registry

- None: every current bank candidate has an exact normalized match in the old bank registry.

## Review files

- `data\runtime\artifacts\l6_scrape\full_scrape\2026-05-21\comparison_with_old_scrape\comparison_summary.json`
- `data\runtime\artifacts\l6_scrape\full_scrape\2026-05-21\comparison_with_old_scrape\old_registry_sector_counts.csv`
- `data\runtime\artifacts\l6_scrape\full_scrape\2026-05-21\comparison_with_old_scrape\current_bank_scrape_status_counts.csv`
- `data\runtime\artifacts\l6_scrape\full_scrape\2026-05-21\comparison_with_old_scrape\matched_current_bank_rows.csv`
- `data\runtime\artifacts\l6_scrape\full_scrape\2026-05-21\comparison_with_old_scrape\old_bank_rows_missing_from_current.csv`
- `data\runtime\artifacts\l6_scrape\full_scrape\2026-05-21\comparison_with_old_scrape\current_bank_rows_not_in_old.csv`
- `data\runtime\artifacts\l6_scrape\full_scrape\2026-05-21\comparison_with_old_scrape\current_operations_by_institution.csv`
