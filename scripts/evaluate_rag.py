"""Run the L3 retrieval evaluation harness against tests/fixtures/gold_eval.yaml."""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rag.pipeline import RAGPipeline


class FixtureRetrievalPipeline:
    """Fixture-only retriever for baseline evals that must not touch live indexes."""

    baseline_mode = "fixture_backed_retrieval_only"

    def __init__(self, cases: List[Dict[str, Any]]):
        self._cases = {
            str(case.get("query") or case.get("question") or ""): case
            for case in cases
        }

    def classify(self, query: str) -> Dict[str, str]:
        case = self._cases.get(query, {})
        return {"behavior": str(case.get("fixture_behavior") or case.get("expected_behavior") or "")}

    def retrieve(self, query: str, k: int = 5, threshold: float = 0.0) -> List[Dict[str, Any]]:
        case = self._cases.get(query, {})
        return list(case.get("fixture_retrieved_chunks") or [])[:k]


class BM25FixtureRetriever:
    """Small BM25 retriever for fixture spikes before adopting a library."""

    baseline_mode = "bm25_fixture"

    def __init__(self, chunks: List[Dict[str, Any]], *, k1: float = 1.5, b: float = 0.75):
        self._chunks = chunks
        self._k1 = k1
        self._b = b
        self._documents = [_tokenize(_chunk_text(chunk)) for chunk in chunks]
        self._term_frequencies = [Counter(document) for document in self._documents]
        self._document_frequency = Counter(
            term for document in self._documents for term in set(document)
        )
        self._average_length = (
            sum(len(document) for document in self._documents) / len(self._documents)
            if self._documents
            else 0.0
        )

    def retrieve(self, query: str, k: int = 5, threshold: float = 0.0) -> List[Dict[str, Any]]:
        query_terms = _tokenize(query)
        scored = []
        for index, chunk in enumerate(self._chunks):
            score = self._score(query_terms, index)
            if score <= threshold:
                continue
            result = dict(chunk)
            metadata = dict(result.get("metadata") or {})
            metadata["retrieval_method"] = "bm25_fixture"
            result["metadata"] = metadata
            result["similarity"] = score
            scored.append(result)
        scored.sort(key=lambda item: float(item.get("similarity", 0.0)), reverse=True)
        return scored[:k]

    def _score(self, query_terms: List[str], index: int) -> float:
        if not query_terms or not self._documents:
            return 0.0
        score = 0.0
        document_length = len(self._documents[index])
        term_frequency = self._term_frequencies[index]
        for term in query_terms:
            frequency = term_frequency.get(term, 0)
            if not frequency:
                continue
            idf = math.log(1 + (len(self._documents) - self._document_frequency[term] + 0.5) / (self._document_frequency[term] + 0.5))
            denominator = frequency + self._k1 * (
                1 - self._b + self._b * document_length / max(self._average_length, 1.0)
            )
            score += idf * frequency * (self._k1 + 1) / denominator
        return score


class HybridFixtureRetrievalPipeline:
    """Combine current dense retrieval with fixture BM25 for measured spikes."""

    baseline_mode = "hybrid_fixture_bm25_plus_dense"

    def __init__(self, dense_pipeline: Any, cases: List[Dict[str, Any]]):
        self._dense_pipeline = dense_pipeline
        self._bm25 = BM25FixtureRetriever(_fixture_corpus_chunks(cases))

    def retrieve(self, query: str, k: int = 5, threshold: float = 0.0) -> List[Dict[str, Any]]:
        dense_results = list(self._dense_pipeline.retrieve(query, k=k, threshold=threshold))
        lexical_results = self._bm25.retrieve(query, k=k, threshold=0.0)
        return _fuse_ranked_results(dense_results, lexical_results, k)


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
    source_family_cases = 0
    source_family_hits = 0
    citation_support_cases = 0
    citation_support_hits = 0
    unsupported_answer_cases = 0
    unsupported_answer_hits = 0
    refusal_cases = 0
    refusal_hits = 0
    clarification_predictions = 0
    clarification_true_positives = 0
    arabic_mixed_cases = 0
    arabic_mixed_passes = 0
    latencies_ms = []
    for case in cases:
        query = case.get("query") or case.get("question") or ""
        answerable = case.get("answerable", True)
        expected_behavior = str(case.get("expected_behavior") or ("answer" if answerable else "refusal"))
        expected_source_family = str(case.get("expected_source_family") or "")
        expected = set(
            case.get("expected_chunk_ids")
            or case.get("expected_chunks")
            or case.get("required_source_ids")
            or case.get("expected_standards")
            or []
        )
        start = time.perf_counter()
        decision = _pipeline_decision(pipeline, query)
        chunks = pipeline.retrieve(query, k=k, threshold=threshold)
        latencies_ms.append((time.perf_counter() - start) * 1000.0)
        predicted_behavior = decision.get("behavior") or ("answer" if chunks else "refusal")
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
        if expected_source_family:
            source_family_cases += 1
            source_family_hits += int(_source_family_hit(chunks, expected_source_family))
        if answerable:
            citation_support_cases += 1
            citation_supported = matched and _citation_supported(chunks, matched_ids or expected)
            citation_support_hits += int(citation_supported)
            unsupported_answer_cases += 1
            unsupported_answer_hits += int(predicted_behavior == "answer" and not citation_supported)
        else:
            citation_supported = False
        if expected_behavior == "refusal":
            refusal_cases += 1
            refusal_hits += int(predicted_behavior == "refusal" and not chunks)
        if predicted_behavior == "clarification":
            clarification_predictions += 1
            clarification_true_positives += int(expected_behavior == "clarification")
        case_passed = _case_passed(
            answerable=answerable,
            matched=matched,
            chunks=chunks,
            expected_behavior=expected_behavior,
            predicted_behavior=predicted_behavior,
            citation_supported=citation_supported,
        )
        if str(case.get("language") or "").lower() in {"ar", "arabic", "mixed", "bilingual"}:
            arabic_mixed_cases += 1
            arabic_mixed_passes += int(case_passed)
        results.append(
            {
                "query": query,
                "answerable": answerable,
                "expected": sorted(expected),
                "retrieved_ids": retrieved,
                "matched": matched,
                "expected_behavior": expected_behavior,
                "predicted_behavior": predicted_behavior,
                "case_passed": case_passed,
                "reciprocal_rank": _reciprocal_rank(retrieved_rank_candidates, expected),
            }
        )
    return {
        "baseline_mode": getattr(pipeline, "baseline_mode", "retrieval_only"),
        "case_count": len(cases),
        "answerable_case_count": answerable_cases,
        "unanswerable_case_count": unanswerable_cases,
        "unanswerable_with_retrieval_count": unanswerable_with_retrieval,
        "hit_at_k": answerable_hits / answerable_cases if answerable_cases else 0.0,
        "recall_at_k": answerable_hits / answerable_cases if answerable_cases else 0.0,
        "expected_standard_hit_rate": answerable_hits / answerable_cases if answerable_cases else 0.0,
        "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0,
        "unanswerable_retrieval_rate": (
            unanswerable_with_retrieval / unanswerable_cases if unanswerable_cases else 0.0
        ),
        "unsupported_answer_rate": (
            unsupported_answer_hits / unsupported_answer_cases if unsupported_answer_cases else 0.0
        ),
        "source_family_accuracy": source_family_hits / source_family_cases if source_family_cases else 0.0,
        "citation_support_rate": (
            citation_support_hits / citation_support_cases if citation_support_cases else 0.0
        ),
        "refusal_correctness": refusal_hits / refusal_cases if refusal_cases else 0.0,
        "clarification_precision": (
            clarification_true_positives / clarification_predictions if clarification_predictions else 0.0
        ),
        "arabic_mixed_language_pass_rate": (
            arabic_mixed_passes / arabic_mixed_cases if arabic_mixed_cases else 0.0
        ),
        "latency": {
            "average_ms": sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0,
            "max_ms": max(latencies_ms) if latencies_ms else 0.0,
        },
        "results": results,
    }


def compare_hybrid_fixture_spike(
    cases: List[Dict[str, Any]],
    dense_pipeline: Any,
    *,
    k: int,
    threshold: float = 0.3,
) -> Dict[str, Any]:
    dense_report = evaluate_retrieval(cases, k, threshold=threshold, pipeline=dense_pipeline)
    hybrid_report = evaluate_retrieval(
        cases,
        k,
        threshold=threshold,
        pipeline=HybridFixtureRetrievalPipeline(dense_pipeline, cases),
    )
    dense_score = float(dense_report.get("expected_standard_hit_rate", 0.0))
    hybrid_score = float(hybrid_report.get("expected_standard_hit_rate", 0.0))
    return {
        "mode": "bm25_plus_dense_fixture_spike",
        "dense": dense_report,
        "hybrid": hybrid_report,
        "delta_expected_standard_hit_rate": hybrid_score - dense_score,
        "adopt_next": hybrid_score > dense_score,
        "qdrant_hybrid_comparison_allowed": hybrid_score > dense_score,
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


def _chunk_text(chunk: Mapping[str, Any]) -> str:
    metadata = chunk.get("metadata", {}) or {}
    return " ".join(
        str(value)
        for value in [
            chunk.get("content", ""),
            chunk.get("text", ""),
            metadata.get("standard_number", ""),
            metadata.get("source_family", ""),
            metadata.get("section_number", ""),
        ]
        if value
    )


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[\w]+", text.lower(), flags=re.UNICODE)


def _fixture_corpus_chunks(cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    seen = set()
    for case in cases:
        for chunk in list(case.get("fixture_corpus_chunks") or case.get("fixture_retrieved_chunks") or []):
            chunk_id = _retrieval_id(chunk)
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            chunks.append(chunk)
    return chunks


def _fuse_ranked_results(
    dense_results: List[Any],
    lexical_results: List[Dict[str, Any]],
    k: int,
) -> List[Any]:
    by_id: Dict[str, Any] = {}
    scores: Dict[str, float] = {}
    for weight, results in [(0.5, dense_results), (1.0, lexical_results)]:
        for rank, result in enumerate(results, start=1):
            result_id = _retrieval_id(result)
            if not result_id:
                continue
            by_id.setdefault(result_id, result)
            scores[result_id] = scores.get(result_id, 0.0) + weight / (60 + rank)
    ranked_ids = sorted(scores, key=lambda result_id: scores[result_id], reverse=True)
    return [by_id[result_id] for result_id in ranked_ids[:k]]


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


def _pipeline_decision(pipeline: Any, query: str) -> Dict[str, str]:
    classifier = getattr(pipeline, "classify", None) or getattr(pipeline, "decide", None)
    if not classifier:
        return {}
    decision = classifier(query)
    return decision if isinstance(decision, dict) else {"behavior": str(decision)}


def _source_family_hit(chunks: List[Any], expected_source_family: str) -> bool:
    normalized_expected = expected_source_family.strip().lower()
    return any(
        normalized_expected
        in {
            str(value).strip().lower()
            for value in _metadata_values(
                chunk,
                ["source_family", "standard_family", "source_type", "document_family"],
            )
            if value
        }
        for chunk in chunks
    )


def _citation_supported(chunks: List[Any], expected: set) -> bool:
    for chunk in chunks:
        if not _retrieval_candidates(chunk).intersection(expected):
            continue
        values = list(_metadata_values(chunk, ["citation_supported", "citation_support", "has_citation"]))
        if not values:
            return True
        return str(values[0]).strip().lower() in {"true", "1", "yes", "supported"}
    return False


def _metadata_values(chunk: Any, keys: List[str]) -> List[Any]:
    if isinstance(chunk, dict):
        metadata = chunk.get("metadata", {}) or {}
        return [metadata.get(key) for key in keys]
    metadata = getattr(chunk, "metadata", {}) or {}
    values = [metadata.get(key) for key in keys] if isinstance(metadata, dict) else []
    citation = getattr(chunk, "citation", None)
    values.extend(getattr(citation, key, None) for key in keys if citation is not None)
    return values


def _case_passed(
    *,
    answerable: bool,
    matched: bool,
    chunks: List[Any],
    expected_behavior: str,
    predicted_behavior: str,
    citation_supported: bool,
) -> bool:
    if expected_behavior == "clarification":
        return predicted_behavior == "clarification"
    if expected_behavior == "refusal":
        return predicted_behavior == "refusal" and not chunks
    return bool(answerable and matched and citation_supported)


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
    parser.add_argument(
        "--fixture-backed",
        action="store_true",
        help="Use fixture_retrieved_chunks from the gold file instead of loading the live vector index.",
    )
    args = parser.parse_args()

    cases = load_cases(Path(args.gold))
    pipeline = FixtureRetrievalPipeline(cases) if args.fixture_backed else None
    report = evaluate_retrieval(cases, args.k, threshold=args.threshold, pipeline=pipeline)
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
    report["external_eval_tools_used"] = []
    report["external_eval_note"] = (
        "Custom Mushir metrics are the baseline. Ragas, DeepEval, RAGChecker, "
        "and observability platforms remain candidates until they improve this report."
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
