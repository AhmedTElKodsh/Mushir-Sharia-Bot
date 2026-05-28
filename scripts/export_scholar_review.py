"""Export pending scholar review queue items to CSV or XLSX.

Usage:
  python scripts/export_scholar_review.py
  python scripts/export_scholar_review.py --output scholar_review_2026-05-27.csv
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path
from typing import Iterable

from src.governance.scholar_review import ScholarReviewQueueStore


FIELDS = [
    "query_id",
    "queue",
    "query_ar",
    "query_en",
    "system_answer_ar",
    "system_answer_en",
    "system_ruling",
    "system_standards",
    "system_confidence",
    "flag_reason",
    "source_chunks",
    "created_at",
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
]


def export_pending(queue_path: Path, output_path: Path) -> int:
    rows = [_row(item.to_dict()) for item in ScholarReviewQueueStore(queue_path).pending()]
    if output_path.suffix.lower() == ".xlsx":
        _write_xlsx(output_path, rows)
    else:
        _write_csv(output_path, rows)
    return len(rows)


def _row(item: dict) -> dict:
    row = {field: "" for field in FIELDS}
    row.update(
        {
            "query_id": item.get("query_id", ""),
            "queue": item.get("queue", ""),
            "query_ar": item.get("query_ar", ""),
            "query_en": item.get("query_en", ""),
            "system_answer_ar": item.get("system_answer_ar", ""),
            "system_answer_en": item.get("system_answer_en", ""),
            "system_ruling": item.get("system_ruling", ""),
            "system_standards": _join(item.get("system_standards")),
            "system_confidence": item.get("system_confidence", ""),
            "flag_reason": item.get("flag_reason", ""),
            "source_chunks": _join(item.get("source_chunks")),
            "created_at": item.get("created_at", ""),
            "new_edge_case": "false",
        }
    )
    return row


def _write_csv(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _write_xlsx(path: Path, rows: Iterable[dict]) -> None:
    try:
        import openpyxl
    except ImportError as exc:
        raise SystemExit("openpyxl is required for XLSX export; use .csv output or install requirements.txt") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "scholar_review"
    sheet.append(FIELDS)
    for row in rows:
        sheet.append([row.get(field, "") for field in FIELDS])
    workbook.save(path)


def _join(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return ", ".join(str(item) for item in value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", default="data/scholar_review_queue.jsonl")
    parser.add_argument("--output", default=f"scholar_review_{date.today()}.csv")
    args = parser.parse_args()
    count = export_pending(Path(args.queue), Path(args.output))
    print(f"Review document ready: {args.output}")
    print(f"Items for scholar review: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
