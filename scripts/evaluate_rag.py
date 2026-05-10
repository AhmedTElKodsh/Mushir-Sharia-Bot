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


def evaluate_retrieval(cases: List[Dict[str, Any]], k: int) -> Dict[str, Any]:
    pipeline = RAGPipeline()
    results = []
    hits = 0
    for case in cases:
        query = case.get("query") or case.get("question") or ""
        expected = set(case.get("expected_chunk_ids") or case.get("expected_chunks") or [])
        chunks = pipeline.retrieve(query, k=k, threshold=0.0)
        retrieved = [getattr(chunk, "chunk_id", None) if not isinstance(chunk, dict) else chunk.get("chunk_id") for chunk in chunks]
        matched = bool(expected.intersection(retrieved)) if expected else bool(retrieved)
        hits += int(matched)
        results.append({"query": query, "retrieved_chunk_ids": retrieved, "matched": matched})
    return {
        "case_count": len(cases),
        "precision_at_k_proxy": hits / len(cases) if cases else 0.0,
        "results": results,
    }


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
