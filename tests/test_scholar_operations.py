import csv
import json

import yaml

from scripts.export_scholar_review import export_pending
from scripts.import_scholar_corrections import import_corrections
from src.governance.scholar_review import (
    ScholarReviewQueue,
    ScholarReviewQueueItem,
    ScholarReviewQueueStore,
)
from src.scholar.review_schema import ScholarReview


def test_scholar_review_schema_normalizes_review_form_fields():
    review = ScholarReview(
        query_id="q-1",
        scholar_name="Dr. Reviewer",
        scholar_institution="Review Board",
        ruling_accuracy="PARTIALLY_CORRECT",
        standard_citation="MISSING",
        disagreement_disclosed="YES",
        severity_if_wrong="HIGH",
        corrected_standards="SS-11, SS-05",
        conditions="contractor delays, actual damage",
    )

    assert review.corrected_standards == ["SS-11", "SS-05"]
    assert review.conditions == ["contractor delays", "actual damage"]
    assert review.requires_ontology_patch is True
    assert review.scholar_sign_off == "DONE"


def test_export_scholar_review_writes_pending_queue_to_csv(tmp_path):
    queue_path = tmp_path / "queue.jsonl"
    output_path = tmp_path / "scholar_review.csv"
    store = ScholarReviewQueueStore(queue_path)
    store.append(
        ScholarReviewQueueItem(
            query_id="q-pending",
            queue=ScholarReviewQueue.AUTO_FLAGGED,
            query_en="Is this allowed?",
            system_answer_en="Needs review.",
            system_ruling="INSUFFICIENT_DATA",
            system_standards=["SS-08"],
            system_confidence=0.6,
            flag_reason="rule_evaluation_requires_scholar_review",
            source_chunks=["chunk-1"],
        )
    )

    count = export_pending(queue_path, output_path)

    rows = list(csv.DictReader(output_path.open(newline="", encoding="utf-8-sig")))
    assert count == 1
    assert rows[0]["query_id"] == "q-pending"
    assert rows[0]["system_standards"] == "SS-08"
    assert rows[0]["ruling_accuracy"] == ""


def test_import_scholar_corrections_logs_patches_gold_case_and_marks_reviewed(tmp_path):
    queue_path = tmp_path / "queue.jsonl"
    review_path = tmp_path / "scholar_review.csv"
    corrections_log = tmp_path / "corrections.jsonl"
    gold_eval = tmp_path / "gold_eval_set.json"
    ontology_patches = tmp_path / "scholar_corrections_pending.yaml"
    ScholarReviewQueueStore(queue_path).append(
        ScholarReviewQueueItem(
            query_id="q-review",
            queue=ScholarReviewQueue.USER_REPORTED,
            query_en="Is this guarantee fee correct?",
            system_answer_en="Answer.",
            system_ruling="CONDITIONAL",
            system_standards=["SS-05"],
            system_confidence=0.7,
            flag_reason="user_reported",
        )
    )
    gold_eval.write_text("[]\n", encoding="utf-8")
    with review_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "query_id",
                "scholar_name",
                "scholar_institution",
                "ruling_accuracy",
                "standard_citation",
                "disagreement_disclosed",
                "severity_if_wrong",
                "corrected_answer_ar",
                "corrected_ruling",
                "corrected_standards",
                "conditions",
                "dalil",
                "new_edge_case",
                "scholar_notes",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "query_id": "q-review",
                "scholar_name": "Dr. Reviewer",
                "scholar_institution": "Review Board",
                "ruling_accuracy": "WRONG",
                "standard_citation": "WRONG",
                "disagreement_disclosed": "NO",
                "severity_if_wrong": "HIGH",
                "corrected_answer_ar": "تصحيح",
                "corrected_ruling": "PROHIBITED",
                "corrected_standards": "SS-05",
                "conditions": "actual admin cost only",
                "dalil": "SS-05",
                "new_edge_case": "true",
                "scholar_notes": "Patch ontology node.",
            }
        )

    count = import_corrections(
        review_path,
        queue_path=queue_path,
        corrections_log_path=corrections_log,
        gold_eval_path=gold_eval,
        ontology_patch_path=ontology_patches,
    )

    correction = json.loads(corrections_log.read_text(encoding="utf-8").splitlines()[0])
    cases = json.loads(gold_eval.read_text(encoding="utf-8"))
    patches = yaml.safe_load(ontology_patches.read_text(encoding="utf-8"))
    assert count == 1
    assert correction["query_id"] == "q-review"
    assert ScholarReviewQueueStore(queue_path).pending() == []
    assert cases[0]["case_id"] == "SCHOLAR-q-review"
    assert patches[0]["status"] == "PENDING_DEVELOPER_RECONCILIATION"
