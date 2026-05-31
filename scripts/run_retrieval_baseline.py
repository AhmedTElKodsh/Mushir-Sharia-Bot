"""Run Mushir's fixture-backed retrieval-only baseline safely.

This command is the stable front door for research-gated RAG/model work. It
does not load the live vector index and does not call an LLM provider.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluate_rag import (  # noqa: E402
    FixtureRetrievalPipeline,
    apply_thresholds,
    evaluate_retrieval,
    load_cases,
)

DEFAULT_GOLD = Path("tests/fixtures/gold_eval_fixture_baseline.yaml")
DEFAULT_OUTPUT = Path("_bmad-output/implementation-artifacts/retrieval-baseline-report.json")
ACCEPTED_SCHOLAR_REVIEW_STATUSES = {
    "accepted",
    "accepted_for_gold_set",
    "accepted_with_correction",
}


def scholar_review_gold_gate(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    tracked_statuses = [
        str(case.get("scholar_review_status") or "").strip().lower()
        for case in cases
        if "scholar_review_status" in case
    ]
    status_counts = Counter(status or "missing" for status in tracked_statuses)
    accepted_count = sum(status_counts.get(status, 0) for status in ACCEPTED_SCHOLAR_REVIEW_STATUSES)
    pending_or_unreviewed = sum(
        count for status, count in status_counts.items() if status not in ACCEPTED_SCHOLAR_REVIEW_STATUSES
    )
    return {
        "tracked_case_count": len(tracked_statuses),
        "accepted_gold_case_count": accepted_count,
        "pending_or_unreviewed_case_count": pending_or_unreviewed,
        "status_counts": dict(sorted(status_counts.items())),
        "accepted_statuses": sorted(ACCEPTED_SCHOLAR_REVIEW_STATUSES),
        "tuning_allowed": bool(tracked_statuses) and pending_or_unreviewed == 0,
    }


def run_retrieval_baseline(
    *,
    gold: Path = DEFAULT_GOLD,
    output: Path = DEFAULT_OUTPUT,
    k: int = 5,
    threshold: float = 0.3,
    min_hit_at_k: float = 0.0,
    min_recall_at_k: float = 0.0,
    min_mrr: float = 0.0,
    min_answerable_cases: int = 1,
    max_unanswerable_retrieval_rate: float = 1.0,
    require_scholar_reviewed_gold: bool = False,
) -> Dict[str, Any]:
    cases = load_cases(gold)
    scholar_gate = scholar_review_gold_gate(cases)
    report = evaluate_retrieval(
        cases,
        k=k,
        threshold=threshold,
        pipeline=FixtureRetrievalPipeline(cases),
    )
    report = apply_thresholds(
        report,
        min_hit_at_k,
        min_recall_at_k,
        min_mrr,
        min_answerable_cases=min_answerable_cases,
        max_unanswerable_retrieval_rate=max_unanswerable_retrieval_rate,
    )
    report.update(
        {
            "gold_file": gold.as_posix(),
            "live_vector_index_used": False,
            "live_llm_used": False,
            "baseline_command": "scripts/run_retrieval_baseline.py",
            "scholar_review_gold_gate": scholar_gate,
            "requires_scholar_reviewed_gold": require_scholar_reviewed_gold,
        }
    )
    if require_scholar_reviewed_gold and not scholar_gate["tuning_allowed"]:
        report["passed"] = False
        report.setdefault("failure_reasons", []).append(
            "scholar-reviewed accepted gold cases are required before tuning or learning"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the fixture-backed Mushir retrieval baseline.")
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=0.3)
    parser.add_argument("--min-hit-at-k", type=float, default=0.0)
    parser.add_argument("--min-recall-at-k", type=float, default=0.0)
    parser.add_argument("--min-mrr", type=float, default=0.0)
    parser.add_argument("--min-answerable-cases", type=int, default=1)
    parser.add_argument("--max-unanswerable-retrieval-rate", type=float, default=1.0)
    parser.add_argument(
        "--require-scholar-reviewed-gold",
        action="store_true",
        help="Fail when hard-case rows are still pending scholar review; use for tuning or learning runs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_retrieval_baseline(
        gold=args.gold,
        output=args.output,
        k=args.k,
        threshold=args.threshold,
        min_hit_at_k=args.min_hit_at_k,
        min_recall_at_k=args.min_recall_at_k,
        min_mrr=args.min_mrr,
        min_answerable_cases=args.min_answerable_cases,
        max_unanswerable_retrieval_rate=args.max_unanswerable_retrieval_rate,
        require_scholar_reviewed_gold=args.require_scholar_reviewed_gold,
    )
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
