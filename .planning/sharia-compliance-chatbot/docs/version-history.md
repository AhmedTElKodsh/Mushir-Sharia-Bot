# Mushir Version History

Last refreshed: 2026-06-01

## V1.5 (`1.5.0`) - 2026-06-01

V1.5 marks the current app version.

Runtime/versioning:

- FastAPI metadata reports `1.5.0`.
- `/api`, `/health`, and `/ready` return `version: 1.5.0` and `version_label: V1.5`.
- `src.__version__`, `package.json`, `package-lock.json`, and the chat header expose the same version.

Egypt institution evidence corpus:

- Official registry completion loaded 2,154 baseline institutions: 36 banks, 797 capital-market entities, 996 insurance entities, and 325 non-bank finance entities.
- Live source checks recorded CBE upstream security blocking and FRA CAPTCHA blocking rather than bypassing access controls.
- The guarded bank evidence scrape discovered 32 bank website candidates, scraped 14, failed or blocked 18, fetched 73 public pages, extracted 69 operation records, and exported 69 machine-proposed AAOIFI mapping rows.
- Outputs live under `data/runtime/artifacts/l6_scrape/full_scrape/2026-06-01/`.
- All institution operation/mapping rows remain review inputs only and are not runtime answer authority.

Verification:

- `.\.venv\Scripts\python.exe -m pytest tests\test_institution_db.py tests\test_l6_institution_pilot_script.py -q --timeout=90`
- Additional targeted API/static versioning checks should be run before release packaging.
