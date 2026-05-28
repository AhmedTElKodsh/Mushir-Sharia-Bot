import csv
from datetime import datetime, timezone

import pytest

from src.governance import (
    ScholarReviewDecision,
    ScholarReviewEvidenceGate,
    ScholarReviewPacket,
    ScholarReviewPacketCsvStore,
    ScholarReviewPacketMarkdownStore,
    ScholarReviewQueue,
    ScholarReviewQueueItem,
    ScholarReviewQueueStore,
    ScholarReviewStore,
    ScholarReviewTargetType,
    ScholarReviewWorkflowStatus,
)
from src.models.ruling import AAOIFICitation, AnswerContract, ComplianceStatus


pytestmark = pytest.mark.service


def test_scholar_review_store_round_trips_manual_decision_without_auto_promotion(tmp_path):
    path = tmp_path / "scholar-reviews.jsonl"
    store = ScholarReviewStore(path)
    reviewed_at = datetime(2026, 5, 24, 12, 0, tzinfo=timezone.utc)

    record = ScholarReviewEvidenceGate(
        review_id="review-answer-001",
        target_type=ScholarReviewTargetType.ANSWER,
        target_id="answer-001",
        reviewer_id="scholar-a",
        decision=ScholarReviewDecision.ACCEPTED_FOR_GOLD_SET,
        source_ids=["aaoifi-ss-08-en"],
        citation_ids=["citation-1"],
        rationale="Citations and answer framing are acceptable for the supervised gold set.",
        reviewed_at=reviewed_at,
        rule_id="murabaha-late-payment-v1",
        rule_version="2026-05-24",
    )

    store.append(record)
    loaded = ScholarReviewStore(path).load()

    assert loaded == [record]
    assert loaded[0].is_gold_candidate is True
    assert loaded[0].can_update_runtime_governance is False
    assert loaded[0].to_dict()["reviewed_at"] == "2026-05-24T12:00:00+00:00"


def test_scholar_review_requires_human_identity_and_evidence_trace():
    with pytest.raises(ValueError, match="reviewer_id is required"):
        ScholarReviewEvidenceGate(
            review_id="review-answer-002",
            target_type=ScholarReviewTargetType.ANSWER,
            target_id="answer-002",
            reviewer_id="",
            decision=ScholarReviewDecision.ACCEPTED_FOR_GOLD_SET,
            source_ids=["aaoifi-ss-08-en"],
            citation_ids=["citation-1"],
            rationale="Manual decision.",
        )

    with pytest.raises(ValueError, match="source_ids and citation_ids are required"):
        ScholarReviewEvidenceGate(
            review_id="review-answer-003",
            target_type=ScholarReviewTargetType.ANSWER,
            target_id="answer-003",
            reviewer_id="scholar-a",
            decision=ScholarReviewDecision.ACCEPTED_FOR_GOLD_SET,
            source_ids=[],
            citation_ids=[],
            rationale="Manual decision.",
        )


def test_scholar_review_cannot_infer_approval_from_model_confidence():
    with pytest.raises(ValueError, match="cannot be promoted by model confidence"):
        ScholarReviewEvidenceGate(
            review_id="review-answer-004",
            target_type=ScholarReviewTargetType.ANSWER,
            target_id="answer-004",
            reviewer_id="model-confidence",
            decision=ScholarReviewDecision.ACCEPTED_FOR_GOLD_SET,
            source_ids=["aaoifi-ss-08-en"],
            citation_ids=["citation-1"],
            rationale="confidence=0.98",
            model_confidence=0.98,
        )


def test_app_scholar_review_packet_exports_human_readable_review_tables(tmp_path):
    answer = AnswerContract(
        answer=(
            "INSUFFICIENT_DATA: This scenario requires explicit rule evidence "
            "and human review before Mushir can provide a safe non-binding assessment."
        ),
        status=ComplianceStatus.INSUFFICIENT_DATA,
        citations=[
            AAOIFICitation(
                document_id="AAOIFI_Sharia_Standard_08_Murabaha.md",
                standard_number="SS-08",
                section_number="1",
                section_title="Murabaha controls",
                excerpt="The institution must own and bear risk in the asset before sale.",
                confidence_score=0.87,
            )
        ],
        reasoning_summary="The deterministic rule trace is exported for scholar review.",
        metadata={
            "response_language": "en",
            "transaction_scenario": {
                "question_type": "permissibility",
                "contract_family": "murabaha",
                "missing_facts": ["ownership_sequence"],
                "uncertainties": ["permissibility_requires_sharia_standards"],
            },
            "standards_route": {
                "route_id": "murabaha-late-payment-penalty",
                "candidate_standards": ["SS-03", "SS-08"],
                "primary": ["sharia_standard"],
                "requires_rule_evaluation": True,
            },
            "rule_evaluation": {
                "rule_id": "murabaha-late-payment-v1",
                "rule_version": "2026-05-24",
                "matched_rules": ["murabaha-late-payment-v1"],
                "missing_facts": ["ownership_sequence"],
                "evidence_requirements": ["sharia_standard_evidence"],
                "human_review_flags": ["human_review_required"],
            },
            "source_families": ["sharia_standard"],
            "scholar_review_workflow": {
                "required": True,
                "path": "scholar_review_enhancement",
                "blocks_main_app": False,
            },
        },
    )
    packet = ScholarReviewPacket.from_answer(
        review_id="review-packet-001",
        query="Is this murabaha late-payment clause allowed?",
        answer=answer,
    )
    csv_path = tmp_path / "scholar_review_packet.csv"
    md_path = tmp_path / "scholar_review_packet.md"

    ScholarReviewPacketCsvStore.export_packet(csv_path, packet)
    ScholarReviewPacketMarkdownStore.export_packet(md_path, packet)

    rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8-sig")))
    markdown = md_path.read_text(encoding="utf-8")
    assert packet.can_update_runtime_governance is False
    assert packet.workflow_status == ScholarReviewWorkflowStatus.PENDING
    assert rows[0]["review_path"] == "scholar_review_enhancement"
    assert rows[0]["blocks_main_app"] == "false"
    assert rows[0]["runtime_governance_update_allowed"] == "false"
    assert rows[0]["standard_number"] == "SS-08"
    assert rows[0]["candidate_standards"] == "SS-03|SS-08"
    assert rows[0]["human_scholar_review"] == ""
    assert "Scholar Review Packet" in markdown
    assert "SS-08" in markdown


def test_scholar_review_queue_store_round_trips_pending_items(tmp_path):
    path = tmp_path / "scholar_review_queue.jsonl"
    store = ScholarReviewQueueStore(path)
    item = ScholarReviewQueueItem(
        query_id="q-001",
        queue=ScholarReviewQueue.AUTO_FLAGGED,
        query_en="Is this late penalty allowed?",
        system_answer_en="Scholar review required.",
        system_ruling="refer_to_scholar",
        system_standards=["SS-03", "SS-08"],
        system_confidence=1.2,
        flag_reason="rule_evaluation_requires_scholar_review",
        source_chunks=["chunk-1"],
    )

    store.append(item)
    loaded = ScholarReviewQueueStore(path).load()
    pending = ScholarReviewQueueStore(path).pending()
    store.mark_reviewed("q-001")

    assert loaded[0].queue == ScholarReviewQueue.AUTO_FLAGGED
    assert loaded[0].system_confidence == 1.0
    assert pending[0].query_id == "q-001"
    assert ScholarReviewQueueStore(path).pending() == []


def test_scholar_review_queue_item_can_be_built_from_answer_contract():
    answer = AnswerContract(
        answer="Supported by AAOIFI.",
        status=ComplianceStatus.COMPLIANT,
        citations=[
            AAOIFICitation(
                document_id="AAOIFI_Sharia_Standard_11_Istisna.md",
                standard_number="SS-11",
                section_number="1",
                excerpt="Istisna excerpt.",
            )
        ],
        reasoning_summary="Grounded.",
        metadata={
            "response_language": "en",
            "confidence": 0.82,
            "retrieved_chunk_ids": ["chunk-9"],
            "standards_route": {"candidate_standards": ["SS-11", "SS-05"]},
            "verdict_contract": {"verdict": "conditional"},
        },
    )

    item = ScholarReviewQueueItem.from_answer(
        queue=ScholarReviewQueue.RANDOM_SAMPLE,
        query="Is a construction delay penalty allowed?",
        answer=answer,
        flag_reason="random_post_launch_sample",
        request_id="req-9",
    )

    assert item.query_id == "req-9"
    assert item.queue == ScholarReviewQueue.RANDOM_SAMPLE
    assert item.system_standards == ["SS-11", "SS-05"]
    assert item.source_chunks == ["chunk-9"]
