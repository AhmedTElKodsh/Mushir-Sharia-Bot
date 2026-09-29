#!/usr/bin/env python3
"""Build a seller/provider map from the latest immutable market crawl per stage."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import secrets
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACTS = ROOT / "data/runtime/artifacts/l6_scrape/installment_market"
DEFAULT_CANDIDATES = ROOT / "data/source_registry/egypt_market_candidates.csv"
STAGES = ("product_market", "online_vendor", "direct_store", "services", "real_estate")
ENTITY_FIELDS = (
    "entity", "roles", "categories", "stages", "discovery_sources",
    "page_evidence_claims", "access_limited_claims", "claim_not_found_claims",
    "named_financing_entities", "best_evidence_status", "evidence_urls",
)
RELATION_FIELDS = (
    "stage", "category", "seller", "sales_channel", "listed_entity", "listed_role",
    "financing_entity", "payment_model", "ordinary_payment_context", "commerce_mode", "claim_scope", "claim",
    "status", "availability_status", "source_url", "source_final_url", "captured_at",
    "evidence_snippet", "raw_sha256", "raw_path",
)
ACCESS_LIMITED = {"robots_disallowed", "robots_unavailable", "blocked_by_security", "fetch_error", "http_error", "page_error"}


def _key(name: str) -> str:
    return re.sub(r"[^\w]", "", name.casefold())


def _ordinary_payment_context(snippet: str) -> str:
    """Record incidental methods in the supporting passage, not as qualifying claims."""
    patterns = {
        "card": r"\b(?:visa|mastercard|master card|debit card|credit card)\b",
        "mobile_wallet": r"\b(?:mobile wallets?|e-wallets?|electronic wallets?)\b",
        "cash_on_delivery": r"\b(?:cash on delivery|payment on delivery|\bCOD\b)\b",
    }
    return " | ".join(name for name, pattern in patterns.items() if re.search(pattern, snippet, re.I))


def _latest_csv(date_root: Path, stage: str) -> Path | None:
    stage_root = date_root / stage
    if not stage_root.exists():
        return None
    for run_dir in sorted((p for p in stage_root.iterdir() if p.is_dir()), reverse=True):
        candidate = run_dir / "installment_evidence.csv"
        if candidate.exists() and (run_dir / "manifest.json").exists():
            return candidate
    legacy = stage_root / "installment_evidence.csv"
    return legacy if legacy.exists() else None


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def summarize(date_root: Path, candidates_csv: Path, output_dir: Path) -> dict:
    selected: dict[str, Path] = {}
    claims: list[dict[str, str]] = []
    for stage in STAGES:
        path = _latest_csv(date_root, stage)
        if path is not None:
            selected[stage] = path
            claims.extend(_read_csv(path))
    candidates = _read_csv(candidates_csv)
    if not claims:
        raise ValueError(f"no crawl CSVs found under {date_root}")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite summary: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    entities: dict[str, dict] = {}

    def entity_record(name: str) -> dict:
        key = _key(name)
        if key not in entities:
            entities[key] = {"entity": name, "roles": set(), "categories": set(), "stages": set(),
                             "discovery_sources": set(), "page_evidence_claims": 0,
                             "access_limited_claims": 0, "claim_not_found_claims": 0,
                             "named_financing_entities": set(), "evidence_urls": set()}
        return entities[key]

    for candidate in candidates:
        record = entity_record(candidate["entity"])
        record["roles"].add(candidate["role"])
        record["categories"].add(candidate["category"])
        record["discovery_sources"].add(candidate["discovery_source_url"])

    relationships: list[dict[str, str]] = []
    for claim in claims:
        entity = claim["entity"]
        record = entity_record(entity)
        record["roles"].add(claim["role"])
        record["categories"].add(claim["category"])
        record["stages"].add(claim["stage"])
        if claim.get("discovery_source_url"):
            record["discovery_sources"].add(claim["discovery_source_url"])
        status = claim["status"]
        if status == "verified_page_evidence":
            record["page_evidence_claims"] += 1
            record["evidence_urls"].add(claim["source_url"])
            if claim.get("financing_entity"):
                record["named_financing_entities"].update(x.strip() for x in claim["financing_entity"].split("|") if x.strip())
        elif status in ACCESS_LIMITED:
            record["access_limited_claims"] += 1
        elif status == "claim_not_found":
            record["claim_not_found_claims"] += 1

        stage, role = claim["stage"], claim["role"]
        if stage == "online_vendor":
            seller, channel = (entity if role in {"marketplace_seller", "retailer"} else ""), claim["vendor"]
        elif role in {"finance_provider", "bank", "marketplace", "auto_marketplace"}:
            seller, channel = "", entity
        else:
            seller, channel = entity, "direct_site"
        relationships.append({
            "stage": stage, "category": claim["category"], "seller": seller,
            "sales_channel": channel, "listed_entity": entity, "listed_role": role,
            "financing_entity": claim.get("financing_entity", ""),
            "payment_model": claim.get("payment_model", ""),
            "ordinary_payment_context": _ordinary_payment_context(claim.get("evidence_snippet", "")) if status == "verified_page_evidence" else "",
            "commerce_mode": claim.get("commerce_mode", ""),
            "claim_scope": claim.get("claim_scope", ""), "claim": claim["claim"],
            "status": status, "availability_status": claim.get("availability_status", ""),
            "source_url": claim["source_url"],
            "source_final_url": claim.get("source_final_url", ""),
            "captured_at": claim.get("captured_at", ""),
            "evidence_snippet": claim.get("evidence_snippet", ""),
            "raw_sha256": claim.get("raw_sha256", ""), "raw_path": claim.get("raw_path", ""),
        })

    entity_rows: list[dict[str, str]] = []
    for record in sorted(entities.values(), key=lambda r: r["entity"].casefold()):
        best = ("page_evidence" if record["page_evidence_claims"] else
                "access_limited" if record["access_limited_claims"] else
                "claim_not_found" if record["claim_not_found_claims"] else "lead_only")
        entity_rows.append({
            "entity": record["entity"],
            "roles": " | ".join(sorted(record["roles"])),
            "categories": " | ".join(sorted(record["categories"])),
            "stages": " | ".join(sorted(record["stages"])),
            "discovery_sources": " | ".join(sorted(record["discovery_sources"])),
            "page_evidence_claims": str(record["page_evidence_claims"]),
            "access_limited_claims": str(record["access_limited_claims"]),
            "claim_not_found_claims": str(record["claim_not_found_claims"]),
            "named_financing_entities": " | ".join(sorted(record["named_financing_entities"])),
            "best_evidence_status": best,
            "evidence_urls": " | ".join(sorted(record["evidence_urls"])),
        })

    entity_csv = output_dir / "market_entities.csv"
    relation_csv = output_dir / "payment_relationships.csv"
    _write_csv(entity_csv, ENTITY_FIELDS, entity_rows)
    _write_csv(relation_csv, RELATION_FIELDS, relationships)
    manifest = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "claim_count": len(claims),
        "candidate_lead_count": len(candidates),
        "distinct_entity_count": len(entity_rows),
        "entities_with_page_evidence": sum(r["best_evidence_status"] == "page_evidence" for r in entity_rows),
        "distinct_selling_entities_with_page_evidence": len({r["seller"] for r in relationships if r["seller"] and r["status"] == "verified_page_evidence"}),
        "candidate_only_entities": sum(r["best_evidence_status"] == "lead_only" for r in entity_rows),
        "status_counts": dict(sorted(Counter(r["status"] for r in relationships).items())),
        "input_stage_csvs": {stage: str(path) for stage, path in selected.items()},
        "entity_csv": str(entity_csv),
        "entity_csv_sha256": "sha256:" + hashlib.sha256(entity_csv.read_bytes()).hexdigest(),
        "relationship_csv": str(relation_csv),
        "relationship_csv_sha256": "sha256:" + hashlib.sha256(relation_csv.read_bytes()).hexdigest(),
        "scope_note": "A page match is evidence of words on that page, not current eligibility, seller-specific checkout, FRA status, or Sharia compliance. Lead-only entities require verification.",
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument("--artifacts-root", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    date.fromisoformat(args.today)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(3)
    output = args.output_dir or args.artifacts_root / args.today / "summary" / run_id
    print(json.dumps(summarize(args.artifacts_root / args.today, args.candidates, output), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
