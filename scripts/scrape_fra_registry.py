#!/usr/bin/env python3
"""Export one typed FRA financing-company register to governed runtime artifacts."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import urllib.parse
from datetime import date
from pathlib import Path
from typing import Callable, Optional, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.acquisition.egypt_financial.fra_registry import (
    KNOWN_FRA_TYPE_TITLES,
    USER_AGENT,
    RegistryRunResult,
    scrape_registry,
)


FRA_FINANCING_REGISTER_PATH = (
    "/%d8%b3%d8%ac%d9%84%d8%a7%d8%aa-%d9%84%d8%b4%d8%b1%d9%83%d8%a7%d8%aa-"
    "%d8%a7%d9%84%d8%aa%d9%85%d9%88%d9%8a%d9%84/"
)


def registry_url(fra_type_code: str) -> str:
    query = urllib.parse.urlencode(
        {
            "taxonomy_filter": "all",
            "filtered_type": fra_type_code,
            "description_search": "",
        }
    )
    return f"https://fra.gov.eg{FRA_FINANCING_REGISTER_PATH}?{query}"


def main(
    argv: Optional[Sequence[str]] = None,
    *,
    scrape: Callable[..., RegistryRunResult] = scrape_registry,
) -> int:
    parser = argparse.ArgumentParser(
        description="Export an FRA financing-company type to one-row-per-company CSV."
    )
    parser.add_argument("--fra-type", default="consumer-finance")
    parser.add_argument("--fra-type-ar", default="تمويل استهلاكي")
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument("--start-url", default="")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    parser.add_argument("--max-pages", type=int, default=25)
    parser.add_argument(
        "--user-agent",
        default=USER_AGENT,
        help="Configured crawler identity sent to FRA and used for robots policy.",
    )
    parser.add_argument(
        "--site-terms-review-state",
        required=True,
        choices=("no-separate-terms-found", "reviewed-compatible"),
        help="Record the operator's current review of published FRA site terms.",
    )
    parser.add_argument(
        "--acknowledge-unavailable-robots",
        action="store_true",
        help=(
            "Permit only an unavailable/malformed robots response after human review. "
            "An explicit robots disallow and all security controls still stop the run."
        ),
    )
    args = parser.parse_args(argv)
    try:
        date.fromisoformat(args.today)
    except ValueError as exc:
        parser.error(str(exc))
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.fra_type):
        parser.error("--fra-type must be a nonempty lowercase hyphenated code")
    if not args.fra_type_ar.strip():
        parser.error("--fra-type-ar must not be blank")
    expected_title = KNOWN_FRA_TYPE_TITLES.get(args.fra_type)
    if expected_title and args.fra_type_ar.strip() != expected_title:
        parser.error("--fra-type-ar does not match the selected known FRA type")
    if not math.isfinite(args.timeout_seconds) or args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be a positive finite number")
    if not math.isfinite(args.delay_seconds) or args.delay_seconds < 0:
        parser.error("--delay-seconds must be a nonnegative finite number")
    if args.max_pages <= 0:
        parser.error("--max-pages must be positive")
    if not args.user_agent.strip() or "\r" in args.user_agent or "\n" in args.user_agent:
        parser.error("--user-agent must be nonempty and contain no line breaks")
    start_url = args.start_url or registry_url(args.fra_type)
    parsed_start = urllib.parse.urlparse(start_url)
    start_host = (parsed_start.hostname or "").lower().removeprefix("www.")
    if (
        parsed_start.scheme.lower() != "https"
        or start_host != "fra.gov.eg"
        or parsed_start.username is not None
        or parsed_start.password is not None
        or parsed_start.port not in {None, 443}
    ):
        parser.error("--start-url must be an uncredentialed HTTPS URL on fra.gov.eg")
    if args.start_url:
        expected_path = urllib.parse.unquote(FRA_FINANCING_REGISTER_PATH).rstrip("/")
        actual_path = urllib.parse.unquote(parsed_start.path).rstrip("/")
        filtered_type = dict(
            urllib.parse.parse_qsl(parsed_start.query, keep_blank_values=True)
        ).get("filtered_type")
        if actual_path != expected_path or filtered_type != args.fra_type:
            parser.error("--start-url must target the requested FRA financing register type")
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else PROJECT_ROOT / "data/runtime/artifacts/l6_scrape/fra_registry" / args.today
    )
    result = scrape(
        start_url=start_url,
        fra_type_code=args.fra_type,
        fra_type_ar=args.fra_type_ar,
        run_date=args.today,
        output_dir=output_dir,
        timeout_seconds=args.timeout_seconds,
        delay_seconds=args.delay_seconds,
        max_pages=args.max_pages,
        acknowledge_unavailable_robots=args.acknowledge_unavailable_robots,
        user_agent=args.user_agent,
        site_terms_review_state=args.site_terms_review_state,
    )
    print(f"CSV: {result.csv_path}")
    print(f"Manifest: {result.manifest_path}")
    if result.manifest_path.exists():
        manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        print(f"Status: {manifest.get('status', 'unknown')}")
        print(f"Rows: {manifest.get('csv_row_count', 0)}")
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
