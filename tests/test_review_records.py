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
