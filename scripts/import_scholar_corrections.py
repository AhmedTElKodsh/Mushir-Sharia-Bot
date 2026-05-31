"""Import scholar review corrections from CSV or XLSX.

Usage:
  python scripts/import_scholar_corrections.py scholar_review_2026-05-27.csv
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Iterable

import yaml

from src.governance.scholar_review import ScholarReviewQueueStore
from src.scholar.review_schema import ScholarReview


def import_corrections(
    review_path: Path,
    *,
    queue_path: Path,
    corrections_log_path: Path,
    gold_eval_path: Path,
    ontology_patch_path: Path,
) -> int:
    reviews = [review for review in _load_reviews(review_path) if review.query_id]
    applied = 0
    queue = ScholarReviewQueueStore(queue_path)
    for review in reviews:
        correction = review.model_dump()
        _append_jsonl(corrections_log_path, correction)
        if review.requires_ontology_patch:
            _append_ontology_patch(ontology_patch_path, review)
        if review.new_edge_case:
            _append_gold_case(gold_eval_path, review)
        try:
            queue.mark_reviewed(review.query_id)
        except ValueError:
            pass
        applied += 1
    return applied


def _load_reviews(path: Path) -> Iterable[ScholarReview]:
    for row in _read_rows(path):
        if not any(str(value or "").strip() for value in row.values()):
            continue
        if not str(row.get("scholar_name") or "").strip():
            continue
        yield ScholarReview(
            query_id=str(row.get("query_id") or "").strip(),
            scholar_name=str(row.get("scholar_name") or "").strip(),
            scholar_institution=str(row.get("scholar_institution") or "").strip(),
            ruling_accuracy=str(row.get("ruling_accuracy") or "").strip().upper(),
            standard_citation=str(row.get("standard_citation") or "").strip().upper(),
            disagreement_disclosed=str(row.get("disagreement_disclosed") or "NA").strip().upper(),
            severity_if_wrong=str(row.get("severity_if_wrong") or "NA").strip().upper(),
            corrected_answer_ar=_optional(row.get("corrected_answer_ar")),
            corrected_ruling=_optional(row.get("corrected_ruling")),
            corrected_standards=row.get("corrected_standards"),
            new_edge_case=_truthy(row.get("new_edge_case")),
            scholar_notes=str(row.get("scholar_notes") or ""),
            dalil=str(row.get("dalil") or ""),
            conditions=row.get("conditions") or "",
        )


def _read_rows(path: Path) -> list[dict]:
    if path.suffix.lower() == ".xlsx":
        try:
            import openpyxl
        except ImportError as exc:
            raise SystemExit("openpyxl is required for XLSX import; use CSV or install requirements.txt") from exc
        workbook = openpyxl.load_workbook(path)
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [str(value or "") for value in rows[0]]
        return [
            {headers[index]: value for index, value in enumerate(row) if index < len(headers)}
            for row in rows[1:]
        ]
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def _append_ontology_patch(path: Path, review: ScholarReview) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    patches = []
    if path.exists():
        patches = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    patches.append(
        {
            "query_id": review.query_id,
            "corrected_ruling": review.corrected_ruling,
            "corrected_standards": review.corrected_standards or [],
            "conditions": review.conditions,
            "dalil": review.dalil,
            "scholar_notes": review.scholar_notes,
            "review_timestamp": review.review_timestamp,
            "status": "PENDING_DEVELOPER_RECONCILIATION",
        }
    )
    path.write_text(yaml.safe_dump(patches, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _append_gold_case(path: Path, review: ScholarReview) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cases = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    cases.append(
        {
            "case_id": f"SCHOLAR-{review.query_id}",
            "query_ar": review.corrected_answer_ar or "",
            "query_en": "",
            "contract_type": "",
            "party_role": "",
            "ruling": review.corrected_ruling or "",
            "dalil": review.dalil or "PENDING_DEVELOPER_RECONCILIATION",
            "applicable_standards": review.corrected_standards or [],
            "forbidden_standards": [],
            "khilaf_flag": review.disagreement_disclosed == "YES",
            "conditions": review.conditions,
            "scholar_sign_off": review.scholar_sign_off,
        }
    )
    path.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _optional(value) -> str | None:
    text = str(value or "").strip()
    return text or None


def _truthy(value) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "نعم"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("review_file")
    parser.add_argument("--queue", default="data/scholar_review_queue.jsonl")
    parser.add_argument("--corrections-log", default="data/scholar_corrections_log.jsonl")
    parser.add_argument("--gold-eval", default="tests/data/gold_eval_set.json")
    parser.add_argument("--ontology-patches", default="data/concept_ontology/scholar_corrections_pending.yaml")
    args = parser.parse_args()
    count = import_corrections(
        Path(args.review_file),
        queue_path=Path(args.queue),
        corrections_log_path=Path(args.corrections_log),
        gold_eval_path=Path(args.gold_eval),
        ontology_patch_path=Path(args.ontology_patches),
    )
    print(f"Import complete. Scholar reviews applied: {count}")
    print("Command: pytest tests/eval/test_routing_accuracy.py -v")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
