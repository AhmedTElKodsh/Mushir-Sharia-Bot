# Public acquisition inputs

The [playbook](../evidence-acquisition-playbook.md) contains the executable command. `access-decisions.empty.json` grants nothing. `access-decisions.fictional.json` demonstrates the schema on a reserved example domain; it is not provider approval. `pilot-urls.txt` uses dated seed URLs, not freshly verified offers or permitted routes.

## Decision schema

The file is a JSON array. Required fields: unique `decision_id`, canonical `origin` without path/query, nonempty exact `allowed_paths`, `terms_state`, `terms_reference`, `reviewed_by`, timezone-aware `reviewed_at` and `expires_at`. Identifiers, reviewers, references and dates must be nonblank strings. `revoked` defaults false. Overlapping active decisions for the same URL are ambiguous and refused.

Paths are exact, including query strings. `/terms` does not include `/terms/`, `/terms?lang=ar`, another domain, or a redirect target. List `/robots.txt` explicitly. Origins include protocol and non-default port. Fragments, credentials, port zero, dot segments and backslashes are refused. Encode non-ASCII URL characters with percent escapes.

`terms_state`: `reviewed_allowed`, `source_permission`, `unknown`, `restricted`. Only the first two permit requests. `source_permission` requires the permission object's `issuer` and `reference`. Record an actual dated clause/review/permission reference in `terms_reference`; operator sign-off is not website-owner permission. The collector enforces the supplied record but does not authenticate its legal authority. The reviewing operator is responsible for accuracy.

`reuse_rights` is descriptive metadata, defaults `internal_research_only`, and never grants publication rights by itself. Private/customer intake is unsupported.

## Missing/empty robots acknowledgement

After a reviewed permitted request records normal missing or genuinely empty/comment-only UTF-8 robots, inspect the preserved response and add:

```json
"robots_acknowledgement": {
  "state": "robots_missing",
  "sha256": "SHA256_OF_DECODED_ROBOTS_RESPONSE"
}
```

Use `robots_empty` for a genuinely empty policy. The hash covers decoded bytes including comments/BOM, not the URL or a description. HTML app shells, security/auth refusals, rate limits and server/network failures cannot use this acknowledgement. Historical `robots_unavailable_acknowledged: true` records are not accepted. Create a new run after review; preserve the failed first run.

## Source-issued robots exception

Only an actual documented source permission can support an exception to a disallowed path. A current record covering the URL must include:

```json
"source_permission": {
  "issuer": "Verified source representative",
  "reference": "Stored written permission reference",
  "robots_exception": true,
  "robots_sha256": "SHA256_OF_CURRENT_DECODED_ROBOTS_RESPONSE"
}
```

The source document establishes the scope, methods, dates and reuse rights. A changed policy hash invalidates the exception. Live security/login challenges and unapproved destinations still stop capture. Source-side changes or exports resolve those restrictions outside this code.

## Outputs

Run identifiers are simple unique names; existing directories are refused. Read `summary.json` and final `capture` events in `manifest.jsonl`; independently recompute raw/decoded/extraction hashes from their locators. PDF extraction gaps do not imply readable terms. Analysts separately record document/offer versions, effective dates and clause applicability.

Tests use fake transport, DNS, clock and sleep, with no live provider calls. Run `python -m pytest tests/test_public_capture.py -q` using the repository environment.
