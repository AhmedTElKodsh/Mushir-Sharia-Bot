"""PostgreSQL (e.g. Supabase free tier) decision review storage.

The durable copy of the review trail. Same interface as the SQLite store so the
two can be mirrored. Appends are idempotent on review_id, which makes replaying
the local outbox safe. The connection URL carries credentials and is never logged.
"""
from __future__ import annotations

from typing import Iterable

from src.models.decision_audit import DecisionAuditRecord

SCHEMA = (
    """CREATE TABLE IF NOT EXISTS decision_reviews (
        review_id TEXT PRIMARY KEY,
        request_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        recorded_at TIMESTAMPTZ NOT NULL,
        payload JSONB NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS decision_reviews_request ON decision_reviews(request_id)",
    "CREATE INDEX IF NOT EXISTS decision_reviews_recorded ON decision_reviews(recorded_at)",
)
INSERT = ("INSERT INTO decision_reviews (review_id, request_id, session_id, recorded_at, payload) "
          "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (review_id) DO NOTHING")


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
        return (record.review_id, record.request_id, record.session_id, record.recorded_at, record.model_dump_json())

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

    def purge_older_than(self, days: int) -> int:
        if type(days) is not int or days < 1:
            raise ValueError("retention must be a positive number of days")
        with self._connect() as conn:
            return conn.execute("DELETE FROM decision_reviews WHERE recorded_at < now() - make_interval(days => %s)",
                                (days,)).rowcount
