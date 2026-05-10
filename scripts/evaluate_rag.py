"""Run the L3 retrieval evaluation harness against tests/fixtures/gold_eval.yaml."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import yaml

from src.rag.pipeline import RAGPipeline


def load_cases(path: Path) -> List[Dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if isinstance(data, dict):
        return list(data.get("cases") or data.get("questions") or [])
    return list(data)


def evaluate_retrieval(cases: List[Dict[str, Any]], k: int, pipeline=None) -> Dict[str, Any]:
    pipeline = pipeline or RAGPipeline()
    results = []
    hits = 0
    reciprocal_ranks = []
    answerable_cases = 0
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
        chunks = pipeline.retrieve(query, k=k, threshold=0.0)
        retrieved = [_retrieval_id(chunk) for chunk in chunks]
        retrieved_rank_candidates = [_retrieval_candidates(chunk) for chunk in chunks]
        retrieved_refs = set().union(*[_retrieval_candidates(chunk) for chunk in chunks]) if chunks else set()
        matched_ids = expected.intersection(retrieved_refs)
        matched = bool(matched_ids) if expected else bool(retrieved)
        hits += int(matched)
        if answerable:
            answerable_cases += 1
            reciprocal_ranks.append(_reciprocal_rank(retrieved_rank_candidates, expected))
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
        "hit_at_k": hits / len(cases) if cases else 0.0,
        "recall_at_k": hits / answerable_cases if answerable_cases else 0.0,
        "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0,
        "results": results,
    }


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
    args = parser.parse_args()

    cases = load_cases(Path(args.gold))
    report = evaluate_retrieval(cases, args.k)
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
