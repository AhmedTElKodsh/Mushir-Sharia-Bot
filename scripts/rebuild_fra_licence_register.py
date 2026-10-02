#!/usr/bin/env python3
"""Rebuild a licence-level FRA register CSV from an earlier run's raw captures.

No network request is made.  The original CSV and manifest are left untouched;
output goes to a new directory with its own manifest naming the source run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.acquisition.egypt_financial.fra_registry import (  # noqa: E402
    rebuild_rows_from_capture,
    write_registry_csv,
)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_manifest", type=Path, help="manifest.json of the earlier run")
    parser.add_argument("output_dir", type=Path, help="new directory; must not already exist")
    args = parser.parse_args(argv)
    if args.output_dir.exists():
        parser.error("output directory already exists; earlier rebuilds are never overwritten")
    manifest = json.loads(args.source_manifest.read_text(encoding="utf-8"))
    rows, stats = rebuild_rows_from_capture(manifest)
    args.output_dir.mkdir(parents=True)
    slug = str(manifest.get("fra_type_code", "registry")).replace("-", "_")
    csv_path = args.output_dir / f"fra_{slug}_licences.csv"
    write_registry_csv(csv_path, rows)
    rebuilt = {
        "mode": "fra_offline_licence_rebuild",
        "network_requests": 0,
        "rebuilt_at": datetime.now(timezone.utc).isoformat(),
        "source_manifest": str(args.source_manifest).replace("\\", "/"),
        "source_run_id": manifest.get("run_id"),
        "source_run_date": manifest.get("run_date"),
        "source_csv_row_count": manifest.get("csv_row_count"),
        "source_duplicate_company_number_count": manifest.get("duplicate_company_number_count"),
        "fra_type_code": manifest.get("fra_type_code"),
        "output_csv": str(csv_path).replace("\\", "/"),
        "output_csv_sha256": "sha256:" + hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        **{f"rebuild_{key}": value for key, value in stats.items()},
        "scope_boundary": (
            "Official FRA registry identity facts only; no Sharia compliance decision "
            "or runtime eligibility is created by this export."
        ),
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(rebuilt, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in rebuilt.items() if k.startswith(("rebuild_", "source_csv"))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
