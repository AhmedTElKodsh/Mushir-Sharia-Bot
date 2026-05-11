"""Run the L3 retrieval evaluation harness against tests/fixtures/gold_eval.yaml."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rag.pipeline import RAGPipeline


def load_cases(path: Path) -> List[Dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if isinstance(data, dict):
        return list(data.get("cases") or data.get("questions") or [])
    return list(data)


def evaluate_retrieval(cases: List[Dict[str, Any]], k: int, threshold: float = 0.3, pipeline=None) -> Dict[str, Any]:
    pipeline = pipeline or RAGPipeline()
    results = []
    answerable_hits = 0
    reciprocal_ranks = []
    answerable_cases = 0
    unanswerable_cases = 0
    unanswerable_with_retrieval = 0
    for case in cases:
        query = case.get("query") or case.get("question") or ""
        answerable = case.get("answerable", True)
        expected = set(
            case.get("expected_chunk_ids")
            or case.get("expected_chunks")
            or case.get("required_source_ids")
            or case.get("expected_standards")
            or []
        )
        chunks = pipeline.retrieve(query, k=k, threshold=threshold)
        retrieved = [_retrieval_id(chunk) for chunk in chunks]
        retrieved_rank_candidates = [_retrieval_candidates(chunk) for chunk in chunks]
        retrieved_refs = set().union(*[_retrieval_candidates(chunk) for chunk in chunks]) if chunks else set()
        matched_ids = expected.intersection(retrieved_refs)
        matched = bool(matched_ids) if expected else False
        if answerable:
            answerable_cases += 1
            answerable_hits += int(matched)
            reciprocal_ranks.append(_reciprocal_rank(retrieved_rank_candidates, expected))
        else:
            unanswerable_cases += 1
            unanswerable_with_retrieval += int(bool(retrieved))
        results.append(
            {
                "query": query,
                "answerable": answerable,
                "expected": sorted(expected),
                "retrieved_ids": retrieved,
                "matched": matched,
                "reciprocal_rank": _reciprocal_rank(retrieved_rank_candidates, expected),
            }
        )
    return {
        "case_count": len(cases),
        "answerable_case_count": answerable_cases,
        "unanswerable_case_count": unanswerable_cases,
        "unanswerable_with_retrieval_count": unanswerable_with_retrieval,
        "hit_at_k": answerable_hits / answerable_cases if answerable_cases else 0.0,
        "recall_at_k": answerable_hits / answerable_cases if answerable_cases else 0.0,
        "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0,
        "unanswerable_retrieval_rate": (
            unanswerable_with_retrieval / unanswerable_cases if unanswerable_cases else 0.0
        ),
        "results": results,
    }


def apply_thresholds(
    report: Dict[str, Any],
    min_hit_at_k: float,
    min_recall_at_k: float,
    min_mrr: float,
    min_answerable_cases: int = 1,
    max_unanswerable_retrieval_rate: float = 1.0,
) -> Dict[str, Any]:
    for name, value in {
        "min_hit_at_k": min_hit_at_k,
        "min_recall_at_k": min_recall_at_k,
        "min_mrr": min_mrr,
        "max_unanswerable_retrieval_rate": max_unanswerable_retrieval_rate,
    }.items():
        if value < 0.0 or value > 1.0:
            raise ValueError(f"{name} must be between 0.0 and 1.0")
    if min_answerable_cases < 0:
        raise ValueError("min_answerable_cases must be at least 0")
    thresholds = {
        "hit_at_k": min_hit_at_k,
        "recall_at_k": min_recall_at_k,
        "mrr": min_mrr,
        "answerable_case_count": min_answerable_cases,
    }
    checks = {
        metric: {
            "actual": float(report.get(metric, 0.0)),
            "minimum": minimum,
            "passed": float(report.get(metric, 0.0)) >= minimum,
        }
        for metric, minimum in thresholds.items()
    }
    checks["unanswerable_retrieval_rate"] = {
        "actual": float(report.get("unanswerable_retrieval_rate", 0.0)),
        "maximum": max_unanswerable_retrieval_rate,
        "passed": float(report.get("unanswerable_retrieval_rate", 0.0)) <= max_unanswerable_retrieval_rate,
    }
    report["thresholds"] = checks
    report["passed"] = all(check["passed"] for check in checks.values())
    return report


def _retrieval_id(chunk: Any) -> str:
    if isinstance(chunk, dict):
        metadata = chunk.get("metadata", {})
        return str(
            chunk.get("chunk_id")
            or metadata.get("chunk_id")
            or metadata.get("standard_number")
            or metadata.get("source_file")
            or ""
        )
    citation = getattr(chunk, "citation", None)
    return str(getattr(chunk, "chunk_id", None) or getattr(citation, "standard_id", "") or "")


def _retrieval_candidates(chunk: Any) -> set:
    if isinstance(chunk, dict):
        metadata = chunk.get("metadata", {})
        return {
            str(value)
            for value in [
                chunk.get("chunk_id"),
                metadata.get("chunk_id"),
                metadata.get("document_id"),
                metadata.get("standard_number"),
                metadata.get("source_file"),
                metadata.get("section_number"),
            ]
            if value
        }
    citation = getattr(chunk, "citation", None)
    return {
        str(value)
        for value in [
            getattr(chunk, "chunk_id", None),
            getattr(citation, "standard_id", None),
            getattr(citation, "source_file", None),
            getattr(citation, "section", None),
        ]
        if value
    }


def _reciprocal_rank(retrieved: List[set], expected: set) -> float:
    if not expected:
        return 0.0
    for index, candidates in enumerate(retrieved, 1):
        if candidates.intersection(expected):
            return 1.0 / index
    return 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Mushir RAG retrieval quality.")
    parser.add_argument("--gold", default="tests/fixtures/gold_eval.yaml")
    parser.add_argument("--output", default="_bmad-output/implementation-artifacts/l3-eval-report.json")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=0.3)
    parser.add_argument("--min-hit-at-k", type=float, default=0.0)
    parser.add_argument("--min-recall-at-k", type=float, default=0.0)
    parser.add_argument("--min-mrr", type=float, default=0.0)
    parser.add_argument("--min-answerable-cases", type=int, default=1)
    parser.add_argument("--max-unanswerable-retrieval-rate", type=float, default=1.0)
    args = parser.parse_args()

    cases = load_cases(Path(args.gold))
    report = evaluate_retrieval(cases, args.k, threshold=args.threshold)
    try:
        report = apply_thresholds(
            report,
            args.min_hit_at_k,
            args.min_recall_at_k,
            args.min_mrr,
            min_answerable_cases=args.min_answerable_cases,
            max_unanswerable_retrieval_rate=args.max_unanswerable_retrieval_rate,
        )
    except ValueError as exc:
        parser.error(str(exc))
    try:
        import ragas  # noqa: F401

        report["ragas_available"] = True
        report["ragas_note"] = "Ragas is installed; add answer/context datasets here for faithfulness scoring."
    except ImportError:
        report["ragas_available"] = False
        report["ragas_note"] = "Install ragas to run faithfulness, answer_relevancy, and context_precision."

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
