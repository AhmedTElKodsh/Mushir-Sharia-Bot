# Deferred Work

- 2026-08-31 — The repository-local `.venv` is pre-existing and broken: its
  `pyvenv.cfg` points to missing `C:\Python314\python.exe` and an older checkout
  path. Repair or recreate that environment in a separate maintenance task.
  This FRA story was verified with `C:\Users\Asd\anaconda3\python.exe`
  (Python 3.13.9, pytest 8.4.2); the fallback environment does not include
  `pytest-timeout`, so verification used pytest without the `--timeout` option.
