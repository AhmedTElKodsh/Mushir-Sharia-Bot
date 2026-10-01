"""Decision review storage with a mandatory early-POC preservation hold.

SQLite is the commit point for delivery: it is atomic and needs no network. When a
PostgreSQL URL is configured, every record is also pushed to Postgres (the durable
copy, since a free Space disk is ephemeral). Rows that could not be pushed stay in the
SQLite outbox (synced=0) and are replayed in the background. All copies are
preserved during scholar review; retention windows are reserved for a later
explicitly activated policy.
"""
import logging
import os
import threading
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sqlite3

from src.models.decision_audit import DecisionAuditRecord

logger = logging.getLogger("sharia_bot")

DEFAULT_DB_PATH = "data/runtime/decision_reviews.sqlite3"
DEFAULT_RETENTION_DAYS = 365
DEFAULT_LOCAL_RETENTION_DAYS = 7
MIRROR_RETRY_SECONDS = 30
DEFAULT_KEEPALIVE_HOURS = 24
DEFAULT_ARCHIVE_PATH = "data/runtime/decision_reviews_archive.sqlite3"
EARLY_POC_REVIEW_HOLD = True


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
            columns = {row[1] for row in conn.execute("PRAGMA table_info(decision_reviews)")}
            if "synced" not in columns:  # Older files: existing rows count as unsynced and are pushed on first sync.
                conn.execute("ALTER TABLE decision_reviews ADD COLUMN synced INTEGER NOT NULL DEFAULT 0")

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        try:
            conn.execute("PRAGMA synchronous=FULL")
            with conn:
                yield conn
        finally:
            conn.close()

    def append(self, record: DecisionAuditRecord, *, synced: bool = False, ignore_duplicates: bool = False) -> str:
        record = DecisionAuditRecord.model_validate(record)
        verb = "INSERT OR IGNORE" if ignore_duplicates else "INSERT"
        with self._connect() as conn:
            conn.execute(
                f"{verb} INTO decision_reviews (review_id, request_id, session_id, recorded_at, payload, synced) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (record.review_id, record.request_id, record.session_id,
                 record.recorded_at.astimezone(UTC).isoformat(), record.model_dump_json(), int(synced)))
        return record.review_id

    def get(self, review_id: str) -> DecisionAuditRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM decision_reviews WHERE review_id=?", (review_id,)).fetchone()
        return DecisionAuditRecord.model_validate_json(row[0]) if row else None

    def delete(self, review_id: str) -> None:
        """Early POC review hold: direct maintenance cannot discard records."""
        return None

    def pending(self, limit: int = 200) -> list[DecisionAuditRecord]:
        with self._connect() as conn:
            rows = conn.execute("SELECT payload FROM decision_reviews WHERE synced=0 ORDER BY recorded_at LIMIT ?",
                                (limit,)).fetchall()
        return [DecisionAuditRecord.model_validate_json(row[0]) for row in rows]

    def count(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM decision_reviews").fetchone()[0]

    def pending_count(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM decision_reviews WHERE synced=0").fetchone()[0]

    def mark_synced(self, review_ids) -> None:
        with self._connect() as conn:
            conn.executemany("UPDATE decision_reviews SET synced=1 WHERE review_id=?", [(i,) for i in review_ids])

    def purge_older_than(self, days: int, *, only_synced: bool = False) -> int:
        """Validate a requested future retention window; preserve rows during review."""
        if type(days) is not int or days < 1:
            raise ValueError("retention must be a positive number of days")
        return 0  # Review hold; a numeric retention setting cannot activate deletion.



class MirroredDecisionReviewStore:
    """Local SQLite commit point plus a durable remote copy fed through the local outbox."""

    def __init__(self, local: SQLiteDecisionReviewStore, remote, *, require_mirror: bool = False,
                 local_retention_days: int = DEFAULT_LOCAL_RETENTION_DAYS, clock=time.monotonic,
                 archive: SQLiteDecisionReviewStore | None = None, keepalive_hours: float = DEFAULT_KEEPALIVE_HOURS,
                 wall_clock=time.time):
        self.local = local
        self.archive = archive  # Full local history, kept separate so the working file stays small.
        self.keepalive_seconds = keepalive_hours * 3600
        self._wall_clock = wall_clock
        self._last_ping = 0.0
        self.last_keepalive: str | None = None
        self.last_keepalive_error: str | None = None
        self.remote = remote
        self.require_mirror = require_mirror
        self.local_retention_days = local_retention_days
        self._clock = clock
        self._lock = threading.Lock()
        self._retry_after = 0.0
        self.last_sync_error: str | None = None

    @property
    def path(self):
        return self.local.path

    def append(self, record: DecisionAuditRecord) -> str:
        review_id = self.local.append(record)  # A local failure fails the answer: nothing was recorded.
        self._archive(record)
        if self._clock() < self._retry_after and not self.require_mirror:
            return review_id  # Remote recently failed: the row waits in the outbox for the sync task.
        try:
            self.remote.append(record)
            self.local.mark_synced([review_id])
            self.last_sync_error = None
        except Exception as exc:
            self.last_sync_error = type(exc).__name__  # Never log the message: it may contain the URL.
            if self.require_mirror:
                # Preserve the failed attempt in the pending outbox; withhold delivery.
                raise
            with self._lock:
                self._retry_after = self._clock() + MIRROR_RETRY_SECONDS
            logger.warning("decision review mirror unavailable (%s); record queued locally", self.last_sync_error)
        return review_id

    def _archive(self, record: DecisionAuditRecord) -> None:
        """Best-effort full copy: it protects against a paused or lost remote, never gates delivery."""
        if self.archive is None:
            return
        try:
            self.archive.append(record, synced=True, ignore_duplicates=True)
        except Exception as exc:
            logger.warning("decision review archive write failed (%s)", type(exc).__name__)

    def keep_alive(self) -> bool:
        """Touch the remote at most once per interval so a free project is not paused for inactivity."""
        ping = getattr(self.remote, "ping", None)
        now = self._wall_clock()
        if ping is None or now - self._last_ping < self.keepalive_seconds:
            return False
        try:
            ping()
        except Exception as exc:
            self.last_keepalive_error = type(exc).__name__
            return False
        self._last_ping = now
        self.last_keepalive = datetime.fromtimestamp(now, UTC).isoformat()
        self.last_keepalive_error = None
        return True

    def get(self, review_id: str) -> DecisionAuditRecord | None:
        found = self.local.get(review_id)
        if found is None and self.archive is not None:
            found = self.archive.get(review_id)
        if found is not None:
            return found
        try:
            return self.remote.get(review_id)  # Older than the short local window.
        except Exception:
            return None

    def sync_pending(self, batch: int = 200) -> int:
        """Replay the outbox to the remote store; returns how many rows were confirmed."""
        confirmed = 0
        while True:
            records = self.local.pending(batch)
            if not records:
                self.last_sync_error = None
                self.keep_alive()
                return confirmed
            try:
                self.remote.append_many(records)
            except Exception as exc:
                self.last_sync_error = type(exc).__name__
                return confirmed
            self.local.mark_synced([record.review_id for record in records])
            confirmed += len(records)
            if len(records) < batch:
                self.last_sync_error = None
                self.keep_alive()
                return confirmed

    def purge_older_than(self, days: int) -> int:
        if type(days) is not int or days < 1:
            raise ValueError("retention must be a positive number of days")
        return 0  # Hold covers local working data, archive and remote mirror.

    def status(self) -> dict:
        return {"mirror": type(self.remote).__name__, "pending_sync": self.local.pending_count(),
                "last_sync_error": self.last_sync_error, "require_mirror": self.require_mirror,
                "archive_rows": self.archive.count() if self.archive is not None else None,
                "review_hold": EARLY_POC_REVIEW_HOLD,
                "last_keepalive": self.last_keepalive, "last_keepalive_error": self.last_keepalive_error}


class _DeferredPostgres:
    """Postgres store whose connection could not be made at boot; it connects on first use."""

    def __init__(self, url: str):
        self._url = url
        self._store = None
        self._lock = threading.Lock()

    def _real(self):
        with self._lock:
            if self._store is None:
                from src.storage.postgres_decision_review_store import PostgresDecisionReviewStore
                self._store = PostgresDecisionReviewStore(self._url)
            return self._store

    def append(self, record):
        return self._real().append(record)

    def append_many(self, records):
        return self._real().append_many(records)

    def get(self, review_id):
        return self._real().get(review_id)

    def purge_older_than(self, days):
        return self._real().purge_older_than(days)

    def ping(self):
        return self._real().ping()

    def iter_records(self, batch=500):
        return self._real().iter_records(batch)


def _postgres_url():
    url = os.getenv("DECISION_REVIEW_DATABASE_URL") or os.getenv("DATABASE_URL") or ""
    # DATABASE_URL may be a sqlite:/// SQLAlchemy URL used elsewhere; only Postgres URLs enable the mirror.
    return url if url.startswith(("postgres://", "postgresql://")) else None


def _int_env(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name) or default)
    except ValueError:
        return default
    return value if value >= 1 else default


def configured_decision_store():
    # A Space has ephemeral disk: an explicit false cannot downgrade its durability.
    required = bool(os.getenv("SPACE_ID") or os.getenv("SPACE_HOST")) or os.getenv("DECISION_REVIEW_REQUIRE_MIRROR", "false").lower() == "true"
    url = _postgres_url()
    if required and not url:
        raise RuntimeError("Strict decision review mirroring requires a valid PostgreSQL URL")
    if url:
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            port = parsed.port  # Access validates numeric syntax and range.
            valid = bool(parsed.hostname and parsed.path.strip("/") and not parsed.fragment)
        except ValueError:
            valid = False
        if not valid:
            raise RuntimeError("Decision review mirror configuration is invalid")
    local = SQLiteDecisionReviewStore(os.getenv("DECISION_REVIEW_DB_PATH") or DEFAULT_DB_PATH)
    if not url:
        return local
    from src.storage.postgres_decision_review_store import PostgresDecisionReviewStore
    try:
        remote = PostgresDecisionReviewStore(url)
    except Exception as exc:
        # An unreachable mirror at boot must not stop the service; the outbox covers it.
        logger.warning("decision review mirror unavailable at startup (%s)", type(exc).__name__)
        remote = _DeferredPostgres(url)
    return MirroredDecisionReviewStore(
        local, remote,
        require_mirror=required,
        local_retention_days=_int_env("DECISION_REVIEW_LOCAL_RETENTION_DAYS", DEFAULT_LOCAL_RETENTION_DAYS),
        archive=configured_archive_store(),
        keepalive_hours=_int_env("DECISION_REVIEW_KEEPALIVE_HOURS", DEFAULT_KEEPALIVE_HOURS))


def configured_archive_store():
    """The full local copy beside the remote; DECISION_REVIEW_ARCHIVE_PATH=off disables it."""
    path = os.getenv("DECISION_REVIEW_ARCHIVE_PATH") or DEFAULT_ARCHIVE_PATH
    if path.strip().lower() in {"off", "none", "disabled"}:
        return None
    return SQLiteDecisionReviewStore(path)


def configured_retention_days() -> int:
    """Conservative default: keep a year of review records unless the operator sets a window."""
    try:
        days = int(os.getenv("DECISION_REVIEW_RETENTION_DAYS") or DEFAULT_RETENTION_DAYS)
    except ValueError:
        return DEFAULT_RETENTION_DAYS
    return days if days >= 1 else DEFAULT_RETENTION_DAYS  # A typo must never shrink the audit window.
