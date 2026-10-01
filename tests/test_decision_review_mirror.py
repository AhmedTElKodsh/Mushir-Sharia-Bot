"""SQLite commit point + durable Postgres mirror, tested with in-memory fakes (no network)."""
import os
import sqlite3
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from src.models.decision_audit import prepare_decision_record
from src.models.ruling import AnswerContract, ComplianceStatus
from src.storage.decision_review_store import (
    MIRROR_RETRY_SECONDS, MirroredDecisionReviewStore, SQLiteDecisionReviewStore, configured_decision_store,
)
from src.storage.postgres_decision_review_store import PostgresDecisionReviewStore


@pytest.fixture(autouse=True)
def isolated_archive(tmp_path, monkeypatch):
    monkeypatch.setenv("DECISION_REVIEW_ARCHIVE_PATH", str(tmp_path / "archive.sqlite3"))


def record(request_id="r", age_days=0):
    answer = AnswerContract(answer="a", status=ComplianceStatus.INSUFFICIENT_DATA)
    made = prepare_decision_record("q", answer, session_id="s", request_id=request_id)
    return made.model_copy(update={"recorded_at": datetime.now(UTC) - timedelta(days=age_days)})


class FakeRemote:
    """In-memory stand-in for the Postgres store; `down` simulates an unreachable database."""

    def __init__(self):
        self.rows, self.down, self.calls = {}, False, 0

    def _check(self):
        self.calls += 1
        if self.down:
            raise ConnectionError("postgresql://user:secret@host/db refused")

    def append(self, rec):
        self._check()
        self.rows.setdefault(rec.review_id, rec)
        return rec.review_id

    def append_many(self, recs):
        self._check()
        for rec in recs:
            self.rows.setdefault(rec.review_id, rec)
        return [rec.review_id for rec in recs]

    def get(self, review_id):
        self._check()
        return self.rows.get(review_id)

    def ping(self):
        self._check()
        self.pings = getattr(self, "pings", 0) + 1

    def iter_records(self, batch=500):
        self._check()
        return iter(sorted(self.rows.values(), key=lambda rec: rec.recorded_at))

    def purge_older_than(self, days):
        self._check()
        cutoff = datetime.now(UTC) - timedelta(days=days)
        old = [i for i, rec in self.rows.items() if rec.recorded_at < cutoff]
        for i in old:
            del self.rows[i]
        return len(old)


def mirrored(tmp_path, remote=None, **kwargs):
    remote = remote or FakeRemote()
    clock = kwargs.pop("clock", None)
    extra = {"clock": clock} if clock else {}
    return MirroredDecisionReviewStore(SQLiteDecisionReviewStore(tmp_path / "local.sqlite3"), remote, **kwargs, **extra), remote


def test_append_lands_in_both_stores_and_leaves_nothing_pending(tmp_path):
    store, remote = mirrored(tmp_path)
    rec = record()
    assert store.append(rec) == rec.review_id
    assert rec.review_id in remote.rows and store.local.get(rec.review_id) is not None
    assert store.local.pending_count() == 0


def test_remote_outage_never_fails_the_answer_and_the_outbox_replays_later(tmp_path):
    now = [100.0]
    store, remote = mirrored(tmp_path, clock=lambda: now[0])
    remote.down = True
    first, second = record("a"), record("b")
    assert store.append(first) == first.review_id            # delivered despite the outage
    calls_after_first = remote.calls
    assert store.append(second) == second.review_id
    assert remote.calls == calls_after_first                 # circuit open: no 3-second penalty per request
    assert store.local.pending_count() == 2 and store.status()["last_sync_error"] == "ConnectionError"
    remote.down = False
    assert store.sync_pending() == 2
    assert set(remote.rows) == {first.review_id, second.review_id} and store.local.pending_count() == 0
    assert store.sync_pending() == 0                         # replay is idempotent
    now[0] += MIRROR_RETRY_SECONDS + 1
    store.append(record("c"))
    assert store.local.pending_count() == 0                  # circuit closed again, direct mirroring resumes


def test_sync_stops_cleanly_on_failure_and_keeps_unconfirmed_rows(tmp_path):
    store, remote = mirrored(tmp_path)
    remote.down = True
    for name in "abc":
        store.append(record(name))
    assert store.sync_pending() == 0 and store.local.pending_count() == 3
    remote.down = False
    assert store.sync_pending(batch=2) == 3 and store.local.pending_count() == 0


def test_error_text_with_credentials_is_never_stored_or_logged(tmp_path, caplog):
    store, remote = mirrored(tmp_path)
    remote.down = True
    store.append(record())
    store.sync_pending()
    assert "secret" not in str(store.status()) and "secret" not in caplog.text


def test_strict_mode_withholds_the_answer_when_the_mirror_is_down(tmp_path):
    store, remote = mirrored(tmp_path, require_mirror=True)
    remote.down = True
    rec = record()
    with pytest.raises(ConnectionError):
        store.append(rec)
    assert store.local.get(rec.review_id) is None and store.local.pending_count() == 0


def test_local_failure_fails_the_answer_without_touching_the_mirror(tmp_path):
    store, remote = mirrored(tmp_path)
    store.local.append = Mock(side_effect=OSError("disk full"))
    with pytest.raises(OSError):
        store.append(record())
    assert remote.calls == 0


def test_get_falls_back_to_the_durable_copy_after_local_purge(tmp_path):
    store, remote = mirrored(tmp_path, local_retention_days=7)
    old = record(age_days=30)
    store.append(old)
    store.purge_older_than(365)
    assert store.local.get(old.review_id) is None            # local file stays small
    assert store.get(old.review_id).review_id == old.review_id
    remote.down = True
    assert store.get(old.review_id) is None                  # unreachable remote is a miss, not a crash


def test_local_purge_never_drops_a_row_the_mirror_has_not_confirmed(tmp_path):
    store, remote = mirrored(tmp_path, local_retention_days=7)
    remote.down = True
    stuck = record(age_days=30)
    store.append(stuck)
    store.purge_older_than(365)                              # remote purge fails; must not raise
    assert store.local.get(stuck.review_id) is not None
    remote.down = False
    store.sync_pending()
    store.purge_older_than(365)
    assert store.local.get(stuck.review_id) is None and stuck.review_id in remote.rows


def test_remote_retention_follows_the_long_window(tmp_path):
    store, remote = mirrored(tmp_path)
    ancient = record(age_days=400)
    store.append(ancient)
    store.purge_older_than(365)
    assert ancient.review_id not in remote.rows


def test_legacy_sqlite_file_without_the_synced_column_is_migrated_and_replayed(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    rec = record()
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE decision_reviews (review_id TEXT PRIMARY KEY, request_id TEXT NOT NULL, "
                     "session_id TEXT NOT NULL, recorded_at TEXT NOT NULL, payload TEXT NOT NULL)")
        conn.execute("INSERT INTO decision_reviews VALUES (?, ?, ?, ?, ?)",
                     (rec.review_id, rec.request_id, rec.session_id, rec.recorded_at.isoformat(), rec.model_dump_json()))
    local = SQLiteDecisionReviewStore(path)
    assert local.pending_count() == 1
    store, remote = MirroredDecisionReviewStore(local, FakeRemote()), None
    assert store.sync_pending() == 1


# ---- configuration -----------------------------------------------------------------------------------------
@pytest.mark.parametrize("url", ["", "sqlite:///data/runtime/l6_evidence.db", "mysql://x/y"])
def test_only_postgres_urls_enable_the_mirror(tmp_path, monkeypatch, url):
    monkeypatch.setenv("DECISION_REVIEW_DB_PATH", str(tmp_path / "s.sqlite3"))
    monkeypatch.delenv("DECISION_REVIEW_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", url)
    assert isinstance(configured_decision_store(), SQLiteDecisionReviewStore)


def test_unreachable_postgres_at_boot_still_yields_a_working_mirrored_store(tmp_path, monkeypatch):
    from src.storage import postgres_decision_review_store as pg
    monkeypatch.setenv("DECISION_REVIEW_DB_PATH", str(tmp_path / "s.sqlite3"))
    monkeypatch.setenv("DECISION_REVIEW_DATABASE_URL", "postgresql://u:p@unreachable.invalid/db")
    monkeypatch.setenv("DECISION_REVIEW_LOCAL_RETENTION_DAYS", "3")
    monkeypatch.setattr(pg.PostgresDecisionReviewStore, "__init__", Mock(side_effect=ConnectionError("down")))
    store = configured_decision_store()
    assert isinstance(store, MirroredDecisionReviewStore) and store.local_retention_days == 3
    rec = record()
    assert store.append(rec) == rec.review_id                # recorded locally, queued for later
    assert store.local.pending_count() == 1


def test_bad_local_retention_setting_falls_back_to_seven_days(tmp_path, monkeypatch):
    monkeypatch.setenv("DECISION_REVIEW_DB_PATH", str(tmp_path / "s.sqlite3"))
    monkeypatch.setenv("DECISION_REVIEW_DATABASE_URL", "postgresql://u:p@h/db")
    monkeypatch.setenv("DECISION_REVIEW_LOCAL_RETENTION_DAYS", "0")
    monkeypatch.setattr(PostgresDecisionReviewStore, "__init__", lambda self, url, **k: None)
    assert configured_decision_store().local_retention_days == 7


# ---- the Postgres store's SQL, against a fake psycopg module ------------------------------------------------
class FakeCursor:
    def __init__(self, row=None, rowcount=0):
        self._row, self.rowcount = row, rowcount

    def fetchone(self):
        return self._row

    def fetchall(self):
        return list(self.pages.pop(0)) if getattr(self, "pages", None) else []


class FakeConn:
    def __init__(self, log, row=None):
        self.log, self.row = log, row

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.log.append((" ".join(sql.split()), params))
        return FakeCursor(self.row, rowcount=3)


class FakePsycopg:
    def __init__(self, row=None):
        self.log, self.row, self.connects = [], row, []

    def connect(self, url, connect_timeout=None):
        self.connects.append((url, connect_timeout))
        return FakeConn(self.log, self.row)


def test_postgres_store_creates_schema_and_appends_idempotently():
    fake = FakePsycopg()
    store = PostgresDecisionReviewStore("postgresql://u:p@h/db", psycopg_module=fake)
    assert any("CREATE TABLE IF NOT EXISTS decision_reviews" in sql and "JSONB" in sql for sql, _ in fake.log)
    rec = record()
    assert store.append(rec) == rec.review_id
    sql, params = fake.log[-1]
    assert "ON CONFLICT (review_id) DO NOTHING" in sql and params[0] == rec.review_id
    assert fake.connects[-1][1] == 3                          # short connect timeout bounds an outage's cost


def test_postgres_append_many_uses_one_connection_and_handles_empty():
    fake = FakePsycopg()
    store = PostgresDecisionReviewStore("postgresql://u:p@h/db", psycopg_module=fake)
    before = len(fake.connects)
    assert store.append_many([]) == []
    assert len(fake.connects) == before
    assert store.append_many([record("a"), record("b")]) and len(fake.connects) == before + 1


def test_postgres_get_accepts_jsonb_dicts_and_text_payloads():
    rec = record()
    for payload in (rec.model_dump(mode="json"), rec.model_dump_json()):
        store = PostgresDecisionReviewStore("postgresql://u:p@h/db", psycopg_module=FakePsycopg(row=(payload,)))
        assert store.get(rec.review_id).review_id == rec.review_id
    assert PostgresDecisionReviewStore("postgresql://u:p@h/db", psycopg_module=FakePsycopg()).get("x") is None


def test_postgres_purge_validates_the_window_and_returns_the_count():
    store = PostgresDecisionReviewStore("postgresql://u:p@h/db", psycopg_module=FakePsycopg())
    assert store.purge_older_than(365) == 3
    for bad in (0, -1, "30", 1.5):
        with pytest.raises(ValueError):
            store.purge_older_than(bad)


def test_postgres_store_requires_a_url():
    with pytest.raises(ValueError):
        PostgresDecisionReviewStore("", psycopg_module=FakePsycopg())


# ---- service and API integration ------------------------------------------------------------------------------
def test_application_answers_survive_a_mirror_outage_and_are_replayed(tmp_path):
    from src.chatbot.application_service import ApplicationService
    from src.chatbot.session_manager import SessionManager
    store, remote = mirrored(tmp_path)
    remote.down = True
    app = ApplicationService(retriever=Mock(), llm_client=Mock(), session_store=SessionManager(), decision_store=store)
    answer = app.answer("I bought an iPhone with deposit EGP 5000 and 12 x EGP 3000.", session_id="s1")
    assert answer.metadata["review_receipt"]["review_id"]
    remote.down = False
    assert store.sync_pending() == 1 and answer.metadata["review_receipt"]["review_id"] in remote.rows


def test_periodic_sync_replays_at_boot_and_survives_failures():
    import asyncio
    from src.api.main import _periodic_store_sync
    store = Mock()
    store.sync_pending.side_effect = [OSError("down"), 0, 0]

    async def run():
        task = asyncio.create_task(_periodic_store_sync(store, interval_seconds=0.01))
        await asyncio.sleep(0.15)
        task.cancel()

    asyncio.run(run())
    assert store.sync_pending.call_count >= 2                 # first pass at boot, failure does not stop the loop


def test_ready_reports_mirror_status_and_is_null_without_a_mirror(tmp_path, monkeypatch):
    from src.api.main import create_app
    monkeypatch.setenv("DECISION_REVIEW_DB_PATH", str(tmp_path / "plain.sqlite3"))
    monkeypatch.delenv("DECISION_REVIEW_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(create_app()) as client:
        assert client.get("/ready").json()["decision_review_mirror"] is None
    monkeypatch.setenv("DECISION_REVIEW_DB_PATH", str(tmp_path / "mirrored.sqlite3"))
    monkeypatch.setenv("DECISION_REVIEW_DATABASE_URL", "postgresql://u:p@h/db")
    monkeypatch.setattr(PostgresDecisionReviewStore, "__init__", Mock(side_effect=ConnectionError("down")))
    with TestClient(create_app()) as client:
        body = client.get("/ready").json()["decision_review_mirror"]
    assert body["mirror"] == "_DeferredPostgres" and body["pending_sync"] == 0 and body["require_mirror"] is False
    assert "postgresql://" not in str(body)


@pytest.mark.skipif(not os.getenv("MUSHIR_TEST_DATABASE_URL"), reason="set MUSHIR_TEST_DATABASE_URL for real PostgreSQL coverage")
def test_real_postgres_round_trip_is_idempotent():
    store = PostgresDecisionReviewStore(os.environ["MUSHIR_TEST_DATABASE_URL"])
    rec = record("integration")
    assert store.append(rec) == rec.review_id
    assert store.append(rec) == rec.review_id                 # replay does not duplicate or fail
    assert store.get(rec.review_id).request_id == "integration"
    assert store.purge_older_than(365) >= 0


# ---- full local archive, keep-alive and backup ----------------------------------------------------------------
def archived(tmp_path, **kwargs):
    archive = SQLiteDecisionReviewStore(tmp_path / "archive.sqlite3")
    store, remote = mirrored(tmp_path, archive=archive, **kwargs)
    return store, remote, archive


def test_archive_keeps_everything_while_the_working_file_stays_small(tmp_path):
    store, remote, archive = archived(tmp_path, local_retention_days=7)
    old, fresh = record("old", age_days=30), record("fresh")
    store.append(old)
    store.append(fresh)
    store.purge_older_than(365)
    assert store.local.get(old.review_id) is None            # working file purged
    assert archive.get(old.review_id) is not None and archive.count() == 2
    remote.down = True
    assert store.get(old.review_id).review_id == old.review_id   # readable with the remote down and local purged


def test_archive_holds_records_even_while_the_remote_is_paused(tmp_path):
    store, remote, archive = archived(tmp_path)
    remote.down = True
    rec = record()
    store.append(rec)
    assert archive.get(rec.review_id) is not None and store.local.pending_count() == 1


def test_archive_failure_never_blocks_delivery(tmp_path):
    store, remote, archive = archived(tmp_path)
    archive.append = Mock(side_effect=OSError("disk full"))
    rec = record()
    assert store.append(rec) == rec.review_id and rec.review_id in remote.rows


def test_archive_follows_the_full_retention_window(tmp_path):
    store, remote, archive = archived(tmp_path)
    ancient, recent = record("a", age_days=400), record("b", age_days=100)
    store.append(ancient)
    store.append(recent)
    store.purge_older_than(365)
    assert archive.get(ancient.review_id) is None and archive.get(recent.review_id) is not None


def test_keepalive_pings_once_per_interval_and_records_failures(tmp_path):
    now = [1_000_000.0]
    store, remote, _ = archived(tmp_path, keepalive_hours=24, wall_clock=lambda: now[0])
    assert store.keep_alive() is True and remote.pings == 1
    assert store.keep_alive() is False and remote.pings == 1    # throttled
    now[0] += 24 * 3600 + 1
    remote.down = True
    assert store.keep_alive() is False and store.last_keepalive_error == "ConnectionError"
    remote.down = False
    assert store.keep_alive() is True and store.last_keepalive_error is None and remote.pings == 2


def test_each_sync_pass_keeps_the_database_active(tmp_path):
    store, remote, _ = archived(tmp_path)
    store.sync_pending()
    assert remote.pings == 1
    store.sync_pending()
    assert remote.pings == 1                                  # still inside the keep-alive interval


def test_status_reports_archive_and_keepalive_without_secrets(tmp_path):
    store, remote, archive = archived(tmp_path)
    store.append(record())
    store.sync_pending()
    status = store.status()
    assert status["archive_rows"] == 1 and status["last_keepalive"]
    assert "secret" not in str(status)


@pytest.mark.parametrize("value", ["off", "NONE", "disabled"])
def test_archive_can_be_switched_off(tmp_path, monkeypatch, value):
    from src.storage.decision_review_store import configured_archive_store
    monkeypatch.setenv("DECISION_REVIEW_ARCHIVE_PATH", value)
    assert configured_archive_store() is None


def test_default_archive_path_sits_beside_the_working_file(tmp_path, monkeypatch):
    from src.storage.decision_review_store import DEFAULT_ARCHIVE_PATH, configured_archive_store
    monkeypatch.delenv("DECISION_REVIEW_ARCHIVE_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    assert configured_archive_store().path == (tmp_path / DEFAULT_ARCHIVE_PATH).resolve()


def test_backup_rebuilds_a_lost_archive_and_is_idempotent(tmp_path):
    from scripts.backup_decision_reviews import backup
    remote = FakeRemote()
    for name in "abc":
        remote.append(record(name))
    archive = SQLiteDecisionReviewStore(tmp_path / "rebuilt.sqlite3")
    assert backup(remote, archive) == (3, 3)
    assert backup(remote, archive) == (3, 0)                  # a second run adds nothing
    assert archive.pending_count() == 0                       # restored rows are not queued for re-upload


def test_backup_script_refuses_without_a_postgres_url(monkeypatch, capsys):
    from scripts import backup_decision_reviews as script
    monkeypatch.delenv("DECISION_REVIEW_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(script, "load_dotenv", lambda: None)
    assert script.main([]) == 2 and "No PostgreSQL URL" in capsys.readouterr().err


def test_backup_script_ping_only_touches_the_database(monkeypatch, capsys):
    from scripts import backup_decision_reviews as script
    from src.storage import postgres_decision_review_store as pg
    pinged = []
    monkeypatch.setattr(script, "load_dotenv", lambda: None)
    monkeypatch.setenv("DECISION_REVIEW_DATABASE_URL", "postgresql://u:p@h/db")
    monkeypatch.setattr(pg.PostgresDecisionReviewStore, "__init__", lambda self, url, **k: None)
    monkeypatch.setattr(pg.PostgresDecisionReviewStore, "ping", lambda self: pinged.append(1))
    assert script.main(["--ping-only"]) == 0 and pinged == [1] and "reachable" in capsys.readouterr().out


def test_postgres_ping_and_keyset_paging_with_the_fake_driver():
    fake = FakePsycopg()
    store = PostgresDecisionReviewStore("postgresql://u:p@h/db", psycopg_module=fake)
    store.ping()
    assert fake.log[-1][0] == "SELECT 1"
    recs = [record(name) for name in "abc"]
    rows = [(r.recorded_at, r.review_id, r.model_dump(mode="json")) for r in recs]
    FakeCursor.pages = [rows[:2], rows[2:]]                   # page size 2: a full page, then a short one
    try:
        got = list(store.iter_records(batch=2))
    finally:
        FakeCursor.pages = []
    assert [r.review_id for r in got] == [r.review_id for r in recs]
    sql, params = fake.log[-1]
    assert "(recorded_at, review_id) > (%s, %s)" in sql and params[1] == recs[1].review_id and params[2] == 2
