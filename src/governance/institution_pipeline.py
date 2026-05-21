"""Executable helpers for the Egypt financial institutions evidence corpus."""
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence

from src.governance.institution_registry import (
    AccessControlDecision,
    ComplianceRiskLabel,
    CorpusPilotPlan,
    DiscoveryEvidenceType,
    DiscoveryStopReason,
    ExtractionStatus,
    InstitutionDiscoveryStatus,
    InstitutionRefreshStatus,
    InstitutionRegulator,
    InstitutionRegistry,
    InstitutionRegistryRecord,
    InstitutionSector,
    MachineAaoifiMappingCandidate,
    OfficialSiteDiscoveryAttempt,
    OfficialSiteDiscoveryResult,
    OperationCatalogRecord,
    OperationEvidenceField,
    OperationEvidenceSpan,
    PublicArtifactAuthorityRank,
    PublicArtifactRecord,
    PublicArtifactType,
    ReviewCandidateStatus,
    ScholarReviewRecord,
)


REGISTRY_WORKBOOK_DEFAULTS: Dict[str, Dict[str, object]] = {
    "01_CBE_Banks": {
        "regulator": InstitutionRegulator.CBE,
        "sector": InstitutionSector.BANK,
        "source": "Central Bank of Egypt banks register",
        "source_url": "https://www.cbe.org.eg/en/banking-supervision",
    },
    "02_Capital_Market": {
        "regulator": InstitutionRegulator.FRA,
        "sector": InstitutionSector.CAPITAL_MARKET,
        "source": "Financial Regulatory Authority capital market registers",
        "source_url": "https://fra.gov.eg/",
    },
    "03_Insurance": {
        "regulator": InstitutionRegulator.FRA,
        "sector": InstitutionSector.INSURANCE,
        "source": "Financial Regulatory Authority insurance registers",
        "source_url": "https://fra.gov.eg/",
    },
    "04_NonBank_Financial": {
        "regulator": InstitutionRegulator.FRA,
        "sector": InstitutionSector.NON_BANK_FINANCE,
        "source": "Financial Regulatory Authority non-bank financial registers",
        "source_url": "https://fra.gov.eg/",
    },
}


@dataclass(frozen=True)
class RegistrySheetConfig:
    """Authoritative defaults for one workbook sheet."""

    sheet_name: str
    regulator: InstitutionRegulator
    sector: InstitutionSector
    registry_source: str
    registry_source_url: str

    @classmethod
    def from_mapping(cls, sheet_name: str, payload: Mapping[str, object]) -> "RegistrySheetConfig":
        return cls(
            sheet_name=sheet_name,
            regulator=InstitutionRegulator(payload["regulator"]),
            sector=InstitutionSector(payload["sector"]),
            registry_source=str(payload["source"]),
            registry_source_url=str(payload["source_url"]),
        )


class WorkbookRegistryLoader:
    """Load baseline institution registry rows from the controlled workbook."""

    def __init__(
        self,
        sheet_configs: Optional[Iterable[RegistrySheetConfig]] = None,
        baseline_input_name: str = "Egypt_Financial_Institutions_COMPLETE.xlsx",
    ) -> None:
        configs = sheet_configs or [
            RegistrySheetConfig.from_mapping(sheet_name, payload)
            for sheet_name, payload in REGISTRY_WORKBOOK_DEFAULTS.items()
        ]
        self._configs = {config.sheet_name: config for config in configs}
        self._baseline_input_name = baseline_input_name

    def load_xlsx(self, workbook_path: str | Path) -> InstitutionRegistry:
        rows = _xlsx_rows_by_sheet(Path(workbook_path))
        records: List[InstitutionRegistryRecord] = []
        for sheet_name, config in self._configs.items():
            records.extend(self._records_from_sheet(sheet_name, rows.get(sheet_name, []), config))
        return InstitutionRegistry(records)

    def load_csv(self, csv_path: str | Path, sheet_name: str) -> InstitutionRegistry:
        config = self._configs[sheet_name]
        with Path(csv_path).open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            rows = list(reader)
        return InstitutionRegistry(self._records_from_sheet(sheet_name, rows, config))

    def load_mappings(
        self,
        rows: Iterable[Mapping[str, object]],
        sheet_name: str,
    ) -> InstitutionRegistry:
        config = self._configs[sheet_name]
        records = []
        for row_number, row in enumerate(rows, start=2):
            record = self._record_from_mapping(row, sheet_name, config, row_number)
            if record:
                records.append(record)
        return InstitutionRegistry(records)

    def _records_from_sheet(
        self,
        sheet_name: str,
        rows: Sequence[Sequence[str]],
        config: RegistrySheetConfig,
    ) -> List[InstitutionRegistryRecord]:
        if not rows:
            return []
        header_index = _first_non_empty_row_index(rows)
        if header_index is None:
            return []
        headers = [_normalize_header(cell) for cell in rows[header_index]]
        records: List[InstitutionRegistryRecord] = []
        for row_number, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
            if not any(str(cell).strip() for cell in row):
                continue
            payload = {
                headers[index] or f"column_{index + 1}": row[index] if index < len(row) else ""
                for index in range(max(len(headers), len(row)))
            }
            record = self._record_from_mapping(payload, sheet_name, config, row_number)
            if record:
                records.append(record)
        return records

    def _record_from_mapping(
        self,
        row: Mapping[str, object],
        sheet_name: str,
        config: RegistrySheetConfig,
        row_number: int,
    ) -> Optional[InstitutionRegistryRecord]:
        name_en = _pick(
            row,
            "name_en",
            "name_english",
            "english_name",
            "institution_name",
            "company_name",
            "bank_name",
            "name",
        )
        if not name_en or not _has_name_letter(name_en):
            return None
        name_ar = _pick(row, "name_ar", "arabic_name")
        website = _pick(row, "official_website", "website", "url")
        source = _pick(row, "registry_source", "source") or config.registry_source
        source_url = _pick(row, "registry_source_url", "source_url") or config.registry_source_url
        sector = _sector_from_text(_pick(row, "sector", "category", "type"), config.sector)
        regulator = _regulator_from_text(_pick(row, "regulator"), config.regulator)
        refresh_status = (
            InstitutionRefreshStatus.REGULATOR_REVALIDATED
            if source_url != config.registry_source_url
            else InstitutionRefreshStatus.BASELINE_UNVERIFIED
        )
        notes = f"{sheet_name} row {row_number}"
        if website:
            notes = f"{notes}; workbook supplied candidate website"
        institution_id = _stable_id_for_row(name_en, regulator, sector, sheet_name, row_number)
        return InstitutionRegistryRecord(
            institution_id=institution_id,
            name_en=name_en,
            name_ar=name_ar or None,
            regulator=regulator,
            sector=sector,
            registry_source=source,
            registry_source_url=source_url,
            official_website=website or None,
            official_website_confidence=0.0,
            refresh_status=refresh_status,
            notes=notes,
            baseline_inputs=[self._baseline_input_name],
        )


@dataclass(frozen=True)
class DiscoveryBudget:
    """Bounded discovery budget; callers must not exceed these limits."""

    max_regulator_links: int = 3
    max_search_results: int = 5
    max_manual_candidates: int = 3
    max_total_attempts: int = 8

    def __post_init__(self) -> None:
        values = [
            self.max_regulator_links,
            self.max_search_results,
            self.max_manual_candidates,
            self.max_total_attempts,
        ]
        if min(values) < 1:
            raise ValueError("discovery budget values must be positive")


@dataclass(frozen=True)
class DiscoveryEvidenceCandidate:
    """Candidate evidence supplied by a deterministic search/regulator adapter."""

    url: str
    evidence_type: DiscoveryEvidenceType
    confidence: float
    status: InstitutionDiscoveryStatus
    notes: str = ""


class OfficialSiteDiscoveryRunner:
    """Turn bounded candidate evidence into a final official-site discovery result."""

    def __init__(self, budget: DiscoveryBudget | None = None) -> None:
        self._budget = budget or DiscoveryBudget()

    def run(
        self,
        record: InstitutionRegistryRecord,
        candidates: Iterable[DiscoveryEvidenceCandidate],
        *,
        checked_at: date,
    ) -> OfficialSiteDiscoveryResult:
        attempts: List[OfficialSiteDiscoveryAttempt] = []
        for candidate in self._bounded_candidates(candidates):
            attempt = OfficialSiteDiscoveryAttempt(
                attempt_number=len(attempts) + 1,
                evidence_type=candidate.evidence_type,
                evidence_url=candidate.url,
                confidence=candidate.confidence,
                status=candidate.status,
                checked_at=checked_at,
                stop_reason=(
                    DiscoveryStopReason.CONFIRMED_OFFICIAL_SITE
                    if candidate.status == InstitutionDiscoveryStatus.OFFICIAL_SITE_CONFIRMED
                    else None
                ),
                notes=candidate.notes,
            )
            attempts.append(attempt)
            if candidate.status == InstitutionDiscoveryStatus.OFFICIAL_SITE_CONFIRMED:
                return OfficialSiteDiscoveryResult.from_attempts(record.institution_id, attempts)

        if not attempts:
            attempts.append(
                OfficialSiteDiscoveryAttempt(
                    attempt_number=1,
                    evidence_type=DiscoveryEvidenceType.MANUAL_REVIEW,
                    evidence_url=record.registry_source_url,
                    confidence=0.0,
                    status=InstitutionDiscoveryStatus.OFFICIAL_SITE_NOT_FOUND,
                    checked_at=checked_at,
                    stop_reason=DiscoveryStopReason.MAX_ATTEMPTS_REACHED,
                    notes="No candidate official-site evidence supplied by bounded discovery adapters.",
                )
            )
        else:
            final = attempts[-1]
            attempts[-1] = OfficialSiteDiscoveryAttempt(
                attempt_number=final.attempt_number,
                evidence_type=final.evidence_type,
                evidence_url=final.evidence_url,
                confidence=final.confidence,
                status=final.status,
                checked_at=final.checked_at,
                stop_reason=final.stop_reason or DiscoveryStopReason.MAX_ATTEMPTS_REACHED,
                notes=final.notes or "Official site not confirmed within configured discovery budget.",
            )
        return OfficialSiteDiscoveryResult.from_attempts(record.institution_id, attempts)

    def _bounded_candidates(
        self,
        candidates: Iterable[DiscoveryEvidenceCandidate],
    ) -> List[DiscoveryEvidenceCandidate]:
        counts = {
            DiscoveryEvidenceType.REGULATOR_LINK: 0,
            DiscoveryEvidenceType.OFFICIAL_WEBSITE: 0,
            DiscoveryEvidenceType.SEARCH_RESULT: 0,
            DiscoveryEvidenceType.MANUAL_REVIEW: 0,
        }
        bounded: List[DiscoveryEvidenceCandidate] = []
        for candidate in sorted(candidates, key=lambda item: item.confidence, reverse=True):
            if len(bounded) >= self._budget.max_total_attempts:
                break
            limit = self._limit_for(candidate.evidence_type)
            if counts[candidate.evidence_type] >= limit:
                continue
            bounded.append(candidate)
            counts[candidate.evidence_type] += 1
        return bounded

    def _limit_for(self, evidence_type: DiscoveryEvidenceType) -> int:
        if evidence_type == DiscoveryEvidenceType.REGULATOR_LINK:
            return self._budget.max_regulator_links
        if evidence_type == DiscoveryEvidenceType.SEARCH_RESULT:
            return self._budget.max_search_results
        return self._budget.max_manual_candidates


@dataclass(frozen=True)
class FetchResponse:
    """Minimal HTTP response abstraction used by controlled fetch adapters."""

    status_code: int
    content_type: str
    body: bytes
    final_url: str = ""


@dataclass(frozen=True)
class ArtifactFetchRequest:
    institution_id: str
    url: str
    authority_rank: PublicArtifactAuthorityRank
    artifact_type: PublicArtifactType
    language: str = "unknown"


class PublicArtifactFetcher:
    """Fetch and store an artifact only after the access-control decision allows it."""

    def __init__(
        self,
        fetch_bytes: Callable[[str], FetchResponse],
        store: "LocalArtifactStore",
    ) -> None:
        self._fetch_bytes = fetch_bytes
        self._store = store

    def fetch(
        self,
        request: ArtifactFetchRequest,
        access_decision: AccessControlDecision,
        *,
        retrieved_at: date,
    ) -> PublicArtifactRecord:
        if request.url != access_decision.url:
            raise ValueError("access decision URL must match artifact request URL")
        if not access_decision.allows_fetch:
            return self._store.blocked_record(
                request=request,
                access_decision=access_decision,
                retrieved_at=retrieved_at,
            )
        response = self._fetch_bytes(request.url)
        return self._store.store_response(request, response, retrieved_at=retrieved_at)


class LocalArtifactStore:
    """Persist raw bytes, extracted text, and metadata under artifacts/l6_scrape."""

    def __init__(self, root_dir: str | Path) -> None:
        self._root_dir = Path(root_dir)

    def store_response(
        self,
        request: ArtifactFetchRequest,
        response: FetchResponse,
        *,
        retrieved_at: date,
    ) -> PublicArtifactRecord:
        artifact_id = _artifact_id(request.institution_id, request.url)
        content_hash = "sha256:" + hashlib.sha256(response.body).hexdigest()
        raw_rel = Path("raw") / request.institution_id / f"{artifact_id}.bin"
        text_rel = Path("extracted_text") / request.institution_id / f"{artifact_id}.txt"
        meta_rel = Path("metadata") / request.institution_id / f"{artifact_id}.json"
        text = ArtifactTextExtractor.extract(response.body, response.content_type)
        extraction_status = ExtractionStatus.EXTRACTED if text.strip() else ExtractionStatus.FAILED
        _write_bytes(self._root_dir / raw_rel, response.body)
        _write_text(self._root_dir / text_rel, text)
        record = PublicArtifactRecord(
            artifact_id=artifact_id,
            institution_id=request.institution_id,
            url=response.final_url or request.url,
            authority_rank=request.authority_rank,
            artifact_type=request.artifact_type,
            language=request.language,
            retrieved_at=retrieved_at,
            http_status=response.status_code,
            content_type=response.content_type,
            content_hash=content_hash,
            raw_path=str(raw_rel).replace("\\", "/"),
            text_path=str(text_rel).replace("\\", "/"),
            extraction_status=extraction_status,
            citation_anchor_strategy="line_range",
            notes="Fetched after access-control allow decision.",
        )
        _write_text(self._root_dir / meta_rel, json.dumps(record.to_dict(), indent=2, sort_keys=True))
        return record

    def blocked_record(
        self,
        request: ArtifactFetchRequest,
        access_decision: AccessControlDecision,
        *,
        retrieved_at: date,
    ) -> PublicArtifactRecord:
        artifact_id = _artifact_id(request.institution_id, request.url)
        body = access_decision.to_dict()
        content_hash = "sha256:" + hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()
        meta_rel = Path("metadata") / request.institution_id / f"{artifact_id}.json"
        record = PublicArtifactRecord(
            artifact_id=artifact_id,
            institution_id=request.institution_id,
            url=request.url,
            authority_rank=request.authority_rank,
            artifact_type=request.artifact_type,
            language=request.language,
            retrieved_at=retrieved_at,
            http_status=403,
            content_type="application/json",
            content_hash=content_hash,
            extraction_status=access_decision.to_extraction_status(),
            citation_anchor_strategy="not_available",
            notes=access_decision.reason,
        )
        _write_text(self._root_dir / meta_rel, json.dumps(record.to_dict(), indent=2, sort_keys=True))
        return record


class ArtifactTextExtractor:
    """Small deterministic extractor for HTML/text artifacts in pilot fixtures."""

    @staticmethod
    def extract(body: bytes, content_type: str) -> str:
        text = body.decode("utf-8", errors="replace")
        if "html" in content_type.lower():
            text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
            text = re.sub(r"(?s)<[^>]+>", " ", text)
            text = html.unescape(text)
        return re.sub(r"[ \t\r\f\v]+", " ", text).strip()


class OperationExtractor:
    """Extract evidence-backed operation records from stored public artifacts."""

    FIELD_KEYWORDS: Dict[OperationEvidenceField, Sequence[str]] = {
        OperationEvidenceField.FEES: ("fee", "fees", "tariff", "charges", "commission"),
        OperationEvidenceField.PAYMENT_TERMS: ("installment", "payment schedule", "deferred payment"),
        OperationEvidenceField.LATE_PAYMENT_CLAUSES: ("late payment", "default", "delay penalty"),
        OperationEvidenceField.PENALTY_BENEFICIARY: ("charity", "donation", "beneficiary"),
        OperationEvidenceField.COLLATERAL: ("collateral", "pledge", "mortgage"),
        OperationEvidenceField.GUARANTEES: ("guarantee", "guarantor", "kafala"),
        OperationEvidenceField.INSURANCE_TAKAFUL_LINKS: ("insurance", "takaful"),
        OperationEvidenceField.OWNERSHIP_OR_ASSET_FLOW: ("ownership", "asset", "bank purchases"),
        OperationEvidenceField.SHARIA_CLAIMS: ("sharia", "shariah", "islamic"),
    }

    def extract(
        self,
        *,
        institution_id: str,
        artifact: PublicArtifactRecord,
        text: str,
        operation_name: str = "",
    ) -> OperationCatalogRecord:
        spans: List[OperationEvidenceSpan] = []
        for field_name, keywords in self.FIELD_KEYWORDS.items():
            snippet = _snippet_for_keywords(text, keywords)
            if snippet:
                spans.append(
                    OperationEvidenceSpan(
                        artifact_id=artifact.artifact_id,
                        field=field_name,
                        text=snippet,
                        citation_anchor="line_range",
                    )
                )
        name = operation_name or _operation_name_from_text(text, artifact.artifact_type)
        return OperationCatalogRecord(
            operation_id=_operation_id(institution_id, name, artifact.artifact_id),
            institution_id=institution_id,
            operation_name=name,
            artifact_ids=[artifact.artifact_id],
            evidence_spans=spans,
        )


class AaoifiMappingGenerator:
    """Generate machine-only AAOIFI mapping candidates for scholar review."""

    def generate(self, operation: OperationCatalogRecord) -> MachineAaoifiMappingCandidate:
        text = " ".join([operation.operation_name] + [span.text for span in operation.evidence_spans]).lower()
        standards: List[str] = []
        risk = ComplianceRiskLabel.UNKNOWN
        rationale = "No recognized operation family found; scholar review must classify from evidence."
        if any(term in text for term in ("murabaha", "deferred payment", "bank purchases", "ownership")):
            standards.extend(["FAS-28", "SS-08"])
            risk = ComplianceRiskLabel.MEDIUM
            rationale = "Evidence suggests murabaha/deferred sale mechanics or asset ownership flow."
        if any(term in text for term in ("ijarah", "lease", "leasing")):
            standards.extend(["FAS-32", "SS-09"])
            risk = ComplianceRiskLabel.MEDIUM
            rationale = "Evidence suggests lease/ijarah mechanics."
        if any(term in text for term in ("sukuk", "prospectus")):
            standards.extend(["FAS-33", "FAS-34"])
            risk = ComplianceRiskLabel.MEDIUM
            rationale = "Evidence suggests sukuk or investment certificate documentation."
        if any(term in text for term in ("takaful", "insurance")):
            standards.extend(["FAS-42", "FAS-43"])
            risk = ComplianceRiskLabel.MEDIUM
            rationale = "Evidence mentions insurance or takaful-linked obligations."
        if any(term in text for term in ("late payment", "delay penalty", "default")):
            standards.append("SS-08")
            risk = ComplianceRiskLabel.HIGH
            rationale = "Late payment/default clauses require focused Sharia review."
        if not standards:
            standards = ["REVIEW_REQUIRED"]
        deduped = list(dict.fromkeys(standards))
        return MachineAaoifiMappingCandidate(
            mapping_id=f"map-{operation.operation_id}",
            operation_id=operation.operation_id,
            candidate_standards=deduped,
            risk_label=risk,
            rationale=rationale,
        )


class ScholarReviewCsvStore:
    """Export machine candidates and import scholar decisions as CSV."""

    @staticmethod
    def export_candidates(path: str | Path, mappings: Iterable[MachineAaoifiMappingCandidate]) -> None:
        rows = [
            {
                "review_id": f"review-{mapping.mapping_id}",
                "mapping_id": mapping.mapping_id,
                "operation_id": mapping.operation_id,
                "candidate_standards": "|".join(mapping.candidate_standards),
                "risk_label": mapping.risk_label.value,
                "rationale": mapping.rationale,
                "decision": "",
                "reviewer": "",
                "aaoifi_references": "",
                "uncertainty_flags": "",
                "correction_type": "",
                "accepted_gold_case": "false",
            }
            for mapping in mappings
        ]
        fields = [
            "review_id",
            "mapping_id",
            "operation_id",
            "candidate_standards",
            "risk_label",
            "rationale",
            "decision",
            "reviewer",
            "aaoifi_references",
            "uncertainty_flags",
            "correction_type",
            "accepted_gold_case",
        ]
        _write_csv(path, fields, rows)

    @classmethod
    def import_reviews(cls, path: str | Path) -> List[ScholarReviewRecord]:
        with Path(path).open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            reviews = []
            for row in reader:
                if not str(row.get("decision", "")).strip():
                    continue
                review_id = row.get("review_id") or f"review-{row['mapping_id']}"
                reviews.append(
                    ScholarReviewRecord(
                        review_id=review_id,
                        mapping_id=row["mapping_id"],
                        reviewer=row["reviewer"],
                        decision=ReviewCandidateStatus(row["decision"]),
                        aaoifi_references=_split_pipe(row["aaoifi_references"]),
                        rationale=row["rationale"],
                        uncertainty_flags=_split_pipe(row.get("uncertainty_flags", "")),
                        correction_type=row.get("correction_type", ""),
                        accepted_gold_case=_as_bool(row.get("accepted_gold_case", "")),
                    )
                )
        return reviews

    @staticmethod
    def accepted_gold_cases(registry: InstitutionRegistry) -> List[Dict[str, object]]:
        rows: List[Dict[str, object]] = []
        for review in registry.accepted_gold_reviews():
            mapping = registry.mapping(review.mapping_id)
            operation = registry.operation(mapping.operation_id)
            rows.append(
                {
                    "review_id": review.review_id,
                    "mapping_id": review.mapping_id,
                    "operation_id": operation.operation_id,
                    "institution_id": operation.institution_id,
                    "operation_name": operation.operation_name,
                    "aaoifi_references": review.aaoifi_references,
                    "rationale": review.rationale,
                }
            )
        return rows


@dataclass(frozen=True)
class CorpusPilotGateReport:
    pilot_id: str
    passed: bool
    findings: List[str] = field(default_factory=list)


class CorpusPilotGate:
    """Readiness gate before approving a full-registry scrape."""

    def evaluate(self, plan: CorpusPilotPlan, registry: InstitutionRegistry) -> CorpusPilotGateReport:
        findings: List[str] = []
        gap_records = []
        for institution_id in plan.institution_ids:
            record = registry.get(institution_id)
            operations = registry.operations_for(institution_id)
            artifacts = registry.artifacts_for(institution_id)
            if record.discovery_status != InstitutionDiscoveryStatus.OFFICIAL_SITE_CONFIRMED:
                if not record.gap_reason:
                    findings.append(f"{institution_id}: non-success discovery requires gap_reason")
                gap_records.append(record)
                continue
            if not artifacts:
                findings.append(f"{institution_id}: confirmed site has no captured artifacts")
            if not operations:
                findings.append(f"{institution_id}: confirmed site has no extracted operations")
        if not gap_records:
            findings.append("pilot must include at least one no-details-found or blocked hard case")
        if not registry.accepted_gold_reviews():
            findings.append("pilot must include at least one accepted scholar-reviewed gold case")
        return CorpusPilotGateReport(
            pilot_id=plan.pilot_id,
            passed=not findings,
            findings=findings,
        )


def _xlsx_rows_by_sheet(path: Path) -> Dict[str, List[List[str]]]:
    namespace = {
        "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    }
    with zipfile.ZipFile(path) as archive:
        shared = _xlsx_shared_strings(archive)
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_targets = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in relationships.findall("rel:Relationship", namespace)
        }
        result: Dict[str, List[List[str]]] = {}
        for sheet in workbook.findall("main:sheets/main:sheet", namespace):
            name = sheet.attrib["name"]
            rel_id = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = rel_targets[rel_id].lstrip("/")
            sheet_path = "xl/" + target if not target.startswith("xl/") else target
            result[name] = _xlsx_sheet_rows(archive.read(sheet_path), shared)
        return result


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> List[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    values = []
    for item in root.findall("main:si", namespace):
        values.append("".join(node.text or "" for node in item.findall(".//main:t", namespace)))
    return values


def _xlsx_sheet_rows(payload: bytes, shared: Sequence[str]) -> List[List[str]]:
    namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    root = ET.fromstring(payload)
    rows: List[List[str]] = []
    for row in root.findall(".//main:row", namespace):
        values: Dict[int, str] = {}
        for cell in row.findall("main:c", namespace):
            reference = cell.attrib.get("r", "")
            index = _column_index(reference)
            value_node = cell.find("main:v", namespace)
            inline_node = cell.find("main:is/main:t", namespace)
            raw = value_node.text if value_node is not None else (inline_node.text if inline_node is not None else "")
            if cell.attrib.get("t") == "s" and raw:
                raw = shared[int(raw)]
            values[index] = raw or ""
        if values:
            rows.append([values.get(index, "") for index in range(max(values) + 1)])
    return rows


def _column_index(reference: str) -> int:
    letters = re.sub(r"[^A-Z]", "", reference.upper())
    index = 0
    for char in letters:
        index = index * 26 + ord(char) - ord("A") + 1
    return max(index - 1, 0)


def _first_non_empty_row_index(rows: Sequence[Sequence[str]]) -> Optional[int]:
    for index, row in enumerate(rows):
        if any(str(cell).strip() for cell in row):
            return index
    return None


def _normalize_header(value: object) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")
    aliases = {
        "english_name": "name_en",
        "institution": "name_en",
        "institution_name": "name_en",
        "company": "name_en",
        "company_name": "name_en",
        "bank": "name_en",
        "bank_name": "name_en",
        "arabic_name": "name_ar",
        "website_url": "official_website",
        "website": "official_website",
    }
    return aliases.get(text, text)


def _stable_id_for_row(
    name: str,
    regulator: InstitutionRegulator,
    sector: InstitutionSector,
    sheet_name: str,
    row_number: int,
) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    normalized = re.sub(r"-+", "-", normalized)
    if normalized and not re.search(r"[\u0600-\u06FF]", name) and re.search(r"[a-z]", normalized):
        return f"{regulator.value}-{sector.value}-{normalized}"
    sheet_slug = re.sub(r"[^a-z0-9]+", "-", sheet_name.lower()).strip("-") or "sheet"
    if normalized:
        return f"{regulator.value}-{sector.value}-{normalized}-row-{row_number}"
    return f"{regulator.value}-{sector.value}-{sheet_slug}-row-{row_number}"


def _pick(row: Mapping[str, object], *keys: str) -> str:
    normalized = {_normalize_header(key): value for key, value in row.items()}
    for key in keys:
        value = normalized.get(_normalize_header(key))
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _has_name_letter(value: str) -> bool:
    return re.search(r"[A-Za-z\u0600-\u06FF]", value) is not None


def _sector_from_text(value: str, default: InstitutionSector) -> InstitutionSector:
    text = value.lower().replace("-", "_").replace(" ", "_")
    if not text:
        return default
    for sector in InstitutionSector:
        if text == sector.value:
            return sector
    if "takaful" in text:
        return InstitutionSector.TAKAFUL
    if "leasing" in text or "lease" in text:
        return InstitutionSector.LEASING
    if "mortgage" in text:
        return InstitutionSector.MORTGAGE_FINANCE
    if "consumer" in text:
        return InstitutionSector.CONSUMER_FINANCE
    if "micro" in text:
        return InstitutionSector.MICROFINANCE
    if "sukuk" in text:
        return InstitutionSector.SUKUK
    if "fund" in text:
        return InstitutionSector.FUND
    return default


def _regulator_from_text(value: str, default: InstitutionRegulator) -> InstitutionRegulator:
    text = value.lower()
    if not text:
        return default
    if "central" in text or "cbe" in text:
        return InstitutionRegulator.CBE
    if "fra" in text or "financial regulatory" in text:
        return InstitutionRegulator.FRA
    if "egx" in text or "exchange" in text:
        return InstitutionRegulator.EGX
    if "mcsd" in text:
        return InstitutionRegulator.MCSD
    return default


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def _write_csv(path: str | Path, fields: Sequence[str], rows: Iterable[Mapping[str, object]]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _artifact_id(institution_id: str, url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    return f"art-{institution_id}-{digest}"


def _operation_id(institution_id: str, operation_name: str, artifact_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", operation_name.lower()).strip("-") or "operation"
    digest = hashlib.sha256(artifact_id.encode("utf-8")).hexdigest()[:8]
    return f"op-{institution_id}-{slug}-{digest}"


def _snippet_for_keywords(text: str, keywords: Sequence[str]) -> str:
    lowered = text.lower()
    for keyword in keywords:
        index = lowered.find(keyword)
        if index >= 0:
            start = max(0, index - 80)
            end = min(len(text), index + 160)
            return text[start:end].strip()
    return ""


def _operation_name_from_text(text: str, artifact_type: PublicArtifactType) -> str:
    lowered = text.lower()
    if "murabaha" in lowered or "deferred payment" in lowered:
        return "Murabaha/deferred payment operation"
    if "ijarah" in lowered or "lease" in lowered:
        return "Ijarah/leasing operation"
    if "sukuk" in lowered:
        return "Sukuk operation"
    if "takaful" in lowered:
        return "Takaful operation"
    return f"{artifact_type.value.replace('_', ' ').title()} operation"


def _split_pipe(value: str) -> List[str]:
    return [item.strip() for item in value.split("|") if item.strip()]


def _as_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}
