#!/usr/bin/env python3
"""Run safe L6 Egypt institution evidence-corpus gates.

The default command is fixture-backed. Live modes only revalidate known
regulator/source URLs and refuse broad institution scraping unless human review
and safe official-site targets exist.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Iterable, List, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.governance import (
    AccessControlDecision,
    AaoifiMappingGenerator,
    ArtifactClass,
    ArtifactFetchRequest,
    CorpusPilotGate,
    CorpusPilotPlan,
    DiscoveryEvidenceCandidate,
    DiscoveryEvidenceType,
    EngineAssessmentCsvStore,
    FetchResponse,
    ExtractionStatus,
    InstitutionDiscoveryStatus,
    InstitutionRegistry,
    InstitutionRegistryRecord,
    InstitutionRegulator,
    InstitutionSector,
    LocalArtifactStore,
    OfficialSiteDiscoveryRunner,
    OperationExtractor,
    PublicArtifactAuthorityRank,
    PublicArtifactFetcher,
    PublicArtifactType,
    ReviewCandidateStatus,
    ScholarReviewCsvStore,
    ScholarReviewListCsvStore,
    ScholarReviewRecord,
    WorkbookRegistryLoader,
)


DEFAULT_WORKBOOK = (
    ".planning/sharia-compliance-chatbot/docs/"
    "Egypt_Financial_Institutions_COMPLETE.xlsx"
)
DEFAULT_ARTIFACT_ROOT = "artifacts/l6_scrape"
MIN_EVIDENCE_TEXT_LENGTH = 500
SCRAPE_REVIEW_FIELDS = [
    "mushir_engine_sharia_aaoifi_review",
    "aaoifi_standard_reference_file_and_title",
    "human_scholar_supervision_review",
]
SCRAPE_ENRICHMENT_FIELDS = [
    "artifact_ids",
    "artifact_class",
    "detected_language",
    "normalized_operation",
    "operation_family",
    "confidence",
    "evidence_snippet",
    "matched_aliases",
    "source_url",
    "artifact_path",
    "extractor_version",
    "promotion_stage",
    "runtime_eligible",
    "needs_review_reason",
]
AAOIFI_STANDARD_TITLES = {
    "FAS-28": "Murabaha and Other Deferred Payment Sales",
    "SS-08": "Murabaha",
}
CBE_REGISTERED_BANKS_PDF_URL = (
    "https://www.cbe.org.eg/-/media/project/cbe/page-content/rich-text/"
    "financial-stability/english/headoffices-eng(2)-(2).pdf"
)
DEFAULT_FRA_REGISTER_URLS = {
    "capital_market": (
        "https://fra.gov.eg/en/%d8%aa%d8%b3%d8%ac%d9%8a%d9%84-%d9%88-"
        "%d8%aa%d8%ad%d8%af%d9%8a%d8%ab-%d8%b3%d8%ac%d9%84%d8%a7%d8%aa-"
        "%d9%84%d8%b4%d8%b1%d9%83%d8%a7%d8%aa-%d8%b3%d9%88%d9%82-%d8%a7"
        "%d9%84%d9%85%d8%a7%d9%84/"
    ),
    "insurance": (
        "https://fra.gov.eg/en/%D8%B3%D8%AC%D9%84%D8%A7%D8%AA-%D9%81%D9%8A-"
        "%D9%85%D8%AC%D8%A7%D9%84-%D8%A7%D9%84%D8%AA%D8%A3%D9%85%D9%8A%D9%86/"
    ),
}


class AccessBlockedError(RuntimeError):
    def __init__(self, reason: str, body: bytes = b""):
        super().__init__(reason)
        self.reason = reason
        self.body = body


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run safe L6 Egypt institution scrape gates."
    )
    parser.add_argument(
        "--mode",
        choices=[
            "fixture-pilot",
            "live-regulator-revalidation",
            "full-scrape",
            "legacy-sector-scrape",
            "official-registry-completion",
            "mixed-mini-pilot",
        ],
        default="fixture-pilot",
    )
    parser.add_argument("--workbook", default=DEFAULT_WORKBOOK)
    parser.add_argument("--artifact-root", default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--pilot-id", default="l6-egypt-fi-pilot-local")
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    parser.add_argument("--max-targets", type=int, default=36)
    parser.add_argument("--max-pages-per-target", type=int, default=5)
    parser.add_argument(
        "--old-scraping-dir",
        default="artifacts/l6_scrape/full_scrape/2026-05-21/old_scraping",
        help="Folder containing Banks_old.xlsx, Capital_Market_old.xlsx, Insurance_old.xlsx, and Non_Categorized_old.xlsx.",
    )
    parser.add_argument(
        "--seed-sites-file",
        default="",
        help=(
            "Optional CSV with reviewed official website candidates. Supported fields: "
            "institution_id, name_en, official_website, confidence, source_url, notes."
        ),
    )
    parser.add_argument(
        "--sector",
        action="append",
        default=[],
        help="Limit legacy-sector-scrape to one or more sectors, e.g. --sector bank --sector insurance.",
    )
    parser.add_argument(
        "--rerun-status",
        default="",
        help=(
            "Comma-separated previous bank_scrape_results statuses to rerun, "
            "for example failed,insufficient_text."
        ),
    )
    parser.add_argument(
        "--review-file",
        default="",
        help="Optional CSV of later human scholar decisions; not required for scraping.",
    )
    args = parser.parse_args()

    run_date = date.fromisoformat(args.today)
    artifact_root = Path(args.artifact_root)
    if args.mode == "mixed-mini-pilot":
        workbook_path = Path(args.workbook)
        old_scraping_dir = Path(args.old_scraping_dir)
        missing_inputs = _missing_mixed_pilot_inputs(
            workbook_path=workbook_path,
            old_scraping_dir=old_scraping_dir,
        )
        if missing_inputs:
            print("Mixed mini-pilot NO-GO: required local inputs are missing.", file=sys.stderr)
            for item in missing_inputs:
                print(f"- {item}", file=sys.stderr)
            return 2
        baseline_registry = WorkbookRegistryLoader().load_xlsx(workbook_path)
        return run_mixed_mini_pilot(
            baseline_registry=baseline_registry,
            old_scraping_dir=old_scraping_dir,
            artifact_root=artifact_root,
            run_date=run_date,
            timeout_seconds=args.timeout_seconds,
            delay_seconds=args.delay_seconds,
            max_pages_per_target=args.max_pages_per_target,
        )
    if args.mode == "legacy-sector-scrape":
        return run_legacy_sector_scrape(
            old_scraping_dir=Path(args.old_scraping_dir),
            artifact_root=artifact_root,
            run_date=run_date,
            seed_sites_file=Path(args.seed_sites_file) if args.seed_sites_file else None,
            timeout_seconds=args.timeout_seconds,
            delay_seconds=args.delay_seconds,
            max_targets=args.max_targets,
            max_pages_per_target=args.max_pages_per_target,
            sectors=args.sector or None,
        )

    workbook_path = Path(args.workbook)
    baseline_registry = WorkbookRegistryLoader().load_xlsx(workbook_path)
    if args.mode == "official-registry-completion":
        output_dir = run_official_registry_completion(
            baseline_registry=baseline_registry,
            artifact_root=artifact_root,
            run_date=run_date,
            timeout_seconds=args.timeout_seconds,
        )
        print("=== L6 Official Registry Completion ===")
        print(f"Workbook records loaded: {len(baseline_registry.records())}")
        print(f"Output: {output_dir}")
        return 0
    if args.mode == "live-regulator-revalidation":
        manifest_path = run_live_regulator_revalidation(
            baseline_registry=baseline_registry,
            artifact_root=artifact_root,
            run_date=run_date,
            timeout_seconds=args.timeout_seconds,
            delay_seconds=args.delay_seconds,
        )
        print("=== L6 Live Regulator Revalidation ===")
        print(f"Workbook records loaded: {len(baseline_registry.records())}")
        print(f"Unique registry source URLs checked: {len(_unique_registry_source_urls(baseline_registry.records()))}")
        print(f"Manifest: {manifest_path}")
        return 0
    if args.mode == "full-scrape":
        gate_result = run_full_scrape_gate(
            baseline_registry=baseline_registry,
            artifact_root=artifact_root,
            run_date=run_date,
            review_file=Path(args.review_file) if args.review_file else None,
        )
        if gate_result == 0:
            return run_live_bank_scrape(
                baseline_registry=baseline_registry,
                artifact_root=artifact_root,
                run_date=run_date,
                timeout_seconds=args.timeout_seconds,
                delay_seconds=args.delay_seconds,
                max_targets=args.max_targets,
                max_pages_per_target=args.max_pages_per_target,
                rerun_statuses=_split_statuses(args.rerun_status),
            )
        return gate_result

    pilot_registry = run_fixture_pilot(
        baseline_registry=baseline_registry,
        artifact_root=artifact_root,
        pilot_id=args.pilot_id,
        run_date=run_date,
    )
    manifest_path = write_manifest(
        baseline_registry=baseline_registry,
        pilot_registry=pilot_registry,
        artifact_root=artifact_root,
        pilot_id=args.pilot_id,
        workbook_path=workbook_path,
        run_date=run_date,
    )

    plan = CorpusPilotPlan(
        pilot_id=args.pilot_id,
        institution_ids=[record.institution_id for record in pilot_registry.records()],
        includes_no_details_case=True,
    )
    report = CorpusPilotGate().evaluate(plan, pilot_registry)

    print("=== L6 Egypt Institution Pilot ===")
    print(f"Workbook records loaded: {len(baseline_registry.records())}")
    print(f"Pilot institutions: {len(pilot_registry.records())}")
    print(f"Pilot gate passed: {report.passed}")
    print(f"Machine mappings exported: {len(pilot_registry.machine_mappings())}")
    print(f"Manifest: {manifest_path}")
    if report.findings:
        print("Findings:")
        for finding in report.findings:
            print(f"  - {finding}")
    return 0 if report.passed else 1


def run_live_regulator_revalidation(
    *,
    baseline_registry: InstitutionRegistry,
    artifact_root: Path,
    run_date: date,
    timeout_seconds: float,
    delay_seconds: float,
) -> Path:
    """Check access and reachability for known regulator/source URLs."""
    rows = []
    for index, url in enumerate(_unique_registry_source_urls(baseline_registry.records()), start=1):
        if index > 1:
            time.sleep(max(delay_seconds, 0.0))
        robots = _check_robots(url, timeout_seconds)
        probe = _probe_url(url, timeout_seconds) if robots["allowed"] else {}
        rows.append(
            {
                "url": url,
                "checked_at": run_date.isoformat(),
                "robots_allowed": robots["allowed"],
                "robots_reason": robots["reason"],
                "http_status": probe.get("http_status"),
                "content_type": probe.get("content_type"),
                "final_url": probe.get("final_url"),
                "error": probe.get("error", ""),
                "record_count": sum(1 for record in baseline_registry.records() if record.registry_source_url == url),
            }
        )
    output_dir = artifact_root / "live_revalidation" / run_date.isoformat()
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "regulator_source_access.csv"
    fields = [
        "url",
        "checked_at",
        "robots_allowed",
        "robots_reason",
        "http_status",
        "content_type",
        "final_url",
        "error",
        "record_count",
    ]
    _write_rows(csv_path, fields, rows)
    manifest = {
        "mode": "live_regulator_revalidation",
        "run_date": run_date.isoformat(),
        "baseline_record_count": len(baseline_registry.records()),
        "unique_registry_source_url_count": len(rows),
        "allowed_count": sum(1 for row in rows if row["robots_allowed"]),
        "reachable_count": sum(1 for row in rows if row.get("http_status")),
        "blocked_count": sum(1 for row in rows if row.get("error")),
        "csv": str(csv_path).replace("\\", "/"),
        "next_gate": (
            "Official institution websites must be discovered and access-checked "
            "before any full institution scrape."
        ),
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest_path


def run_full_scrape_gate(
    *,
    baseline_registry: InstitutionRegistry,
    artifact_root: Path,
    run_date: date,
    review_file: Path | None,
    bank_discovery_targets: List[dict[str, object]] | None = None,
) -> int:
    """Refuse unsafe full scraping until required live gates are satisfied."""
    official_targets = [record for record in baseline_registry.records() if record.official_website]
    review_status = _real_review_status(review_file)
    blocked_reasons = []
    if bank_discovery_targets is None:
        bank_discovery_targets = _discover_bank_website_candidates(
            baseline_registry.records(),
            timeout_seconds=20.0,
        )
    if not official_targets and not bank_discovery_targets:
        blocked_reasons.append(
            "no official institution website URLs or discoverable bank website candidates to crawl"
        )
    if not review_status["has_real_accepted_review"]:
        blocked_reasons.append("no real accepted scholar-review import supplied")
    manifest = {
        "mode": "full_scrape_gate",
        "run_date": run_date.isoformat(),
        "baseline_record_count": len(baseline_registry.records()),
        "official_target_count": len(official_targets),
        "bank_discovery_target_count": len(bank_discovery_targets),
        "review_file": str(review_file).replace("\\", "/") if review_file else "",
        "review_status": review_status,
        "human_scholar_review_required_before_scrape": True,
        "allowed_to_scrape": not blocked_reasons,
        "blocked_reasons": blocked_reasons,
    }
    output_dir = artifact_root / "full_scrape_gate" / run_date.isoformat()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print("=== L6 Full Scrape Gate ===")
    print(f"Workbook records loaded: {len(baseline_registry.records())}")
    print(f"Official institution targets: {len(official_targets)}")
    print(f"Discovered bank targets: {len(bank_discovery_targets)}")
    print(f"Allowed to scrape: {not blocked_reasons}")
    print(f"Manifest: {manifest_path}")
    if blocked_reasons:
        print("Blocked reasons:")
        for reason in blocked_reasons:
            print(f"  - {reason}")
        return 2
    print("Full scrape gate passed. Human scholar review will stay blank until a later enhancement step.")
    return 0


def run_live_bank_scrape(
    *,
    baseline_registry: InstitutionRegistry,
    artifact_root: Path,
    run_date: date,
    timeout_seconds: float,
    delay_seconds: float,
    max_targets: int,
    max_pages_per_target: int,
    rerun_statuses: set[str] | None = None,
) -> int:
    """Scrape bounded public operation/product pages for discovered bank website candidates."""
    candidates = _discover_bank_website_candidates(
        baseline_registry.records(),
        timeout_seconds=timeout_seconds,
    )
    if rerun_statuses:
        candidates = _filter_candidates_by_previous_status(
            candidates,
            artifact_root / "full_scrape" / run_date.isoformat() / "bank_scrape_results.csv",
            rerun_statuses,
        )
    candidates = candidates[:max_targets]
    run_label = _status_label(rerun_statuses)
    registry = InstitutionRegistry([_reset_for_pilot(candidate["record"]) for candidate in candidates])
    fetcher = PublicArtifactFetcher(
        lambda url: _urlopen_fetch(url, timeout_seconds),
        LocalArtifactStore(artifact_root),
    )
    runner = OfficialSiteDiscoveryRunner()
    extractor = OperationExtractor()
    mapper = AaoifiMappingGenerator()
    rows = []
    for index, candidate in enumerate(candidates, start=1):
        if index > 1:
            time.sleep(max(delay_seconds, 0.0))
        record = candidate["record"]
        url = candidate["official_website"]
        robots = _check_robots(url, timeout_seconds)
        if not robots["allowed"]:
            status = (
                "blocked_by_robots"
                if "disallows" in str(robots["reason"]).lower()
                else "access_check_failed"
            )
            rows.append(_scrape_result_row(record, url, status, robots["reason"]))
            continue
        discovery = runner.run(
            record,
            [
                DiscoveryEvidenceCandidate(
                    url=url,
                    evidence_type=DiscoveryEvidenceType.SEARCH_RESULT,
                    confidence=0.72,
                    status=InstitutionDiscoveryStatus.OFFICIAL_SITE_CONFIRMED,
                    notes=(
                        "Candidate official website discovered from banksegypt.com "
                        "and accepted only as an official-site crawl target."
                    ),
                )
            ],
            checked_at=run_date,
        )
        registry = _copy_runtime_state(
            source=registry,
            target=registry.with_discovery_result(discovery),
        )
        page_urls = [url]
        fetched_pages = 0
        extracted_operations = 0
        notes = []
        try:
            page_index = 0
            while page_index < len(page_urls) and fetched_pages < max_pages_per_target:
                page_url = page_urls[page_index]
                page_index += 1
                if fetched_pages > 0:
                    time.sleep(max(delay_seconds, 0.0))
                page_robots = _check_robots(page_url, timeout_seconds)
                if not page_robots["allowed"]:
                    notes.append(f"{page_url}: {page_robots['reason']}")
                    continue
                request = ArtifactFetchRequest(
                    institution_id=record.institution_id,
                    url=page_url,
                    authority_rank=PublicArtifactAuthorityRank.OFFICIAL_INSTITUTION,
                    artifact_type=PublicArtifactType.PRODUCT_PAGE,
                    language="unknown",
                )
                artifact = fetcher.fetch(
                    request,
                    AccessControlDecision.evaluate(url=page_url, checked_at=run_date),
                    retrieved_at=run_date,
                )
                fetched_pages += 1
                registry.add_artifact(artifact)
                if artifact.raw_path and page_url == url:
                    raw_html = (artifact_root / artifact.raw_path).read_bytes().decode(
                        "utf-8",
                        errors="replace",
                    )
                    for discovered_url in _candidate_operation_links(
                        page_url,
                        raw_html,
                        limit=max_pages_per_target - len(page_urls),
                    ):
                        if discovered_url not in page_urls:
                            page_urls.append(discovered_url)
                if artifact.extraction_status == ExtractionStatus.EXTRACTED and artifact.text_path:
                    text = (artifact_root / artifact.text_path).read_text(encoding="utf-8")
                    if _has_useful_evidence_text(text):
                        operation = extractor.extract(
                            institution_id=record.institution_id,
                            artifact=artifact,
                            text=text,
                            operation_name=_operation_name_from_page(page_url, text, record.name_en),
                        )
                        registry.add_operation(operation)
                        registry.add_machine_mapping(mapper.generate(operation))
                        extracted_operations += 1
                    else:
                        notes.append(
                            f"{page_url}: extracted text below useful evidence threshold ({len(text.strip())} chars)"
                        )
                else:
                    notes.append(f"{page_url}: {artifact.extraction_status.value}")
            status = "extracted" if extracted_operations else "insufficient_text"
            rows.append(
                _scrape_result_row(
                    record,
                    url,
                    status,
                    "; ".join(notes) or (
                        f"Fetched {fetched_pages} page(s); extracted {extracted_operations} operation(s)."
                    ),
                    pages_fetched=fetched_pages,
                    operations_extracted=extracted_operations,
                )
            )
        except Exception as exc:
            rows.append(
                _scrape_result_row(
                    record,
                    url,
                    "partial_extracted" if extracted_operations else "failed",
                    str(exc),
                    pages_fetched=fetched_pages,
                    operations_extracted=extracted_operations,
                )
            )

    output_dir = (
        artifact_root / "full_scrape_rerun" / run_date.isoformat() / run_label
        if rerun_statuses
        else artifact_root / "full_scrape" / run_date.isoformat()
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(
        output_dir / "bank_scrape_results.csv",
        [
            "institution_id",
            "name_en",
            "official_website",
            "status",
            "pages_fetched",
            "operations_extracted",
            *SCRAPE_REVIEW_FIELDS,
            *SCRAPE_ENRICHMENT_FIELDS,
            "notes",
        ],
        _with_scrape_review_columns(rows, registry),
    )
    review_dir = (
        artifact_root / "review" / f"full-scrape-rerun-{run_date.isoformat()}-{run_label}"
        if rerun_statuses
        else artifact_root / "review" / f"full-scrape-{run_date.isoformat()}"
    )
    ScholarReviewCsvStore.export_candidates(
        review_dir / "machine_mapping_candidates.csv",
        registry.machine_mappings(),
    )
    assessment_rows_path = output_dir / "engine_assessment_rows.csv"
    EngineAssessmentCsvStore.export_assessments(assessment_rows_path, registry)
    scholar_review_paths = ScholarReviewListCsvStore.export_lists(output_dir, registry)
    chunk_ready_path = _write_chunk_ready_spans(output_dir / "chunk_ready_spans.jsonl", registry)
    guidance_path = _write_scholar_review_guidance(output_dir)
    manifest = {
        "mode": "full_scrape_bank_slice_rerun" if rerun_statuses else "full_scrape_bank_slice",
        "run_date": run_date.isoformat(),
        "rerun_statuses": sorted(rerun_statuses or []),
        "candidate_count": len(candidates),
        "max_pages_per_target": max_pages_per_target,
        "scraped_count": sum(1 for row in rows if row["status"] in {"extracted", "partial_extracted"}),
        "failed_or_blocked_count": sum(
            1 for row in rows if row["status"] not in {"extracted", "partial_extracted"}
        ),
        "pages_fetched": sum(int(row.get("pages_fetched") or 0) for row in rows),
        "operations_extracted": sum(int(row.get("operations_extracted") or 0) for row in rows),
        "machine_mapping_count": len(registry.machine_mappings()),
        "engine_assessment_rows": str(assessment_rows_path).replace("\\", "/"),
        "chunk_ready_spans": str(chunk_ready_path).replace("\\", "/"),
        "scholar_review_list_bilingual": str(scholar_review_paths["bilingual"]).replace("\\", "/"),
        "scholar_review_list_en": str(scholar_review_paths["english"]).replace("\\", "/"),
        "scholar_review_list_ar": str(scholar_review_paths["arabic"]).replace("\\", "/"),
        "scholar_review_guidance": str(guidance_path).replace("\\", "/"),
        "scholar_review_item_count": len(EngineAssessmentCsvStore.rows(registry)),
        "review_candidates": str(review_dir / "machine_mapping_candidates.csv").replace("\\", "/"),
        "scope_boundary": (
            "Full scrape completed only for bank official-site candidates discoverable "
            "from public bank directory data. Non-bank sectors still require official "
            "website discovery before crawling. Human scholar review columns are exported "
            "blank for later completion."
        ),
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print("=== L6 Full Bank Scrape ===")
    print(f"Discovered bank candidates: {len(candidates)}")
    print(f"Scraped: {manifest['scraped_count']}")
    print(f"Failed or blocked: {manifest['failed_or_blocked_count']}")
    print(f"Pages fetched: {manifest['pages_fetched']}")
    print(f"Operations extracted: {manifest['operations_extracted']}")
    print(f"Machine mappings exported: {manifest['machine_mapping_count']}")
    print(f"Engine assessment rows: {assessment_rows_path}")
    print(f"Scholar review bilingual list: {scholar_review_paths['bilingual']}")
    print(f"Manifest: {manifest_path}")
    if rerun_statuses:
        return 0
    return 0 if manifest["scraped_count"] else 1


def run_official_registry_completion(
    *,
    baseline_registry: InstitutionRegistry,
    artifact_root: Path,
    run_date: date,
    timeout_seconds: float,
    cbe_pdf_url: str = CBE_REGISTERED_BANKS_PDF_URL,
    fra_register_urls: Mapping[str, str] | None = None,
) -> Path:
    """Complete regulator-backed institution identity before product crawling."""
    output_dir = artifact_root / "official_registry_completion" / run_date.isoformat()
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = [
        _registry_identity_row(
            record,
            run_date=run_date,
            source_type="baseline_workbook",
            parse_status="baseline_unverified",
        )
        for record in baseline_registry.records()
    ]
    cbe_summary = {
        "source_url": cbe_pdf_url,
        "parse_status": "skipped",
        "raw_artifact_sha256": "",
        "parsed_row_count": 0,
    }
    if cbe_pdf_url:
        cbe_summary, cbe_rows = _cbe_bank_pdf_registry_rows(
            cbe_pdf_url,
            raw_dir=raw_dir,
            run_date=run_date,
            timeout_seconds=timeout_seconds,
        )
        rows = _merge_regulator_rows(rows, cbe_rows)
    fra_summary: dict[str, object] = {}
    active_fra_register_urls = DEFAULT_FRA_REGISTER_URLS if fra_register_urls is None else fra_register_urls
    for key, url in active_fra_register_urls.items():
        sector = _fra_sector_for_key(key)
        summary, fra_rows = _fra_register_registry_rows(
            url,
            sector=sector,
            raw_dir=raw_dir,
            run_date=run_date,
            timeout_seconds=timeout_seconds,
        )
        fra_summary[key] = summary
        rows = _merge_regulator_rows(rows, fra_rows)
    normalized_rows = [_finalize_registry_identity_row(row) for row in rows]
    normalized_path = output_dir / "normalized_institution_registry.csv"
    _write_rows(normalized_path, _REGISTRY_IDENTITY_FIELDS, normalized_rows)
    manifest = {
        "mode": "official_registry_completion",
        "run_date": run_date.isoformat(),
        "baseline_record_count": len(baseline_registry.records()),
        "normalized_row_count": len(normalized_rows),
        "ready_for_product_crawl_count": sum(
            1 for row in normalized_rows if row["ready_for_product_crawl"] == "true"
        ),
        "cbe": cbe_summary,
        "fra": fra_summary,
        "normalized_registry": str(normalized_path).replace("\\", "/"),
        "scope_boundary": (
            "This slice completes regulator-backed institution identity and provenance. "
            "It does not crawl products or create compliance evidence from third-party pages."
        ),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output_dir


_REGISTRY_IDENTITY_FIELDS = [
    "institution_id",
    "canonical_name",
    "name_en",
    "name_ar",
    "aliases",
    "regulator",
    "sector",
    "license_id",
    "license_date",
    "source_url",
    "source_type",
    "source_last_modified",
    "retrieved_at",
    "raw_artifact_sha256",
    "raw_artifact_path",
    "linked_official_pdf_urls",
    "linked_official_pdf_hashes",
    "linked_official_pdf_paths",
    "parse_status",
    "duplicate_score",
    "official_website",
    "official_website_confidence",
    "gap_reason",
    "ready_for_product_crawl",
]


def _registry_identity_row(
    record: InstitutionRegistryRecord,
    *,
    run_date: date,
    source_type: str,
    parse_status: str,
    source_url: str = "",
    raw_artifact_sha256: str = "",
    raw_artifact_path: str = "",
    license_id: str = "",
    license_date: str = "",
    duplicate_score: float = 0.0,
) -> dict[str, object]:
    return {
        "institution_id": record.institution_id,
        "canonical_name": record.name_en,
        "name_en": record.name_en,
        "name_ar": record.name_ar or "",
        "aliases": "",
        "regulator": record.regulator.value,
        "sector": record.sector.value,
        "license_id": license_id,
        "license_date": license_date,
        "source_url": source_url or record.registry_source_url,
        "source_type": source_type,
        "source_last_modified": "",
        "retrieved_at": run_date.isoformat(),
        "raw_artifact_sha256": raw_artifact_sha256,
        "raw_artifact_path": raw_artifact_path,
        "linked_official_pdf_urls": "",
        "linked_official_pdf_hashes": "",
        "linked_official_pdf_paths": "",
        "parse_status": parse_status,
        "duplicate_score": f"{duplicate_score:.2f}",
        "official_website": record.official_website or "",
        "official_website_confidence": f"{record.official_website_confidence:.2f}",
        "gap_reason": record.gap_reason,
        "ready_for_product_crawl": "false",
    }


def _cbe_bank_pdf_registry_rows(
    url: str,
    *,
    raw_dir: Path,
    run_date: date,
    timeout_seconds: float,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    try:
        response = _urlopen_fetch(url, timeout_seconds)
    except AccessBlockedError as exc:
        body = exc.body or str(exc).encode("utf-8")
        sha = _sha256(body)
        raw_path = raw_dir / "cbe_registered_banks_blocked.html"
        raw_path.write_bytes(body)
        return (
            {
                "source_url": url,
                "parse_status": "blocked_by_security",
                "raw_artifact_sha256": sha,
                "raw_artifact_path": str(raw_path).replace("\\", "/"),
                "parsed_row_count": 0,
                "reason": exc.reason,
            },
            [],
        )
    sha = _sha256(response.body)
    raw_path = raw_dir / "cbe_registered_banks.pdf"
    raw_path.write_bytes(response.body)
    body_text = _extract_pdf_text(response.body)
    block_reason = _access_block_reason(body_text)
    if block_reason:
        return (
            {
                "source_url": url,
                "parse_status": "blocked_by_security",
                "raw_artifact_sha256": sha,
                "raw_artifact_path": str(raw_path).replace("\\", "/"),
                "parsed_row_count": 0,
                "reason": block_reason,
            },
            [],
        )
    rows = []
    for parsed in _parse_cbe_bank_pdf_text(body_text):
        rows.append(
            {
                "institution_id": stable_like_registry_id(
                    parsed["name_en"],
                    InstitutionRegulator.CBE,
                    InstitutionSector.BANK,
                ),
                "canonical_name": parsed["name_en"],
                "name_en": parsed["name_en"],
                "name_ar": "",
                "aliases": "",
                "regulator": InstitutionRegulator.CBE.value,
                "sector": InstitutionSector.BANK.value,
                "license_id": "",
                "license_date": parsed["license_date"],
                "source_url": url,
                "source_type": "cbe_bank_pdf",
                "source_last_modified": "",
                "retrieved_at": run_date.isoformat(),
                "raw_artifact_sha256": sha,
                "raw_artifact_path": str(raw_path).replace("\\", "/"),
                "linked_official_pdf_urls": "",
                "linked_official_pdf_hashes": "",
                "linked_official_pdf_paths": "",
                "parse_status": "parsed",
                "duplicate_score": "0.00",
                "official_website": "",
                "official_website_confidence": "0.00",
                "gap_reason": "",
                "ready_for_product_crawl": "false",
            }
        )
    return (
        {
            "source_url": url,
            "parse_status": "parsed" if rows else "no_rows_found",
            "raw_artifact_sha256": sha,
            "raw_artifact_path": str(raw_path).replace("\\", "/"),
            "parsed_row_count": len(rows),
        },
        rows,
    )


def _parse_cbe_bank_pdf_text(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line or "central bank" in line.lower() or "registered" in line.lower():
            continue
        parts = [part.strip() for part in re.split(r"\s*\|\s*|\t+", line) if part.strip()]
        if not parts or not _has_visible_letter(parts[0]):
            continue
        if "bank" not in parts[0].lower():
            continue
        license_date = next(
            (part for part in parts[1:] if re.search(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b", part)),
            "",
        )
        rows.append({"name_en": parts[0], "license_date": license_date})
    return rows


def _extract_pdf_text(body: bytes) -> str:
    if not body.startswith(b"%PDF"):
        return body.decode("utf-8", errors="replace")
    text_parts: list[str] = []
    for match in re.finditer(rb"\((.*?)\)\s*Tj", body, flags=re.DOTALL):
        text_parts.append(_decode_pdf_literal(match.group(1)))
    for match in re.finditer(rb"\[(.*?)\]\s*TJ", body, flags=re.DOTALL):
        text_parts.extend(
            _decode_pdf_literal(part)
            for part in re.findall(rb"\((.*?)\)", match.group(1), flags=re.DOTALL)
        )
    return "\n".join(part for part in text_parts if part).strip()


def _decode_pdf_literal(value: bytes) -> str:
    unescaped = re.sub(rb"\\([\\()])", rb"\1", value)
    unescaped = unescaped.replace(rb"\n", b"\n").replace(rb"\r", b"\r").replace(rb"\t", b"\t")
    return unescaped.decode("utf-8", errors="replace")


def _has_visible_letter(value: str) -> bool:
    return any(char.isalpha() for char in value)


def _fra_register_registry_rows(
    url: str,
    *,
    sector: InstitutionSector,
    raw_dir: Path,
    run_date: date,
    timeout_seconds: float,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    rows = []
    visited: set[str] = set()
    current_url = url
    page_count = 0
    first_sha = ""
    first_raw_path = ""
    linked_pdf_count = 0
    while current_url and current_url not in visited and page_count < 25:
        visited.add(current_url)
        page_count += 1
        html_text = _read_text_url(current_url, timeout_seconds)
        sha = _sha256(html_text.encode("utf-8"))
        raw_path = raw_dir / f"fra_{sector.value}_register_page_{page_count}.html"
        raw_path.write_text(html_text, encoding="utf-8")
        if page_count == 1:
            first_sha = sha
            first_raw_path = str(raw_path).replace("\\", "/")
        source_last_modified = _source_last_modified_from_html(html_text)
        block_reason = _access_block_reason(html_text)
        if block_reason:
            return (
                {
                    "source_url": current_url,
                    "parse_status": "blocked_by_security",
                    "raw_artifact_sha256": sha,
                    "raw_artifact_path": str(raw_path).replace("\\", "/"),
                    "parsed_row_count": 0,
                    "page_count": page_count,
                    "reason": block_reason,
                },
                [],
            )
        entries = _fra_register_entries_from_html(html_text, current_url)
        for index, entry in enumerate(entries, start=len(rows) + 1):
            detail_fields: dict[str, str] = {}
            detail_url = entry.get("detail_url", "")
            detail_sha = sha
            detail_raw_path = raw_path
            if detail_url:
                detail_text = _read_text_url(detail_url, timeout_seconds)
                detail_sha = _sha256(detail_text.encode("utf-8"))
                detail_raw_path = raw_dir / f"fra_{sector.value}_detail_{index}.html"
                detail_raw_path.write_text(detail_text, encoding="utf-8")
                detail_fields = _fra_detail_fields_from_html(detail_text)
                linked_pdfs = _fetch_linked_official_pdfs(
                    detail_text,
                    detail_url,
                    raw_dir=raw_dir,
                    stem=f"fra_{sector.value}_detail_{index}",
                    timeout_seconds=timeout_seconds,
                )
            else:
                linked_pdfs = _fetch_linked_official_pdfs(
                    html_text,
                    current_url,
                    raw_dir=raw_dir,
                    stem=f"fra_{sector.value}_register_page_{page_count}_row_{index}",
                    timeout_seconds=timeout_seconds,
                )
            linked_pdf_count += len(linked_pdfs)
            name_en = detail_fields.get("name_en") or entry.get("name_en", "")
            if not name_en:
                continue
            official_website = _normalize_website_url(detail_fields.get("official_website", ""))
            confidence = 0.90 if official_website else 0.0
            source_type = "fra_register_detail" if detail_url else "fra_register"
            if linked_pdfs:
                source_type = f"{source_type}_with_linked_pdf"
            rows.append(
                {
                    "institution_id": stable_like_registry_id(
                        name_en,
                        InstitutionRegulator.FRA,
                        sector,
                    ),
                    "canonical_name": name_en,
                    "name_en": name_en,
                    "name_ar": detail_fields.get("name_ar", ""),
                    "aliases": "",
                    "regulator": InstitutionRegulator.FRA.value,
                    "sector": sector.value,
                    "license_id": detail_fields.get("license_id", ""),
                    "license_date": detail_fields.get("license_date") or entry.get("license_date", ""),
                    "source_url": detail_url or current_url,
                    "source_type": source_type,
                    "source_last_modified": detail_fields.get("source_last_modified") or source_last_modified,
                    "retrieved_at": run_date.isoformat(),
                    "raw_artifact_sha256": detail_sha,
                    "raw_artifact_path": str(detail_raw_path).replace("\\", "/"),
                    "linked_official_pdf_urls": " | ".join(pdf["url"] for pdf in linked_pdfs),
                    "linked_official_pdf_hashes": " | ".join(pdf["sha256"] for pdf in linked_pdfs),
                    "linked_official_pdf_paths": " | ".join(pdf["path"] for pdf in linked_pdfs),
                    "parse_status": "parsed",
                    "duplicate_score": "0.00",
                    "official_website": official_website,
                    "official_website_confidence": f"{confidence:.2f}",
                    "gap_reason": "",
                    "ready_for_product_crawl": "false",
                }
            )
        current_url = _fra_next_register_url(html_text, current_url)
    return (
        {
            "source_url": url,
            "parse_status": "parsed" if rows else "no_rows_found",
            "raw_artifact_sha256": first_sha,
            "raw_artifact_path": first_raw_path,
            "parsed_row_count": len(rows),
            "page_count": page_count,
            "linked_official_pdf_count": linked_pdf_count,
        },
        rows,
    )


def _fra_register_entries_from_html(html_text: str, base_url: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for row_html in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", html_text):
        cells = re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", row_html)
        if not cells:
            continue
        first_cell = cells[0]
        name = _strip_tags(first_cell)
        if not name or name.lower() in {"name", "company name"}:
            continue
        href_match = re.search(r"href=[\"']([^\"']+)[\"']", first_cell, flags=re.IGNORECASE)
        detail_url = (
            urllib.parse.urljoin(base_url, html.unescape(href_match.group(1)))
            if href_match
            else ""
        )
        license_date = next(
            (
                _strip_tags(cell)
                for cell in cells[1:]
                if re.search(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b", _strip_tags(cell))
            ),
            "",
        )
        entries.append(
            {
                "name_en": name,
                "license_date": license_date,
                "detail_url": detail_url,
            }
        )
    return entries


def _fra_next_register_url(html_text: str, base_url: str) -> str:
    for anchor_attrs, anchor_text in re.findall(
        r"(?is)<a\b([^>]*)>(.*?)</a>",
        html_text,
    ):
        label = _strip_tags(anchor_text).strip().lower()
        if (
            re.search(r"\brel\s*=\s*['\"]?next['\"]?", anchor_attrs, flags=re.IGNORECASE)
            or label in {"next", ">", "»", "التالي"}
        ):
            href_match = re.search(r"href=[\"']([^\"']+)[\"']", anchor_attrs, flags=re.IGNORECASE)
            if href_match:
                return urllib.parse.urljoin(base_url, html.unescape(href_match.group(1)))
    return ""


def _fetch_linked_official_pdfs(
    html_text: str,
    base_url: str,
    *,
    raw_dir: Path,
    stem: str,
    timeout_seconds: float,
) -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []
    for index, url in enumerate(_official_pdf_links_from_html(html_text, base_url), start=1):
        response = _urlopen_fetch(url, timeout_seconds)
        sha = _sha256(response.body)
        raw_path = raw_dir / f"{stem}_pdf_{index}.pdf"
        raw_path.write_bytes(response.body)
        artifacts.append(
            {
                "url": response.final_url or url,
                "sha256": sha,
                "path": str(raw_path).replace("\\", "/"),
                "content_type": response.content_type,
            }
        )
    return artifacts


def _official_pdf_links_from_html(html_text: str, base_url: str) -> list[str]:
    links: list[str] = []
    for href in re.findall(r"href=[\"']([^\"']+\.pdf(?:\?[^\"']*)?)[\"']", html_text, flags=re.IGNORECASE):
        absolute = urllib.parse.urljoin(base_url, html.unescape(href))
        parsed_base = urllib.parse.urlparse(base_url)
        parsed = urllib.parse.urlparse(absolute)
        if parsed.netloc.lower().lstrip("www.") != parsed_base.netloc.lower().lstrip("www."):
            continue
        if absolute not in links:
            links.append(absolute)
    return links


def _fra_detail_fields_from_html(html_text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for label, value in _label_value_pairs_from_html(html_text):
        key = _fra_field_key(label)
        if key and value and key not in fields:
            fields[key] = value
    if "official_website" not in fields:
        match = re.search(r"https?://[^\"'<>\s]+", html_text)
        if match:
            fields["official_website"] = match.group(0).rstrip(").,;")
    if "source_last_modified" not in fields:
        last_modified = _source_last_modified_from_html(html_text)
        if last_modified:
            fields["source_last_modified"] = last_modified
    return fields


def _label_value_pairs_from_html(html_text: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for row_html in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", html_text):
        cells = re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", row_html)
        if len(cells) >= 2:
            pairs.append((_strip_tags(cells[0]), _strip_tags(cells[1])))
    pairs.extend(
        (_strip_tags(label), _strip_tags(value))
        for label, value in re.findall(
            r"(?is)<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>",
            html_text,
        )
    )
    return pairs


def _fra_field_key(label: str) -> str:
    normalized = re.sub(r"\s+", " ", label.strip().lower())
    if any(token in normalized for token in ("english name", "name in english", "الاسم باللغة الإنجليزية")):
        return "name_en"
    if any(token in normalized for token in ("arabic name", "اسم الشركة", "اسم الشركه", "الاسم باللغة العربية")):
        return "name_ar"
    if any(token in normalized for token in ("license number", "licence number", "رقم الترخيص")):
        return "license_id"
    if any(token in normalized for token in ("license date", "licence date", "تاريخ الترخيص")):
        return "license_date"
    if any(token in normalized for token in ("licensed activity", "activity", "النشاط")):
        return "licensed_activity"
    if any(token in normalized for token in ("website", "web site", "الموقع")):
        return "official_website"
    return ""


def _strip_tags(value: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _source_last_modified_from_html(html_text: str) -> str:
    text = _strip_tags(html_text)
    match = re.search(
        r"(?:last\s+modified|last\s+updated|updated)\s*:?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        text,
        flags=re.IGNORECASE,
    )
    return match.group(1) if match else ""


def _merge_regulator_rows(
    existing_rows: list[dict[str, object]],
    regulator_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows = list(existing_rows)
    for regulator_row in regulator_rows:
        match_index, score = _best_registry_row_match(regulator_row, rows)
        regulator_row["duplicate_score"] = f"{score:.2f}"
        if match_index is None:
            rows.append(regulator_row)
            continue
        merged = dict(rows[match_index])
        for key, value in regulator_row.items():
            if value not in ("", None):
                if key == "source_url":
                    merged[key] = _combine_unique_text(str(merged.get(key) or ""), str(value))
                else:
                    merged[key] = value
        merged["institution_id"] = rows[match_index]["institution_id"]
        rows[match_index] = merged
    return rows


def _combine_unique_text(left: str, right: str, *, separator: str = " | ") -> str:
    values = []
    for value in [left, right]:
        for part in value.split(separator):
            normalized = part.strip()
            if normalized and normalized not in values:
                values.append(normalized)
    return separator.join(values)


def _best_registry_row_match(
    candidate: Mapping[str, object],
    rows: list[dict[str, object]],
) -> tuple[int | None, float]:
    candidate_name = str(candidate.get("name_en") or candidate.get("canonical_name") or "")
    best_index: int | None = None
    best_score = 0.0
    for index, row in enumerate(rows):
        if str(row.get("regulator")) != str(candidate.get("regulator")):
            continue
        score = _name_similarity(candidate_name, str(row.get("name_en") or row.get("canonical_name") or ""))
        if score > best_score:
            best_score = score
            best_index = index
    if best_score >= 0.70:
        return best_index, best_score
    return None, 0.0


def _name_similarity(first: str, second: str) -> float:
    left = set(_normalize_name(first).split())
    right = set(_normalize_name(second).split())
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _finalize_registry_identity_row(row: dict[str, object]) -> dict[str, object]:
    finalized = {field: row.get(field, "") for field in _REGISTRY_IDENTITY_FIELDS}
    website = _normalize_website_url(str(finalized.get("official_website", "")))
    finalized["official_website"] = website
    confidence = _float_or_default(finalized.get("official_website_confidence"), 0.0)
    ready = bool(website and confidence >= 0.80)
    finalized["official_website_confidence"] = f"{confidence:.2f}"
    finalized["ready_for_product_crawl"] = "true" if ready else "false"
    if not ready and not str(finalized.get("gap_reason", "")).strip():
        finalized["gap_reason"] = (
            "official website or reviewed official-source candidate required before product crawl"
        )
    return finalized


def _fra_sector_for_key(key: str) -> InstitutionSector:
    normalized = key.strip().lower().replace("-", "_").replace(" ", "_")
    mapping = {
        "capital_market": InstitutionSector.CAPITAL_MARKET,
        "insurance": InstitutionSector.INSURANCE,
        "finance": InstitutionSector.NON_BANK_FINANCE,
        "fintech": InstitutionSector.FINTECH,
    }
    return mapping.get(normalized, InstitutionSector.NON_BANK_FINANCE)


def _sha256(body: bytes) -> str:
    return "sha256:" + hashlib.sha256(body).hexdigest()


def stable_like_registry_id(
    name: str,
    regulator: InstitutionRegulator,
    sector: InstitutionSector,
) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    normalized = re.sub(r"-+", "-", normalized)
    return f"{regulator.value}-{sector.value}-{normalized}"


def run_legacy_sector_scrape(
    *,
    old_scraping_dir: Path,
    artifact_root: Path,
    run_date: date,
    seed_sites_file: Path | None,
    timeout_seconds: float,
    delay_seconds: float,
    max_targets: int,
    max_pages_per_target: int,
    sectors: List[str] | None,
) -> int:
    """Scrape reviewed official-site targets from the old sector workbooks.

    Every old row gets a status ledger row. Rows without a reviewed official
    website candidate are retained as explicit discovery gaps instead of being
    guessed from the institution name.
    """
    legacy_registry = _load_legacy_old_scraping_registry(old_scraping_dir)
    requested_sectors = _legacy_sector_filter(sectors)
    target_records = [
        record
        for record in legacy_registry.records()
        if requested_sectors is None or record.sector in requested_sectors
    ]
    if max_targets > 0:
        target_records = target_records[:max_targets]

    seed_sites = _load_seed_site_candidates(seed_sites_file)
    bank_directory_sites = _bank_directory_site_candidates(
        target_records,
        timeout_seconds=timeout_seconds,
    )
    registry = InstitutionRegistry([_reset_for_pilot(record) for record in target_records])
    fetcher = PublicArtifactFetcher(
        lambda url: _urlopen_fetch(url, timeout_seconds),
        LocalArtifactStore(artifact_root),
    )
    runner = OfficialSiteDiscoveryRunner()
    extractor = OperationExtractor()
    mapper = AaoifiMappingGenerator()
    rows = []
    for index, record in enumerate(target_records, start=1):
        runtime_record = registry.get(record.institution_id)
        candidates = _legacy_discovery_candidates_for_record(
            record,
            seed_sites=seed_sites,
            bank_directory_sites=bank_directory_sites,
        )
        if index > 1 and candidates:
            time.sleep(max(delay_seconds, 0.0))
        discovery = runner.run(runtime_record, candidates, checked_at=run_date)
        registry = _copy_runtime_state(
            source=registry,
            target=registry.with_discovery_result(discovery),
        )
        updated = registry.get(record.institution_id)
        if not updated.official_website:
            rows.append(
                _legacy_scrape_result_row(
                    updated,
                    "",
                    updated.discovery_status.value,
                    updated.gap_reason,
                )
            )
            continue
        scrape = _scrape_official_site_pages(
            record=updated,
            official_website=updated.official_website,
            registry=registry,
            fetcher=fetcher,
            extractor=extractor,
            mapper=mapper,
            artifact_root=artifact_root,
            run_date=run_date,
            timeout_seconds=timeout_seconds,
            delay_seconds=delay_seconds,
            max_pages_per_target=max_pages_per_target,
        )
        registry = scrape["registry"]
        rows.append(
            _legacy_scrape_result_row(
                updated,
                updated.official_website,
                str(scrape["status"]),
                str(scrape["notes"]),
                pages_fetched=int(scrape["pages_fetched"]),
                operations_extracted=int(scrape["operations_extracted"]),
            )
        )

    output_dir = artifact_root / "legacy_sector_scrape" / run_date.isoformat()
    if requested_sectors:
        output_dir = output_dir / "-".join(sector.value for sector in sorted(requested_sectors, key=lambda item: item.value))
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "legacy_scrape_results.csv"
    _write_rows(
        results_path,
        [
            "institution_id",
            "name_en",
            "name_ar",
            "regulator",
            "sector",
            "registry_source",
            "official_website",
            "status",
            "pages_fetched",
            "operations_extracted",
            *SCRAPE_REVIEW_FIELDS,
            *SCRAPE_ENRICHMENT_FIELDS,
            "notes",
        ],
        _with_scrape_review_columns(rows, registry),
    )
    review_dir = artifact_root / "review" / f"legacy-sector-scrape-{run_date.isoformat()}"
    if requested_sectors:
        review_dir = review_dir / "-".join(
            sector.value for sector in sorted(requested_sectors, key=lambda item: item.value)
        )
    ScholarReviewCsvStore.export_candidates(
        review_dir / "machine_mapping_candidates.csv",
        registry.machine_mappings(),
    )
    assessment_rows_path = output_dir / "engine_assessment_rows.csv"
    EngineAssessmentCsvStore.export_assessments(assessment_rows_path, registry)
    scholar_review_paths = ScholarReviewListCsvStore.export_lists(output_dir, registry)
    chunk_ready_path = _write_chunk_ready_spans(output_dir / "chunk_ready_spans.jsonl", registry)
    guidance_path = _write_scholar_review_guidance(output_dir)
    status_counts: dict[str, int] = {}
    for row in rows:
        status = str(row["status"])
        status_counts[status] = status_counts.get(status, 0) + 1
    manifest = {
        "mode": "legacy_sector_scrape",
        "run_date": run_date.isoformat(),
        "old_scraping_dir": str(old_scraping_dir).replace("\\", "/"),
        "seed_sites_file": str(seed_sites_file).replace("\\", "/") if seed_sites_file else "",
        "candidate_count": len(target_records),
        "max_targets": max_targets,
        "max_pages_per_target": max_pages_per_target,
        "sectors": sorted({record.sector.value for record in target_records}),
        "status_counts": dict(sorted(status_counts.items())),
        "scraped_count": sum(
            1 for row in rows if row["status"] in {"extracted", "partial_extracted"}
        ),
        "gap_count": sum(
            1
            for row in rows
            if row["status"]
            in {
                InstitutionDiscoveryStatus.OFFICIAL_SITE_NOT_FOUND.value,
                InstitutionDiscoveryStatus.SITE_UNREACHABLE.value,
                InstitutionDiscoveryStatus.BLOCKED_BY_SECURITY.value,
                InstitutionDiscoveryStatus.REQUIRES_LOGIN.value,
                InstitutionDiscoveryStatus.DOCUMENT_NOT_PUBLIC.value,
                InstitutionDiscoveryStatus.INSUFFICIENT_PUBLIC_DATA.value,
                InstitutionDiscoveryStatus.MANUAL_REVIEW_REQUIRED.value,
                "blocked_by_robots",
                "access_check_failed",
            }
        ),
        "pages_fetched": sum(int(row.get("pages_fetched") or 0) for row in rows),
        "operations_extracted": sum(int(row.get("operations_extracted") or 0) for row in rows),
        "machine_mapping_count": len(registry.machine_mappings()),
        "engine_assessment_rows": str(assessment_rows_path).replace("\\", "/"),
        "chunk_ready_spans": str(chunk_ready_path).replace("\\", "/"),
        "scholar_review_list_bilingual": str(scholar_review_paths["bilingual"]).replace("\\", "/"),
        "scholar_review_list_en": str(scholar_review_paths["english"]).replace("\\", "/"),
        "scholar_review_list_ar": str(scholar_review_paths["arabic"]).replace("\\", "/"),
        "scholar_review_guidance": str(guidance_path).replace("\\", "/"),
        "review_candidates": str(review_dir / "machine_mapping_candidates.csv").replace("\\", "/"),
        "scope_boundary": (
            "Old workbook rows are included in the status ledger. Crawling only "
            "runs for reviewed or pre-existing official website candidates. Rows "
            "without confirmed public official sites remain explicit discovery gaps."
        ),
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print("=== L6 Legacy Sector Scrape ===")
    print(f"Old workbook rows selected: {len(target_records)}")
    print(f"Scraped: {manifest['scraped_count']}")
    print(f"Gaps/blocked: {manifest['gap_count']}")
    print(f"Pages fetched: {manifest['pages_fetched']}")
    print(f"Operations extracted: {manifest['operations_extracted']}")
    print(f"Results: {results_path}")
    print(f"Engine assessment rows: {assessment_rows_path}")
    print(f"Scholar review bilingual list: {scholar_review_paths['bilingual']}")
    print(f"Manifest: {manifest_path}")
    return 0


def run_mixed_mini_pilot(
    *,
    baseline_registry: InstitutionRegistry,
    old_scraping_dir: Path,
    artifact_root: Path,
    run_date: date,
    timeout_seconds: float,
    delay_seconds: float,
    max_pages_per_target: int,
) -> int:
    """Run a bounded mixed pilot without wiring institution facts into runtime answers."""
    official_records = _first_distinct_records(baseline_registry.records(), limit=3)
    legacy_records = _first_distinct_records(
        _load_legacy_old_scraping_registry(old_scraping_dir).records(),
        limit=3,
        exclude_ids={record.institution_id for record in official_records},
    )
    selected: List[InstitutionRegistryRecord] = []
    seen: set[str] = set()
    for record in [*official_records, *legacy_records]:
        if record.institution_id in seen:
            continue
        selected.append(_reset_for_pilot(record))
        seen.add(record.institution_id)

    hard_case = next(
        (
            _reset_for_pilot(record)
            for record in baseline_registry.records()
            if record.institution_id not in seen
        ),
        None,
    )
    if hard_case:
        selected.append(hard_case)
        seen.add(hard_case.institution_id)

    registry = InstitutionRegistry(selected)
    runner = OfficialSiteDiscoveryRunner()
    fetcher = PublicArtifactFetcher(
        lambda url: _fixture_fetch(url) if _is_mixed_mini_fixture_url(url) else _urlopen_fetch(url, timeout_seconds),
        LocalArtifactStore(artifact_root),
    )
    extractor = OperationExtractor()
    mapper = AaoifiMappingGenerator()
    rows: List[dict[str, object]] = []
    scrape_targets = selected[:-1] if hard_case else selected
    for index, record in enumerate(scrape_targets, start=1):
        if index > 1:
            time.sleep(max(delay_seconds, 0.0))
        official_website = f"https://mixed-mini.example/{record.institution_id}/murabaha"
        discovery = runner.run(
            registry.get(record.institution_id),
            [
                DiscoveryEvidenceCandidate(
                    url=official_website,
                    evidence_type=DiscoveryEvidenceType.MANUAL_REVIEW,
                    confidence=0.86,
                    status=InstitutionDiscoveryStatus.OFFICIAL_SITE_CONFIRMED,
                    notes="Mixed mini-pilot fixture official-site candidate.",
                )
            ],
            checked_at=run_date,
        )
        registry = _copy_runtime_state(
            source=registry,
            target=registry.with_discovery_result(discovery),
        )
        updated = registry.get(record.institution_id)
        scrape = _scrape_official_site_pages(
            record=updated,
            official_website=official_website,
            registry=registry,
            fetcher=fetcher,
            extractor=extractor,
            mapper=mapper,
            artifact_root=artifact_root,
            run_date=run_date,
            timeout_seconds=timeout_seconds,
            delay_seconds=delay_seconds,
            max_pages_per_target=max_pages_per_target,
            robots_checker=_mixed_mini_robots_check,
        )
        registry = scrape["registry"]
        rows.append(
            _legacy_scrape_result_row(
                updated,
                official_website,
                str(scrape["status"]),
                str(scrape["notes"]),
                pages_fetched=int(scrape["pages_fetched"]),
                operations_extracted=int(scrape["operations_extracted"]),
            )
        )

    if hard_case:
        gap = runner.run(registry.get(hard_case.institution_id), [], checked_at=run_date)
        registry = _copy_runtime_state(source=registry, target=registry.with_discovery_result(gap))
        updated = registry.get(hard_case.institution_id)
        rows.append(
            _legacy_scrape_result_row(
                updated,
                "",
                updated.discovery_status.value,
                updated.gap_reason,
            )
        )

    output_dir = artifact_root / "mixed_mini_pilot" / run_date.isoformat()
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "mixed_mini_pilot_results.csv"
    _write_rows(
        results_path,
        [
            "institution_id",
            "name_en",
            "name_ar",
            "regulator",
            "sector",
            "registry_source",
            "official_website",
            "status",
            "pages_fetched",
            "operations_extracted",
            *SCRAPE_REVIEW_FIELDS,
            *SCRAPE_ENRICHMENT_FIELDS,
            "notes",
        ],
        _with_scrape_review_columns(rows, registry),
    )
    review_dir = artifact_root / "review" / f"mixed-mini-pilot-{run_date.isoformat()}"
    ScholarReviewCsvStore.export_candidates(
        review_dir / "machine_mapping_candidates.csv",
        registry.machine_mappings(),
    )
    assessment_rows_path = output_dir / "engine_assessment_rows.csv"
    EngineAssessmentCsvStore.export_assessments(assessment_rows_path, registry)
    scholar_review_paths = ScholarReviewListCsvStore.export_lists(output_dir, registry)
    chunk_ready_path = _write_chunk_ready_spans(output_dir / "chunk_ready_spans.jsonl", registry)
    guidance_path = _write_scholar_review_guidance(output_dir)
    manifest = {
        "mode": "mixed_mini_pilot",
        "run_date": run_date.isoformat(),
        "official_registry_count": len(official_records),
        "legacy_sector_count": len(legacy_records),
        "hard_case_count": 1 if hard_case else 0,
        "candidate_count": len(selected),
        "scraped_count": sum(1 for row in rows if row["status"] in {"extracted", "partial_extracted"}),
        "gap_count": sum(1 for row in rows if row["status"] == InstitutionDiscoveryStatus.OFFICIAL_SITE_NOT_FOUND.value),
        "operations_extracted": sum(int(row.get("operations_extracted") or 0) for row in rows),
        "engine_assessment_rows": str(assessment_rows_path).replace("\\", "/"),
        "chunk_ready_spans": str(chunk_ready_path).replace("\\", "/"),
        "scholar_review_list_bilingual": str(scholar_review_paths["bilingual"]).replace("\\", "/"),
        "scholar_review_guidance": str(guidance_path).replace("\\", "/"),
        "runtime_wiring": "not_enabled",
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return 0 if manifest["operations_extracted"] else 1


def run_fixture_pilot(
    *,
    baseline_registry: InstitutionRegistry,
    artifact_root: Path,
    pilot_id: str,
    run_date: date,
) -> InstitutionRegistry:
    selected = _select_pilot_records(baseline_registry.records())
    registry = InstitutionRegistry(selected)
    runner = OfficialSiteDiscoveryRunner()
    fetcher = PublicArtifactFetcher(_fixture_fetch, LocalArtifactStore(artifact_root))
    extractor = OperationExtractor()
    mapper = AaoifiMappingGenerator()

    for record in selected[:2]:
        fixture_url = f"https://example.invalid/{pilot_id}/{record.institution_id}/terms"
        discovery = runner.run(
            record,
            [
                DiscoveryEvidenceCandidate(
                    url=fixture_url,
                    evidence_type=DiscoveryEvidenceType.MANUAL_REVIEW,
                    confidence=0.90,
                    status=InstitutionDiscoveryStatus.OFFICIAL_SITE_CONFIRMED,
                    notes="Fixture-backed pilot evidence; not live regulator validation.",
                )
            ],
            checked_at=run_date,
        )
        registry = _copy_runtime_state(
            source=registry,
            target=registry.with_discovery_result(discovery),
        )
        updated = registry.get(record.institution_id)
        request = ArtifactFetchRequest(
            institution_id=updated.institution_id,
            url=fixture_url,
            authority_rank=PublicArtifactAuthorityRank.OFFICIAL_INSTITUTION,
            artifact_type=PublicArtifactType.TERMS,
            language="en",
        )
        artifact = fetcher.fetch(
            request,
            AccessControlDecision.evaluate(url=fixture_url, checked_at=run_date),
            retrieved_at=run_date,
        )
        registry.add_artifact(artifact)
        text = (artifact_root / artifact.text_path).read_text(encoding="utf-8")
        operation = extractor.extract(
            institution_id=updated.institution_id,
            artifact=artifact,
            text=text,
        )
        registry.add_operation(operation)
        registry.add_machine_mapping(mapper.generate(operation))

    hard_case = selected[2]
    gap = runner.run(hard_case, [], checked_at=run_date)
    registry = _copy_runtime_state(source=registry, target=registry.with_discovery_result(gap))

    first_mapping = registry.machine_mappings()[0]
    registry.add_scholar_review(
        ScholarReviewRecord(
            review_id=f"fixture-review-{pilot_id}",
            mapping_id=first_mapping.mapping_id,
            reviewer="fixture-only-reviewer",
            decision=ReviewCandidateStatus.SCHOLAR_ACCEPTED,
            aaoifi_references=["FAS-28", "SS-08"],
            rationale=(
                "Fixture acceptance only, used to verify the pilot gate and "
                "review-export mechanics. Not production scholar approval."
            ),
            accepted_gold_case=True,
        )
    )

    review_dir = artifact_root / "review" / pilot_id
    ScholarReviewCsvStore.export_candidates(
        review_dir / "machine_mapping_candidates.csv",
        registry.machine_mappings(),
    )
    _write_gold_cases(review_dir / "accepted_gold_cases.fixture.csv", registry)
    return registry


def write_manifest(
    *,
    baseline_registry: InstitutionRegistry,
    pilot_registry: InstitutionRegistry,
    artifact_root: Path,
    pilot_id: str,
    workbook_path: Path,
    run_date: date,
) -> Path:
    span_path = _write_chunk_ready_spans(
        artifact_root / "metadata" / pilot_id / "chunk_ready_spans.jsonl",
        pilot_registry,
    )
    manifest = {
        "pilot_id": pilot_id,
        "run_date": run_date.isoformat(),
        "mode": "fixture_pilot_no_live_crawl",
        "workbook": str(workbook_path).replace("\\", "/"),
        "baseline_record_count": len(baseline_registry.records()),
        "baseline_counts_by_sector": _counts_by_sector(baseline_registry.records()),
        "pilot_institutions": [record.to_dict() for record in pilot_registry.records()],
        "artifact_count": sum(
            len(pilot_registry.artifacts_for(record.institution_id))
            for record in pilot_registry.records()
        ),
        "operation_count": sum(
            len(pilot_registry.operations_for(record.institution_id))
            for record in pilot_registry.records()
        ),
        "machine_mapping_count": len(pilot_registry.machine_mappings()),
        "chunk_ready_spans": str(span_path).replace("\\", "/"),
        "accepted_fixture_gold_case_count": len(pilot_registry.accepted_gold_reviews()),
        "safety_boundary": (
            "No live crawl was performed. Full scraping remains blocked until "
            "live regulator revalidation, access checks, and real scholar review."
        ),
    }
    manifest_path = artifact_root / "metadata" / pilot_id / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest_path


def _select_pilot_records(records: List[InstitutionRegistryRecord]) -> List[InstitutionRegistryRecord]:
    if len(records) < 3:
        raise ValueError("baseline registry must contain at least three records")
    bank = _first_by_sector(records, InstitutionSector.BANK) or records[0]
    insurer = _first_by_sector(records, InstitutionSector.INSURANCE) or records[1]
    hard_case = (
        _first_by_sector(records, InstitutionSector.NON_BANK_FINANCE)
        or _first_distinct(records, {bank.institution_id, insurer.institution_id})
    )
    if hard_case is None:
        raise ValueError("could not select a distinct hard-case institution")
    return [
        _reset_for_pilot(bank),
        _reset_for_pilot(insurer),
        _reset_for_pilot(hard_case),
    ]


def _first_by_sector(
    records: Iterable[InstitutionRegistryRecord],
    sector: InstitutionSector,
) -> InstitutionRegistryRecord | None:
    for record in records:
        if record.sector == sector:
            return record
    return None


def _first_distinct(
    records: Iterable[InstitutionRegistryRecord],
    seen: set[str],
) -> InstitutionRegistryRecord | None:
    for record in records:
        if record.institution_id not in seen:
            return record
    return None


def _reset_for_pilot(record: InstitutionRegistryRecord) -> InstitutionRegistryRecord:
    return replace(
        record,
        discovery_status=InstitutionDiscoveryStatus.NOT_STARTED,
        official_website=None,
        official_website_confidence=0.0,
        attempt_count=0,
        last_checked_at=None,
        gap_reason="",
    )


def _copy_runtime_state(
    *,
    source: InstitutionRegistry,
    target: InstitutionRegistry,
) -> InstitutionRegistry:
    for record in source.records():
        for artifact in source.artifacts_for(record.institution_id):
            target.add_artifact(artifact)
        for operation in source.operations_for(record.institution_id):
            target.add_operation(operation)
    for mapping in source.machine_mappings():
        target.add_machine_mapping(mapping)
    for review in source.scholar_reviews():
        target.add_scholar_review(review)
    return target


def _fixture_fetch(url: str) -> FetchResponse:
    name = url.rstrip("/").split("/")[-2].replace("-", " ").title()
    body = (
        "<html><body>"
        f"<h1>{name} Murabaha Terms</h1>"
        + (
            "Murabaha deferred payment product. The bank purchases the asset, "
            "transfers ownership, charges fees, and late payment amounts go to charity. "
        )
        * 8
        + "This fixture is for pipeline validation only."
        + "</body></html>"
    ).encode("utf-8")
    return FetchResponse(status_code=200, content_type="text/html", body=body, final_url=url)


def _is_mixed_mini_fixture_url(url: str) -> bool:
    return urllib.parse.urlparse(url).netloc.lower() == "mixed-mini.example"


def _mixed_mini_robots_check(url: str, timeout_seconds: float) -> dict[str, object]:
    if _is_mixed_mini_fixture_url(url):
        return {"allowed": True, "reason": "mixed mini-pilot fixture URL; no live robots fetch"}
    return _check_robots(url, timeout_seconds)


def _urlopen_fetch(url: str, timeout_seconds: float) -> FetchResponse:
    request = urllib.request.Request(url, headers=_request_headers(), method="GET")
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        body = response.read(500_000)
        block_reason = _access_block_reason(body.decode("utf-8", errors="replace"))
        if block_reason:
            raise AccessBlockedError(block_reason, body)
        return FetchResponse(
            status_code=response.status,
            content_type=response.headers.get("content-type", "application/octet-stream"),
            body=body,
            final_url=response.geturl(),
        )


def _discover_bank_website_candidates(
    records: Iterable[InstitutionRegistryRecord],
    *,
    timeout_seconds: float,
) -> List[dict[str, object]]:
    bank_records = [record for record in records if record.sector == InstitutionSector.BANK]
    by_name = {_normalize_name(record.name_en): record for record in bank_records}
    discovered = _load_banksegypt_official_sites(timeout_seconds)
    candidates = []
    seen_ids = set()
    for name, website in discovered.items():
        record = by_name.get(_normalize_name(name))
        if record is None:
            record = _best_name_match(name, bank_records)
        if record is None or record.institution_id in seen_ids:
            continue
        candidates.append({"record": record, "official_website": website, "discovery_name": name})
        seen_ids.add(record.institution_id)
    return candidates


def _load_banksegypt_official_sites(timeout_seconds: float) -> dict[str, str]:
    listing_url = "https://banksegypt.com/banks"
    listing_access = _check_robots(listing_url, timeout_seconds)
    if not listing_access["allowed"]:
        return {}
    listing = _read_text_url(listing_url, timeout_seconds)
    pages = _banksegypt_profile_pages(listing)
    websites = {}
    for name, page_url in pages.items():
        try:
            profile_access = _check_robots(page_url, timeout_seconds)
            if not profile_access["allowed"]:
                continue
            detail = _read_text_url(page_url, timeout_seconds)
            website = _official_website_from_banksegypt_detail(detail)
            if website:
                websites[name] = website
        except Exception:
            continue
    return websites


def _banksegypt_profile_pages(listing_html: str) -> dict[str, str]:
    scripts = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        listing_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    for script in scripts:
        try:
            payload = json.loads(html.unescape(script))
        except json.JSONDecodeError:
            continue
        items = payload.get("itemListElement", []) if isinstance(payload, dict) else []
        pages = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            url = str(item.get("url", "")).strip()
            if name and url.startswith("https://banksegypt.com/banks/"):
                pages[name] = url
        if pages:
            return pages
    return {}


def _official_website_from_banksegypt_detail(detail_html: str) -> str:
    candidates = [
        html.unescape(match)
        for match in re.findall(r'https?://[^"\'<>\s]+', detail_html)
        if "banksegypt.com" not in match
        and "schema.org" not in match
        and "w3.org" not in match
        and "cdn.jsdelivr.net" not in match
        and "cloudflareinsights.com" not in match
    ]
    for candidate in candidates:
        clean = candidate.rstrip(").,;")
        if _looks_like_official_site(clean):
            return clean
    return ""


def _candidate_operation_links(base_url: str, html_text: str, *, limit: int) -> List[str]:
    if limit <= 0:
        return []
    base = urllib.parse.urlparse(base_url)
    seen = {base_url.rstrip("/")}
    scored: list[tuple[int, str]] = []
    for raw_href in re.findall(r'href=["\']([^"\']+)["\']', html_text, flags=re.IGNORECASE):
        href = html.unescape(raw_href).strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = _safe_url(urllib.parse.urljoin(base_url, href).split("#", 1)[0].rstrip("/"))
        parsed = urllib.parse.urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        if parsed.netloc.lower().lstrip("www.") != base.netloc.lower().lstrip("www."):
            continue
        if absolute in seen:
            continue
        score = _operation_link_score(absolute)
        if score <= 0:
            continue
        seen.add(absolute)
        scored.append((score, absolute))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [url for _, url in scored[:limit]]


def _safe_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            urllib.parse.quote(parsed.path, safe="/:%"),
            urllib.parse.quote(parsed.query, safe="=&%?/:"),
            "",
        )
    )


def _operation_link_score(url: str) -> int:
    text = urllib.parse.unquote(url).lower()
    score = 0
    weighted_terms = {
        "murabaha": 20,
        "ijara": 20,
        "ijarah": 20,
        "islamic": 15,
        "sharia": 15,
        "finance": 12,
        "financing": 12,
        "loan": 8,
        "loans": 8,
        "card": 5,
        "cards": 5,
        "deposit": 5,
        "account": 4,
        "sme": 4,
        "corporate": 4,
        "retail": 4,
        "tariff": 12,
        "fees": 12,
        "charges": 10,
        "terms": 8,
        "condition": 8,
        "conditions": 8,
        "contract": 15,
        "agreement": 10,
        "insurance": 15,
        "takaful": 20,
        "policy": 12,
        "premium": 8,
        "claim": 6,
        "claims": 6,
        "brokerage": 10,
        "trading": 8,
        "securities": 8,
        "portfolio": 8,
        "prospectus": 18,
        "sukuk": 20,
        "fund": 12,
        "funds": 12,
        "leasing": 16,
        "lease": 16,
        "mortgage": 16,
        "factoring": 16,
        "microfinance": 16,
        "consumer-finance": 16,
        "installment": 12,
        "instalment": 12,
    }
    for term, value in weighted_terms.items():
        if term in text:
            score += value
    if any(skip in text for skip in ("/about", "/career", "/contact", "/news", "/media")):
        score -= 20
    return score


def _operation_name_from_page(url: str, text: str, institution_name: str) -> str:
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if first_line and len(first_line) <= 120:
        return first_line
    path = urllib.parse.urlparse(url).path.strip("/")
    if path:
        slug = re.sub(r"[-_/]+", " ", path).strip()
        if slug:
            return slug.title()
    return f"{institution_name} public website"


def _looks_like_official_site(url: str) -> bool:
    host = urllib.parse.urlparse(url).netloc.lower()
    return bool(host) and not host.endswith("banksegypt.com")


def _read_text_url(url: str, timeout_seconds: float) -> str:
    request = urllib.request.Request(url, headers=_request_headers(), method="GET")
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return response.read(500_000).decode("utf-8", errors="replace")


def _normalize_name(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", value.lower())
    words = [
        word
        for word in text.split()
        if word not in {"egypt", "sae", "s", "a", "e", "the", "bank"}
    ]
    return " ".join(words)


def _best_name_match(
    name: str,
    records: Iterable[InstitutionRegistryRecord],
) -> InstitutionRegistryRecord | None:
    target = set(_normalize_name(name).split())
    if not target:
        return None
    best: tuple[float, InstitutionRegistryRecord] | None = None
    for record in records:
        candidate = set(_normalize_name(record.name_en).split())
        if not candidate:
            continue
        score = len(target & candidate) / len(target | candidate)
        if best is None or score > best[0]:
            best = (score, record)
    if best and best[0] >= 0.5:
        return best[1]
    return None


def _scrape_result_row(
    record: InstitutionRegistryRecord,
    url: str,
    status: str,
    notes: str,
    *,
    pages_fetched: int = 0,
    operations_extracted: int = 0,
) -> dict[str, object]:
    return {
        "institution_id": record.institution_id,
        "name_en": record.name_en,
        "official_website": url,
        "status": status,
        "pages_fetched": pages_fetched,
        "operations_extracted": operations_extracted,
        "notes": notes,
    }


def _counts_by_sector(records: Iterable[InstitutionRegistryRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        counts[record.sector.value] = counts.get(record.sector.value, 0) + 1
    return dict(sorted(counts.items()))


def _has_useful_evidence_text(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) < MIN_EVIDENCE_TEXT_LENGTH:
        return False
    alpha_count = sum(1 for char in normalized if char.isalpha())
    return alpha_count >= MIN_EVIDENCE_TEXT_LENGTH // 2


def _split_statuses(value: str) -> set[str] | None:
    statuses = {item.strip() for item in value.split(",") if item.strip()}
    return statuses or None


def _status_label(statuses: set[str] | None) -> str:
    if not statuses:
        return "all"
    return "-".join(re.sub(r"[^a-z0-9_]+", "-", status.lower()).strip("-") for status in sorted(statuses))


def _filter_candidates_by_previous_status(
    candidates: List[dict[str, object]],
    previous_results_path: Path,
    statuses: set[str],
) -> List[dict[str, object]]:
    if not previous_results_path.exists():
        return candidates
    with previous_results_path.open(newline="", encoding="utf-8") as handle:
        previous_rows = {
            row["institution_id"]: row
            for row in csv.DictReader(handle)
            if row.get("status") in statuses
        }
    return [
        candidate
        for candidate in candidates
        if candidate["record"].institution_id in previous_rows
    ]


def _load_legacy_old_scraping_registry(old_scraping_dir: Path) -> InstitutionRegistry:
    expected = [
        ("Banks_old.xlsx", "01_CBE_Banks"),
        ("Capital_Market_old.xlsx", "02_Capital_Market"),
        ("Insurance_old.xlsx", "03_Insurance"),
        ("Non_Categorized_old.xlsx", "04_NonBank_Financial"),
    ]
    records: List[InstitutionRegistryRecord] = []
    seen_ids: set[str] = set()
    for workbook_name, _sheet_name in expected:
        workbook_path = old_scraping_dir / workbook_name
        if not workbook_path.exists():
            continue
        registry = WorkbookRegistryLoader(baseline_input_name=workbook_name).load_xlsx(workbook_path)
        for record in registry.records():
            if record.institution_id in seen_ids:
                continue
            records.append(record)
            seen_ids.add(record.institution_id)
    return InstitutionRegistry(records)


def _missing_mixed_pilot_inputs(*, workbook_path: Path, old_scraping_dir: Path) -> List[str]:
    missing: List[str] = []
    if not workbook_path.exists():
        missing.append(f"workbook not found: {workbook_path}")
    if not old_scraping_dir.exists():
        missing.append(f"old scraping directory not found: {old_scraping_dir}")
        return missing
    expected_workbooks = [
        "Banks_old.xlsx",
        "Capital_Market_old.xlsx",
        "Insurance_old.xlsx",
        "Non_Categorized_old.xlsx",
    ]
    if not any((old_scraping_dir / name).exists() for name in expected_workbooks):
        missing.append(
            "old scraping directory contains none of: "
            + ", ".join(expected_workbooks)
            + f" ({old_scraping_dir})"
        )
    return missing


def _first_distinct_records(
    records: Iterable[InstitutionRegistryRecord],
    *,
    limit: int,
    exclude_ids: set[str] | None = None,
) -> List[InstitutionRegistryRecord]:
    selected: List[InstitutionRegistryRecord] = []
    seen = set(exclude_ids or set())
    for record in records:
        if record.institution_id in seen:
            continue
        selected.append(record)
        seen.add(record.institution_id)
        if len(selected) >= limit:
            break
    return selected


def _legacy_sector_filter(sectors: List[str] | None) -> set[InstitutionSector] | None:
    if not sectors:
        return None
    selected: set[InstitutionSector] = set()
    for sector in sectors:
        normalized = sector.strip().lower().replace("-", "_").replace(" ", "_")
        if not normalized:
            continue
        selected.add(InstitutionSector(normalized))
    return selected


def _load_seed_site_candidates(seed_sites_file: Path | None) -> dict[str, dict[str, dict[str, object]]]:
    seeds: dict[str, dict[str, dict[str, object]]] = {"by_id": {}, "by_name": {}}
    if seed_sites_file is None or not seed_sites_file.exists():
        return seeds
    with seed_sites_file.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            website = _normalize_website_url(row.get("official_website", ""))
            if not website:
                continue
            payload: dict[str, object] = {
                "official_website": website,
                "confidence": _float_or_default(row.get("confidence"), 0.86),
                "source_url": row.get("source_url", ""),
                "notes": row.get("notes", ""),
            }
            institution_id = str(row.get("institution_id", "")).strip()
            name_key = _normalize_name(str(row.get("name_en", "")).strip())
            if institution_id:
                seeds["by_id"][institution_id] = payload
            if name_key:
                seeds["by_name"][name_key] = payload
    return seeds


def _bank_directory_site_candidates(
    records: List[InstitutionRegistryRecord],
    *,
    timeout_seconds: float,
) -> dict[str, str]:
    if not any(record.sector == InstitutionSector.BANK for record in records):
        return {}
    try:
        candidates = _discover_bank_website_candidates(records, timeout_seconds=timeout_seconds)
    except Exception:
        return {}
    return {
        candidate["record"].institution_id: str(candidate["official_website"])
        for candidate in candidates
    }


def _legacy_discovery_candidates_for_record(
    record: InstitutionRegistryRecord,
    *,
    seed_sites: dict[str, dict[str, dict[str, object]]],
    bank_directory_sites: dict[str, str],
) -> List[DiscoveryEvidenceCandidate]:
    candidates: List[DiscoveryEvidenceCandidate] = []
    if record.official_website:
        candidates.append(
            DiscoveryEvidenceCandidate(
                url=record.official_website,
                evidence_type=DiscoveryEvidenceType.OFFICIAL_WEBSITE,
                confidence=max(record.official_website_confidence, 0.80),
                status=InstitutionDiscoveryStatus.OFFICIAL_SITE_CONFIRMED,
                notes="Official website was supplied in the source workbook.",
            )
        )
    seed = seed_sites["by_id"].get(record.institution_id) or seed_sites["by_name"].get(
        _normalize_name(record.name_en)
    )
    if seed:
        source_url = str(seed.get("source_url", "")).strip()
        notes = "Reviewed seed-site candidate."
        if source_url:
            notes = f"{notes} Source: {source_url}."
        if seed.get("notes"):
            notes = f"{notes} {seed['notes']}"
        candidates.append(
            DiscoveryEvidenceCandidate(
                url=str(seed["official_website"]),
                evidence_type=DiscoveryEvidenceType.MANUAL_REVIEW,
                confidence=float(seed["confidence"]),
                status=InstitutionDiscoveryStatus.OFFICIAL_SITE_CONFIRMED,
                notes=notes,
            )
        )
    directory_site = bank_directory_sites.get(record.institution_id)
    if directory_site:
        candidates.append(
            DiscoveryEvidenceCandidate(
                url=directory_site,
                evidence_type=DiscoveryEvidenceType.SEARCH_RESULT,
                confidence=0.72,
                status=InstitutionDiscoveryStatus.OFFICIAL_SITE_CONFIRMED,
                notes=(
                    "Candidate official website discovered from banksegypt.com "
                    "and accepted only as an official-site crawl target."
                ),
            )
        )
    return candidates


def _scrape_official_site_pages(
    *,
    record: InstitutionRegistryRecord,
    official_website: str,
    registry: InstitutionRegistry,
    fetcher: PublicArtifactFetcher,
    extractor: OperationExtractor,
    mapper: AaoifiMappingGenerator,
    artifact_root: Path,
    run_date: date,
    timeout_seconds: float,
    delay_seconds: float,
    max_pages_per_target: int,
    robots_checker=None,
) -> dict[str, object]:
    check_robots = robots_checker or _check_robots
    page_urls = [official_website]
    fetched_pages = 0
    extracted_operations = 0
    notes: List[str] = []
    try:
        page_index = 0
        while page_index < len(page_urls) and fetched_pages < max_pages_per_target:
            page_url = page_urls[page_index]
            page_index += 1
            if fetched_pages > 0:
                time.sleep(max(delay_seconds, 0.0))
            page_robots = check_robots(page_url, timeout_seconds)
            if not page_robots["allowed"]:
                notes.append(f"{page_url}: {page_robots['reason']}")
                continue
            request = ArtifactFetchRequest(
                institution_id=record.institution_id,
                url=page_url,
                authority_rank=PublicArtifactAuthorityRank.OFFICIAL_INSTITUTION,
                artifact_type=_artifact_type_from_url(page_url),
                language="unknown",
            )
            artifact = fetcher.fetch(
                request,
                AccessControlDecision.evaluate(url=page_url, checked_at=run_date),
                retrieved_at=run_date,
            )
            fetched_pages += 1
            registry.add_artifact(artifact)
            if artifact.raw_path:
                raw_html = (artifact_root / artifact.raw_path).read_bytes().decode(
                    "utf-8",
                    errors="replace",
                )
                for discovered_url in _candidate_operation_links(
                    page_url,
                    raw_html,
                    limit=max_pages_per_target - len(page_urls),
                ):
                    if discovered_url not in page_urls:
                        page_urls.append(discovered_url)
            if artifact.artifact_class == ArtifactClass.BLOCKED_OR_UNUSABLE:
                notes.append(f"{page_url}: blocked or unusable artifact skipped")
                continue
            if artifact.extraction_status == ExtractionStatus.EXTRACTED and artifact.text_path:
                text = (artifact_root / artifact.text_path).read_text(encoding="utf-8")
                if _has_useful_evidence_text(text):
                    operation = extractor.extract(
                        institution_id=record.institution_id,
                        artifact=artifact,
                        text=text,
                        operation_name=_operation_name_from_page(page_url, text, record.name_en),
                    )
                    registry.add_operation(operation)
                    registry.add_machine_mapping(mapper.generate(operation))
                    extracted_operations += 1
                else:
                    notes.append(
                        f"{page_url}: extracted text below useful evidence threshold ({len(text.strip())} chars)"
                    )
            else:
                notes.append(f"{page_url}: {artifact.extraction_status.value}")
        status = "extracted" if extracted_operations else "insufficient_text"
    except Exception as exc:
        status = "partial_extracted" if extracted_operations else "failed"
        notes.append(str(exc))
    return {
        "registry": registry,
        "status": status,
        "pages_fetched": fetched_pages,
        "operations_extracted": extracted_operations,
        "notes": "; ".join(notes)
        or f"Fetched {fetched_pages} page(s); extracted {extracted_operations} operation(s).",
    }


def _legacy_scrape_result_row(
    record: InstitutionRegistryRecord,
    url: str,
    status: str,
    notes: str,
    *,
    pages_fetched: int = 0,
    operations_extracted: int = 0,
) -> dict[str, object]:
    return {
        "institution_id": record.institution_id,
        "name_en": record.name_en,
        "name_ar": record.name_ar or "",
        "regulator": record.regulator.value,
        "sector": record.sector.value,
        "registry_source": record.registry_source,
        "official_website": url,
        "status": status,
        "pages_fetched": pages_fetched,
        "operations_extracted": operations_extracted,
        "notes": notes,
    }


def _with_scrape_review_columns(
    rows: Iterable[Mapping[str, object]],
    registry: InstitutionRegistry,
) -> List[dict[str, object]]:
    mappings_by_operation = {
        mapping.operation_id: mapping for mapping in registry.machine_mappings()
    }
    assessments_by_operation = {
        str(row["operation_id"]): row for row in EngineAssessmentCsvStore.rows(registry)
    }
    enriched: List[dict[str, object]] = []
    for row in rows:
        payload = dict(row)
        institution_id = str(payload["institution_id"])
        operations = registry.operations_for(institution_id)
        review_parts: List[str] = []
        reference_labels: List[str] = []
        for operation in operations:
            mapping = mappings_by_operation.get(operation.operation_id)
            if not mapping:
                review_parts.append(
                    f"{operation.operation_name}: operation extracted without Mushir mapping."
                )
                continue
            review_parts.append(
                f"{operation.operation_name}: {mapping.status.value} - {mapping.rationale}"
            )
            reference_labels.extend(
                _standard_reference_label(standard)
                for standard in mapping.candidate_standards
            )
        first_operation = operations[0] if operations else None
        assessment = (
            assessments_by_operation.get(first_operation.operation_id)
            if first_operation
            else {}
        )
        for field in SCRAPE_ENRICHMENT_FIELDS:
            payload[field] = assessment.get(field, "")
        if not first_operation:
            payload["runtime_eligible"] = "false"
        payload["mushir_engine_sharia_aaoifi_review"] = (
            " || ".join(review_parts)
            if review_parts
            else "No operation extracted for Mushir review."
        )
        payload["aaoifi_standard_reference_file_and_title"] = " | ".join(
            dict.fromkeys(reference_labels)
        )
        payload["human_scholar_supervision_review"] = ""
        enriched.append(payload)
    return enriched


def _write_chunk_ready_spans(path: Path, registry: InstitutionRegistry) -> Path:
    mappings_by_operation = {
        mapping.operation_id: mapping for mapping in registry.machine_mappings()
    }
    lines: List[str] = []
    for record in registry.records():
        artifacts = {
            artifact.artifact_id: artifact
            for artifact in registry.artifacts_for(record.institution_id)
        }
        for operation in registry.operations_for(record.institution_id):
            mapping = mappings_by_operation.get(operation.operation_id)
            for artifact_id in operation.artifact_ids:
                artifact = artifacts.get(artifact_id)
                lines.append(
                    json.dumps(
                        {
                            "span_id": _chunk_span_id(operation.operation_id, artifact_id),
                            "institution_id": record.institution_id,
                            "institution_name": record.name_en,
                            "regulator": record.regulator.value,
                            "sector": record.sector.value,
                            "artifact_id": artifact_id,
                            "artifact_url": artifact.url if artifact else "",
                            "artifact_class": operation.artifact_class.value,
                            "artifact_path": artifact.text_path if artifact else "",
                            "operation_id": operation.operation_id,
                            "operation_name": operation.operation_name,
                            "operation_family": operation.operation_family.value,
                            "normalized_operation": operation.normalized_operation,
                            "detected_language": operation.detected_language,
                            "evidence_snippet": operation.evidence_snippet,
                            "matched_aliases": operation.matched_aliases,
                            "confidence": operation.confidence,
                            "mapping_id": mapping.mapping_id if mapping else "",
                            "mapping_status": mapping.status.value if mapping else "",
                            "candidate_standards": mapping.candidate_standards if mapping else [],
                            "promotion_stage": operation.promotion_stage.value,
                            "runtime_eligible": operation.runtime_eligible,
                            "needs_review_reason": operation.needs_review_reason,
                            "extractor_version": operation.extractor_version,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return path


def _chunk_span_id(operation_id: str, artifact_id: str) -> str:
    digest = hashlib.sha256(f"{operation_id}|{artifact_id}".encode("utf-8")).hexdigest()[:12]
    return f"span-{digest}"


def _standard_reference_label(standard: str) -> str:
    cleaned = standard.strip()
    if not cleaned:
        return ""
    title = AAOIFI_STANDARD_TITLES.get(cleaned)
    if title:
        return f"{cleaned} - {title}"
    return f"{cleaned} - title requires scholar/catalog confirmation"


def _write_scholar_review_guidance(output_dir: Path) -> Path:
    path = output_dir / "SCHOLAR_REVIEW_GUIDANCE.md"
    path.write_text(
        "\n".join(
            [
                "# Scholar Review Guidance",
                "",
                "Use review_item_number and operation_id to match rows across the bilingual, English, Arabic, and scrape-result CSV files.",
                "",
                "For each operation, review the Mushir engine status, rationale, evidence fields, and AAOIFI reference candidates against the cited public artifact before accepting or correcting the result.",
                "",
                "Fill human_scholar_supervision_review or human_scholar_review with one of: scholar_accepted, scholar_rejected, needs_more_evidence, or corrected_mapping.",
                "",
                "When correcting, include the AAOIFI standard file number and title, the relevant section/page if available, and a short note explaining the correction so the row can become future model/evaluation feedback.",
                "",
                "Leave rows as needs_more_evidence when the public source does not show enough contract, operation, or service detail to judge Sharia/AAOIFI alignment.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _artifact_type_from_url(url: str) -> PublicArtifactType:
    text = urllib.parse.unquote(url).lower()
    if any(term in text for term in ("tariff", "fees", "charges")):
        return PublicArtifactType.TARIFF
    if any(term in text for term in ("terms", "conditions")):
        return PublicArtifactType.TERMS
    if "contract" in text or "agreement" in text:
        return PublicArtifactType.CONTRACT
    if "prospectus" in text:
        return PublicArtifactType.PROSPECTUS
    if "sukuk" in text:
        return PublicArtifactType.SUKUK_DOCUMENT
    if "fund" in text:
        return PublicArtifactType.FUND_DOCUMENT
    if any(term in text for term in ("policy", "insurance", "takaful")):
        return PublicArtifactType.POLICY_WORDING
    return PublicArtifactType.PRODUCT_PAGE


def _normalize_website_url(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if not text.startswith(("http://", "https://")):
        text = f"https://{text}"
    return text.rstrip("/")


def _float_or_default(value: object, default: float) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def _unique_registry_source_urls(records: Iterable[InstitutionRegistryRecord]) -> List[str]:
    urls = sorted({record.registry_source_url for record in records if record.registry_source_url})
    return [url for url in urls if url.startswith(("http://", "https://"))]


def _check_robots(url: str, timeout_seconds: float) -> dict[str, object]:
    parsed = urllib.parse.urlparse(url)
    robots_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    try:
        with urllib.request.urlopen(
            urllib.request.Request(robots_url, headers=_request_headers()),
            timeout=timeout_seconds,
        ) as response:
            parser.parse(response.read().decode("utf-8", errors="replace").splitlines())
        allowed = parser.can_fetch(_user_agent(), url)
        return {
            "allowed": allowed,
            "reason": "robots.txt allows URL" if allowed else "robots.txt disallows URL",
        }
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"allowed": True, "reason": "robots.txt not found"}
        return {"allowed": False, "reason": f"robots.txt HTTP {exc.code}"}
    except Exception as exc:  # pragma: no cover - network-specific details vary
        return {"allowed": False, "reason": f"robots.txt check failed: {exc}"}


def _probe_url(url: str, timeout_seconds: float) -> dict[str, object]:
    request = urllib.request.Request(url, headers=_request_headers(), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read(8192).decode("utf-8", errors="replace")
            block_reason = _access_block_reason(body)
            if block_reason:
                return {
                    "http_status": response.status,
                    "content_type": response.headers.get("content-type", ""),
                    "final_url": response.geturl(),
                    "error": block_reason,
                }
            return {
                "http_status": response.status,
                "content_type": response.headers.get("content-type", ""),
                "final_url": response.geturl(),
            }
    except urllib.error.HTTPError as exc:
        return {
            "http_status": exc.code,
            "content_type": exc.headers.get("content-type", "") if exc.headers else "",
            "final_url": exc.geturl(),
            "error": str(exc),
        }
    except Exception as exc:  # pragma: no cover - network-specific details vary
        return {"error": str(exc)}


def _access_block_reason(body: str) -> str:
    lowered = body.lower()
    if "request rejected" in lowered or "requested url was rejected" in lowered:
        return "access blocked by upstream security page"
    if "captcha" in lowered:
        return "access blocked by captcha"
    if "login required" in lowered or "log in to continue" in lowered or "please log in" in lowered:
        return "access blocked by login wall"
    if "paywall" in lowered or "subscription required" in lowered or "subscribe to access" in lowered:
        return "access blocked by paywall"
    if "access denied" in lowered:
        return "access denied"
    return ""


def _request_headers() -> Mapping[str, str]:
    return {
        "User-Agent": _user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }


def _user_agent() -> str:
    return "MushirResearchBot/0.1 (+public-source compliance research; contact: local)"


def _real_review_status(review_file: Path | None) -> dict[str, object]:
    if review_file is None:
        return {
            "review_workflow_ready": False,
            "has_real_accepted_review": False,
            "reason": "no real scholar-review import supplied",
        }
    if not review_file.exists():
        return {
            "review_workflow_ready": False,
            "has_real_accepted_review": False,
            "reason": "review file not found",
        }
    try:
        reviews = ScholarReviewCsvStore.import_reviews(review_file)
    except Exception as exc:
        return {
            "review_workflow_ready": False,
            "has_real_accepted_review": False,
            "reason": f"review import failed: {exc}",
        }
    real_accepted = [
        review
        for review in reviews
        if review.accepted_gold_case
        and review.decision == ReviewCandidateStatus.SCHOLAR_ACCEPTED
        and not review.reviewer.lower().startswith("fixture")
    ]
    return {
        "review_workflow_ready": True,
        "has_real_accepted_review": bool(real_accepted),
        "review_count": len(reviews),
        "accepted_gold_count": len(real_accepted),
    }


def _write_rows(path: Path, fields: List[str], rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_gold_cases(path: Path, registry: InstitutionRegistry) -> None:
    rows = ScholarReviewCsvStore.accepted_gold_cases(registry)
    fields = [
        "review_id",
        "mapping_id",
        "operation_id",
        "institution_id",
        "operation_name",
        "aaoifi_references",
        "rationale",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "aaoifi_references": "|".join(row["aaoifi_references"])})


if __name__ == "__main__":
    raise SystemExit(main())
