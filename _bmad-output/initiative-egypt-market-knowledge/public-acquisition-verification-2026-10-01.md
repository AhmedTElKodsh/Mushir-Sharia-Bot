# Public acquisition foundation verification

Completed 2026-10-01. This is fixture and executable-foundation verification; it establishes no live provider permission, current contract, completed dossier or legal clearance.

The operative [playbook](evidence-acquisition-playbook.md), [input/schema templates](acquisition-templates/README.md), [five-pilot gap board](acquisition-templates/pilot-gap-board.md) and [implementation/review log](../implementation-artifacts/spec-public-evidence-acquisition.md) describe the result. The original baseline SHA-256 remains `1222e97fb440ef5e7edf480379cfc1356e91f7cfda5a2e914a8a7186f6084ddd`.

## Executed verification

- 185 passed: `tests/test_public_capture.py` (134) plus existing FRA, Egyptian market and role-summary regressions (51).
- 13 passed, 73 intentionally deselected: the existing URL-safety subset in `tests/test_review_followups.py`.
- JSON decisions load through the real schema; ticket TOML parses; local documentation links resolve; `git diff --check` passes.
- The documented five-provider empty-decision CLI run records five `access_decision_missing_or_expired` gaps and zero HTTP requests. Its summary and manifest are under `data/runtime/artifacts/l6_scrape/public_capture/pilot-access-gap-20261001/` in the primary workspace. These are gap records, not new provider captures.
- Raw, decoded and extracted fixture artifacts are independently hashed in tests. Production adapter tests retain its real HTTP framing/connection code with fake DNS/sockets/TLS wrappers: no live provider requests. The real PDF worker installs limits; a child process queries the effective 512 MiB memory/eight-second CPU bounds. Parent timeout, unavailable limits, compressed expansion and mixed-page OCR gaps are executed cases.

## Review resolution

Four independent lenses ran in each of three review passes: blind hunter, edge cases, verification gaps and intent alignment. The complete per-finding verdicts are retained in the implementation log. Accepted findings were corrected; the initial HTML-anchor claim was rejected under the then-stated surface, while a later concrete source-normalization gap was addressed with literal source text and offsets. Nothing is deferred from this public foundation.

The final regressions cover policy-rule precedence and wildcards, malformed/missing/empty/unreachable policy states, changed source hashes, required source-permission terms references, gated redirects, long and Arabic gates, optional footer widgets, hidden content, HTTP framing, bounded DNS and connection fallback, host-wide cooldowns, output errors without network retries, immutable run refusal, charset fidelity, page anchors and linked capture/request provenance.

Full automatic link discovery, browser/API acquisition, OCR automation, dossier-store integration, outreach and private intake remain outside this build. The five provider contract/relationship gaps stay open. Successful acquisition and extraction do not approve applicability or a Sharia verdict. No push or deployment was performed.
