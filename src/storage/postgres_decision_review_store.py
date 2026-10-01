"""PostgreSQL (e.g. Supabase free tier) decision review storage.

The durable copy of the review trail. Same interface as the SQLite store so the
two can be mirrored. Appends are idempotent on review_id, which makes replaying
the local outbox safe. The connection URL carries credentials and is never logged.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from src.models.decision_audit import CLASSIFICATION_FIELDS, DecisionAuditRecord, classify

SCHEMA = (
    """CREATE TABLE IF NOT EXISTS decision_reviews (
        review_id TEXT PRIMARY KEY,
        request_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        recorded_at TIMESTAMPTZ NOT NULL,
        payload JSONB NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS decision_reviews_request ON decision_reviews(request_id)",
    "CREATE INDEX IF NOT EXISTS decision_reviews_recorded ON decision_reviews(recorded_at)",
    # Additive classification columns; rows written before them keep nulls (payload stays authoritative).
    *(f"ALTER TABLE decision_reviews ADD COLUMN IF NOT EXISTS {field} TEXT" for field in CLASSIFICATION_FIELDS),
    *(f"CREATE INDEX IF NOT EXISTS decision_reviews_{field} ON decision_reviews({field})"
      for field in ("lane", "status", "language", "deciding_gate")),
)
INSERT = ("INSERT INTO decision_reviews (review_id, request_id, session_id, recorded_at, payload, "
          f"{', '.join(CLASSIFICATION_FIELDS)}) VALUES (%s, %s, %s, %s, %s{', %s' * len(CLASSIFICATION_FIELDS)}) "
          "ON CONFLICT (review_id) DO NOTHING")


class PostgresDecisionReviewStore:
    def __init__(self, database_url: str, *, connect_timeout: int = 3, psycopg_module=None):
        if not database_url:
            raise ValueError("a PostgreSQL URL is required")
        if psycopg_module is None:
            try:
                import psycopg as psycopg_module
            except ImportError as exc:
                raise RuntimeError("psycopg is required for the PostgreSQL decision review store") from exc
        self._psycopg = psycopg_module
        self._url = database_url
        self._timeout = connect_timeout
        with self._connect() as conn:
            for statement in SCHEMA:
                conn.execute(statement)

    def _connect(self):
        # Short timeout: an unreachable database must not stall every request.
        return self._psycopg.connect(self._url, connect_timeout=self._timeout)

    @staticmethod
    def _row(record: DecisionAuditRecord):
        record = DecisionAuditRecord.model_validate(record)
        values = classify(record)
        return (record.review_id, record.request_id, record.session_id, record.recorded_at, record.model_dump_json(),
                *(values[field] for field in CLASSIFICATION_FIELDS))

    def append(self, record: DecisionAuditRecord) -> str:
        with self._connect() as conn:
            conn.execute(INSERT, self._row(record))
        return DecisionAuditRecord.model_validate(record).review_id

    def append_many(self, records: Iterable[DecisionAuditRecord]) -> list[str]:
        rows = [self._row(record) for record in records]
        if not rows:
            return []
        with self._connect() as conn:  # One transaction: a replay either lands whole or not at all.
            for row in rows:
                conn.execute(INSERT, row)
        return [row[0] for row in rows]

    def get(self, review_id: str) -> DecisionAuditRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM decision_reviews WHERE review_id = %s", (review_id,)).fetchone()
        if not row:
            return None
        payload = row[0]
        return (DecisionAuditRecord.model_validate(payload) if isinstance(payload, dict)
                else DecisionAuditRecord.model_validate_json(payload))

    def ping(self) -> None:
        """Cheapest possible round trip; counts as database activity for free-tier inactivity pausing."""
        with self._connect() as conn:
            conn.execute("SELECT 1")

    def iter_records(self, batch: int = 500):
        """Every stored record in (recorded_at, review_id) order, paged by keyset so memory stays flat."""
        cursor_at, cursor_id = datetime(1970, 1, 1, tzinfo=timezone.utc), ""
        while True:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT recorded_at, review_id, payload FROM decision_reviews "
                    "WHERE (recorded_at, review_id) > (%s, %s) ORDER BY recorded_at, review_id LIMIT %s",
                    (cursor_at, cursor_id, batch)).fetchall()
            for recorded_at, review_id, payload in rows:
                yield (DecisionAuditRecord.model_validate(payload) if isinstance(payload, dict)
                       else DecisionAuditRecord.model_validate_json(payload))
            if len(rows) < batch:
                return
            cursor_at, cursor_id = rows[-1][0], rows[-1][1]

    def purge_older_than(self, days: int) -> int:
        if type(days) is not int or days < 1:
            raise ValueError("retention must be a positive number of days")
        return 0  # Early POC review hold applies to direct remote maintenance too.
