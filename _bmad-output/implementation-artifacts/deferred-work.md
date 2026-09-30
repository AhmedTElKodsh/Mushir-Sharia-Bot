# Deferred Work

- 2026-08-31 — The repository-local `.venv` is pre-existing and broken: its
  `pyvenv.cfg` points to missing `C:\Python314\python.exe` and an older checkout
  path. Repair or recreate that environment in a separate maintenance task.
  This FRA story was verified with `C:\Users\Asd\anaconda3\python.exe`
  (Python 3.13.9, pytest 8.4.2); the fallback environment does not include
  `pytest-timeout`, so verification used pytest without the `--timeout` option.
- source_spec: `_bmad-output/implementation-artifacts/spec-runtime-1-shared-evidence-contracts.md`
  summary: Enforce semantic mechanism evidence and claim-scoped verdict eligibility during runtime adoption.
  evidence: Structural source classes cannot distinguish marketing self-labels from mechanism clauses; blocked conclusion gates may coexist with independently supported facts under the adopted dual-query contract. Runtime must enforce that separation explicitly.

- source_spec: `_bmad-output/implementation-artifacts/spec-runtime-1-shared-evidence-contracts.md`
  summary: Add private document locators when V1.7 schedule intake is implemented.
  evidence: CaptureManifest currently requires public HTTP(S) provenance; local uploads need a distinct immutable locator and the planned consent/redaction controls. Private agreement intake is excluded from V1.6.
