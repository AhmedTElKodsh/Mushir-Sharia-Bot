# POC implementation validation — 2026-09-30

Baseline revision: `3f59ddfe44d6c31ec77f82f7fd5fc4c51f2adb35`.

## Restored environment

Created the ignored `.venv` with Python 3.12.14 and installed `requirements.txt` plus `requirements-dev.txt` using uv. No execution policy or Application Control changes were made.

## Baseline evidence

- Unscoped `python -m pytest -q --timeout=90` collected installed BMad tooling tests and failed importing their `helpers` module. Added `testpaths = tests` in `pytest.ini` so the default command targets the product suite; tooling tests remain explicitly addressable.
- Product baseline `python -m pytest tests -q --timeout=90`: **668 passed, 16 failed, 47 skipped**, before shared-contract implementation. Offline Hugging Face/Transformers mode was set for this run.
- Ten failures came from eager `sentence_transformers` import in `scripts/ingest.py`; Windows Application Control blocks the native PyTorch extension. Loading that runtime now occurs only when embedding is requested, after the existing input/catalog guards. This makes file-selection and provenance tests independent of a native model installation. Actual embedding execution remains unverified and subject to the same Windows policy.
- After this repair, `python -m pytest tests/test_ingest_bilingual.py tests/test_api_schemas.py tests/test_scholar_review.py tests/test_source_governance.py -q --timeout=60 --tb=short`: **60 passed**.

## Other baseline failures to resolve in subsequent runtime work

- Four tests in `tests/test_concept_ontology.py` depend on `data/concept_ontology`, which is absent and has no tracked files/history in this checkout. The loader returns an empty ontology; `get('late_penalty')` raises `KeyError`. Do not invent an approved ruling seed to make these tests pass.
- `tests/test_l1_contracts.py::test_application_service_passes_source_family_filter_and_strict_metadata_gate` expects `SS-03, SS-08, SS-19, SS-28`, but the current route returns `SS-03, SS-08` without the missing ontology additions.
- `tests/evaluation/test_critical_goldset.py::TestCriticalGoldSet::test_ruling_correctness[GC-005]` expects `PROHIBITED`, while the fixture-backed runtime returns `INSUFFICIENT_DATA`. This is a mismatch with the old fixture expectation, not evidence of an unsafe permissibility answer. It requires review during the approved-rule runtime migration; changing the expectation alone would not establish correctness.

## Shared-contract implementation checkpoint

- Added `src/models/evidence.py` and `src/governance/rule_cards.py` with corresponding focused tests. Includes distinct fact statuses/scopes, exact-span and user-turn provenance, decimal monetary values, dossier observations, gate/review envelopes, and approved-only rule-card selection.
- Latest focused run: **155 passed** (`tests/test_evidence_contracts.py tests/test_rule_cards.py`). Includes rejection of overlapping rule outcomes rather than relying on row order.
- Combined contracts and existing ingestion/API-schema/scholar-review/source-governance run: **202 passed** before the subsequent 13 focused regression cases were added; those additional cases passed in the latest 155-test focused run.
- Implementation subagent stopped on a usage-limit error. Parent completed the interrupted test updates and added adversarial checks. Independent BMad review and runtime adoption remain pending; this checkpoint does not mark ticket 1 or the POC complete.

## Final foundation verification

- Four independent review lenses completed. Fixed citation authority bypasses, cross-session review provenance, duplicate active facts, conflicting capture identities, duplicate gate results, unknown-field access provenance, and weak YAML ambiguity tests. Runtime semantic evidence checks and V1.7 private locators remain explicitly deferred to their planned stories.
- Focused boundary suite: **229 passed**.
- Full product suite: **847 passed, 6 failed, 47 skipped**, 83.02 seconds. The six failures are exactly those listed above after removal of the ten ingestion import failures. Saved JUnit: `data/runtime/artifacts/poc-contract-tests.xml`.
- A repeat intermediate boundary run timed out importing SciPy through the text splitter. Deferring Chroma and text-splitter imports resolved that preflight dependency. A subprocess regression verifies importing ingestion loads none of Torch, SentenceTransformers, Chroma or the splitter.

## Evidence limits

Local tests use controlled fixtures. No live provider generation, model-index rebuild, market recrawl, scholar approval or deployment has been performed in this validation slice. A passing structural contract test does not establish that a quoted source is truthful, a reviewer identity is authentic, or the full V1.6 POC is release-ready.

## Structural clarification continuation

See `spec-structure-clarification.md` for implementation and independent review evidence. Latest full run: **975 passed, 10 failed, 47 skipped**, 111.03 seconds (`data/runtime/artifacts/poc-structure-final-tests.xml`). All six previous ambiguity/clarification assertions now pass. After the final cross-topic personal-fact binding fix, **74 focused checks passed**; the reviewer independently confirmed all **22 structural tests passed**. The full run preceded that final fix. Ten ruling-correctness failures remain unresolved because the approved runtime outcome path is incomplete. No gold labels were altered, and no scholar approval or live deployment is claimed.

## Evidence-status surfaces continuation

See `spec-evidence-status-surfaces.md`. Latest full run: **993 passed, 11 failed, 47 skipped**, 122.07 seconds (`data/runtime/artifacts/poc-evidence-surface-tests.xml`). Ten existing ruling-correctness failures remain; migrated the additional obsolete SSE confidence assertion and verified **117 combined API/cache/CLI/contract/SSE checks** after that test-only edit. Final dedicated evidence suite: **19 passed**. Chromium passed all four evidence-label scenarios across an initial 3-pass run and a bounded low-memory retry of the known-date case. EN/AR screenshots inspected. No production deployment or live retrieval/provider verification is claimed.

## Generic mechanism continuation

See `spec-mechanism-unknown-gate.md`. Final full suite: **1090 passed, 12 failed, 47 skipped**, 110.03 seconds (`data/runtime/artifacts/poc-mechanism-final-tests.xml`). Reviewer independently verified **96 generic-mechanism checks**. The remaining failures comprise ten existing ruling-correctness assertions and two PENDING gold-label conflicts, TC-F1 and TC-G1, which assume mechanisms from generic descriptions. Original gold labels are unchanged; `mechanism-label-review.json` records them with the source dataset hash for adjudication. Generic language, incidental insurance/manufacturing/interest, negation, session carry-over and an Arabic substring no longer supply a mechanism through the tested paths. User-reported mechanism labels cannot authorize approved-card selection.


## Status on 2026-10-01

After the review-fix passes (commits `eabea95`..`69eb5a2`, `79e9aa6`): full suite **1,234 passed, 12 failed, 47 skipped**; Playwright **30/30**. The 12 failures are the ten gold ruling cases and TC-F1/TC-G1, all awaiting scholar decisions; no gold labels were changed. The decision-review store (committed before delivery, 365-day retention) and the removal of confidence scores are described in `.planning/sharia-compliance-chatbot/docs/runtime-safety-model.md`. No scholar has been appointed.
