"""Report AAOIFI Sharia Standards coverage from the governed source catalog."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

import yaml

DEFAULT_CATALOG = Path("data/source_registry/aaoifi-source-catalog.yaml")
DEFAULT_ACQUISITION_MANIFEST = Path("data/source_registry/aaoifi-sharia-acquisition-manifest.yaml")
DEFAULT_TARGET_SHARIA_STANDARD_COUNT = 60
TARGET_INVENTORY_SOURCES = [
    {
        "url": "https://aaoifi.com/announcement/aaoifi-makes-all-its-standards-accessible-on-its-website-on-a-complimentary-basis/?lang=en",
        "claim": "AAOIFI announced 59 Shari'ah standards in its complimentary-access standards notice.",
    },
    {
        "url": "https://aaoifi.com/announcement/aaoifi-officially-issues-shariah-standard-no-60-waqf/?lang=en",
        "claim": "AAOIFI later announced the English translation of Shari'ah Standard No. 60 on Waqf.",
    },
]


def load_catalog(path: Path) -> list[Mapping[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(payload.get("records") or [])


def load_acquisition_manifest(path: Path) -> Mapping[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def sharia_coverage_report(
    records: Iterable[Mapping[str, Any]],
    *,
    target_sharia_standard_count: int = DEFAULT_TARGET_SHARIA_STANDARD_COUNT,
    acquisition_manifest: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    rows = list(records)
    sharia_rows = [
        row for row in rows if str(row.get("source_family") or "").strip().lower() == "sharia_standard"
    ]
    standards = sorted({str(row.get("standard_number") or "").strip() for row in sharia_rows if row.get("standard_number")})
    by_language = Counter(str(row.get("language") or "unknown") for row in sharia_rows)
    by_currentness = Counter(str(row.get("currentness") or "unknown") for row in sharia_rows)
    by_review_status = Counter(str(row.get("review_status") or "unknown") for row in sharia_rows)
    languages_by_standard: dict[str, set[str]] = defaultdict(set)
    currentness_by_standard: dict[str, set[str]] = defaultdict(set)
    supersession_by_standard: dict[str, set[str]] = defaultdict(set)
    for row in sharia_rows:
        standard = str(row.get("standard_number") or "").strip()
        language = str(row.get("language") or "").strip()
        if standard and language:
            languages_by_standard[standard].add(language)
        if standard:
            currentness_by_standard[standard].add(str(row.get("currentness") or "unknown"))
            for replacement in row.get("superseded_by") or []:
                supersession_by_standard[standard].add(str(replacement))

    bilingual = sorted(
        standard for standard, languages in languages_by_standard.items() if {"ar", "en"}.issubset(languages)
    )
    missing_bilingual = sorted(set(standards) - set(bilingual))
    coverage_ratio = len(standards) / target_sharia_standard_count if target_sharia_standard_count else 0.0

    missing_standards = _missing_sharia_standards(standards, target_sharia_standard_count)
    blocked_sources = _blocked_sources_by_standard(acquisition_manifest)
    matrix = build_sharia_coverage_matrix(
        rows,
        target_sharia_standard_count=target_sharia_standard_count,
        acquisition_manifest=acquisition_manifest,
    )
    release_gate_fail_count = sum(1 for row in matrix if row["release_gate"] != "pass")
    release_gate = (
        "pass"
        if len(standards) >= target_sharia_standard_count
        and not missing_bilingual
        and release_gate_fail_count == 0
        else "fail"
    )

    return {
        "target_sharia_standard_count": target_sharia_standard_count,
        "target_inventory_sources": TARGET_INVENTORY_SOURCES,
        "target_inventory_notes": [
            "Target is source-tracked as at least SS-60 because AAOIFI has an official SS-60 Waqf announcement.",
            "The public complimentary-access announcement still states 59 Shari'ah standards; keep this mismatch visible until the official inventory page is reconciled.",
        ],
        "catalog_record_count": len(rows),
        "sharia_record_count": len(sharia_rows),
        "covered_sharia_standard_count": len(standards),
        "covered_sharia_standards": standards,
        "missing_sharia_standards": missing_standards,
        "missing_sharia_standard_count": len(missing_standards),
        "blocked_source_count": len(blocked_sources),
        "blocked_source_standards": sorted(blocked_sources),
        "blocked_source_details": [
            {
                "standard_number": standard,
                "status": details.get("status", "blocked"),
                "required_next_action": details.get("required_next_action", "Acquire governed source text."),
            }
            for standard, details in sorted(blocked_sources.items())
        ],
        "coverage_ratio": coverage_ratio,
        "language_counts": dict(sorted(by_language.items())),
        "currentness_counts": dict(sorted(by_currentness.items())),
        "review_status_counts": dict(sorted(by_review_status.items())),
        "superseded_sharia_standards": sorted(
            standard
            for standard, states in currentness_by_standard.items()
            if "superseded" in states
        ),
        "unverified_currentness_sharia_standards": sorted(
            standard
            for standard, states in currentness_by_standard.items()
            if "unverified" in states or "unknown" in states
        ),
        "supersession_map": {
            standard: sorted(replacements)
            for standard, replacements in sorted(supersession_by_standard.items())
        },
        "bilingual_sharia_standard_count": len(bilingual),
        "bilingual_sharia_standards": bilingual,
        "missing_bilingual_sharia_standards": missing_bilingual,
        "hard_sharia_ready": release_gate == "pass",
        "release_gate": release_gate,
        "release_gate_fail_count": release_gate_fail_count,
        "status": "complete" if len(standards) >= target_sharia_standard_count else "partial",
        "no_go_reasons": _no_go_reasons(
            covered=len(standards),
            target=target_sharia_standard_count,
            missing_standards=missing_standards,
            missing_bilingual=missing_bilingual,
            release_gate_fail_count=release_gate_fail_count,
        ),
    }


def build_sharia_coverage_matrix(
    records: Iterable[Mapping[str, Any]],
    *,
    target_sharia_standard_count: int = DEFAULT_TARGET_SHARIA_STANDARD_COUNT,
    acquisition_manifest: Mapping[str, Any] | None = None,
) -> list[Dict[str, Any]]:
    rows = [
        row for row in records if str(row.get("source_family") or "").strip().lower() == "sharia_standard"
    ]
    by_standard: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        standard = str(row.get("standard_number") or "").strip()
        if standard:
            by_standard[standard].append(row)

    blocked_sources = _blocked_sources_by_standard(acquisition_manifest)
    matrix: list[Dict[str, Any]] = []
    for standard in _target_sharia_standards(target_sharia_standard_count):
        standard_rows = by_standard.get(standard, [])
        blocked_source = blocked_sources.get(standard, {})
        languages = sorted({str(row.get("language") or "").strip() for row in standard_rows if row.get("language")})
        missing_languages = sorted({"ar", "en"} - set(languages))
        cataloged = bool(standard_rows)
        gate_reasons: list[str] = []
        if not cataloged:
            gate_reasons.append("No governed source catalog record is present.")
        if blocked_source:
            gate_reasons.append(
                "Source acquisition is blocked: "
                + str(blocked_source.get("required_next_action") or blocked_source.get("status") or "blocked")
            )
        if missing_languages:
            gate_reasons.append("Arabic/English source parity is incomplete: " + ", ".join(missing_languages))
        if cataloged:
            gate_reasons.append("Retrieval smoke and scholar-review gates are not yet recorded for this standard.")
        states = sorted({str(row.get("currentness")).strip() for row in standard_rows if row.get("currentness")}) or ["current"]
        superseded_by = sorted(
            {
                str(replacement)
                for row in standard_rows
                for replacement in (row.get("superseded_by") or [])
            }
        )
        if cataloged and any(state != "current" for state in states):
            gate_reasons.append("Currentness/supersession state blocks answer admissibility.")

        matrix.append(
            {
                "standard_number": standard,
                "cataloged": cataloged,
                "source_ids": sorted(str(row.get("source_id")) for row in standard_rows if row.get("source_id")),
                "languages_present": languages,
                "missing_languages": missing_languages,
                "catalog_record_count": len(standard_rows),
                "currentness_states": states,
                "superseded_by": superseded_by,
                "ingestion_status": "cataloged" if cataloged else "missing_source",
                "acquisition_status": (
                    str(blocked_source.get("status"))
                    if blocked_source
                    else ("acquired" if cataloged else "unknown_missing_source")
                ),
                "required_next_action": str(blocked_source.get("required_next_action") or ""),
                "metadata_validation_status": "catalog_governed" if cataloged else "blocked_no_source",
                "retrieval_smoke_status": "not_recorded",
                "representative_question_status": "not_seeded",
                "answerability_status": (
                    "source_present_pending_retrieval_smoke" if cataloged else "blocked_no_source"
                ),
                "scholar_review_status": "not_reviewed",
                "source_coverage_gate": (
                    "pass"
                    if cataloged and not missing_languages and states and all(state == "current" for state in states)
                    else "fail"
                ),
                "release_gate": "fail",
                "gate_reasons": gate_reasons,
            }
        )
    return matrix


def _target_sharia_standards(target: int) -> list[str]:
    return [f"SS-{number:02d}" for number in range(1, target + 1)]


def _missing_sharia_standards(covered_standards: Iterable[str], target: int) -> list[str]:
    return sorted(set(_target_sharia_standards(target)) - set(covered_standards))


def _blocked_sources_by_standard(acquisition_manifest: Mapping[str, Any] | None) -> dict[str, Mapping[str, Any]]:
    if not acquisition_manifest:
        return {}
    blocked: dict[str, Mapping[str, Any]] = {}
    for item in acquisition_manifest.get("blocked_sources") or []:
        standard = str(item.get("standard_number") or "").strip()
        if standard:
            blocked[standard] = item
    return blocked


def _no_go_reasons(
    *,
    covered: int,
    target: int,
    missing_standards: list[str],
    missing_bilingual: list[str],
    release_gate_fail_count: int,
) -> list[str]:
    reasons: list[str] = []
    if covered < target:
        reasons.append(f"Sharia standard coverage is partial: {covered}/{target} standards cataloged.")
    if missing_standards:
        reasons.append(
            "Missing governed Sharia standards: "
            + ", ".join(missing_standards[:15])
            + ("..." if len(missing_standards) > 15 else "")
        )
    if missing_bilingual:
        reasons.append(
            "Some cataloged Sharia standards are not bilingual: "
            + ", ".join(missing_bilingual[:10])
            + ("..." if len(missing_bilingual) > 10 else "")
        )
    if release_gate_fail_count:
        reasons.append(
            f"Hard-Sharia release gates are incomplete for {release_gate_fail_count}/{target} target standards."
        )
    return reasons


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--acquisition-manifest", type=Path, default=DEFAULT_ACQUISITION_MANIFEST)
    parser.add_argument("--target-sharia-standard-count", type=int, default=DEFAULT_TARGET_SHARIA_STANDARD_COUNT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--matrix-output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = sharia_coverage_report(
        load_catalog(args.catalog),
        target_sharia_standard_count=args.target_sharia_standard_count,
        acquisition_manifest=load_acquisition_manifest(args.acquisition_manifest),
    )
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    if args.matrix_output:
        matrix = build_sharia_coverage_matrix(
            load_catalog(args.catalog),
            target_sharia_standard_count=args.target_sharia_standard_count,
            acquisition_manifest=load_acquisition_manifest(args.acquisition_manifest),
        )
        args.matrix_output.parent.mkdir(parents=True, exist_ok=True)
        args.matrix_output.write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
