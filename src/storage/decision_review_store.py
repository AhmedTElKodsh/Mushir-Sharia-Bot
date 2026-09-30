"""Atomic local decision review storage; failed writes cannot acknowledge delivery."""
import os
from datetime import UTC, datetime, timedelta
from contextlib import contextmanager
from pathlib import Path
import sqlite3

from src.models.decision_audit import DecisionAuditRecord


DEFAULT_DB_PATH = "data/runtime/decision_reviews.sqlite3"
DEFAULT_RETENTION_DAYS = 365


class SQLiteDecisionReviewStore:
    def __init__(self, path):
        if str(path) == ":memory:":
            raise ValueError("decision review storage requires a durable file")
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("CREATE TABLE IF NOT EXISTS decision_reviews (review_id TEXT PRIMARY KEY, request_id TEXT NOT NULL, session_id TEXT NOT NULL, recorded_at TEXT NOT NULL, payload TEXT NOT NULL)")
            conn.execute("CREATE INDEX IF NOT EXISTS decision_reviews_request ON decision_reviews(request_id)")

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        try:
            conn.execute("PRAGMA synchronous=FULL")
            with conn:
                yield conn
        finally:
            conn.close()

    def append(self, record: DecisionAuditRecord) -> str:
        record = DecisionAuditRecord.model_validate(record)
        with self._connect() as conn:
            conn.execute("INSERT INTO decision_reviews VALUES (?, ?, ?, ?, ?)", (
                record.review_id, record.request_id, record.session_id, record.recorded_at.astimezone(UTC).isoformat(), record.model_dump_json()))
        return record.review_id

    def purge_older_than(self, days: int) -> int:
        """Delete records past the retention window; returns the number removed."""
        if type(days) is not int or days < 1:
            raise ValueError("retention must be a positive number of days")
        cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        with self._connect() as conn:
            return conn.execute("DELETE FROM decision_reviews WHERE recorded_at < ?", (cutoff,)).rowcount

    def get(self, review_id: str) -> DecisionAuditRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM decision_reviews WHERE review_id=?", (review_id,)).fetchone()
        return DecisionAuditRecord.model_validate_json(row[0]) if row else None


def configured_decision_store():
    return SQLiteDecisionReviewStore(os.getenv("DECISION_REVIEW_DB_PATH") or DEFAULT_DB_PATH)


def configured_retention_days() -> int:
    """Conservative default: keep a year of review records unless the operator sets a window."""
    try:
        days = int(os.getenv("DECISION_REVIEW_RETENTION_DAYS") or DEFAULT_RETENTION_DAYS)
    except ValueError:
        return DEFAULT_RETENTION_DAYS
    return days if days >= 1 else DEFAULT_RETENTION_DAYS  # A typo must never shrink the audit window.
