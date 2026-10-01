"""Goal B: classified review records with internal signals, queryable for scholar review."""
import csv
import io
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from scripts import review_answers
from src.chatbot.application_service import ApplicationService
from src.chatbot.session_manager import SessionManager
from src.models.decision_audit import CLASSIFICATION_FIELDS, classify, prepare_decision_record
from src.models.ruling import AnswerContract, ComplianceStatus
from src.storage.decision_review_store import MirroredDecisionReviewStore, SQLiteDecisionReviewStore
from tests.test_l1_contracts import FakeLLM, FakeRetriever, _chunk

STORY = "I bought an iPhone, paid EGP 5,000 down, and owe EGP 3,000 monthly for 12 months. Is it halal?"


def _numbers(value, path=""):
    """Every numeric leaf (excluding bools) with its path, to prove client JSON carries no signal."""
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [path]
    if isinstance(value, dict):
        return [p for k, v in value.items() for p in _numbers(v, f"{path}.{k}")]
    if isinstance(value, list):
        return [p for i, v in enumerate(value) for p in _numbers(v, f"{path}[{i}]")]
    return []


def test_grounded_answer_record_holds_retrieval_signals_and_client_json_holds_none(tmp_path):
    store = SQLiteDecisionReviewStore(tmp_path / "r.sqlite3")
    chunks = [_chunk("c-1", score=0.91), _chunk("c-2", score=0.55), _chunk("c-3", score=0.12)]
    app = ApplicationService(retriever=FakeRetriever(chunks), llm_client=FakeLLM("COMPLIANT: maybe [FAS-01 §1]."),
                             decision_store=store)
    app._handle_clarification_stage = Mock(return_value=None)
    answer = app.answer("How is accounting profit recognized?", session_id="s")

    record = store.get(answer.metadata["review_receipt"]["review_id"])
    retrieval = record.internal_signals["retrieval"]
    assert retrieval and retrieval[0]["threshold"] == app.threshold
    scored = {c["id"]: (c["score"], c["kept"]) for c in retrieval[0]["chunks"]}
    assert scored == {"c-1": (0.91, True), "c-2": (0.55, True), "c-3": (0.12, False)}
    assert record.internal_signals["configured_threshold"] == app.threshold
    assert record.internal_signals["model"] == "fake-gemini"

    client = answer.to_dict()
    assert "retrieval" not in json.dumps(client) and "internal_signals" not in json.dumps(client)
    allowed = {".metadata.review_receipt", ".metadata.decision_trace", ".metadata.evidence", ".citations"}
    leaked = [p for p in _numbers(client) if not any(p.startswith(a) for a in allowed)]
    assert leaked == []


def test_signals_are_per_request_and_do_not_leak_between_answers(tmp_path):
    store = SQLiteDecisionReviewStore(tmp_path / "r.sqlite3")
    retriever = FakeRetriever([_chunk("first", score=0.9)])
    app = ApplicationService(retriever=retriever, llm_client=FakeLLM("x"), decision_store=store,
                             session_store=SessionManager())
    app._handle_clarification_stage = Mock(return_value=None)
    first = app.answer("How is accounting profit recognized?")
    retriever.chunks = []
    app._cached_answer = Mock(return_value=None)
    second = app.answer("")  # Empty input never retrieves.
    assert store.get(first.metadata["review_receipt"]["review_id"]).internal_signals["retrieval"]
    assert store.get(second.metadata["review_receipt"]["review_id"]).internal_signals["retrieval"] == []


def test_described_clarification_is_classified_from_typed_state(tmp_path):
    store = SQLiteDecisionReviewStore(tmp_path / "r.sqlite3")
    app = ApplicationService(retriever=Mock(), llm_client=Mock(), session_store=SessionManager(), decision_store=store)
    answer = app.answer(STORY, session_id="s1")
    record = store.get(answer.metadata["review_receipt"]["review_id"])
    assert classify(record) == {"lane": "described_operation", "status": "CLARIFICATION_NEEDED", "language": "en",
                                "deciding_gate": "clarification", "reason_code": "financing_party_unknown",
                                "mechanism": "unknown"}
    [found] = store.query(lane="described_operation", status="CLARIFICATION_NEEDED")
    assert found.review_id == record.review_id
    assert store.query(lane="general") == []


def test_router_weights_live_in_record_only(tmp_path):
    answer = AnswerContract(answer="Which contract is this?", status=ComplianceStatus.CLARIFICATION_NEEDED,
                            metadata={"router_signals": {"surface:murabaha": 0.4}, "response_language": "en"})
    record = prepare_decision_record("q", answer, session_id="s", request_id="r")
    assert record.internal_signals["router_signals"] == {"surface:murabaha": 0.4}
    assert "router_signals" not in json.dumps(answer.to_dict())


def _legacy_db(path, records):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE decision_reviews (review_id TEXT PRIMARY KEY, request_id TEXT NOT NULL, "
                 "session_id TEXT NOT NULL, recorded_at TEXT NOT NULL, payload TEXT NOT NULL)")
    for record in records:
        conn.execute("INSERT INTO decision_reviews VALUES (?, ?, ?, ?, ?)", (record.review_id, record.request_id,
                     record.session_id, record.recorded_at.isoformat(), record.model_dump_json()))
    conn.execute("INSERT INTO decision_reviews VALUES ('broken', 'r', 's', '2026-01-01T00:00:00+00:00', '{not json')")
    conn.commit()
    conn.close()


def _record(status=ComplianceStatus.INSUFFICIENT_DATA, language="ar", request_id="r", age_days=0):
    answer = AnswerContract(answer="a", status=status, metadata={"response_language": language,
                            "decision_trace": {"understood_as": {"lane": "general", "language": language,
                                                                  "mechanism": "unknown"},
                                               "decided_by": {"gate": "approved_rule", "reason_code": "approved_rule_missing"}}})
    made = prepare_decision_record("q", answer, session_id="s", request_id=request_id)
    return made.model_copy(update={"recorded_at": datetime.now(UTC) - timedelta(days=age_days)})


def test_legacy_database_migrates_additively_and_backfills_readable_rows(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    old = _record(request_id="old", age_days=400)
    _legacy_db(path, [old])
    store = SQLiteDecisionReviewStore(path)
    columns = {row[1] for row in sqlite3.connect(path).execute("PRAGMA table_info(decision_reviews)")}
    assert set(CLASSIFICATION_FIELDS) <= columns
    assert store.count() == 2  # The unreadable row is preserved with null classification, never dropped.
    [found] = store.query(deciding_gate="approved_rule", language="ar")
    assert found.review_id == old.review_id
    assert store.stats()["by"]["lane"] == {"general": 1, "unclassified": 1}
    assert store.purge_older_than(365) == 0 and store.count() == 2  # Review hold still preserves everything.


def test_query_filters_since_limit_and_rejects_unknown_filters(tmp_path):
    store = SQLiteDecisionReviewStore(tmp_path / "r.sqlite3")
    for i, age in enumerate((10, 3, 1)):
        store.append(_record(request_id=f"r{i}", age_days=age, language="en" if i else "ar"))
    assert len(store.query(since=datetime.now(UTC) - timedelta(days=5))) == 2
    assert [r.request_id for r in store.query(language="en", limit=1)] == ["r1"]
    with pytest.raises(ValueError, match="unknown review filter"):
        store.query(answer_text="anything")


def test_mirrored_store_queries_the_full_archive(tmp_path):
    local = SQLiteDecisionReviewStore(tmp_path / "local.sqlite3")
    archive = SQLiteDecisionReviewStore(tmp_path / "archive.sqlite3")
    archive.append(_record(request_id="only-in-archive"), synced=True)
    mirrored = MirroredDecisionReviewStore(local, Mock(), archive=archive)
    assert [r.request_id for r in mirrored.query(status="INSUFFICIENT_DATA")] == ["only-in-archive"]
    assert mirrored.stats()["total"] == 1


def test_postgres_rows_carry_classification_columns():
    from src.storage.postgres_decision_review_store import INSERT, SCHEMA, PostgresDecisionReviewStore
    assert all(f"ADD COLUMN IF NOT EXISTS {f} TEXT" in " ".join(SCHEMA) for f in CLASSIFICATION_FIELDS)
    row = PostgresDecisionReviewStore._row(_record())
    assert INSERT.count("%s") == len(row)
    assert row[5:] == ("general", "INSUFFICIENT_DATA", "ar", "approved_rule", "approved_rule_missing", "unknown")


def test_cli_stats_filters_and_exports(tmp_path, capsys):
    db = tmp_path / "r.sqlite3"
    store = SQLiteDecisionReviewStore(db)
    store.append(_record(request_id="a", language="ar"))
    store.append(_record(request_id="b", language="en", status=ComplianceStatus.CLARIFICATION_NEEDED))
    assert review_answers.main(["--db", str(db), "--stats"]) == 0
    stats = json.loads(capsys.readouterr().out)
    assert stats["total"] == 2 and stats["by"]["language"] == {"ar": 1, "en": 1} and stats["bytes_on_disk"] > 0

    assert review_answers.main(["--db", str(db), "--language", "ar", "--since", "7d"]) == 0
    table = capsys.readouterr().out
    assert "1 record(s)" in table and "approved_rule" in table

    out = tmp_path / "x.csv"
    assert review_answers.main(["--db", str(db), "--status", "CLARIFICATION_NEEDED", "--format", "csv",
                                "--out", str(out)]) == 0
    rows = list(csv.DictReader(io.StringIO(out.read_text(encoding="utf-8"))))
    assert [r["language"] for r in rows] == ["en"]

    assert review_answers.main(["--db", str(db), "--format", "jsonl", "--gate", "approved_rule"]) == 0
    assert len(capsys.readouterr().out.strip().splitlines()) == 2


def test_cli_refuses_missing_store_and_bad_since(tmp_path):
    assert review_answers.main(["--db", str(tmp_path / "absent.sqlite3"), "--stats"]) == 2
    assert not (tmp_path / "absent.sqlite3").exists()  # Never creates an empty store by accident.
    with pytest.raises(SystemExit):
        review_answers.main(["--db", str(tmp_path / "x"), "--since", "last week"])


# ---- lineage, versions, failures and annotations (slice 2) --------------------------------------------------
def _service(tmp_path, store=None):
    store = store or SQLiteDecisionReviewStore(tmp_path / "r.sqlite3")
    app = ApplicationService(retriever=FakeRetriever([_chunk()]), llm_client=FakeLLM("x"),
                             session_store=SessionManager(), decision_store=store)
    app._handle_clarification_stage = Mock(return_value=None)
    return app, store


def test_record_carries_versions_and_lists_unknown_provenance(tmp_path, monkeypatch):
    monkeypatch.setenv("AAOIFI_CORPUS_VERSION", "corpus-2026-09-30")
    monkeypatch.delenv("AAOIFI_INDEX_VERSION", raising=False)
    monkeypatch.setenv("EVAL_RUN_ID", "run-7")
    app, store = _service(tmp_path)
    answer = app.answer("How is accounting profit recognized?", session_id="s", request_id="req-1")
    prov = store.get(answer.metadata["review_receipt"]["review_id"]).provenance
    v = prov["versions"]
    assert v["corpus_version"] == "corpus-2026-09-30" and v["model"] == "fake-gemini"
    assert v["prompt_version"] and v["public_answer_policy"] == "literal-support-v2"
    assert v["code_revision"]  # From the environment or the checkout's HEAD.
    assert v["rule_set"] == []  # No approved cards: an honest empty set, not a fabricated version.
    assert "index_version" in prov["unavailable"] and "corpus_version" not in prov["unavailable"]
    assert prov["run_id"] == "run-7" and prov["attempt"] == 1 and prov["parent_review_id"] is None
    assert prov["duration_ms"] >= 0 and prov["started_at"]
    assert "provenance" not in json.dumps(answer.to_dict())


def test_retry_of_same_request_links_to_previous_attempt(tmp_path):
    app, store = _service(tmp_path)
    first = app.answer("How is accounting profit recognized?", session_id="s", request_id="same")
    second = app.answer("How is accounting profit recognized?", session_id="s", request_id="same")
    prov = store.get(second.metadata["review_receipt"]["review_id"]).provenance
    assert prov["attempt"] == 2 and prov["parent_review_id"] == first.metadata["review_receipt"]["review_id"]


def test_described_turn_id_is_linked(tmp_path):
    store = SQLiteDecisionReviewStore(tmp_path / "r.sqlite3")
    app = ApplicationService(retriever=Mock(), llm_client=Mock(), session_store=SessionManager(), decision_store=store)
    answer = app.answer(STORY, session_id="s1")
    record = store.get(answer.metadata["review_receipt"]["review_id"])
    assert record.provenance["turn_id"] == record.typed_review.turn_id


def test_generation_failure_is_recorded_without_its_message_and_still_raised(tmp_path):
    app, store = _service(tmp_path)
    app._answer = Mock(side_effect=RuntimeError("postgresql://user:secret@host failed"))
    with pytest.raises(RuntimeError):
        app.answer("anything", session_id="s", request_id="boom")
    [failed] = store.query(status="FAILED")
    assert failed.response["failure"] == {"stage": "generation", "error_category": "RuntimeError"}
    assert failed.response["delivery"] == "not_delivered"
    assert "secret" not in failed.model_dump_json()
    assert any(g.gate == "review_and_feedback" and g.status == "blocked" for g in failed.gates)


def test_failed_commit_is_not_claimed_as_preserved(tmp_path):
    class Broken:
        def append(self, record):
            raise OSError("disk full")
    app, _ = _service(tmp_path, store=Broken())
    with pytest.raises(OSError):
        app.answer("How is accounting profit recognized?", session_id="s")  # No record, no answer, no false claim.


def test_annotations_are_append_only_and_leave_the_record_untouched(tmp_path):
    store = SQLiteDecisionReviewStore(tmp_path / "r.sqlite3")
    record = _record()
    store.append(record)
    before = store.get(record.review_id).model_dump_json()
    store.annotate(record.review_id, reviewer="Dr. A", kind="scholar_review", label="agree_withheld", reason="ok")
    store.annotate(record.review_id, reviewer="Dr. B", kind="scholar_review", label="disagree", reason="see SS-8")
    assert [a["reviewer"] for a in store.annotations(record.review_id)] == ["Dr. A", "Dr. B"]
    assert store.get(record.review_id).model_dump_json() == before
    assert store.stats()["by"]["reviewed_records"] == 1
    with pytest.raises(ValueError):
        store.annotate(record.review_id, reviewer=" ", kind="scholar_review", label="x", reason="y")
    with pytest.raises(ValueError):
        store.annotate(record.review_id, reviewer="A", kind="verdict", label="x", reason="y")
    with pytest.raises(KeyError):
        store.annotate("missing", reviewer="A", kind="note", label="x", reason="y")


def test_cli_show_and_annotate(tmp_path, capsys):
    db = tmp_path / "r.sqlite3"
    store = SQLiteDecisionReviewStore(db)
    record = _record()
    store.append(record)
    assert review_answers.main(["--db", str(db), "--annotate", record.review_id, "--reviewer", "Dr. A",
                                "--label", "agree_withheld", "--rationale", "correct abstention"]) == 0
    capsys.readouterr()
    assert review_answers.main(["--db", str(db), "--show", record.review_id]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["record"]["review_id"] == record.review_id and shown["annotations"][0]["label"] == "agree_withheld"
    assert review_answers.main(["--db", str(db), "--annotate", record.review_id, "--reviewer", "Dr. A"]) == 2


def test_legacy_record_without_provenance_still_loads(tmp_path):
    payload = json.loads(_record().model_dump_json())
    payload.pop("provenance")
    from src.models.decision_audit import DecisionAuditRecord
    assert DecisionAuditRecord.model_validate(payload).provenance == {}


# ---- annotation mirroring ------------------------------------------------------------------------------------
class _AnnotationRemote:
    def __init__(self):
        self.rows, self.down = {}, False

    def append_annotations(self, rows):
        if self.down:
            raise ConnectionError("postgresql://user:secret@host refused")
        for row in rows:
            self.rows.setdefault(row["annotation_id"], dict(row))  # Idempotent like ON CONFLICT DO NOTHING.
        return [row["annotation_id"] for row in rows]

    def append_many(self, records):
        return [r.review_id for r in records]

    def iter_annotations(self):
        return iter(self.rows.values())


def _mirrored(tmp_path, **kwargs):
    local = SQLiteDecisionReviewStore(tmp_path / "local.sqlite3")
    archive = SQLiteDecisionReviewStore(tmp_path / "archive.sqlite3")
    record = _record()
    archive.append(record, synced=True)
    remote = _AnnotationRemote()
    return MirroredDecisionReviewStore(local, remote, archive=archive, **kwargs), remote, archive, record


def test_annotation_is_committed_locally_then_mirrored(tmp_path):
    store, remote, archive, record = _mirrored(tmp_path)
    row = store.annotate(record.review_id, reviewer="Dr. A", kind="scholar_review", label="agree", reason="ok")
    assert remote.rows[row["annotation_id"]]["label"] == "agree"
    assert archive.pending_annotations() == []


def test_unreachable_mirror_queues_annotation_and_sync_replays_it_once(tmp_path):
    store, remote, archive, record = _mirrored(tmp_path)
    remote.down = True
    row = store.annotate(record.review_id, reviewer="Dr. A", kind="note", label="x", reason="y")
    assert [a["annotation_id"] for a in archive.pending_annotations()] == [row["annotation_id"]]
    assert store.status()["pending_annotation_sync"] == 1 and store.last_sync_error == "ConnectionError"
    remote.down = False
    store.sync_pending()
    store.sync_pending()  # A second replay must not duplicate.
    assert list(remote.rows) == [row["annotation_id"]] and archive.pending_annotations() == []


def test_required_mirror_reports_queued_annotation_without_losing_it(tmp_path):
    store, remote, archive, record = _mirrored(tmp_path, require_mirror=True)
    remote.down = True
    with pytest.raises(RuntimeError, match="queued") as raised:
        store.annotate(record.review_id, reviewer="Dr. A", kind="note", label="x", reason="y")
    assert "secret" not in str(raised.value)
    assert len(archive.annotations(record.review_id)) == 1 and len(archive.pending_annotations()) == 1


def test_backup_copies_mirrored_annotations_into_the_archive(tmp_path):
    from scripts.backup_decision_reviews import backup
    remote = _AnnotationRemote()
    record = _record()
    remote.iter_records = lambda batch=500: iter([record])
    remote.rows["a1"] = {"annotation_id": "a1", "review_id": record.review_id, "kind": "scholar_review",
                         "label": "agree", "reason": "ok", "reviewer": "Dr. A", "created_at": "2026-10-01T10:00:00+00:00"}
    archive = SQLiteDecisionReviewStore(tmp_path / "rebuilt.sqlite3")
    backup(remote, archive)
    backup(remote, archive)
    assert [a["annotation_id"] for a in archive.annotations(record.review_id)] == ["a1"]
    assert archive.pending_annotations() == []  # Copied from the mirror, so nothing to push back.


def test_postgres_annotation_sql_is_idempotent():
    from src.storage.postgres_decision_review_store import ANNOTATION_FIELDS, INSERT_ANNOTATION, SCHEMA
    assert "ON CONFLICT (annotation_id) DO NOTHING" in INSERT_ANNOTATION
    assert INSERT_ANNOTATION.count("%s") == len(ANNOTATION_FIELDS)
    assert any("CREATE TABLE IF NOT EXISTS review_annotations" in s for s in SCHEMA)
