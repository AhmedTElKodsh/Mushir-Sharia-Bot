# Current scrape vs old_scraping folder comparison

Old folder: `D:\AI Projects\Freelance\Sabry\Mushir-Sharia-Bot\data\runtime\artifacts\l6_scrape\full_scrape\2026-05-21\old_scraping`
Current folder: `D:\AI Projects\Freelance\Sabry\Mushir-Sharia-Bot\data\runtime\artifacts\l6_scrape\full_scrape\2026-05-21`

## Executive summary

- Old `old_scraping` folder contains 2,154 non-empty registry rows across four sector workbooks.
- Current 2026-05-21 scrape output contains 32 bank website candidates and 57 extracted bank operation/evidence rows.
- The current output is bank-only. It does not include current scrape rows for capital-market, insurance, or non-bank-finance entities.
- All 32 current bank candidates are present in `Banks_old.xlsx` after normalized-name matching.
- `Banks_old.xlsx` has 4 bank registry rows that are not in the current bank scrape candidate list.
- Current operation/evidence rows are not directly comparable to the old workbooks because the old files are registry lists, not operation/evidence scrape outputs.

## Sector coverage

- bank: old 36, current scrape rows 32, current engine rows 57
- capital_market: old 797, current scrape rows 0, current engine rows 0
- insurance: old 996, current scrape rows 0, current engine rows 0
- non_bank_finance: old 325, current scrape rows 0, current engine rows 0

## Current bank scrape status

- access_check_failed: 7
- extracted: 11
- failed: 7
- insufficient_text: 4
- partial_extracted: 3

## Bank-name comparison

- Exact normalized matches from current bank candidates to old bank workbook: 32
- Current bank candidates missing from old bank workbook: 0
- Old bank workbook rows missing from current candidates: 4

## Old bank rows missing from current candidates

- Ahli United Bank - Egypt (old row 21; nearest current: The United Bank, similarity 0.706)
- Arab Investment Bank (old row 18; nearest current: Arab International Bank, similarity 0.606)
- Emirates National Bank of Dubai S.A.E. (old row 15; nearest current: Qatar National Bank Alahli S.A.E, similarity 0.636)
- National Bank of Greece (old row 37; nearest current: National Bank of Egypt, similarity 0.696)

## Current extracted operation rows by institution

- AL Ahli Bank of Kuwait - Egypt: 5
- Arab Banking Corporation – Egypt S.A.E: 5
- Arab International Bank: 5
- Banque Du Caire: 5
- HSBC Bank Egypt S.A.E: 5
- Mashreq Bank: 5
- Societe Arabe Internationale de Banque: 5
- Suez Canal Bank: 5
- Faisal Islamic Bank of Egypt: 5
- Banque Misr: 5
- National Bank Of Kuwait - Egypt (NBK): 4
- The United Bank: 1
- Abu Dhabi Islamic Bank - Egypt: 1
- Agricultural Bank of Egypt: 1

## Generated review files

- `D:\AI Projects\Freelance\Sabry\Mushir-Sharia-Bot\data\runtime\artifacts\l6_scrape\full_scrape\2026-05-21\comparison_with_old_scrape\old_scraping_folder_summary.json`
- `D:\AI Projects\Freelance\Sabry\Mushir-Sharia-Bot\data\runtime\artifacts\l6_scrape\full_scrape\2026-05-21\comparison_with_old_scrape\old_scraping_folder_sector_counts.csv`
- `D:\AI Projects\Freelance\Sabry\Mushir-Sharia-Bot\data\runtime\artifacts\l6_scrape\full_scrape\2026-05-21\comparison_with_old_scrape\old_scraping_folder_matched_current_bank_rows.csv`
- `D:\AI Projects\Freelance\Sabry\Mushir-Sharia-Bot\data\runtime\artifacts\l6_scrape\full_scrape\2026-05-21\comparison_with_old_scrape\old_scraping_folder_old_bank_rows_missing_from_current.csv`
- `D:\AI Projects\Freelance\Sabry\Mushir-Sharia-Bot\data\runtime\artifacts\l6_scrape\full_scrape\2026-05-21\comparison_with_old_scrape\old_scraping_folder_current_bank_rows_not_in_old.csv`
- `D:\AI Projects\Freelance\Sabry\Mushir-Sharia-Bot\data\runtime\artifacts\l6_scrape\full_scrape\2026-05-21\comparison_with_old_scrape\old_scraping_folder_current_bank_status_counts.csv`
- `D:\AI Projects\Freelance\Sabry\Mushir-Sharia-Bot\data\runtime\artifacts\l6_scrape\full_scrape\2026-05-21\comparison_with_old_scrape\old_scraping_folder_current_operations_by_institution.csv`
