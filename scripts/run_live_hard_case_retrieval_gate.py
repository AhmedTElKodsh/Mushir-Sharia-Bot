"""Run hard-case answer-path checks against the live vector index.

This gate loads the configured vector index and executes ApplicationService.answer()
for hard Shari'ah cases. The service path applies the same clarification,
source-family, candidate-standard, citation, and deterministic review gates used
by users. These cases are selected so the answer path fails closed before any
LLM provider is needed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.chatbot.application_service import ApplicationService  # noqa: E402
from src.chatbot.commercial_assessment import ScenarioExtractor, StandardsRouter  # noqa: E402
from src.rag.pipeline import RAGPipeline  # noqa: E402


DEFAULT_HARD_CASES = Path("tests/fixtures/live_hard_case_retrieval_gate.yaml")
DEFAULT_OUTPUT = Path("_bmad-output/implementation-artifacts/live-hard-case-retrieval-gate.json")


def load_hard_cases(path: Path) -> List[Dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(payload, list):
        raise ValueError("hard-case gate file must contain a list of cases")
    return [dict(item) for item in payload]


def run_live_hard_case_retrieval_gate(
    *,
    cases_path: Path = DEFAULT_HARD_CASES,
    output: Path = DEFAULT_OUTPUT,
    k: int = 8,
    threshold: float = 0.0,
    pipeline_factory: Callable[[], Any] = RAGPipeline,
) -> Dict[str, Any]:
    cases = load_hard_cases(cases_path)
    pipeline = pipeline_factory()
    extractor = ScenarioExtractor()
    router = StandardsRouter()
    service = ApplicationService(retriever=pipeline)
    service.k = k
    service.threshold = threshold
    results = []

    for case in cases:
        query = str(case.get("query") or "").strip()
        if not query:
            raise ValueError("hard-case query is required")
        expected_behavior = str(case.get("expected_behavior") or "retrieval").strip()
        scenario = extractor.extract(query)
        route = router.route(scenario, query)
        answer = service.answer(query)
        route_payload = answer.metadata.get("standards_route") or {}
        candidate_trace = answer.metadata.get("candidate_standard_filter") or {}
        expected_standards = _normalise_list(
            case.get("expected_candidate_standards")
            or route_payload.get("candidate_standards")
            or route.candidate_standards
        )
        retrieved_standards = sorted(candidate_trace.get("retrieved") or [])
        matched_standards = sorted(candidate_trace.get("matched") or [])
        expected_family = str(case.get("expected_source_family") or "").lower()

        failures: List[str] = []
        if expected_behavior == "retrieval":
            if not matched_standards:
                failures.append("no candidate-standard-matched chunks retrieved")
            missing = sorted(set(expected_standards) - set(matched_standards))
            if missing:
                failures.append(f"missing expected standards: {', '.join(missing)}")
            if expected_family:
                families = sorted(answer.metadata.get("source_families") or [])
                if expected_family not in families:
                    failures.append(f"missing expected source family: {expected_family}")
        elif expected_behavior == "clarification":
            if matched_standards:
                failures.append("clarification case unexpectedly retrieved candidate-standard evidence")
            answer_status = str(answer.status.value).lower()
            if answer_status != "clarification_needed":
                failures.append(f"expected clarification, got {answer_status}")
        else:
            raise ValueError(f"unsupported expected_behavior: {expected_behavior}")

        results.append(
            {
                "case_id": case.get("case_id"),
                "query": query,
                "passed": not failures,
                "failures": failures,
                "answer_status": str(answer.status.value).lower(),
                "route_id": route_payload.get("route_id"),
                "candidate_standards": route_payload.get("candidate_standards") or [],
                "expected_candidate_standards": expected_standards,
                "retrieved_standards": retrieved_standards,
                "matched_standards": matched_standards,
                "filters": ApplicationService._retrieval_filters(route),
                "candidate_standard_filter": candidate_trace,
                "application_metadata": answer.metadata,
                "retrieved_chunk_ids": answer.metadata.get("retrieved_chunk_ids") or [],
            }
        )

    report = {
        "passed": all(item["passed"] for item in results),
        "case_count": len(results),
        "live_vector_index_used": True,
        "live_llm_used": False,
        "application_answer_used": True,
        "gate_command": "scripts/run_live_hard_case_retrieval_gate.py",
        "cases_file": cases_path.as_posix(),
        "results": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def _normalise_list(values: Any) -> List[str]:
    if not values:
        return []
    if isinstance(values, str):
        values = [values]
    return sorted({ApplicationService._normalize_standard_id(str(value)) for value in values if str(value).strip()})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run live hard-case answer-path gate against the configured vector index.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_HARD_CASES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--k", type=int, default=8)
    parser.add_argument("--threshold", type=float, default=0.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_live_hard_case_retrieval_gate(
        cases_path=args.cases,
        output=args.output,
        k=args.k,
        threshold=args.threshold,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
