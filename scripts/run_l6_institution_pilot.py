#!/usr/bin/env python3
"""Run safe L6 Egypt institution evidence-corpus gates.

The default command is fixture-backed. Live modes only revalidate known
regulator/source URLs and refuse broad institution scraping unless human review
and safe official-site targets exist.
"""

from __future__ import annotations

import argparse
import csv
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
    ArtifactFetchRequest,
    CorpusPilotGate,
    CorpusPilotPlan,
    DiscoveryEvidenceCandidate,
    DiscoveryEvidenceType,
    FetchResponse,
    ExtractionStatus,
    InstitutionDiscoveryStatus,
    InstitutionRegistry,
    InstitutionRegistryRecord,
    InstitutionSector,
    LocalArtifactStore,
    OfficialSiteDiscoveryRunner,
    OperationExtractor,
    PublicArtifactAuthorityRank,
    PublicArtifactFetcher,
    PublicArtifactType,
    ReviewCandidateStatus,
    ScholarReviewCsvStore,
    ScholarReviewRecord,
    WorkbookRegistryLoader,
)


DEFAULT_WORKBOOK = (
    ".kiro/specs/sharia-compliance-chatbot/"
    "Egypt_Financial_Institutions_COMPLETE.xlsx"
)
DEFAULT_ARTIFACT_ROOT = "artifacts/l6_scrape"
MIN_EVIDENCE_TEXT_LENGTH = 500


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run safe L6 Egypt institution scrape gates."
    )
    parser.add_argument(
        "--mode",
        choices=["fixture-pilot", "live-regulator-revalidation", "full-scrape"],
        default="fixture-pilot",
    )
    parser.add_argument("--workbook", default=DEFAULT_WORKBOOK)
    parser.add_argument("--artifact-root", default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--pilot-id", default="l6-egypt-fi-pilot-local")
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    parser.add_argument("--max-targets", type=int, default=36)
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
        help="CSV of real scholar decisions. Required before full-scrape can proceed.",
    )
    args = parser.parse_args()

    run_date = date.fromisoformat(args.today)
    workbook_path = Path(args.workbook)
    artifact_root = Path(args.artifact_root)

    baseline_registry = WorkbookRegistryLoader().load_xlsx(workbook_path)
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
    if not review_status["review_workflow_ready"]:
        blocked_reasons.append(
            "scholar-review workflow is not ready"
        )
    if not review_status.get("has_real_accepted_review"):
        blocked_reasons.append(
            "full scrape requires a non-fixture accepted scholar-review file"
        )
    if bank_discovery_targets is None:
        bank_discovery_targets = (
            []
            if blocked_reasons
            else _discover_bank_website_candidates(
                baseline_registry.records(),
                timeout_seconds=20.0,
            )
        )
    if not official_targets and not bank_discovery_targets:
        blocked_reasons.append(
            "no official institution website URLs or discoverable bank website candidates to crawl"
        )
    manifest = {
        "mode": "full_scrape_gate",
        "run_date": run_date.isoformat(),
        "baseline_record_count": len(baseline_registry.records()),
        "official_target_count": len(official_targets),
        "bank_discovery_target_count": len(bank_discovery_targets),
        "review_file": str(review_file).replace("\\", "/") if review_file else "",
        "review_status": review_status,
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
    print("Full scrape gate passed. Live crawl adapter implementation can run next.")
    return 0


def run_live_bank_scrape(
    *,
    baseline_registry: InstitutionRegistry,
    artifact_root: Path,
    run_date: date,
    timeout_seconds: float,
    delay_seconds: float,
    max_targets: int,
    rerun_statuses: set[str] | None = None,
) -> int:
    """Scrape public home pages for discovered official bank website candidates."""
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
        request = ArtifactFetchRequest(
            institution_id=record.institution_id,
            url=url,
            authority_rank=PublicArtifactAuthorityRank.OFFICIAL_INSTITUTION,
            artifact_type=PublicArtifactType.PRODUCT_PAGE,
            language="unknown",
        )
        try:
            artifact = fetcher.fetch(
                request,
                AccessControlDecision.evaluate(url=url, checked_at=run_date),
                retrieved_at=run_date,
            )
            registry.add_artifact(artifact)
            if artifact.extraction_status == ExtractionStatus.EXTRACTED and artifact.text_path:
                text = (artifact_root / artifact.text_path).read_text(encoding="utf-8")
                if _has_useful_evidence_text(text):
                    operation = extractor.extract(
                        institution_id=record.institution_id,
                        artifact=artifact,
                        text=text,
                        operation_name=f"{record.name_en} public website",
                    )
                    registry.add_operation(operation)
                    registry.add_machine_mapping(mapper.generate(operation))
                    rows.append(_scrape_result_row(record, url, "extracted", artifact.notes))
                else:
                    rows.append(
                        _scrape_result_row(
                            record,
                            url,
                            "insufficient_text",
                            f"Extracted text below useful evidence threshold: {len(text.strip())} chars.",
                        )
                    )
            else:
                status = artifact.extraction_status.value
                notes = artifact.notes
                if artifact.text_path and artifact.extraction_status == ExtractionStatus.FAILED:
                    text = (artifact_root / artifact.text_path).read_text(encoding="utf-8")
                    if not text.strip():
                        status = "insufficient_text"
                        notes = "Fetched response produced empty extracted text."
                rows.append(_scrape_result_row(record, url, status, notes))
        except Exception as exc:
            rows.append(_scrape_result_row(record, url, "failed", str(exc)))

    output_dir = (
        artifact_root / "full_scrape_rerun" / run_date.isoformat() / run_label
        if rerun_statuses
        else artifact_root / "full_scrape" / run_date.isoformat()
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(
        output_dir / "bank_scrape_results.csv",
        ["institution_id", "name_en", "official_website", "status", "notes"],
        rows,
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
    manifest = {
        "mode": "full_scrape_bank_slice_rerun" if rerun_statuses else "full_scrape_bank_slice",
        "run_date": run_date.isoformat(),
        "rerun_statuses": sorted(rerun_statuses or []),
        "candidate_count": len(candidates),
        "scraped_count": sum(1 for row in rows if row["status"] == "extracted"),
        "failed_or_blocked_count": sum(1 for row in rows if row["status"] != "extracted"),
        "machine_mapping_count": len(registry.machine_mappings()),
        "review_candidates": str(review_dir / "machine_mapping_candidates.csv").replace("\\", "/"),
        "scope_boundary": (
            "Full scrape completed only for bank official-site candidates discoverable "
            "from public bank directory data. Non-bank sectors still require official "
            "website discovery before crawling."
        ),
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print("=== L6 Full Bank Scrape ===")
    print(f"Discovered bank candidates: {len(candidates)}")
    print(f"Scraped: {manifest['scraped_count']}")
    print(f"Failed or blocked: {manifest['failed_or_blocked_count']}")
    print(f"Machine mappings exported: {manifest['machine_mapping_count']}")
    print(f"Manifest: {manifest_path}")
    if rerun_statuses:
        return 0
    return 0 if manifest["scraped_count"] else 1


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
        "Murabaha deferred payment product. The bank purchases the asset, "
        "transfers ownership, charges fees, and late payment amounts go to charity. "
        "This fixture is for pipeline validation only."
        "</body></html>"
    ).encode("utf-8")
    return FetchResponse(status_code=200, content_type="text/html", body=body, final_url=url)


def _urlopen_fetch(url: str, timeout_seconds: float) -> FetchResponse:
    request = urllib.request.Request(url, headers=_request_headers(), method="GET")
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        body = response.read(500_000)
        block_reason = _access_block_reason(body.decode("utf-8", errors="replace"))
        if block_reason:
            raise RuntimeError(block_reason)
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
) -> dict[str, object]:
    return {
        "institution_id": record.institution_id,
        "name_en": record.name_en,
        "official_website": url,
        "status": status,
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
    if "request rejected" in lowered and "support id" in lowered:
        return "access blocked by upstream security page"
    if "captcha" in lowered:
        return "access blocked by captcha"
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
