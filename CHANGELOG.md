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

### Added (2026-10-02 to 2026-10-03, acquisition: FRA-first company database)
- FRA register collector keeps one row per **licence** (`fra:<register>:<number>`, company-number fallback). A shared company number no longer drops a licence: the 2026-09-23 export had lost 60 of 388, including Drive Finance's consumer-finance #26 (Forsa).
- Full FRA register taxonomy, including the consumer-finance **providers** register (sellers financing their own goods), with a role per register type; former-name parsing of FRA Arabic names.
- Robots answered by a security page is its own state (`security_response`) with its own acknowledgement; register-page security responses still stop the run. The access decision is recorded under `acquisition-templates/fra-first-2026-10-02/`.
- FRA-first entity table (`data/source_registry/fra_consumer_finance_entities.csv`, 39 licensees + 13 providers), evidenced brand links (`fra_brand_links.csv`: established/verified/lead), market-label resolution (`not_found_by_name`, never "no FRA match"), and FRA's Islamic-product licences (`fra_islamic_product_licences.csv`: B.TECH #48, Aman #43, ADI #27).
- Pilot widened to seven: B.TECH/Mylo and Drive/Forsa added; valU kept as an established financier.
- 111 FRA publications captured and catalogued (`fra_documents_catalogue.csv`): rulebook with model contracts, Sharia model contracts, Sharia committee decrees and sukuk rulings, legislation, Takaful. The 51 scanned documents (812 pages) were OCR'd with the Windows built-in engine (Arabic reading order restored).
- Comparisons for the scholar: FRA model contracts 2021 vs 2026 (unchanged in substance) and the Sharia Murabaha model vs conventional Model (1). No Sharia finding is made.

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
- With a mirror configured, every decision review is also written to a separate full local archive (`DECISION_REVIEW_ARCHIVE_PATH`, default `data/runtime/decision_reviews_archive.sqlite3`, `off` to disable; kept for `DECISION_REVIEW_RETENTION_DAYS`) so history stays readable if the remote is paused or lost. Each sync pass pings the remote at most every `DECISION_REVIEW_KEEPALIVE_HOURS` (default 24) to avoid free-tier inactivity pausing. `scripts/backup_decision_reviews.py` rebuilds the archive from the remote (idempotent); `--ping-only` is for an external scheduler.
