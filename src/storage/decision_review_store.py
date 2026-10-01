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

from src.models.decision_audit import CLASSIFICATION_FIELDS, DecisionAuditRecord, classify

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
            missing = [field for field in CLASSIFICATION_FIELDS if field not in columns]
            for field in missing:  # Additive migration; legacy rows are backfilled below or stay null.
                conn.execute(f"ALTER TABLE decision_reviews ADD COLUMN {field} TEXT")
            for field in ("lane", "status", "language", "deciding_gate", "recorded_at"):
                conn.execute(f"CREATE INDEX IF NOT EXISTS decision_reviews_{field} ON decision_reviews({field})")
            if missing:
                self._backfill_classification(conn)
            # Human review is appended beside the record; the original record and labels are never edited.
            conn.execute("CREATE TABLE IF NOT EXISTS review_annotations (annotation_id TEXT PRIMARY KEY, "
                         "review_id TEXT NOT NULL, kind TEXT NOT NULL, label TEXT NOT NULL, reason TEXT NOT NULL, "
                         "reviewer TEXT NOT NULL, created_at TEXT NOT NULL)")
            conn.execute("CREATE INDEX IF NOT EXISTS review_annotations_review ON review_annotations(review_id)")
            if "synced" not in {row[1] for row in conn.execute("PRAGMA table_info(review_annotations)")}:
                conn.execute("ALTER TABLE review_annotations ADD COLUMN synced INTEGER NOT NULL DEFAULT 0")

    @staticmethod
    def _backfill_classification(conn) -> None:
        rows = conn.execute("SELECT review_id, payload FROM decision_reviews").fetchall()
        for review_id, payload in rows:
            try:
                values = classify(DecisionAuditRecord.model_validate_json(payload))
            except ValueError:
                continue  # An unreadable legacy row keeps null classification; it is never rewritten.
            conn.execute(f"UPDATE decision_reviews SET {', '.join(f'{f}=?' for f in CLASSIFICATION_FIELDS)} "
                         "WHERE review_id=?", (*(values[f] for f in CLASSIFICATION_FIELDS), review_id))

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
        values = classify(record)
        with self._connect() as conn:
            conn.execute(
                f"{verb} INTO decision_reviews (review_id, request_id, session_id, recorded_at, payload, synced, "
                f"{', '.join(CLASSIFICATION_FIELDS)}) VALUES (?, ?, ?, ?, ?, ?{', ?' * len(CLASSIFICATION_FIELDS)})",
                (record.review_id, record.request_id, record.session_id,
                 record.recorded_at.astimezone(UTC).isoformat(), record.model_dump_json(), int(synced),
                 *(values[f] for f in CLASSIFICATION_FIELDS)))
        return record.review_id

    def query(self, *, since: datetime | None = None, limit: int | None = None,
              **filters: str | None) -> list[DecisionAuditRecord]:
        """Filter by indexed classification columns (lane, status, language, deciding_gate, reason_code, mechanism)."""
        unknown = set(filters) - set(CLASSIFICATION_FIELDS)
        if unknown:
            raise ValueError(f"unknown review filter: {', '.join(sorted(unknown))}")
        clauses, params = [], []
        for field, value in filters.items():
            if value is not None:
                clauses.append(f"{field}=?"); params.append(value)
        if since is not None:
            clauses.append("recorded_at>=?"); params.append(since.astimezone(UTC).isoformat())
        sql = "SELECT payload FROM decision_reviews" + (f" WHERE {' AND '.join(clauses)}" if clauses else "")
        sql += " ORDER BY recorded_at"
        if limit is not None:
            sql += " LIMIT ?"; params.append(int(limit))
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [DecisionAuditRecord.model_validate_json(row[0]) for row in rows]

    def by_request(self, request_id: str) -> list[DecisionAuditRecord]:
        """Earlier attempts for the same request, oldest first (retry lineage)."""
        with self._connect() as conn:
            rows = conn.execute("SELECT payload FROM decision_reviews WHERE request_id=? ORDER BY recorded_at",
                                (request_id,)).fetchall()
        return [DecisionAuditRecord.model_validate_json(row[0]) for row in rows]

    ANNOTATION_KINDS = ("scholar_review", "failure_type", "behavior_case", "note")

    def annotate(self, review_id: str, *, reviewer: str, kind: str, label: str, reason: str) -> dict:
        """Append a human annotation. Every field is required; the reviewed record must exist here."""
        from uuid import uuid4
        values = {"reviewer": reviewer, "label": label, "reason": reason}
        if kind not in self.ANNOTATION_KINDS:
            raise ValueError(f"annotation kind must be one of {', '.join(self.ANNOTATION_KINDS)}")
        if any(not isinstance(v, str) or not v.strip() or len(v) > 2000 for v in values.values()):
            raise ValueError("reviewer, label and reason are required (at most 2000 characters each)")
        if self.get(review_id) is None:
            raise KeyError(f"no review record {review_id}")
        row = {"annotation_id": str(uuid4()), "review_id": review_id, "kind": kind,
               **{k: v.strip() for k, v in values.items()}, "created_at": datetime.now(UTC).isoformat()}
        self.insert_annotation(row)
        return row

    def insert_annotation(self, row: dict, *, synced: bool = False) -> None:
        """Store an annotation as given (also used to copy mirrored ones back); duplicates are ignored."""
        with self._connect() as conn:
            conn.execute("INSERT OR IGNORE INTO review_annotations (annotation_id, review_id, kind, label, reason, "
                         "reviewer, created_at, synced) VALUES (:annotation_id, :review_id, :kind, :label, :reason, "
                         ":reviewer, :created_at, :synced)", {**row, "synced": int(synced)})

    _ANNOTATION_COLUMNS = "annotation_id, review_id, kind, label, reason, reviewer, created_at"

    def annotations(self, review_id: str) -> list[dict]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(f"SELECT {self._ANNOTATION_COLUMNS} FROM review_annotations WHERE review_id=? "
                                "ORDER BY created_at", (review_id,)).fetchall()
        return [dict(row) for row in rows]

    def pending_annotations(self, limit: int = 200) -> list[dict]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(f"SELECT {self._ANNOTATION_COLUMNS} FROM review_annotations WHERE synced=0 "
                                "ORDER BY created_at LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]

    def mark_annotations_synced(self, annotation_ids) -> None:
        with self._connect() as conn:
            conn.executemany("UPDATE review_annotations SET synced=1 WHERE annotation_id=?",
                             [(i,) for i in annotation_ids])

    def stats(self) -> dict:
        """Counts per classification value plus on-disk size, for review planning and capacity watch."""
        with self._connect() as conn:
            counts = {field: dict(conn.execute(
                f"SELECT COALESCE({field}, 'unclassified'), COUNT(*) FROM decision_reviews GROUP BY 1 ORDER BY 2 DESC"
            ).fetchall()) for field in CLASSIFICATION_FIELDS}
            total = conn.execute("SELECT COUNT(*) FROM decision_reviews").fetchone()[0]
            counts["annotation_kind"] = dict(conn.execute(
                "SELECT kind, COUNT(*) FROM review_annotations GROUP BY kind ORDER BY 2 DESC").fetchall())
            counts["reviewed_records"] = conn.execute(
                "SELECT COUNT(DISTINCT review_id) FROM review_annotations WHERE kind='scholar_review'").fetchone()[0]
        size = sum(p.stat().st_size for p in self.path.parent.glob(self.path.name + "*") if p.is_file())
        return {"total": total, "bytes_on_disk": size, "review_hold": EARLY_POC_REVIEW_HOLD, "by": counts}

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
                self.sync_annotations()
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
                self.sync_annotations()
                self.keep_alive()
                return confirmed

    def purge_older_than(self, days: int) -> int:
        if type(days) is not int or days < 1:
            raise ValueError("retention must be a positive number of days")
        return 0  # Hold covers local working data, archive and remote mirror.

    def _history(self) -> SQLiteDecisionReviewStore:
        return self.archive if self.archive is not None else self.local

    def query(self, **kwargs) -> list[DecisionAuditRecord]:
        """Review queries read the full local archive; the working file may hold only a short window."""
        return self._history().query(**kwargs)

    def stats(self) -> dict:
        return {**self._history().stats(), "pending_sync": self.local.pending_count()}

    def by_request(self, request_id: str) -> list[DecisionAuditRecord]:
        return self.local.by_request(request_id)  # Retries arrive within seconds; the working store has them.

    def annotate(self, review_id: str, **kwargs) -> dict:
        """Local commit first, then the remote copy; a failed push stays in the annotation outbox."""
        history = self._history()
        row = history.annotate(review_id, **kwargs)
        try:
            self.remote.append_annotations([row])
            history.mark_annotations_synced([row["annotation_id"]])
        except Exception as exc:
            self.last_sync_error = type(exc).__name__  # Never the message: it may contain the URL.
            if self.require_mirror:
                raise RuntimeError("annotation saved locally but the required mirror is unavailable; "
                                   "it is queued and the sync task will replay it") from None
        return row

    def sync_annotations(self, batch: int = 200) -> int:
        history, confirmed = self._history(), 0
        while rows := history.pending_annotations(batch):
            try:
                self.remote.append_annotations(rows)
            except Exception as exc:
                self.last_sync_error = type(exc).__name__
                break
            history.mark_annotations_synced([row["annotation_id"] for row in rows])
            confirmed += len(rows)
            if len(rows) < batch:
                break
        return confirmed

    def annotations(self, review_id: str) -> list[dict]:
        return self._history().annotations(review_id)

    def status(self) -> dict:
        return {"mirror": type(self.remote).__name__, "pending_sync": self.local.pending_count(),
                "last_sync_error": self.last_sync_error, "require_mirror": self.require_mirror,
                "archive_rows": self.archive.count() if self.archive is not None else None,
                "review_hold": EARLY_POC_REVIEW_HOLD,
                "pending_annotation_sync": len(self._history().pending_annotations(1000)),
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

    def append_annotations(self, rows):
        return self._real().append_annotations(rows)

    def iter_annotations(self):
        return self._real().iter_annotations()


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
