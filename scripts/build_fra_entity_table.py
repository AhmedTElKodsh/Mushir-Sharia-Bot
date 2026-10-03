#!/usr/bin/env python3
"""Build the FRA-first consumer-finance entity table (offline; no network).

Inputs are licence-level FRA CSVs (newest first: the first row seen for a licence
wins), the evidenced brand-link table and the market discovery CSV.  Outputs:

- ``fra_consumer_finance_entities.csv``: one row per consumer-finance licence and
  per consumer-finance-provider registration, with sibling licences of the same
  company, former names, linked brands, websites and open questions.
- ``fra_market_label_resolution.csv``: how every financier label in the market
  discovery CSV resolves to FRA licences.  A failed name search is reported as
  ``not_found_by_name``, never as "no FRA match".
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.acquisition.egypt_financial.fra_entities import (  # noqa: E402
    ENTITY_FIELDS,
    build_entity_rows,
    load_csv,
    resolve_brand,
    write_csv,
)

# Pilot scope accepted 2026-10-02: the original five plus B.TECH/Mylo and
# Drive/Forsa, with the two seller-financier contrast registrations.
PILOT_KEYS = (
    "fra:consumer_finance:13",  # valU (established financier)
    "fra:consumer_finance:1",  # Contact
    "fra:consumer_finance:33",  # Contact Credit Tech
    "fra:consumer_finance:10",  # Souhoola
    "fra:consumer_finance:43",  # Aman
    "fra:consumer_finance_providers:2",  # Aman Financial Services (contrast)
    "fra:consumer_finance:23",  # Halan
    "fra:consumer_finance:48",  # B.TECH Finance / Mylo
    "fra:consumer_finance_providers:7",  # B.TECH Trading & Distribution (contrast)
    "fra:consumer_finance:26",  # Drive Finance / Forsa
)

RESOLUTION_FIELDS = ["market_label", "outcome", "licence_keys", "link_statuses", "note"]


def market_bank_labels(market_csv: Path) -> set[str]:
    """Labels the market CSV itself records as banks (CBE-supervised, not FRA)."""
    return {row["entity"] for row in load_csv(market_csv) if row.get("role") == "bank"}


def market_financier_labels(market_csv: Path) -> list[str]:
    labels: list[str] = []
    for row in load_csv(market_csv):
        for label in (row.get("financing_entity") or "").split("|"):
            label = label.strip()
            if label and label not in labels:
                labels.append(label)
    return labels


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--licences", type=Path, nargs="+", required=True,
                        help="licence-level FRA CSVs, newest first")
    parser.add_argument("--brand-links", type=Path,
                        default=PROJECT_ROOT / "data/source_registry/fra_brand_links.csv")
    parser.add_argument("--market", type=Path,
                        default=PROJECT_ROOT / "data/source_registry/egypt_installment_market.csv")
    parser.add_argument("--islamic", type=Path,
                        default=PROJECT_ROOT / "data/source_registry/fra_islamic_product_licences.csv",
                        help="FRA register of Islamic-product licences (optional)")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "data/source_registry")
    args = parser.parse_args(argv)

    licence_rows = [row for path in args.licences for row in load_csv(path)]
    links = load_csv(args.brand_links)

    resolutions = []
    labels_by_key: dict[str, set[str]] = defaultdict(set)
    banks = market_bank_labels(args.market)
    for label in market_financier_labels(args.market):
        if label in banks:
            resolutions.append(
                {
                    "market_label": label,
                    "outcome": "bank_outside_fra_register",
                    "licence_keys": "",
                    "link_statuses": "",
                    "note": "bank instalment programme; CBE-supervised, not in the FRA financing register",
                }
            )
            continue
        result = resolve_brand(label, licence_rows, links)
        resolutions.append(
            {
                "market_label": label,
                "outcome": result.outcome,
                "licence_keys": " | ".join(result.licence_keys),
                "link_statuses": " | ".join(result.link_statuses),
                "note": result.note,
            }
        )
        for key in result.licence_keys:
            labels_by_key[key].add(label)

    entities = build_entity_rows(
        licence_rows, links, market_labels=labels_by_key, pilot_keys=PILOT_KEYS
    )
    if args.islamic.exists():
        islamic = {row["licence_key"]: row for row in load_csv(args.islamic)}
        for entity in entities:
            listed = islamic.get(entity["licence_key"])
            if listed:
                note = f" ({listed['fra_note']})" if listed.get("fra_note") else ""
                entity["fra_islamic_products"] = (
                    f"{listed['products_en']} since {listed['islamic_product_date']}{note}"
                )
    write_csv(args.output_dir / "fra_consumer_finance_entities.csv", ENTITY_FIELDS, entities)
    write_csv(args.output_dir / "fra_market_label_resolution.csv", RESOLUTION_FIELDS, resolutions)

    by_type: dict[str, int] = defaultdict(int)
    by_status: dict[str, int] = defaultdict(int)
    for entity in entities:
        by_type[entity["fra_register_type"]] += 1
        by_status[entity["brand_link_status"]] += 1
    print(f"entities: {len(entities)} {dict(by_type)}")
    print(f"brand link status: {dict(by_status)}")
    print(f"pilot rows: {sum(entity['pilot'] == 'yes' for entity in entities)}")
    for row in resolutions:
        print(f"  {row['market_label']!r:>16} -> {row['outcome']}: {row['licence_keys']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
