"""Generate a machine-checked AAOIFI source catalog from the local markdown corpus."""
from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path
from typing import Iterable

import yaml

DEFAULT_CORPUS_DIR = Path("data/aaoifi_md")
DEFAULT_OUTPUT = Path("data/source_registry/aaoifi-source-catalog.yaml")
EXCLUDED_MARKDOWN = {"INDEX.md", "CONVERSION_SUMMARY.md", ".gitkeep"}


def detect_language(path: Path) -> str:
    if "_ar_" in path.name or "_ar." in path.name:
        return "ar"
    if "_en_" in path.name or "_en." in path.name:
        return "en"
    return "unknown"


def source_family_for(path: Path) -> str:
    name = path.name.lower()
    if "shari" in name:
        return "sharia_standard"
    if "governance" in name:
        return "governance"
    if "audit" in name:
        return "auditing"
    return "fas"


def source_id_for(path: Path) -> str:
    match = re.search(r"AAOIFI_Standard_(\d+)_([a-z]{2})_", path.name)
    if not match:
        raise ValueError(f"Cannot derive source_id from {path.name}")
    number, language = match.groups()
    prefix = "ss" if source_family_for(path) == "sharia_standard" else "fas"
    return f"aaoifi-{prefix}-{int(number):02d}-{language}"


def standard_number_for(path: Path) -> str:
    match = re.search(r"AAOIFI_Standard_(\d+)_", path.name)
    if not match:
        return path.stem
    prefix = "SS" if source_family_for(path) == "sharia_standard" else "FAS"
    return f"{prefix}-{int(match.group(1)):02d}"


def title_for(path: Path) -> str:
    stem = path.stem
    match = re.match(r"AAOIFI_Standard_\d+_[a-z]{2}_(.+)", stem)
    raw = match.group(1) if match else stem
    return raw.replace("_", " ").strip()


def catalog_records(corpus_dir: Path) -> Iterable[dict]:
    for path in sorted(corpus_dir.glob("*.md")):
        if path.name in EXCLUDED_MARKDOWN or detect_language(path) not in {"en", "ar"}:
            continue
        family = source_family_for(path)
        standard_number = standard_number_for(path)
        official_page = "shariaa-standards" if family == "sharia_standard" else "accounting-standards-2"
        yield {
            "source_id": source_id_for(path),
            "source_family": family,
            "standard_number": standard_number,
            "title_en": title_for(path),
            "language": detect_language(path),
            "official_url": f"https://aaoifi.com/{official_page}/?lang=en",
            "acquired_at": date.today().isoformat(),
            "extraction_method": "local_markdown_corpus_machine_catalog",
            "source_type": "derived_markdown",
            "currentness": "current",
            "review_status": "machine_checked",
            "source_confidence": "derived_from_official",
            "derived_path": path.as_posix(),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.corpus_dir.exists():
        raise SystemExit(f"Corpus directory not found: {args.corpus_dir}")
    records = list(catalog_records(args.corpus_dir))
    if not records:
        raise SystemExit(f"No AAOIFI markdown files found in {args.corpus_dir}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        yaml.safe_dump({"records": records}, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print(f"Wrote {len(records)} source catalog records to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
