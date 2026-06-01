"""Extract accessible AAOIFI Shari'ah Standards into governed markdown files.

The public AAOIFI Shari'ah compendium currently exposes SS-01 through SS-54
as a single PDF. SS-60 is exposed as a separate official PDF. This script
splits those accessible official sources into per-standard markdown files for
local governed ingestion. It does not fabricate records for unavailable
standards; SS-55 through SS-59 must be acquired through an official/licensed
source before they can become answer evidence.
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

try:
    from pypdf import PdfReader
except ImportError as exc:  # pragma: no cover - operator-facing setup error
    raise SystemExit("pypdf is required: python -m pip install pypdf") from exc


DEFAULT_COMPENDIUM = Path("data/raw/aaoifi_sharia/Shariaa-Standards-ENG.pdf")
DEFAULT_SS60 = Path("data/raw/aaoifi_sharia/AAOIFI-SS-60-Waqf-English.pdf")
DEFAULT_OUTPUT_DIR = Path("data/aaoifi_md")

COMPENDIUM_OFFICIAL_URL = "https://aaoifi.com/shariaa-standards/?lang=en"
SS60_OFFICIAL_URL = (
    "https://aaoifi.com/announcement/"
    "aaoifi-officially-issues-shariah-standard-no-60-waqf/?lang=en"
)


@dataclass(frozen=True)
class StandardRange:
    number: int
    title: str
    start_print_page: int


COMPENDIUM_RANGES: list[StandardRange] = [
    StandardRange(1, "Trading in Currencies", 47),
    StandardRange(2, "Debit Card, Charge Card and Credit Card", 67),
    StandardRange(3, "Procrastinating Debtor", 83),
    StandardRange(4, "Settlement of Debt by Set-Off", 103),
    StandardRange(5, "Guarantees", 119),
    StandardRange(6, "Conversion of a Conventional Bank to an Islamic Bank", 147),
    StandardRange(7, "Hawalah", 171),
    StandardRange(8, "Murabahah", 195),
    StandardRange(9, "Ijarah and Ijarah Muntahia Bittamleek", 233),
    StandardRange(10, "Salam and Parallel Salam", 267),
    StandardRange(11, "Istisna'a and Parallel Istisna'a", 291),
    StandardRange(12, "Sharikah (Musharakah) and Modern Corporations", 321),
    StandardRange(13, "Mudarabah", 365),
    StandardRange(14, "Documentary Credit", 391),
    StandardRange(15, "Ju'alah", 421),
    StandardRange(16, "Commercial Papers", 439),
    StandardRange(17, "Investment Sukuk", 463),
    StandardRange(18, "Possession (Qabd)", 489),
    StandardRange(19, "Loan (Qard)", 513),
    StandardRange(20, "Sale of Commodities in Organized Markets", 535),
    StandardRange(21, "Financial Paper (Shares and Bonds)", 555),
    StandardRange(22, "Concession Contracts", 583),
    StandardRange(23, "Agency and the Act of an Uncommissioned Agent (Fodooli)", 605),
    StandardRange(24, "Syndicated Financing", 629),
    StandardRange(25, "Combination of Contracts", 647),
    StandardRange(26, "Islamic Insurance", 673),
    StandardRange(27, "Indices", 701),
    StandardRange(28, "Banking Services in Islamic Banks", 719),
    StandardRange(29, "Stipulations and Ethics of Fatwa in the Institutional Framework", 733),
    StandardRange(30, "Monetization (Tawarruq)", 753),
    StandardRange(31, "Controls on Gharar in Financial Transactions", 767),
    StandardRange(32, "Arbitration", 789),
    StandardRange(33, "Waqf", 809),
    StandardRange(34, "Hiring of Persons", 839),
    StandardRange(35, "Zakah", 865),
    StandardRange(36, "Impact of Contingent Incidents on Commitments", 905),
    StandardRange(37, "Credit Agreement", 921),
    StandardRange(38, "Online Financial Dealings", 943),
    StandardRange(39, "Mortgage and its Contemporary Applications", 963),
    StandardRange(40, "Distribution of Profit in Mudarabah-Based Investment Accounts", 989),
    StandardRange(41, "Islamic Reinsurance", 1013),
    StandardRange(42, "Financial Rights and How They Are Exercised and Transferred", 1039),
    StandardRange(43, "Insolvency", 1061),
    StandardRange(44, "Obtaining and Deploying Liquidity", 1083),
    StandardRange(45, "Protection of Capital and Investments", 1097),
    StandardRange(46, "Al-Wakalah Bi Al-Istithmar (Investment Agency)", 1115),
    StandardRange(47, "Rules for Calculating Profit in Financial Transactions", 1133),
    StandardRange(48, "Options to Terminate Due to Breach of Trust (Trust-Based Options)", 1145),
    StandardRange(49, "Unilateral and Bilateral Promise", 1159),
    StandardRange(50, "Irrigation Partnership (Musaqat)", 1175),
    StandardRange(51, "Options to Revoke Contracts Due to Incomplete Performance", 1197),
    StandardRange(
        52,
        "Options to Reconsider (Cooling-Off Options, Either-Or Options, and Options to Revoke Due to Non-Payment)",
        1213,
    ),
    StandardRange(53, "'Arboun (Earnest Money)", 1231),
    StandardRange(54, "Revocation of Contracts by Exercise of a Cooling-Off Option", 1245),
]


def slugify(value: str) -> str:
    value = value.replace("'", "")
    value = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return value[:120]


def output_path(output_dir: Path, number: int, title: str) -> Path:
    return output_dir / (
        f"AAOIFI_Standard_{number:02d}_en_AAOIFI_Sharia_Standard_No._{number:02d}_{slugify(title)}.md"
    )


def standard_exists(output_dir: Path, number: int) -> bool:
    return any(output_dir.glob(f"AAOIFI_Standard_{number:02d}_en_*Shari*.md"))


def clean_extracted_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{4,}", "\n\n", text)
    return text.strip()


def markdown_header(number: int, title: str, source_url: str, source_file: Path) -> str:
    return f"""---
document_type: "AAOIFI Shari'ah Standard"
standard_number: "SS-{number:02d}"
title: "{title}"
language: "English"
language_code: "en"
source: "AAOIFI"
official_url: "{source_url}"
source_file: "{source_file.name}"
source_type: "converted_pdf"
extracted_date: "{date.today().isoformat()}"
review_status: "machine_extracted_pending_scholar_review"
---

# AAOIFI Shari'ah Standard No. {number:02d}: {title}

"""


def extract_pages(reader: PdfReader, start_print_page: int, end_print_page: int) -> str:
    # The public compendium's PDF page number is one greater than the printed page number.
    start_index = start_print_page
    end_index = min(end_print_page, len(reader.pages))
    pieces: list[str] = []
    for page_index in range(start_index, end_index):
        page_text = reader.pages[page_index].extract_text() or ""
        if page_text.strip():
            pieces.append(f"\n\n## Source PDF page {page_index + 1}\n\n{page_text}")
    return clean_extracted_text("\n".join(pieces))


def extract_compendium(compendium: Path, output_dir: Path, overwrite: bool = False) -> list[Path]:
    reader = PdfReader(str(compendium))
    created: list[Path] = []
    for index, standard in enumerate(COMPENDIUM_RANGES):
        target = output_path(output_dir, standard.number, standard.title)
        if target.exists() and not overwrite:
            continue
        if standard_exists(output_dir, standard.number) and not overwrite:
            continue
        next_start = (
            COMPENDIUM_RANGES[index + 1].start_print_page
            if index + 1 < len(COMPENDIUM_RANGES)
            else 1259
        )
        text = extract_pages(reader, standard.start_print_page, next_start)
        if not text:
            raise RuntimeError(f"No text extracted for SS-{standard.number:02d}")
        target.write_text(
            markdown_header(standard.number, standard.title, COMPENDIUM_OFFICIAL_URL, compendium)
            + text
            + "\n",
            encoding="utf-8",
        )
        created.append(target)
    return created


def extract_single_pdf(
    pdf_path: Path,
    output_dir: Path,
    number: int,
    title: str,
    source_url: str,
    overwrite: bool = False,
) -> Path | None:
    target = output_path(output_dir, number, title)
    if target.exists() and not overwrite:
        return None
    if standard_exists(output_dir, number) and not overwrite:
        return None
    reader = PdfReader(str(pdf_path))
    pieces = []
    for page_index, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        if page_text.strip():
            pieces.append(f"\n\n## Source PDF page {page_index + 1}\n\n{page_text}")
    text = clean_extracted_text("\n".join(pieces))
    if not text:
        raise RuntimeError(f"No text extracted for SS-{number:02d}")
    target.write_text(
        markdown_header(number, title, source_url, pdf_path) + text + "\n",
        encoding="utf-8",
    )
    return target


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compendium", type=Path, default=DEFAULT_COMPENDIUM)
    parser.add_argument("--ss60", type=Path, default=DEFAULT_SS60)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if not args.compendium.exists():
        raise SystemExit(f"Missing compendium PDF: {args.compendium}")
    created = extract_compendium(args.compendium, args.output_dir, overwrite=args.overwrite)
    ss60 = None
    if args.ss60.exists():
        ss60 = extract_single_pdf(
            args.ss60,
            args.output_dir,
            60,
            "Waqf",
            SS60_OFFICIAL_URL,
            overwrite=args.overwrite,
        )
    print(f"Created {len(created)} compendium markdown files")
    if ss60:
        print(f"Created {ss60}")
    elif args.ss60.exists():
        print("SS-60 markdown already present; skipped")
    else:
        print(f"SS-60 PDF not found: {args.ss60}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
