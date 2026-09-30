"""Regressions for the second independent review of the fixes (synthetic fixtures only)."""
import csv
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.chatbot.application_service import ApplicationService
from src.chatbot.described_operation import DescribedOperationService
from src.chatbot.mechanism_terms import mechanism_routing_text
from src.chatbot.session_manager import SessionManager
from src.chatbot.structure_clarification import clarify_structure
from src.governance.scholar_review import (
    ScholarReviewQueue, ScholarReviewQueueItem, ScholarReviewQueueStore,
)
from src.models.evidence import CaptureManifest, FactCandidate, FactObservation, Money, UserTurnProvenance
from src.models.evidence_display import without_answer_scores
from src.models.ruling import AnswerContract, ComplianceStatus
from tests.test_approved_card_evaluator import NOW, SCOPE, card
from tests.test_l1_contracts import FakeLLM, FakeRetriever
from tests.test_review_blockers import FIRST_TURN, _documented_previous
from tests.test_review_hardening import CAPTURE, STORY
from scripts.export_scholar_review import export_pending


def _service(tmp_path, **kwargs):
    from src.storage.decision_review_store import SQLiteDecisionReviewStore
    return ApplicationService(retriever=FakeRetriever([]), llm_client=FakeLLM("unused"),
                              session_store=SessionManager(),
                              decision_store=SQLiteDecisionReviewStore(tmp_path / "r.sqlite3"), **kwargs)


# ---- atomic answer(): every failure mode of the commit point ---------------------------------------
@pytest.mark.parametrize("failure", ["raises", "wrong_id"])
def test_failed_commit_leaves_a_new_session_absent(tmp_path, failure):
    app = _service(tmp_path)
    app.decision_store.append = (Mock(side_effect=OSError("disk")) if failure == "raises"
                                 else Mock(return_value="not-the-review-id"))
    with pytest.raises((OSError, RuntimeError)):
        app.answer(STORY, session_id="s1")
    assert app.session_store.get_session("s1") is None


def test_failed_commit_restores_an_existing_session_exactly(tmp_path):
    import copy
    app = _service(tmp_path)
    app.answer(STORY, session_id="s1")
    state = app.session_store.get_session("s1")
    before = (copy.deepcopy(state.metadata), len(state.conversation_history))
    app.decision_store.append = Mock(side_effect=OSError("disk"))
    with pytest.raises(OSError):
        app.answer("The bank", session_id="s1")
    state = app.session_store.get_session("s1")
    assert (state.metadata, len(state.conversation_history)) == before


def test_restore_failure_never_masks_the_storage_error(tmp_path):
    app = _service(tmp_path)
    app.decision_store.append = Mock(side_effect=OSError("disk"))
    app.session_store.delete_session = Mock(side_effect=RuntimeError("redis down"))
    with pytest.raises(OSError, match="disk"):
        app.answer(STORY, session_id="s1")


def test_anonymous_request_never_leaves_a_session_whichever_branch_creates_it(tmp_path):
    app = _service(tmp_path)

    def creating_answer(query, session_id, *args, **kwargs):
        app.session_store.create_session(session_id)  # e.g. a scenario-clarification branch
        return AnswerContract(answer="a", status=ComplianceStatus.INSUFFICIENT_DATA)

    app._answer = creating_answer
    app.answer("anything")
    assert app.session_store._sessions == {}
    app.answer("anything", session_id="named")
    assert "named" in app.session_store._sessions


def test_non_list_review_rows_in_a_corrupt_session_are_reset(tmp_path):
    app = _service(tmp_path)
    app.answer(STORY, session_id="s1")
    app.session_store.get_session("s1").metadata["operation_review_rows"] = "corrupt"
    app.answer("The bank", session_id="s1")
    assert isinstance(app.session_store.get_session("s1").metadata["operation_review_rows"], list)


def test_malformed_yaml_card_file_fails_fast_with_the_path_named(tmp_path, monkeypatch):
    bad = tmp_path / "bad.yaml"
    bad.write_text("- [unclosed", encoding="utf-8")
    monkeypatch.setenv("APPROVED_RULE_CARDS_PATH", str(bad))
    with pytest.raises(RuntimeError, match="APPROVED_RULE_CARDS_PATH"):
        ApplicationService(retriever=Mock(), llm_client=Mock())


# ---- structure clarification timestamps ------------------------------------------------------------------
def _pending(created_at="__none__"):
    state = {"slot": "resale_arranger", "original_query": "q", "asked_count": 1, "language": "en"}
    if created_at != "__none__":
        state["created_at"] = created_at
    return state


def test_live_legacy_and_naive_pending_states_continue_but_stale_ones_expire():
    fresh_aware = datetime.now(UTC).isoformat()
    fresh_naive = datetime.now(UTC).replace(tzinfo=None).isoformat()
    stale_naive = (datetime.now(UTC) - timedelta(hours=2)).replace(tzinfo=None).isoformat()
    for created in (fresh_aware, fresh_naive, "__none__"):
        answer, nxt = clarify_structure("The broker", "the broker", "en", _pending(created))
        assert answer is not None, created
    answer, nxt = clarify_structure("The broker", "the broker", "en", _pending(stale_naive))
    assert answer is None and nxt is None


def test_first_structure_question_carries_a_creation_time():
    _, pending = clarify_structure("Is tawarruq permissible?", "is tawarruq permissible?", "en")
    assert datetime.fromisoformat(pending["created_at"])


# ---- pending replies must look like answers ----------------------------------------------------------------
def _pending_conversation(slot):
    _, conversation = DescribedOperationService([]).answer(
        STORY, session_id="s1", request_id="r1", previous=None, language="en")
    return conversation.model_copy(update={"pending_slot": slot})


@pytest.mark.parametrize("slot, reply", [
    ("payment_breakdown", "The schedule includes a 2000 admin fee"),
    ("payment_breakdown", "I don't know"),
    ("instalment_count", "12"),
    ("instalment_amount", "EGP 3000"),
    ("instalment_count", "I don't know"),
])
def test_valid_replies_to_open_questions_are_accepted(slot, reply):
    assert DescribedOperationService.accepts(reply, _pending_conversation(slot))


@pytest.mark.parametrize("slot", ["payment_breakdown", "instalment_count", "instalment_amount"])
def test_unrelated_messages_are_not_swallowed_by_any_open_question(slot):
    assert not DescribedOperationService.accepts("Tell me about riba", _pending_conversation(slot))


def test_withheld_answer_does_not_publish_the_rule_outcome():
    _, conversation = DescribedOperationService([]).answer(
        FIRST_TURN, session_id="s1", request_id="r1", previous=None, language="en")
    party = next(fact for fact in conversation.snapshot.facts if fact.slot == "financing_party")
    approved = card(material_facts=["financing_party"],
                    outcomes=[dict(when={"financing_party": party.value}, outcome="no_issue_under_this_rule")])
    contract, _ = DescribedOperationService([approved]).answer(
        "The deposit was EGP 5000", session_id="s1", request_id="r2",
        previous=_documented_previous(conversation), language="en")
    evaluation = contract.metadata["approved_rule_evaluation"]
    assert evaluation["status"] == "evaluated"
    assert "outcome" not in evaluation and "supporting_facts" not in evaluation


# ---- currency window --------------------------------------------------------------------------------------
def test_foreign_instalment_amount_is_never_recorded_as_egp():
    from tests.test_review_hardening import _extract
    facts = _extract("I paid deposit EGP 5000 and 12 x USD 300 for the iPhone")
    assert facts["instalment_amount"].status == "unknown"
    assert facts["down_payment"].status == "user_reported"


# ---- mechanism masking --------------------------------------------------------------------------------------
def test_negation_far_from_the_contract_does_not_mask_it():
    assert "murabaha" in mechanism_routing_text("What is not permitted in a murabaha?")
    assert "murabaha" not in mechanism_routing_text("this is not a murabaha, it is ijara")


# ---- evidence contracts ---------------------------------------------------------------------------------------
@pytest.mark.parametrize("url", ["http://127.1/a", "http://2130706433/a", "http://localhost./a",
                                 "http://service.internal/a", "http://printer.local/a"])
def test_shortened_and_internal_hosts_are_not_public(url):
    with pytest.raises(ValidationError):
        CaptureManifest(**{**CAPTURE, "url": url})


def test_public_ip_literal_is_still_accepted():
    assert CaptureManifest(**{**CAPTURE, "url": "http://8.8.8.8/a"}).url == "http://8.8.8.8/a"


def test_high_precision_amounts_that_differ_are_a_real_conflict():
    source = UserTurnProvenance(session_id="s1", turn_id="t1", exact_text="x", recorded_at=NOW, version=1, scope=SCOPE)
    candidates = tuple(FactCandidate(status="user_reported", source=source,
                                     value=Money(amount="1" * 35 + tail, currency="EGP")) for tail in ("1", "2"))
    fact = FactObservation(slot="down_payment", scope=SCOPE, version=1, recorded_at=NOW,
                           status="conflicting", candidates=candidates)
    assert fact.status == "conflicting"


def test_numeric_score_collections_are_scrubbed():
    assert without_answer_scores({"scores": [0.9, 0.8], "label": "x"}) == {"label": "x"}


# ---- confidence handling end to end ---------------------------------------------------------------------------
def test_non_finite_confidence_is_no_confidence():
    item = ScholarReviewQueueItem(query_id="q", queue=ScholarReviewQueue.AUTO_FLAGGED,
                                  flag_reason="t", system_confidence=float("nan"))
    assert item.system_confidence is None


def test_unscored_item_round_trips_through_the_store_and_exports_a_blank_cell(tmp_path):
    queue = tmp_path / "queue.jsonl"
    ScholarReviewQueueStore(queue).append(ScholarReviewQueueItem(
        query_id="q-none", queue=ScholarReviewQueue.AUTO_FLAGGED, flag_reason="t", system_confidence=None))
    assert ScholarReviewQueueStore(queue).load()[0].system_confidence is None
    out = tmp_path / "out.csv"
    export_pending(queue, out)
    rows = list(csv.DictReader(out.open(newline="", encoding="utf-8-sig")))
    assert rows[0]["system_confidence"] == ""


@pytest.mark.api
@pytest.mark.parametrize("confidence", [True, None])
def test_flag_answer_stores_no_score_for_bool_or_missing(monkeypatch, tmp_path, confidence):
    from src.api.main import create_app
    monkeypatch.setenv("SCHOLAR_REVIEW_QUEUE_PATH", str(tmp_path / "q.jsonl"))
    metadata = {} if confidence is None else {"confidence": confidence}
    with TestClient(create_app()) as client:
        response = client.post("/api/v1/flag-answer", json={"query": "q", "answer": "a", "reason": "r",
                                                            "metadata": metadata})
    assert response.status_code == 200
    assert ScholarReviewQueueStore(tmp_path / "q.jsonl").load()[0].system_confidence is None


# ---- retention configuration ------------------------------------------------------------------------------
@pytest.mark.parametrize("raw", ["0", "-5", "abc", ""])
def test_bad_retention_settings_fall_back_to_the_default_never_one_day(monkeypatch, raw):
    from src.storage.decision_review_store import DEFAULT_RETENTION_DAYS, configured_retention_days
    monkeypatch.setenv("DECISION_REVIEW_RETENTION_DAYS", raw)
    assert configured_retention_days() == DEFAULT_RETENTION_DAYS


def test_records_are_stored_with_a_utc_timestamp_so_purge_compares_correctly(tmp_path):
    import sqlite3
    from src.models.decision_audit import prepare_decision_record
    from src.storage.decision_review_store import SQLiteDecisionReviewStore
    store = SQLiteDecisionReviewStore(tmp_path / "r.sqlite3")
    record = prepare_decision_record("q", AnswerContract(answer="a", status=ComplianceStatus.INSUFFICIENT_DATA),
                                     session_id="s", request_id="r")
    offset = datetime.now(UTC).astimezone(timezone(timedelta(hours=5)))
    store.append(record.model_copy(update={"recorded_at": offset}))
    stored = sqlite3.connect(store.path).execute("SELECT recorded_at FROM decision_reviews").fetchone()[0]
    assert stored.endswith("+00:00")


from datetime import timezone  # noqa: E402  (kept beside its only user)


# ---- remaining items: dedupe, locking, periodic purge, registry, names, bare numbers, currency ----------
def test_audit_response_does_not_repeat_the_typed_review(tmp_path):
    app = _service(tmp_path)
    answer = app.answer(STORY, session_id="s1")
    row = app.decision_store.get(answer.metadata["review_receipt"]["review_id"])
    assert row.typed_review is not None
    assert "decision_review" not in row.response["metadata"]


def test_same_session_requests_never_overlap_through_the_commit_point(tmp_path):
    import threading
    import time
    app = _service(tmp_path)
    active, overlaps = [], []

    def slow_answer(query, session_id, *args, **kwargs):
        active.append(1)
        if len(active) > 1:
            overlaps.append(1)
        time.sleep(0.05)
        active.pop()
        return AnswerContract(answer="a", status=ComplianceStatus.INSUFFICIENT_DATA)

    app._answer = slow_answer
    threads = [threading.Thread(target=app.answer, args=("q",), kwargs={"session_id": "same"}) for _ in range(4)]
    [thread.start() for thread in threads]
    [thread.join() for thread in threads]
    assert overlaps == []


def test_periodic_purge_runs_repeatedly_and_survives_a_failed_pass():
    import asyncio
    from src.api.main import _periodic_retention_purge
    store = Mock()
    store.purge_older_than.side_effect = [OSError("locked"), 0, 0]

    async def run():
        task = asyncio.create_task(_periodic_retention_purge(store, interval_seconds=0.01))
        await asyncio.sleep(0.15)
        task.cancel()

    asyncio.run(run())
    assert store.purge_older_than.call_count >= 2


def test_reviewer_registry_restricts_identities_only_when_configured(tmp_path, monkeypatch):
    from src.models.evidence import require_human_reviewer
    assert require_human_reviewer("bob") == "bob"
    registry = tmp_path / "reviewers.txt"
    registry.write_text("# scholars\nAlice\n", encoding="utf-8")
    monkeypatch.setenv("REVIEWER_REGISTRY_PATH", str(registry))
    assert require_human_reviewer("alice ") == "alice "
    with pytest.raises(ValueError, match="registry"):
        require_human_reviewer("bob")
    with pytest.raises(ValueError, match="automatic"):
        require_human_reviewer("auto")


@pytest.mark.parametrize("text, party", [
    ("financed by Bank of Egypt and Gulf Finance", "Bank of Egypt and Gulf Finance"),
    ("التمويل من بنك وطني", "بنك وطني"),
    ("financed by Example Finance and I paid EGP 5000 down", "Example Finance"),
])
def test_financier_names_are_cut_only_where_a_new_clause_begins(text, party):
    from tests.test_review_hardening import _extract
    assert _extract(text)["financing_party"].value == party


def test_bare_number_continues_the_transactions_single_currency():
    from src.chatbot.described_operation_facts import known_currency, parse_schedule_reply
    conversation = _pending_conversation("down_payment")
    assert known_currency(conversation.snapshot) == "EGP"
    assert parse_schedule_reply("5000", "down_payment", "EGP").currency == "EGP"
    assert DescribedOperationService.accepts("5000", conversation)
    assert parse_schedule_reply("5000", "down_payment") is None  # nothing known: never invent a currency
    assert parse_schedule_reply("USD 5000", "down_payment", "EGP") is None
    assert parse_schedule_reply("5000 dollars", "down_payment", "EGP") is None


def test_currency_binds_to_the_amount_it_touches():
    from tests.test_review_hardening import _extract
    assert _extract("I paid deposit EGP 5000 (about USD 100)")["down_payment"].status == "user_reported"
    assert _extract("I paid deposit EGP 5000 USD")["down_payment"].status == "unknown"
