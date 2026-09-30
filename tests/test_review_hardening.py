"""Hardening regressions from the 2026-09-30 review (synthetic fixtures only)."""
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from src.chatbot.application_service import ApplicationService
from src.chatbot.described_operation import DescribedOperationService
from src.chatbot.described_operation_facts import extract_operation_facts, parse_schedule_reply
from src.chatbot.mechanism_terms import generic_mechanism_unknown, mechanism_routing_text
from src.chatbot.session_manager import SessionManager
from src.chatbot.structure_clarification import clarify_structure
from src.governance.rule_cards import MAX_RULE_FILE_BYTES, load_rule_cards
from src.models.evidence import (
    CaptureManifest, EvidenceScope, FactCandidate, FactObservation, Money, UserTurnProvenance,
    VerificationRecord,
)
from src.models.evidence_display import without_answer_scores
from src.models.ruling import AnswerContract, ComplianceStatus
from tests.test_approved_card_evaluator import NOW, SCOPE, card, fact
from tests.test_l1_contracts import FakeLLM, FakeRetriever

CAPTURE = dict(source_id="s", url="https://example.org/a", captured_at=NOW, sha256="a" * 64,
               content_type="text/plain", language="en", access_status="accessible", document_version="v1")


# ---- evidence contracts: negative cases -------------------------------------------------
@pytest.mark.parametrize("slot", ["down_payment", "cash_price", "financed_or_final_price", "instalment_amount"])
def test_monetary_slots_reject_bare_numbers(slot):
    with pytest.raises(ValidationError):
        fact(slot, 5000)


@pytest.mark.parametrize("kwargs", [
    dict(lane="personal", document_scope="schedule"),
    dict(lane="general", transaction_id="t", document_scope="general"),
    dict(lane="company", document_scope="template"),
])
def test_scope_identity_rules(kwargs):
    with pytest.raises(ValidationError):
        EvidenceScope(**kwargs)


@pytest.mark.parametrize("url", [
    "file:///etc/passwd", "ftp://example.org/a", "http://localhost/a", "http://127.0.0.1/a",
    "http://192.168.1.5/a", "https://user:pw@example.org/a", "https://example.org/a?token=x",
])
def test_capture_urls_must_be_public_http(url):
    with pytest.raises(ValidationError):
        CaptureManifest(**{**CAPTURE, "url": url})


def test_capture_digest_is_case_normalised():
    assert CaptureManifest(**{**CAPTURE, "sha256": "A" * 64}).sha256 == "a" * 64


@pytest.mark.parametrize("reviewer", ["auto", "Claude", " LLM "])
def test_verification_cannot_be_recorded_by_automatic_identity(reviewer):
    with pytest.raises(ValidationError):
        VerificationRecord(reviewer_id=reviewer, recorded_at=NOW, decision="verified", notes="n")


def test_numerically_equal_money_is_not_a_conflict():
    source = UserTurnProvenance(session_id="s1", turn_id="t1", exact_text="x", recorded_at=NOW, version=1, scope=SCOPE)
    candidates = tuple(FactCandidate(status="user_reported", source=source,
                                     value=Money(amount=amount, currency="EGP"))
                       for amount in (100, "100.00"))
    with pytest.raises(ValidationError):
        FactObservation(slot="down_payment", scope=SCOPE, version=1, recorded_at=NOW,
                        status="conflicting", candidates=candidates)


# ---- rule cards ---------------------------------------------------------------------------
def test_default_fact_question_must_be_single():
    with pytest.raises(ValidationError):
        card(unknown_fact_question="Is there a fee? And a penalty?")


def test_yaml_aliases_and_oversized_files_are_refused(tmp_path):
    alias = tmp_path / "alias.yaml"
    alias.write_text("- &a {rule_id: x}\n- *a\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_rule_cards(alias)
    big = tmp_path / "big.yaml"
    big.write_text("#" * (MAX_RULE_FILE_BYTES + 1), encoding="utf-8")
    with pytest.raises(ValueError, match="size limit"):
        load_rule_cards(big)


def _card_yaml(tmp_path):
    import yaml
    data = card().model_dump(mode="json")
    path = tmp_path / "cards.yaml"
    path.write_text(yaml.safe_dump([data]), encoding="utf-8")
    return path


def test_env_card_path_reaches_the_evaluator(tmp_path, monkeypatch):
    monkeypatch.setenv("APPROVED_RULE_CARDS_PATH", str(_card_yaml(tmp_path)))
    service = ApplicationService(retriever=Mock(), llm_client=Mock())
    assert [c.rule_id for c in service.described_operations.evaluator.cards] == ["synthetic-test-only"]


def test_explicit_cards_outrank_env_and_bad_path_fails_fast(tmp_path, monkeypatch):
    monkeypatch.setenv("APPROVED_RULE_CARDS_PATH", str(tmp_path / "missing.yaml"))
    with pytest.raises(RuntimeError, match="APPROVED_RULE_CARDS_PATH"):
        ApplicationService(retriever=Mock(), llm_client=Mock())
    service = ApplicationService(retriever=Mock(), llm_client=Mock(), approved_rule_cards=[card()])
    assert len(service.described_operations.evaluator.cards) == 1


# ---- decision store -----------------------------------------------------------------------
def test_empty_db_path_env_falls_back_to_default(tmp_path, monkeypatch):
    from src.storage import decision_review_store as store
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DECISION_REVIEW_DB_PATH", "")
    assert store.configured_decision_store().path == (tmp_path / store.DEFAULT_DB_PATH).resolve()


def test_purge_removes_only_expired_records(tmp_path):
    from src.storage.decision_review_store import SQLiteDecisionReviewStore, configured_retention_days
    from src.models.decision_audit import prepare_decision_record
    store = SQLiteDecisionReviewStore(tmp_path / "r.sqlite3")
    answer = AnswerContract(answer="a", status=ComplianceStatus.INSUFFICIENT_DATA)
    old = prepare_decision_record("q", answer, session_id="s", request_id="old")
    new = prepare_decision_record("q", answer, session_id="s", request_id="new")
    store.append(old.model_copy(update={"recorded_at": datetime.now(UTC) - timedelta(days=400)}))
    store.append(new)
    assert store.purge_older_than(configured_retention_days()) == 1
    assert store.get(new.review_id) is not None and store.get(old.review_id) is None
    with pytest.raises(ValueError):
        store.purge_older_than(0)


# ---- score scrubbing and contract construction ---------------------------------------------
def test_score_scrub_covers_other_score_names_but_keeps_flags_and_odd_keys():
    cleaned = without_answer_scores({"rerank_score": .8, "similarity_score": .7, "relevance": .6, "low_confidence": True,
                                     "source_confidence": "official", 7: 1.5, "k": 5})
    assert cleaned == {"low_confidence": True, "source_confidence": "official", 7: 1.5, "k": 5}


def test_contract_tolerates_missing_metadata_and_rejects_bad_status_cleanly():
    assert AnswerContract(answer="a", status=ComplianceStatus.INSUFFICIENT_DATA, metadata=None).metadata["evidence"]
    with pytest.raises(ValueError, match="ComplianceStatus"):
        AnswerContract(answer="a", status="INSUFFICIENT_DATA")


# ---- mechanism wording and fact extraction ---------------------------------------------------
def test_arabic_connector_inside_a_word_does_not_hide_a_negation():
    # "بلغ" merely contains the connector letters "بل"; the negation before it must survive.
    assert generic_mechanism_unknown("تقسيط ليس بلغ مرابحة")
    # A genuine contrast word ("بل") does start a new clause, so the ijarah is affirmed.
    assert not generic_mechanism_unknown("تقسيط ليس مرابحة بل اجارة")


def test_negated_named_contract_is_masked_even_without_generic_wording():
    assert "murabaha" not in mechanism_routing_text("this is not a murabaha, it is ijara")
    assert "ijara" in mechanism_routing_text("this is not a murabaha, it is ijara")


def test_extra_named_topics_are_not_generic_unknowns():
    assert not generic_mechanism_unknown("takaful financing")


def _extract(text):
    return {f.slot: f for f in extract_operation_facts(
        text, session_id="s", transaction_id="t", turn_id="u", version=1, recorded_at=datetime.now(UTC)).facts}


def test_absurd_instalment_counts_are_not_facts_and_do_not_crash():
    assert parse_schedule_reply("9" * 5000, "instalment_count") is None
    assert parse_schedule_reply("1001", "instalment_count") is None
    facts = _extract("I paid deposit EGP 5000 and " + "9" * 5000 + " x EGP 5")
    assert facts["instalment_count"].status == "unknown"


def test_financing_party_stops_at_the_end_of_the_name():
    assert _extract("financed by Example Finance and I paid EGP 5000 down")["financing_party"].value == "Example Finance"


def test_arabic_word_containing_negation_letters_does_not_drop_a_fact():
    facts = _extract("اشتريت من المشتري ايفون مقدم 5000 جنيه")
    assert facts["down_payment"].status == "user_reported"


def test_negation_is_scoped_to_its_own_clause():
    facts = _extract("Not sure about the total, but the deposit is EGP 5000")
    assert facts["down_payment"].status == "user_reported"


# ---- pending-question handling -----------------------------------------------------------------
STORY = "I bought an iPhone with deposit EGP 5000 and 12 x EGP 3000."


def test_unrelated_message_is_not_swallowed_by_an_open_financier_question():
    _, conversation = DescribedOperationService([]).answer(
        STORY, session_id="s1", request_id="r1", previous=None, language="en")
    assert conversation.pending_slot == "financing_party"
    assert not DescribedOperationService.accepts("Tell me about riba", conversation)
    assert DescribedOperationService.accepts("The bank", conversation)


def test_exhausted_budget_leaves_nothing_pending():
    service = DescribedOperationService([])
    _, conv = service.answer(STORY, session_id="s1", request_id="r", previous=None, language="en")
    for turn in range(3):
        _, conv = service.answer("Please continue", session_id="s1", request_id=f"r{turn}", previous=conv, language="en")
    assert conv.pending_slot is None


# ---- structure clarification state ---------------------------------------------------------------
@pytest.mark.parametrize("pending", [
    {"slot": "nonsense", "language": "en", "asked_count": 0},
    {"slot": "resale_arranger", "asked_count": 0},
    "garbage",
])
def test_malformed_pending_structure_state_is_ignored(pending):
    answer, nxt = clarify_structure("hello there", "hello there", "en", pending)
    assert answer is None and nxt is None


def test_stale_pending_structure_question_expires():
    stale = {"slot": "resale_arranger", "original_query": "q", "asked_count": 1, "language": "en",
             "created_at": (datetime.now(UTC) - timedelta(hours=3)).isoformat()}
    answer, nxt = clarify_structure("banana", "banana", "en", stale)
    assert answer is None and nxt is None


# ---- application service session handling ---------------------------------------------------------
def _service(tmp_path):
    from src.storage.decision_review_store import SQLiteDecisionReviewStore
    return ApplicationService(retriever=FakeRetriever([]), llm_client=FakeLLM("unused"), session_store=SessionManager(),
                              decision_store=SQLiteDecisionReviewStore(tmp_path / "r.sqlite3"))


def test_corrupt_saved_operation_is_dropped_instead_of_failing_every_turn(tmp_path):
    app = _service(tmp_path)
    app.answer(STORY, session_id="s1")
    app.session_store.get_session("s1").metadata["described_operation"] = {"bogus": True}
    result = app.answer("The bank", session_id="s1")
    assert result.status in set(ComplianceStatus)


def test_session_review_rows_are_bounded(tmp_path):
    app = _service(tmp_path)
    for _ in range(ApplicationService.MAX_SESSION_REVIEW_ROWS + 5):
        app.answer(STORY + " Different purchase.", session_id="s1")
    assert len(app.session_store.get_session("s1").metadata["operation_review_rows"]) == ApplicationService.MAX_SESSION_REVIEW_ROWS


def test_anonymous_request_creates_no_session(tmp_path):
    app = _service(tmp_path)
    app.answer(STORY)
    assert app.session_store._sessions == {}


# ---- CLI --------------------------------------------------------------------------------------------
class _FakeService:
    def __init__(self):
        self.calls = []
        self.k = None

    def answer(self, query, **kwargs):
        self.calls.append((query, kwargs["disclaimer_acknowledged"]))
        return AnswerContract(answer="ok", status=ComplianceStatus.INSUFFICIENT_DATA)


def _run_cli(monkeypatch, argv, inputs, env=None):
    from src.chatbot import cli
    fake = _FakeService()
    monkeypatch.setattr(cli, "create_service", lambda: fake)
    monkeypatch.setattr("sys.argv", ["mushir", *argv])
    monkeypatch.setenv("REQUIRE_DISCLAIMER_ACK", env or "false")
    feed = iter(inputs)

    def fake_input(_prompt=""):
        try:
            return next(feed)
        except StopIteration:
            raise EOFError

    monkeypatch.setattr("builtins.input", fake_input)
    cli.main()
    return fake


def test_cli_interactive_requires_acknowledgement_when_configured(monkeypatch):
    assert _run_cli(monkeypatch, ["--interactive"], ["nope", "Q?"], env="true").calls == []
    fake = _run_cli(monkeypatch, ["--interactive", "--k", "3"], ["I acknowledge", "Is X ok?", "", "exit"], env="true")
    assert fake.calls == [("Is X ok?", True)] and fake.k == 3


def test_cli_survives_closed_stdin_and_rejects_bad_k(monkeypatch, capsys):
    assert _run_cli(monkeypatch, ["--interactive"], []).calls == []
    with pytest.raises(SystemExit):
        _run_cli(monkeypatch, ["--query", "x", "--k", "0"], [])
    assert "--k must be at least 1" in capsys.readouterr().err


# ---- API surface ---------------------------------------------------------------------------------------
def test_citation_captured_at_and_readiness_store_are_published():
    from fastapi.testclient import TestClient
    from src.api.dependencies import get_application_service
    from src.api.main import create_app
    from src.models.ruling import AAOIFICitation

    class Service:
        def answer(self, query, **kwargs):
            return AnswerContract(answer="Evidence excerpt", status=ComplianceStatus.INSUFFICIENT_DATA,
                citations=[AAOIFICitation(document_id="doc", standard_number="SS-08", captured_at="2026-01-01T00:00:00Z")])

    app = create_app()
    app.dependency_overrides[get_application_service] = Service
    with TestClient(app) as client:
        rest = client.post("/api/v1/query", json={"query": "What is murabaha?"})
        stream = client.post("/api/v1/query/stream", json={"query": "What is murabaha?"})
        ready = client.get("/ready")
    assert rest.json()["citations"][0]["captured_at"] == "2026-01-01T00:00:00+00:00"
    assert "2026-01-01T00:00:00+00:00" in stream.text
    assert "decision_review_store" in ready.json()["infrastructure"]
