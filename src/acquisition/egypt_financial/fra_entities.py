"""FRA-first entity table: one row per consumer-scope FRA licence.

The FRA register is the spine.  Brands, websites and market labels hang off a
licence only through an explicit, evidenced link (``fra_brand_links.csv``) or a
verbatim register-name match.  Market brands are not legal names, so a failed
name search is reported as ``not_found_by_name`` together with any evidenced
candidate links, never as "no FRA match".

Nothing here classifies a financing arrangement or creates a Sharia ruling.
"""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from src.acquisition.egypt_financial.fra_registry import (
    FRA_REGISTER_ROLES,
    NO_DATA,
    Activity,
    licence_key,
    split_fra_name,
)


CONSUMER_SCOPE_TYPES = ("consumer_finance", "consumer_finance_providers")

ENTITY_FIELDS = [
    "licence_key",
    "fra_register_type",
    "fra_register_role",
    "fra_islamic_products",
    "licence_number",
    "company_number",
    "name_ar_observed",
    "name_ar_current",
    "former_names_ar",
    "latin_text_in_name_ar",
    "name_en_observed",
    "licence_date",
    "address",
    "other_licences_same_company",
    "brands",
    "brand_link_status",
    "website_url",
    "corporate_contact",
    "market_db_labels",
    "pilot",
    "evidence_urls",
    "fra_detail_url",
    "fra_captured_on",
    "open_questions",
]

BRAND_LINK_FIELDS = [
    "brand",
    "brand_script",
    "licence_key",
    "relation",
    "link_basis",
    "status",
    "website_url",
    "corporate_contact",
    "evidence_url",
    "observed_text",
    "checked_on",
    "note",
]

# Ordered from strongest to weakest.  "established" requires first-party or
# regulator evidence naming the licensee; "lead" is a third-party or inferred link.
LINK_STATUS_ORDER = ("established", "verified", "lead", "unresolved")


@dataclass(frozen=True)
class BrandResolution:
    brand: str
    outcome: str  # register_name | former_name | evidence_link | not_found_by_name
    licence_keys: tuple[str, ...] = ()
    link_statuses: tuple[str, ...] = ()
    note: str = ""


@dataclass
class _Licence:
    row: dict[str, str]
    current: str = ""
    former: tuple[str, ...] = ()
    keys: set[str] = field(default_factory=set)


def normalize_name(value: str) -> str:
    """Matching key only.  Stored names are always kept verbatim."""
    value = value.casefold()
    value = re.sub(r"[ً-ْـ]", "", value)  # harakat, tatweel
    value = (
        value.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        .replace("ة", "ه").replace("ى", "ي").replace("ڤ", "ف").replace("ﻻ", "لا")
    )
    value = re.sub(r"[^\w؀-ۿ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def latin_segments(name_ar: str) -> tuple[str, ...]:
    """Latin-script runs FRA embeds inside the Arabic name field, verbatim."""
    runs = re.findall(r"[A-Za-z][A-Za-z0-9 .&'\-]*[A-Za-z0-9.]", name_ar)
    return tuple(run.strip() for run in runs if len(run.strip()) > 1)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def row_licence_key(row: dict[str, str]) -> str:
    """Recompute the licence key from the row, so CSVs written before the
    key format settled still join on the same identity."""
    try:
        activities = tuple(
            Activity(item["activity_ar"]) for item in json.loads(row.get("activities_json") or "[]")
        )
    except (ValueError, TypeError, KeyError):
        activities = ()
    return licence_key(activities, row.get("license_number"), row.get("company_number"))


def licence_type(row: dict[str, str]) -> str:
    key = row.get("licence_key", "")
    parts = key.split(":")
    return parts[1] if len(parts) == 3 else "unmapped"


def build_entity_rows(
    licence_rows: Iterable[dict[str, str]],
    brand_links: Iterable[dict[str, str]] = (),
    *,
    market_labels: Optional[dict[str, set[str]]] = None,
    pilot_keys: Iterable[str] = (),
) -> list[dict[str, str]]:
    """Join licence rows (any register) into consumer-scope entity rows."""
    rows = [
        {**row, "licence_key": row_licence_key(row)}
        for row in licence_rows
        if row.get("scrape_status") == "complete"
    ]
    by_key: dict[str, dict[str, str]] = {}
    for row in rows:
        by_key.setdefault(row["licence_key"], row)
    by_company: dict[str, list[str]] = defaultdict(list)
    for key, row in by_key.items():
        number = row.get("company_number", "")
        if number and number != NO_DATA and key not in by_company[number]:
            by_company[number].append(key)
    links_by_key: dict[str, list[dict[str, str]]] = defaultdict(list)
    for link in brand_links:
        links_by_key[link["licence_key"]].append(link)
    pilot = set(pilot_keys)
    labels = market_labels or {}

    entities: list[dict[str, str]] = []
    for key, row in sorted(by_key.items(), key=_sort_key):
        register_type = licence_type(row)
        if register_type not in CONSUMER_SCOPE_TYPES:
            continue
        current, former = split_fra_name(row["company_name_ar"])
        links = links_by_key.get(key, [])
        statuses = [link["status"] for link in links if link.get("status")]
        siblings = [
            other for other in by_company.get(row.get("company_number", ""), []) if other != key
        ]
        entities.append(
            {
                "licence_key": key,
                "fra_register_type": register_type,
                "fra_register_role": FRA_REGISTER_ROLES.get(register_type.replace("_", "-"), ""),
                "licence_number": row.get("license_number", ""),
                "company_number": row.get("company_number", ""),
                "name_ar_observed": row["company_name_ar"],
                "name_ar_current": current,
                "former_names_ar": " | ".join(former),
                "latin_text_in_name_ar": " | ".join(latin_segments(current)),
                "name_en_observed": row.get("company_name_en", ""),
                "licence_date": row.get("license_date", ""),
                "address": row.get("address", ""),
                "other_licences_same_company": " | ".join(sorted(siblings)),
                "brands": " | ".join(_unique(link["brand"] for link in links)),
                "brand_link_status": _strongest(statuses),
                "website_url": " | ".join(_unique(link.get("website_url", "") for link in links)),
                "corporate_contact": " | ".join(
                    _unique(link.get("corporate_contact", "") for link in links)
                ),
                "market_db_labels": " | ".join(sorted(labels.get(key, set()))),
                "pilot": "yes" if key in pilot else "",
                "evidence_urls": " | ".join(_unique(link.get("evidence_url", "") for link in links)),
                "fra_detail_url": row.get("company_detail_url", ""),
                "fra_captured_on": row.get("scraped_at", ""),
                "open_questions": _open_questions(links, register_type),
            }
        )
    return entities


def resolve_brand(
    brand: str,
    licence_rows: Iterable[dict[str, str]],
    brand_links: Iterable[dict[str, str]] = (),
) -> BrandResolution:
    """Resolve a market brand to FRA licences without inventing a match.

    Order: evidenced brand links, verbatim current register names (Arabic, the
    Latin text inside it, and the English field), then former names.  Whole-word
    matching only, so "Aman" does not match inside another word.
    """
    target = normalize_name(brand)
    if not target:
        raise ValueError("brand must contain letters")
    links = [link for link in brand_links if normalize_name(link["brand"]) == target]
    if links:
        ordered = sorted(links, key=lambda link: _status_rank(link.get("status", "")))
        return BrandResolution(
            brand,
            "evidence_link",
            tuple(_unique(link["licence_key"] for link in ordered)),
            tuple(link.get("status", "") for link in ordered),
            "; ".join(_unique(link.get("link_basis", "") for link in ordered)),
        )
    current_hits: list[str] = []
    former_hits: list[str] = []
    pattern = re.compile(rf"(?:^| ){re.escape(target)}(?: |$)")
    for row in licence_rows:
        if row.get("scrape_status") != "complete":
            continue
        row = {**row, "licence_key": row_licence_key(row)}
        current, former = split_fra_name(row["company_name_ar"])
        if any(pattern.search(normalize_name(text)) for text in (current, row.get("company_name_en", ""))):
            current_hits.append(row["licence_key"])
        elif any(pattern.search(normalize_name(text)) for text in former):
            former_hits.append(row["licence_key"])
    if current_hits:
        return BrandResolution(brand, "register_name", tuple(_unique(current_hits)),
                               note="name match is a lead until a first-party document names the licensee")
    if former_hits:
        return BrandResolution(brand, "former_name", tuple(_unique(former_hits)),
                               note="matched an earlier FRA name; confirm the current holder")
    return BrandResolution(
        brand,
        "not_found_by_name",
        note=(
            "brand is not an FRA legal name; search parent/operator names from first-party "
            "terms, app developer, EGX disclosures, and add an evidenced brand link"
        ),
    )


def write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: _excel_safe(str(row.get(name, ""))) for name in fields})


def _open_questions(links: list[dict[str, str]], register_type: str) -> str:
    questions = []
    if not links:
        questions.append("brand/website not yet linked")
    elif not any(link.get("status") in {"established", "verified"} for link in links):
        questions.append("brand link is a lead only")
    if register_type == "consumer_finance_providers":
        questions.append("confirm the provider sells and finances its own goods in the selected arrangement")
    else:
        questions.append("confirm seller vs financier roles per arrangement from the customer agreement")
    return "; ".join(questions)


def _strongest(statuses: list[str]) -> str:
    if not statuses:
        return "unlinked"
    return min(statuses, key=_status_rank)


def _status_rank(status: str) -> int:
    return LINK_STATUS_ORDER.index(status) if status in LINK_STATUS_ORDER else len(LINK_STATUS_ORDER)


def _sort_key(item: tuple[str, dict[str, str]]) -> tuple[str, int, str]:
    key = item[0]
    number = key.rsplit(":", 1)[-1]
    return (licence_type(item[1]), int(number) if number.isdigit() else 10**6, key)


def _unique(values: Iterable[str]) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen


def _excel_safe(value: str) -> str:
    return f"'{value}" if value.startswith(("=", "+", "-", "@")) else value
