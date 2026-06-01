from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


DEFAULT_ARTIFACT_ROOT = Path("data/runtime/artifacts/l6_scrape")


@dataclass
class FinancialOperation:
    operation_id: str
    institution_name: str
    operation_title: str
    mapped_aaoifi_contract: Optional[str] = None
    compliance_status: str = "UNVERIFIED"
    institution_id: str = ""
    sector: str = ""
    regulator: str = ""
    source_url: str = ""
    evidence_snippet: str = ""
    confidence: float = 0.0
    human_scholar_review: str = ""


class InstitutionScraper:
    """
    Reads the governed L6 evidence-corpus exports produced by
    scripts/run_l6_institution_pilot.py.

    The live crawling step writes artifact evidence under data/runtime/artifacts/l6_scrape.
    This adapter intentionally does not invent operations when no reviewed or
    machine-extracted corpus exists.
    """

    def __init__(self, artifact_root: str | Path = DEFAULT_ARTIFACT_ROOT):
        self.artifact_root = Path(artifact_root)

    def scrape_operations(self) -> List[FinancialOperation]:
        operations = list(self._operations_from_chunk_spans())
        if operations:
            return operations
        return list(self._operations_from_assessment_rows())

    def _operations_from_chunk_spans(self) -> Iterable[FinancialOperation]:
        for path in _latest_files(self.artifact_root, "chunk_ready_spans.jsonl"):
            seen: set[str] = set()
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                operation_id = str(row.get("operation_id", "")).strip()
                if not operation_id or operation_id in seen:
                    continue
                seen.add(operation_id)
                yield FinancialOperation(
                    operation_id=operation_id,
                    institution_id=str(row.get("institution_id", "")),
                    institution_name=str(row.get("institution_name", "")),
                    operation_title=str(row.get("operation_name", "")),
                    mapped_aaoifi_contract="|".join(_standards_list(row.get("candidate_standards"))) or None,
                    compliance_status=_status_from_mapping(str(row.get("mapping_status", ""))),
                    sector=str(row.get("sector", "")),
                    regulator=str(row.get("regulator", "")),
                    source_url=str(row.get("artifact_url", "")),
                    evidence_snippet=str(row.get("evidence_snippet", "")),
                    confidence=_float(row.get("confidence")),
                    human_scholar_review="",
                )
            return

    def _operations_from_assessment_rows(self) -> Iterable[FinancialOperation]:
        for path in _latest_files(self.artifact_root, "engine_assessment_rows.csv"):
            with path.open(newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    operation_id = str(row.get("operation_id", "")).strip()
                    if not operation_id:
                        continue
                    human_review = str(row.get("human_scholar_review", "")).strip()
                    yield FinancialOperation(
                        operation_id=operation_id,
                        institution_id=str(row.get("institution_id", "")),
                        institution_name=str(row.get("financial_institution_name", "")),
                        operation_title=str(row.get("contract_operation_name", "")),
                        mapped_aaoifi_contract=str(
                            row.get("mushir_engine_aaoifi_references", "")
                        )
                        or None,
                        compliance_status=(
                            "SCHOLAR_REVIEWED" if human_review else "PENDING_SCHOLAR_REVIEW"
                        ),
                        source_url=str(row.get("source_url", "")),
                        evidence_snippet=str(row.get("evidence_snippet", "")),
                        human_scholar_review=human_review,
                    )
            return


class ComplianceCrossReferencer:
    """
    Marks extracted operations according to the L6 evidence policy.

    Machine mappings identify AAOIFI candidate references only; they are not a
    final Sharia ruling and stay pending until a scholar review row is imported.
    """

    def assess_compliance(self, operation: FinancialOperation) -> FinancialOperation:
        if operation.human_scholar_review:
            operation.compliance_status = "SCHOLAR_REVIEWED"
        elif operation.mapped_aaoifi_contract:
            operation.compliance_status = "PENDING_SCHOLAR_REVIEW"
        else:
            operation.compliance_status = "UNMAPPED_REVIEW_REQUIRED"
        return operation


def _latest_files(root: Path, filename: str) -> List[Path]:
    if not root.exists():
        return []
    return sorted(
        root.rglob(filename),
        key=lambda path: (path.stat().st_mtime, str(path)),
        reverse=True,
    )


def _status_from_mapping(status: str) -> str:
    if status == "machine_proposed":
        return "PENDING_SCHOLAR_REVIEW"
    if status == "scholar_accepted":
        return "SCHOLAR_REVIEWED"
    return "UNVERIFIED"


def _float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _standards_list(value: object) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, Iterable):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)] if str(value).strip() else []
