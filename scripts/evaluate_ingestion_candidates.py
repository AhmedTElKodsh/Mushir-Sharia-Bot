"""Evaluate optional ingestion candidates without wiring them into runtime."""
from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
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
            "status": "install_blocked",
            "sample": "controlled_aaoifi_source_sample",
            "evidence": (
                "Docling is not importable in the active Python 3.14 venv. "
                "Latest install timed out; docling==1.20.0 failed dependency resolution "
                "because deepsearch-glm<0.23.0,>=0.22.0 was unavailable."
            ),
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
    import pdfplumber

    sample_text = "Arab Investment Bank | 1974-08-08 | CBE Registry"
    with tempfile.TemporaryDirectory() as tmp_dir:
        sample_path = Path(tmp_dir) / "cbe_registry_sample.pdf"
        sample_path.write_bytes(_minimal_text_pdf(sample_text))
        with pdfplumber.open(sample_path) as pdf:
            extracted = "\n".join(page.extract_text() or "" for page in pdf.pages)
    matched = "Arab Investment Bank" in extracted and "1974-08-08" in extracted
    return {
        "tool": "pdfplumber",
        "status": "probe_passed" if matched else "probe_failed",
        "sample": "cbe_fra_registry_pdf_sample",
        "evidence": (
            "pdfplumber extracted controlled registry sample fields."
            if matched
            else "pdfplumber import worked, but controlled registry sample fields were not extracted."
        ),
        "extracted_text_preview": extracted[:120],
        "adopt_next": False,
    }


def _minimal_text_pdf(text: str) -> bytes:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("utf-8")
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n",
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        b"5 0 obj\n<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream\nendobj\n",
    ]
    payload = b"%PDF-1.4\n"
    offsets = [0]
    for obj in objects:
        offsets.append(len(payload))
        payload += obj
    xref_offset = len(payload)
    payload += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii")
    for offset in offsets[1:]:
        payload += f"{offset:010d} 00000 n \n".encode("ascii")
    payload += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("ascii")
    return payload


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
