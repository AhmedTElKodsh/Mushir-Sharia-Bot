from datetime import UTC, datetime

import pytest

from src.models.ruling import AAOIFICitation, AnswerContract, ComplianceStatus


def test_answer_metadata_and_citations_do_not_publish_legacy_scores():
    answer = AnswerContract(answer="Source excerpt", status=ComplianceStatus.INSUFFICIENT_DATA,
        citations=[AAOIFICitation(document_id="doc", standard_number="SS-08", confidence_score=.99)],
        metadata={"confidence": .99, "nested": {"confidence_score": .9}, "source_confidence": "official"})
    public = answer.to_dict()
    assert "confidence" not in public["metadata"]
    assert "confidence_score" not in public["metadata"]["nested"]
    assert "confidence_score" not in public["citations"][0]
    assert public["metadata"]["evidence"]["source_age_status"] == "unknown"
    assert public["metadata"]["source_confidence"] == "official"


@pytest.mark.parametrize("status", list(ComplianceStatus))
def test_every_answer_has_evidence_summary(status):
    answer = AnswerContract(answer="Question?" if status == ComplianceStatus.CLARIFICATION_NEEDED else "Text",
        status=status, clarification_question="Question?" if status == ComplianceStatus.CLARIFICATION_NEEDED else None,
        citations=[AAOIFICitation(document_id="doc", standard_number="SS-08")])
    assert answer.to_dict()["metadata"]["evidence"]["status"]


@pytest.mark.parametrize("date", [None, "bad", "2026-01-01", "2027-01-01T00:00:00Z"])
def test_missing_invalid_naive_future_capture_dates_are_unknown(date):
    from src.models.evidence_display import source_age
    result = source_age(date, now=datetime(2026, 9, 30, tzinfo=UTC))
    assert result == {"captured_at": None, "age_days": None}


@pytest.mark.parametrize("date", ["not a timestamp", "2099-01-01T00:00:00Z", "2026-01-01"])
def test_public_citation_dates_follow_same_unknown_policy(date):
    citation = AAOIFICitation(document_id="doc", standard_number="SS-08", captured_at=date)
    assert citation.to_dict()["captured_at"] is None


def test_capture_age_uses_observed_date_and_aware_clock():
    from src.models.evidence_display import source_age
    assert source_age("2026-09-28T03:00:00+03:00", now=datetime(2026, 9, 30, tzinfo=UTC)) == {
        "captured_at": "2026-09-28T00:00:00+00:00", "age_days": 2}


def test_real_rest_and_stream_remove_legacy_scores():
    from fastapi.testclient import TestClient
    from src.api.dependencies import get_application_service
    from src.api.main import create_app

    class Service:
        def answer(self, query, **kwargs):
            return AnswerContract(answer="Evidence excerpt", status=ComplianceStatus.INSUFFICIENT_DATA,
                citations=[AAOIFICitation(document_id="doc", standard_number="SS-08", confidence_score=.99,
                                          captured_at="2026-01-01T00:00:00Z")], metadata={"confidence": .99})

    app = create_app()
    app.dependency_overrides[get_application_service] = Service
    with TestClient(app) as client:
        rest = client.post("/api/v1/query", json={"query": "What is murabaha?"})
        stream = client.post("/api/v1/query/stream", json={"query": "What is murabaha?"})
    assert rest.status_code == stream.status_code == 200
    assert "confidence" not in rest.text + stream.text
    assert rest.json()["metadata"]["evidence"]["source_age_status"] == "known"
    assert '"evidence"' in stream.text


def test_cli_main_uses_shared_gate_and_prints_unknown_source_age(monkeypatch, capsys):
    from src.chatbot import cli
    monkeypatch.delenv("REQUIRE_DISCLAIMER_ACK", raising=False)
    monkeypatch.setattr("sys.argv", ["mushir", "--query", "Is banking Tawarruq permissible?"])
    cli.main()
    output = capsys.readouterr().out
    assert "Who arranges" in output
    assert "Evidence status: clarification_required" in output
    assert "Source capture date and age: unknown" in output
    assert "confidence" not in output.lower()


def test_cli_respects_required_disclaimer(monkeypatch, capsys):
    from src.chatbot import cli
    monkeypatch.setenv("REQUIRE_DISCLAIMER_ACK", "true")
    monkeypatch.setattr("sys.argv", ["mushir", "--query", "Is banking Tawarruq permissible?"])
    cli.main()
    output = capsys.readouterr().out
    assert "Who arranges" not in output
    assert "acknowledge" in output.lower()


def test_dated_citation_survives_cache_roundtrip():
    from src.chatbot.application_service import ApplicationService
    from src.chatbot.citation_validator import CitationValidator
    citation = CitationValidator().citation_for_chunk({"content": "Definition.", "metadata": {
        "standard_number": "SS-08", "captured_at": "2026-01-01T00:00:00Z"}})
    assert citation is not None
    answer = AnswerContract(answer="Definition.", status=ComplianceStatus.INSUFFICIENT_DATA, citations=[citation])
    restored = ApplicationService._contract_from_dict(answer.to_dict())
    assert restored.metadata["evidence"]["sources"][0]["captured_at"] == "2026-01-01T00:00:00+00:00"


def test_answer_surface_templates_have_no_numeric_confidence_widget():
    from pathlib import Path
    import re
    root = Path(__file__).resolve().parents[1]
    for relative in ("src/static/js/app.js", "src/static/js/renderer.js", "src/chatbot/cli.py"):
        text = (root / relative).read_text(encoding="utf-8")
        assert not re.search(r"confidence|درجة الثقة|average relevance|\.score\b", text, re.I), relative
