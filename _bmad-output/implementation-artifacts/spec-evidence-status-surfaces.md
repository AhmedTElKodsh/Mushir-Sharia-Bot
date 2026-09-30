# Evidence status on answer surfaces

Status: implemented and locally verified; live deployment pending

Implements evidence-safe-runtime ticket 4 (CAP-5). Answer-facing numeric retrieval confidence is replaced by descriptive evidence availability, per-source capture dates and elapsed days. A capture date is not a source-validity or correctness claim. Unknown, malformed, timezone-free and future dates stay unknown; no acquisition timestamp is invented.

## Implementation

- Canonical answer serialization strips legacy score metadata, including nested records, and citation confidence. Cached answers use the same boundary.
- Every canonical answer includes an evidence summary. Insufficient and clarification statuses remain explicit even when citations exist. Source dates are attached only when available in source metadata.
- ApplicationService no longer computes a mean retrieval score as confidence. Incomplete answers are queued for review independently of that score.
- REST, SSE and the streaming smoke script expose evidence metadata. Citation dates follow the same validation policy as evidence summaries.
- Web replies show localized evidence status and capture age, including restored conversations. Historical messages without this new metadata show unavailable evidence status.
- CLI uses ApplicationService and its session-bound gates rather than a separate RAG/generation path. It honors configured disclaimer acknowledgement and supports an explicit acknowledgement flag.

## Verification

- Eleven newly written boundary tests failed before implementation.
- Initial combined API/cache/contract/SSE checks: 101 passed. Subsequent focused suite: 18 passed, including real REST/SSE, CLI invocation, cache provenance and date edge cases.
- Independent review reproduced CLI acknowledgement bypass, misleading old-history labels and invalid citation dates. All fixed; reviewer independently re-ran 18 passing boundary tests.
- Full Python run: **993 passed, 11 failed, 47 skipped**, 122.07 seconds, `data/runtime/artifacts/poc-evidence-surface-tests.xml`. Ten failures are the existing unsigned mocked ruling-correctness gaps. The eleventh was an SSE test still expecting numeric confidence; migrated it to evidence status, explicit unknown age and a no-confidence payload assertion. After that test-only change, the combined API/cache/CLI/contract/SSE suite passed **117 checks**.
- Final focused boundary suite: **19 passed**, including a source-backed static assertion that CLI and browser templates contain no confidence/relevance-score widgets. `git diff --check` passed.
- Browser setup initially lacked local dependencies and the pinned browser. Installed dependencies from the existing lockfile and pinned Chromium shell without changing package versions. Chromium verified EN/AR display and reload persistence plus historical citation fallback (**3 passed**). The fourth case failed to navigate with `ERR_INSUFFICIENT_RESOURCES`; Windows reported roughly 720 MB free physical memory. No task-owned browser/server processes remained. A bounded retry of the known-date case with `NODE_OPTIONS=--max-old-space-size=256` passed (**1 passed**). All four scenarios have executed successfully, across those runs. No unrelated processes were stopped.
- Inspected screenshots `test-results/evidence-status-en.png` and `test-results/evidence-status-ar.png`; evidence labels and unknown capture dates are readable in both layouts. Browser tests use intercepted fixture streams and do not verify retrieval or live provider output. Server startup still reports the missing local retrieval index.

## Limits

Descriptive source availability is not claim support or approval. Positive approved-outcome rendering, universal typed review rows, named-offer integration, reviewed cards/cases and live deployment remain separate unfinished requirements. Internal retrieval rankings and historical scholar-review records are not reinterpreted as answer probabilities.
