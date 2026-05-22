"""Evaluate optional ingestion candidates without wiring them into runtime."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any, Dict


def evaluate_ingestion_candidates() -> Dict[str, Any]:
    results = {
        "mode": "ingestion_candidate_probe",
        "runtime_ingestion_modified": False,
        "candidates": {
            "docling": _docling_probe(),
            "pdfplumber": _pdfplumber_probe(),
            "pymupdf": _license_block("PyMuPDF/PyMuPDF4LLM"),
            "marker": _license_block("Marker"),
        },
    }
    results["summary"] = {
        "docling_ready_for_controlled_aaoifi_sample": results["candidates"]["docling"]["status"] == "probe_passed",
        "pdfplumber_ready_for_registry_pdf_sample": results["candidates"]["pdfplumber"]["status"] == "probe_passed",
        "license_blocked_candidates": [
            name
            for name, result in results["candidates"].items()
            if result["status"] == "blocked_pending_license_review"
        ],
    }
    return results


def _docling_probe() -> Dict[str, Any]:
    if importlib.util.find_spec("docling") is None:
        return {
            "tool": "Docling",
            "status": "missing_optional_dependency",
            "sample": "controlled_aaoifi_source_sample",
            "evidence": "Docling is not installed in the active environment.",
            "adopt_next": False,
        }
    return {
        "tool": "Docling",
        "status": "probe_passed",
        "sample": "controlled_aaoifi_source_sample",
        "evidence": "Docling import is available; run source-sample conversion before production adoption.",
        "adopt_next": False,
    }


def _pdfplumber_probe() -> Dict[str, Any]:
    if importlib.util.find_spec("pdfplumber") is None:
        return {
            "tool": "pdfplumber",
            "status": "missing_optional_dependency",
            "sample": "cbe_fra_registry_pdf_sample",
            "evidence": "pdfplumber is not installed in the active environment.",
            "adopt_next": False,
        }
    return {
        "tool": "pdfplumber",
        "status": "probe_passed",
        "sample": "cbe_fra_registry_pdf_sample",
        "evidence": "pdfplumber import is available; run registry PDF/table extraction before production adoption.",
        "adopt_next": False,
    }


def _license_block(tool: str) -> Dict[str, Any]:
    return {
        "tool": tool,
        "status": "blocked_pending_license_review",
        "evidence": "Candidate remains blocked until license review is recorded.",
        "adopt_next": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate optional ingestion candidates.")
    parser.add_argument(
        "--output",
        default="_bmad-output/implementation-artifacts/ingestion-candidate-probe.json",
    )
    args = parser.parse_args()
    report = evaluate_ingestion_candidates()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
