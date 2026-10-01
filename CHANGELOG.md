# Changelog

All notable changes to Mushir. Versions follow the [release ladder](_bmad-output/initiative-egypt-market-knowledge/spec-egypt-market-poc/release-ladder.md). Earlier history is in [version-history.md](.planning/sharia-compliance-chatbot/docs/version-history.md).

## Unreleased (V1.6 dual-lane prototype, in build)

### Added
- Scholar-approved rule cards and an approved-card evaluator: a Sharia verdict requires an approved card; without one, judgment questions defer and are queued for scholar review.
- Described-operation lane for personal deals: typed facts from explicit user wording, conflict reconciliation, at most two clarification questions, then `INSUFFICIENT_DATA` naming the documents needed.
- Mechanism gate: generic wording (instalment, financing, تقسيط) never establishes a contract type.
- Structure clarification for tawarruq and fixed-return sukuk questions.
- Evidence status on every answer (`metadata.evidence`: sources, capture date, age).
- Decision-review store (SQLite): every answer is committed before delivery; `DECISION_REVIEW_DB_PATH`, `DECISION_REVIEW_RETENTION_DAYS` (default 365), purge at startup and every 24 hours; docker-compose mounts `./data/runtime`.
- Optional `REVIEWER_REGISTRY_PATH` restricting who may approve rule cards and verifications.

### Changed (API contract)
- `Citation.confidence_score` is removed from REST and SSE citation payloads and replaced by `captured_at`. Answers no longer carry any confidence score. No API version bump was made; revisit before external consumers exist.
- `metadata.decision_review` (full fact snapshot) is no longer returned by `/api/v1/query` or the stream `done` event; clients keep `metadata.review_receipt`.
- Scholar review queue items store `system_confidence` as `null` when the answer carried no score (previously a fabricated `0.0`).

### Known
- 12 tests wait for scholar decisions (GC-003, 005, 007, 008, 009, 010, 012, 016, 017, 019; TC-F1, TC-G1). They expect verdicts that the rule-card gate now withholds. No scholar has been appointed.

## V1.5 (`1.5.0`), 2026-06-01

- Versioned app (API metadata, health/readiness, chat header).
- Guarded Egypt institution evidence corpus: 2,154 registry records; bounded bank scrape (14 sites, 69 operation records for review).
- Decision reviews can be mirrored to PostgreSQL (e.g. Supabase free tier): set `DECISION_REVIEW_DATABASE_URL` (or a `postgres://` `DATABASE_URL`). SQLite stays the local commit point and keeps only `DECISION_REVIEW_LOCAL_RETENTION_DAYS` (default 7) of confirmed rows; unconfirmed rows wait in a local outbox and are replayed in the background. `DECISION_REVIEW_REQUIRE_MIRROR=true` makes an unreachable mirror withhold answers instead of queueing. `/ready` reports `decision_review_mirror` (outbox depth, last error class).
